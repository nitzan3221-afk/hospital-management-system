"""Demo data: 3 users (one per role) and 14 patients across 4 wards.

Each patient gets a diagnosis, at least one active medication, two sets of vitals and a
timeline of 6+ events spanning the last three days (admission, doctor visits, prescriptions,
vitals, medication given). Timestamps are relative to "now" so the data always looks fresh.

Runs automatically on startup when the database is empty (``SEED_ON_STARTUP=true``).
Manual reset:  ``python -m app.seed --reset``
"""

import argparse
import asyncio
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.core.security import hash_password
from app.domain.enums import HealthPlan, Role, Sex, TimelineEventType, Ward
from app.domain.models import Medication, Patient, TimelineEvent, User, VitalSigns, utcnow
from app.repositories.base import PatientRepository, UserRepository

logger = logging.getLogger(__name__)

DEMO_PASSWORD = "password123"

DOCTOR = "dr_house"
NURSE = "nurse_joy"
SECRETARY = "pam_beesly"


def build_users() -> list[User]:
    password_hash = hash_password(DEMO_PASSWORD)
    return [
        User(username=DOCTOR, full_name="Dr. Gregory House", role=Role.DOCTOR, password_hash=password_hash),
        User(username=NURSE, full_name="Nurse Joy", role=Role.NURSE, password_hash=password_hash),
        User(username=SECRETARY, full_name="Pam Beesly", role=Role.SECRETARY, password_hash=password_hash),
    ]


@dataclass(frozen=True)
class _PatientSpec:
    id: str
    first_name: str
    last_name: str
    sex: Sex
    birth_date: date
    health_plan: HealthPlan
    ward: Ward
    diagnosis: str
    medications: list[tuple[str, str, str]]  # (name, dose, frequency)
    vitals: tuple[int, int, int, float]  # (heart rate, systolic, diastolic, temperature)


_M, _F = Sex.MALE, Sex.FEMALE
_CLALIT, _MACCABI, _MEUHEDET, _LEUMIT = HealthPlan.CLALIT, HealthPlan.MACCABI, HealthPlan.MEUHEDET, HealthPlan.LEUMIT

