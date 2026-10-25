"""Patient business logic.

Responsibilities: enforce business rules (e.g. only an active medication can be given),
build timeline events for every action, and write the audit log. Permission checks happen
before this layer (in the API), so every method here receives an already-authorized actor.
"""

from collections.abc import Callable
from datetime import datetime

from app.core.audit import audit
from app.domain.enums import TimelineEventType
from app.domain.errors import InvalidOperationError, NotFoundError
from app.domain.models import (
    AuthenticatedUser,
    Medication,
    MedicationCreate,
    Patient,
    PatientCreate,
    PatientUpdate,
    TimelineEvent,
    VitalsCreate,
    VitalSigns,
    WardGroup,
    utcnow,
)
from app.repositories.base import PatientRepository


class PatientService:
    def __init__(self, patients: PatientRepository, clock: Callable[[], datetime] = utcnow) -> None:
        self._patients = patients
        self._clock = clock  # injectable for deterministic tests

    # ------------------------------------------------------------------ queries

    async def list_by_ward(self) -> list[WardGroup]:
        return await self._patients.list_grouped_by_ward()

    async def get(self, patient_id: str) -> Patient:
        """Return the patient with the timeline in chronological order (oldest first)."""
        patient = await self._patients.get(patient_id)
        if patient is None:
            raise NotFoundError(f"Patient {patient_id} not found")
        patient.timeline.sort(key=lambda e: e.at)
        return patient

    # ------------------------------------------------------------------ patient management

    async def create(self, data: PatientCreate, actor: AuthenticatedUser) -> Patient:
        now = self._clock()
        patient = Patient(
            **data.model_dump(),
            admitted_at=now,
            updated_at=now,
            timeline=[
                TimelineEvent(
                    type=TimelineEventType.ADMITTED,
                    at=now,
                    by=actor.username,
                    summary=f"Admitted to {data.ward.display_name} — {data.diagnosis}",
                    details={"ward": data.ward.value, "diagnosis": data.diagnosis},
                )
            ],
        )
        await self._patients.create(patient)
        audit("patient_created", actor=actor.username, role=actor.role.value, patient_id=patient.id)
        return patient

    async def update_info(self, patient_id: str, data: PatientUpdate, actor: AuthenticatedUser) -> Patient:
        changes = data.model_dump(exclude_unset=True, exclude_none=True)
        if not changes:
            raise InvalidOperationError("No fields to update")

        summary = f"Details updated: {', '.join(sorted(changes))}"
        if "ward" in changes:
            summary = f"Moved to {changes['ward'].display_name}. " + summary
        event = self._event(TimelineEventType.PATIENT_UPDATED, actor, summary, {"fields": sorted(changes)})

        stored = {key: getattr(value, "value", value) for key, value in changes.items()}  # enums -> str
        if not await self._patients.update_fields(patient_id, stored, event):
            raise NotFoundError(f"Patient {patient_id} not found")
        audit("patient_updated", actor=actor.username, role=actor.role.value, patient_id=patient_id,
              fields=sorted(changes))
        return await self.get(patient_id)

    async def delete(self, patient_id: str, actor: AuthenticatedUser) -> None:
        if not await self._patients.delete(patient_id):
            raise NotFoundError(f"Patient {patient_id} not found")
        audit("patient_deleted", actor=actor.username, role=actor.role.value, patient_id=patient_id)

    # ------------------------------------------------------------------ clinical actions

    async def change_diagnosis(self, patient_id: str, diagnosis: str, actor: AuthenticatedUser) -> Patient:
        patient = await self.get(patient_id)
        diagnosis = diagnosis.strip()
        if diagnosis == patient.diagnosis:
            raise InvalidOperationError("New diagnosis is the same as the current one")

        event = self._event(
            TimelineEventType.DIAGNOSIS_CHANGED, actor,
            f"Diagnosis changed to: {diagnosis}",
            {"previous": patient.diagnosis, "new": diagnosis},
        )
        await self._patients.update_fields(patient_id, {"diagnosis": diagnosis}, event)
        audit("diagnosis_changed", actor=actor.username, role=actor.role.value, patient_id=patient_id)
        return await self.get(patient_id)

    async def prescribe(self, patient_id: str, data: MedicationCreate, actor: AuthenticatedUser) -> Patient:
        now = self._clock()
        medication = Medication(**data.model_dump(), prescribed_by=actor.username, prescribed_at=now)
        event = self._event(
            TimelineEventType.MEDICATION_PRESCRIBED, actor,
            f"Prescribed {medication.name} {medication.dose}, {medication.frequency}",
            {"medication_id": medication.id, "name": medication.name, "dose": medication.dose},
            at=now,
        )
        if not await self._patients.add_medication(patient_id, medication, event):
            raise NotFoundError(f"Patient {patient_id} not found")
        audit("medication_prescribed", actor=actor.username, role=actor.role.value, patient_id=patient_id,
              medication_id=medication.id, medication=medication.name, dose=medication.dose)
        return await self.get(patient_id)

    async def give_medication(self, patient_id: str, medication_id: str, actor: AuthenticatedUser) -> Patient:
        patient = await self.get(patient_id)
        medication = patient.find_medication(medication_id)
        if medication is None:
            raise NotFoundError(f"Medication {medication_id} not found for patient {patient_id}")
        if not medication.active:
            raise InvalidOperationError(f"Medication {medication.name} is not active")

        now = self._clock()
        event = self._event(
            TimelineEventType.MEDICATION_GIVEN, actor,
            f"Gave {medication.name} {medication.dose}",
            {"medication_id": medication.id, "name": medication.name},
            at=now,
        )
        # The repository re-checks "active" inside the same atomic update (guards against races).
        if not await self._patients.mark_medication_given(patient_id, medication_id, now, actor.username, event):
            raise InvalidOperationError(f"Medication {medication.name} is no longer active")
        audit("medication_given", actor=actor.username, role=actor.role.value, patient_id=patient_id,
              medication_id=medication_id, medication=medication.name)
        return await self.get(patient_id)

    async def record_vitals(self, patient_id: str, data: VitalsCreate, actor: AuthenticatedUser) -> Patient:
        now = self._clock()
        vitals = VitalSigns(**data.model_dump(), recorded_at=now, recorded_by=actor.username)
        event = self._event(
            TimelineEventType.VITALS_RECORDED, actor,
            f"Vitals: HR {vitals.heart_rate}, BP {vitals.bp_systolic}/{vitals.bp_diastolic}, "
            f"{vitals.temperature:.1f}°C",
            data.model_dump(),
            at=now,
        )
        if not await self._patients.add_vitals(patient_id, vitals, event):
            raise NotFoundError(f"Patient {patient_id} not found")
        audit("vitals_recorded", actor=actor.username, role=actor.role.value, patient_id=patient_id,
              **data.model_dump())
        return await self.get(patient_id)

    # ------------------------------------------------------------------ helpers

    def _event(
        self,
        event_type: TimelineEventType,
        actor: AuthenticatedUser,
        summary: str,
        details: dict | None = None,
        at: datetime | None = None,
    ) -> TimelineEvent:
        return TimelineEvent(
            type=event_type, at=at or self._clock(), by=actor.username, summary=summary, details=details or {}
        )
