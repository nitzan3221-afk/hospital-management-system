"""Shared test fixtures. Tests run against in-memory repositories — no database needed."""

import logging

import pytest

from app.domain.enums import Role
from app.domain.models import AuthenticatedUser, Patient
from app.seed import build_patients
from app.services.patient_service import PatientService
from tests.fakes import InMemoryPatientRepository

DOCTOR = AuthenticatedUser(username="dr_house", full_name="Dr. Gregory House", role=Role.DOCTOR)
NURSE = AuthenticatedUser(username="nurse_joy", full_name="Nurse Joy", role=Role.NURSE)
SECRETARY = AuthenticatedUser(username="pam_beesly", full_name="Pam Beesly", role=Role.SECRETARY)


@pytest.fixture
def seeded_patients() -> list[Patient]:
    return build_patients()


@pytest.fixture
def patient_repo(seeded_patients: list[Patient]) -> InMemoryPatientRepository:
    return InMemoryPatientRepository(seeded_patients)


@pytest.fixture
def patient_service(patient_repo: InMemoryPatientRepository) -> PatientService:
    return PatientService(patient_repo)


class AuditCapture(logging.Handler):
    """Collects records written to the audit logger."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)

    def events(self) -> list[tuple[str, str]]:
        return [(r.event, r.outcome) for r in self.records]


@pytest.fixture
def audit_log():
    handler = AuditCapture()
    logger = logging.getLogger("hospital.audit")
    previous_level = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    yield handler
    logger.removeHandler(handler)
    logger.setLevel(previous_level)