_PATIENTS: list[_PatientSpec] = [
    # --- Emergency (ER) ---
    _PatientSpec("301234567", "David", "Cohen", _M, date(1968, 3, 14), _CLALIT, Ward.ER,
                 "Acute chest pain — rule out MI", [("Aspirin", "100 mg", "once daily")], (98, 145, 92, 37.1)),
    _PatientSpec("302345678", "Noa", "Levi", _F, date(1991, 7, 2), _MACCABI, Ward.ER,
                 "Fractured left wrist", [("Tramadol", "50 mg", "every 6 hours as needed")], (84, 122, 78, 36.8)),
    _PatientSpec("303456789", "Yossi", "Mizrahi", _M, date(1979, 11, 23), _MEUHEDET, Ward.ER,
                 "Severe dehydration", [("Normal saline IV", "1 L", "every 8 hours")], (110, 105, 65, 37.6)),
    _PatientSpec("304567890", "Maya", "Peretz", _F, date(2001, 1, 9), _LEUMIT, Ward.ER,
                 "Allergic reaction", [("Prednisone", "40 mg", "once daily"), ("Cetirizine", "10 mg", "once daily")],
                 (92, 118, 76, 37.0)),
    # --- Internal Medicine A ---
    _PatientSpec("305678901", "Avraham", "Biton", _M, date(1950, 5, 30), _CLALIT, Ward.INTERNAL_A,
                 "Community-acquired pneumonia", [("Ceftriaxone", "1 g", "once daily IV")], (88, 132, 84, 38.2)),
    _PatientSpec("306789012", "Rivka", "Friedman", _F, date(1945, 9, 17), _MACCABI, Ward.INTERNAL_A,
                 "Congestive heart failure exacerbation", [("Furosemide", "40 mg", "twice daily")],
                 (76, 138, 86, 36.7)),
    _PatientSpec("307890123", "Moshe", "Azoulay", _M, date(1962, 12, 5), _MEUHEDET, Ward.INTERNAL_A,
                 "Uncontrolled type 2 diabetes", [("Insulin glargine", "20 units", "once nightly"),
                                                  ("Metformin", "850 mg", "twice daily")], (80, 128, 82, 36.9)),
    _PatientSpec("308901234", "Tamar", "Shapiro", _F, date(1974, 4, 21), _CLALIT, Ward.INTERNAL_A,
                 "Urinary tract infection", [("Ciprofloxacin", "500 mg", "twice daily")], (90, 120, 75, 37.9)),
    # --- ICU ---
    _PatientSpec("309012345", "Eli", "Dahan", _M, date(1958, 8, 11), _LEUMIT, Ward.ICU,
                 "Septic shock", [("Norepinephrine", "0.1 mcg/kg/min", "continuous infusion"),
                                  ("Meropenem", "1 g", "every 8 hours")], (118, 95, 58, 38.9)),
    _PatientSpec("310123456", "Shira", "Katz", _F, date(1983, 2, 27), _MACCABI, Ward.ICU,
                 "Post-op monitoring after cardiac surgery", [("Heparin", "5000 units", "every 12 hours")],
                 (86, 112, 70, 37.3)),
    _PatientSpec("311234567", "Itzik", "Malka", _M, date(1970, 6, 3), _CLALIT, Ward.ICU,
                 "Acute respiratory failure", [("Propofol", "20 mcg/kg/min", "continuous infusion")],
                 (104, 108, 66, 37.8)),
    # --- Pediatrics ---
    _PatientSpec("312345678", "Lior", "Ben-David", _M, date(2018, 10, 15), _MEUHEDET, Ward.PEDIATRICS,
                 "Acute bronchiolitis", [("Salbutamol inhaler", "2 puffs", "every 4 hours")], (122, 100, 62, 37.7)),
    _PatientSpec("313456789", "Yael", "Avraham", _F, date(2015, 3, 8), _CLALIT, Ward.PEDIATRICS,
                 "Appendicitis — post appendectomy", [("Paracetamol", "15 mg/kg", "every 6 hours")],
                 (100, 104, 64, 37.4)),
    _PatientSpec("314567890", "Omer", "Gabay", _M, date(2020, 12, 1), _MACCABI, Ward.PEDIATRICS,
                 "Febrile seizure", [("Ibuprofen", "10 mg/kg", "every 8 hours")], (128, 98, 60, 38.4)),
]


def _vitals_summary(v: VitalSigns) -> str:
    return f"Vitals: HR {v.heart_rate}, BP {v.bp_systolic}/{v.bp_diastolic}, {v.temperature:.1f}°C"


