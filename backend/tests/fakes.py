"""In-memory implementations of the repository interfaces, for unit tests.

They honour the same contracts as the MongoDB repositories (e.g. ``mark_medication_given``
only matches an *active* medication), so the services can be tested without a database.
"""

from datetime import datetime
from typing import Any

from app.domain.enums import Ward
from app.domain.errors import AlreadyExistsError
from app.domain.models import (
    Medication,
    Patient,
    PatientSummary,
    TimelineEvent,
    User,
    VitalSigns,
    WardGroup,
)


class InMemoryPatientRepository:
    def __init__(self, patients: list[Patient] | None = None) -> None:
        self._patients: dict[str, Patient] = {p.id: p.model_copy(deep=True) for p in patients or []}

    async def list_grouped_by_ward(self) -> list[WardGroup]:
        groups: list[WardGroup] = []
        for ward in Ward:
            members = sorted(
                (p for p in self._patients.values() if p.ward == ward),
                key=lambda p: (p.last_name, p.first_name),
            )
            if members:
                groups.append(WardGroup(ward=ward, ward_name=ward.display_name, patients=[
                    PatientSummary(
                        id=p.id, full_name=p.full_name, sex=p.sex, age=p.age, ward=p.ward,
                        health_plan=p.health_plan, diagnosis=p.diagnosis,
                        last_vitals_at=p.latest_vitals.recorded_at if p.latest_vitals else None,
                        active_medications=sum(m.active for m in p.medications),
                    )
                    for p in members
                ]))
        return groups

    async def get(self, patient_id: str) -> Patient | None:
        patient = self._patients.get(patient_id)
        return patient.model_copy(deep=True) if patient else None

    async def create(self, patient: Patient) -> None:
        if patient.id in self._patients:
            raise AlreadyExistsError(f"Patient {patient.id} already exists")
        self._patients[patient.id] = patient.model_copy(deep=True)

    async def update_fields(self, patient_id: str, fields: dict[str, Any], event: TimelineEvent) -> bool:
        patient = self._patients.get(patient_id)
        if patient is None:
            return False
        data = patient.model_dump()
        data.update(fields)
        data["updated_at"] = event.at
        updated = Patient.model_validate(data)
        updated.timeline.append(event)
        self._patients[patient_id] = updated
        return True

    async def delete(self, patient_id: str) -> bool:
        return self._patients.pop(patient_id, None) is not None

    async def add_medication(self, patient_id: str, medication: Medication, event: TimelineEvent) -> bool:
        patient = self._patients.get(patient_id)
        if patient is None:
            return False
        patient.medications.append(medication)
        patient.timeline.append(event)
        return True

    async def mark_medication_given(
        self, patient_id: str, medication_id: str, given_at: datetime, given_by: str, event: TimelineEvent
    ) -> bool:
        patient = self._patients.get(patient_id)
        medication = patient.find_medication(medication_id) if patient else None
        if medication is None or not medication.active:
            return False
        medication.last_given_at, medication.last_given_by = given_at, given_by
        patient.timeline.append(event)
        return True

    async def add_vitals(self, patient_id: str, vitals: VitalSigns, event: TimelineEvent) -> bool:
        patient = self._patients.get(patient_id)
        if patient is None:
            return False
        patient.vitals.append(vitals)
        patient.timeline.append(event)
        return True


class InMemoryUserRepository:
    def __init__(self, users: list[User] | None = None) -> None:
        self._users = {u.username: u for u in users or []}

    async def get_by_username(self, username: str) -> User | None:
        return self._users.get(username)

    async def create(self, user: User) -> None:
        if user.username in self._users:
            raise AlreadyExistsError(f"User {user.username} already exists")
        self._users[user.username] = user

    async def count(self) -> int:
        return len(self._users)
