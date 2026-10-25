"""Input validation rules on domain input models."""

from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from app.domain.enums import HealthPlan, Sex, Ward
from app.domain.models import PatientCreate, VitalsCreate, calculate_age


@pytest.mark.parametrize(
    "vitals",
    [
        dict(heart_rate=80, bp_systolic=80, bp_diastolic=90, temperature=36.8),  # systolic <= diastolic
        dict(heart_rate=80, bp_systolic=120, bp_diastolic=80, temperature=80.0),  # impossible temperature
        dict(heart_rate=0, bp_systolic=120, bp_diastolic=80, temperature=36.8),  # impossible heart rate
    ],
)
def test_invalid_vitals_are_rejected(vitals: dict) -> None:
    with pytest.raises(ValidationError):
        VitalsCreate(**vitals)


@pytest.mark.parametrize("bad_id", ["12345", "12345678a", "1234567890"])
def test_patient_id_must_be_nine_digits(bad_id: str) -> None:
    with pytest.raises(ValidationError):
        PatientCreate(id=bad_id, first_name="A", last_name="B", sex=Sex.MALE, birth_date=date(1990, 1, 1),
                      health_plan=HealthPlan.CLALIT, ward=Ward.ER, diagnosis="X")


def test_birth_date_cannot_be_in_future() -> None:
    with pytest.raises(ValidationError):
        PatientCreate(id="123456789", first_name="A", last_name="B", sex=Sex.MALE,
                      birth_date=date.today() + timedelta(days=1),
                      health_plan=HealthPlan.CLALIT, ward=Ward.ER, diagnosis="X")


def test_age_counts_only_full_years() -> None:
    assert calculate_age(date(2000, 6, 15), today=date(2026, 6, 14)) == 25
    assert calculate_age(date(2000, 6, 15), today=date(2026, 6, 15)) == 26