def _build_patient(spec: _PatientSpec, index: int, now: datetime) -> Patient:
    admitted_at = now - timedelta(days=3, hours=index)
    hr, sys_bp, dia_bp, temp = spec.vitals
    timeline: list[TimelineEvent] = [
        TimelineEvent(type=TimelineEventType.ADMITTED, at=admitted_at, by=SECRETARY,
                      summary=f"Admitted to {spec.ward.display_name}", details={"ward": spec.ward.value}),
        TimelineEvent(type=TimelineEventType.DOCTOR_VISIT, at=admitted_at + timedelta(hours=1), by=DOCTOR,
                      summary=f"Initial assessment: {spec.diagnosis}", details={"diagnosis": spec.diagnosis}),
    ]

    # Prescriptions (2 hours after admission)
    medications: list[Medication] = []
    for name, dose, frequency in spec.medications:
        med = Medication(name=name, dose=dose, frequency=frequency, prescribed_by=DOCTOR,
                         prescribed_at=admitted_at + timedelta(hours=2))
        medications.append(med)
        timeline.append(TimelineEvent(type=TimelineEventType.MEDICATION_PRESCRIBED, at=med.prescribed_at, by=DOCTOR,
                                      summary=f"Prescribed {name} {dose}, {frequency}",
                                      details={"medication_id": med.id, "name": name}))

    # Day 2: first vitals + first dose given
    first_vitals = VitalSigns(heart_rate=hr + 6, bp_systolic=sys_bp + 8, bp_diastolic=dia_bp + 4,
                              temperature=round(temp + 0.4, 1), recorded_at=admitted_at + timedelta(days=1),
                              recorded_by=NURSE)
    timeline.append(TimelineEvent(type=TimelineEventType.VITALS_RECORDED, at=first_vitals.recorded_at, by=NURSE,
                                  summary=_vitals_summary(first_vitals)))

    first_med = medications[0]
    given_at = admitted_at + timedelta(days=1, hours=2)
    first_med.last_given_at, first_med.last_given_by = given_at, NURSE
    timeline.append(TimelineEvent(type=TimelineEventType.MEDICATION_GIVEN, at=given_at, by=NURSE,
                                  summary=f"Gave {first_med.name} {first_med.dose}",
                                  details={"medication_id": first_med.id, "name": first_med.name}))

    # Day 3: doctor follow-up; then the most recent vitals a few hours ago
    timeline.append(TimelineEvent(type=TimelineEventType.DOCTOR_VISIT, at=admitted_at + timedelta(days=2), by=DOCTOR,
                                  summary="Follow-up visit: condition monitored, treatment continued"))
    latest_vitals = VitalSigns(heart_rate=hr, bp_systolic=sys_bp, bp_diastolic=dia_bp, temperature=temp,
                               recorded_at=now - timedelta(hours=1 + index % 5), recorded_by=NURSE)
    timeline.append(TimelineEvent(type=TimelineEventType.VITALS_RECORDED, at=latest_vitals.recorded_at, by=NURSE,
                                  summary=_vitals_summary(latest_vitals)))

    return Patient(
        id=spec.id,
        first_name=spec.first_name,
        last_name=spec.last_name,
        sex=spec.sex,
        birth_date=spec.birth_date,
        health_plan=spec.health_plan,
        ward=spec.ward,
        diagnosis=spec.diagnosis,
        admitted_at=admitted_at,
        updated_at=latest_vitals.recorded_at,
        medications=medications,
        vitals=[first_vitals, latest_vitals],
        timeline=sorted(timeline, key=lambda e: e.at),
    )


def build_patients(now: datetime | None = None) -> list[Patient]:
    now = now or utcnow()
    return [_build_patient(spec, i, now) for i, spec in enumerate(_PATIENTS)]


async def seed_database(patients: PatientRepository, users: UserRepository) -> bool:
    """Insert demo data if there are no users yet. Returns True if data was inserted."""
    if await users.count() > 0:
        logger.info("Seed skipped: database already contains data")
        return False

    for user in build_users():
        await users.create(user)
    demo_patients = build_patients()
    for patient in demo_patients:
        await patients.create(patient)

    logger.info("Seeded database", extra={"users": 3, "patients": len(demo_patients)})
    return True


async def _main(reset: bool) -> None:
    from app.core.config import get_settings
    from app.core.database import MongoDatabase
    from app.repositories.mongo_patient_repository import MongoPatientRepository
    from app.repositories.mongo_user_repository import MongoUserRepository

    settings = get_settings()
    database = MongoDatabase(settings.mongo_uri, settings.mongo_db)
    try:
        if reset:
            await database.db.drop_collection("patients")
            await database.db.drop_collection("users")
            logger.info("Dropped existing collections")
        patient_repo = MongoPatientRepository(database.db)
        await patient_repo.ensure_indexes()
        await seed_database(patient_repo, MongoUserRepository(database.db))
    finally:
        await database.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Seed the hospital database with demo data")
    parser.add_argument("--reset", action="store_true", help="drop existing patients and users first")
    asyncio.run(_main(parser.parse_args().reset))
