"""Business rules of PatientService."""

from datetime import date

import pytest

from app.domain.enums import HealthPlan, Sex, TimelineEventType, Ward
from app.domain.errors import AlreadyExistsError, InvalidOperationError, NotFoundError
from app.domain.models import MedicationCreate, PatientCreate, PatientUpdate, VitalsCreate
from app.services.patient_service import PatientService
from tests.conftest import DOCTOR, NURSE, SECRETARY
from tests.fakes import InMemoryPatientRepository

PATIENT_ID = "301234567"  # David Cohen, seeded in the ER


def _new_patient(**overrides) -> PatientCreate:
    data = dict(id="123456789", first_name="Dana", last_name="Levi", sex=Sex.FEMALE,
                birth_date=date(1985, 4, 12), health_plan=HealthPlan.CLALIT, ward=Ward.SURGERY,
                diagnosis="Observation after fall")
    return PatientCreate(**{**data, **overrides})


async def test_give_medication_marks_dose_and_adds_timeline_event(patient_service: PatientService, audit_log) -> None:
    patient = await patient_service.get(PATIENT_ID)
    medication = patient.medications[0]
    events_before = len(patient.timeline)

    updated = await patient_service.give_medication(PATIENT_ID, medication.id, NURSE)

    given = updated.find_medication(medication.id)
    assert given.last_given_by == "nurse_joy"
    assert given.last_given_at is not None
    assert len(updated.timeline) == events_before + 1
    last_event = updated.timeline[-1]
    assert last_event.type == TimelineEventType.MEDICATION_GIVEN
    assert last_event.details["medication_id"] == medication.id
    assert ("medication_given", "success") in audit_log.events()


async def test_cannot_give_inactive_medication(patient_repo: InMemoryPatientRepository) -> None:
    patient = await patient_repo.get(PATIENT_ID)
    patient.medications[0].active = False
    service = PatientService(InMemoryPatientRepository([patient]))

    with pytest.raises(InvalidOperationError):
        await service.give_medication(PATIENT_ID, patient.medications[0].id, NURSE)

    unchanged = await service.get(PATIENT_ID)
    assert len(unchanged.timeline) == len(patient.timeline)  # nothing recorded


async def test_give_unknown_medication_is_not_found(patient_service: PatientService) -> None:
    with pytest.raises(NotFoundError):
        await patient_service.give_medication(PATIENT_ID, "no-such-medication", NURSE)


async def test_timeline_is_chronological_after_new_actions(patient_service: PatientService) -> None:
    await patient_service.prescribe(PATIENT_ID, MedicationCreate(name="Omeprazole", dose="20 mg",
                                                                 frequency="once daily"), DOCTOR)
    patient = await patient_service.record_vitals(
        PATIENT_ID, VitalsCreate(heart_rate=80, bp_systolic=125, bp_diastolic=82, temperature=36.9), NURSE
    )

    times = [event.at for event in patient.timeline]
    assert times == sorted(times)
    assert patient.timeline[-1].type == TimelineEventType.VITALS_RECORDED
    assert patient.latest_vitals.heart_rate == 80


async def test_create_patient_records_admission_and_rejects_duplicate_id(patient_service: PatientService) -> None:
    created = await patient_service.create(_new_patient(), SECRETARY)

    assert created.timeline[0].type == TimelineEventType.ADMITTED
    assert created.timeline[0].by == "pam_beesly"
    with pytest.raises(AlreadyExistsError):
        await patient_service.create(_new_patient(first_name="Other"), SECRETARY)


async def test_change_diagnosis_keeps_previous_value_in_timeline(patient_service: PatientService) -> None:
    before = await patient_service.get(PATIENT_ID)

    after = await patient_service.change_diagnosis(PATIENT_ID, "Unstable angina", DOCTOR)

    assert after.diagnosis == "Unstable angina"
    assert after.timeline[-1].details == {"previous": before.diagnosis, "new": "Unstable angina"}
    with pytest.raises(InvalidOperationError):
        await patient_service.change_diagnosis(PATIENT_ID, "Unstable angina", DOCTOR)


async def test_update_with_no_fields_is_rejected(patient_service: PatientService) -> None:
    with pytest.raises(InvalidOperationError):
        await patient_service.update_info(PATIENT_ID, PatientUpdate(), SECRETARY)


async def test_list_groups_patients_by_ward(patient_service: PatientService, seeded_patients) -> None:
    groups = await patient_service.list_by_ward()

    assert sum(len(g.patients) for g in groups) == len(seeded_patients)
    for group in groups:
        assert all(p.ward == group.ward for p in group.patients)
