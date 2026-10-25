"""Domain entities.

A patient is stored as a single MongoDB document that embeds its medications, vitals and
timeline. This makes the patient page a single read, and lets every clinical action
(e.g. "mark medication as given" + "add timeline event") be one atomic document update.
"""

from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from app.domain.enums import HealthPlan, Role, Sex, TimelineEventType, Ward


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return uuid4().hex


class VitalSigns(BaseModel):
    """One set of vital-sign measurements. Ranges reject obvious typos, not clinical outliers."""

    heart_rate: int = Field(ge=20, le=250, description="Beats per minute")
    bp_systolic: int = Field(ge=50, le=260, description="mmHg")
    bp_diastolic: int = Field(ge=30, le=160, description="mmHg")
    temperature: float = Field(ge=30.0, le=45.0, description="Celsius")
    recorded_at: datetime = Field(default_factory=utcnow)
    recorded_by: str

    @model_validator(mode="after")
    def systolic_above_diastolic(self) -> "VitalSigns":
        if self.bp_systolic <= self.bp_diastolic:
            raise ValueError("bp_systolic must be greater than bp_diastolic")
        return self


class Medication(BaseModel):
    """A prescription. ``last_given_*`` tracks the most recent administration."""

    id: str = Field(default_factory=new_id)
    name: str = Field(min_length=1, max_length=100)
    dose: str = Field(min_length=1, max_length=50, examples=["500 mg"])
    frequency: str = Field(min_length=1, max_length=50, examples=["every 8 hours"])
    active: bool = True
    prescribed_by: str
    prescribed_at: datetime = Field(default_factory=utcnow)
    last_given_at: datetime | None = None
    last_given_by: str | None = None


class TimelineEvent(BaseModel):
    """One entry in the patient's chronological event feed."""

    id: str = Field(default_factory=new_id)
    type: TimelineEventType
    at: datetime = Field(default_factory=utcnow)
    by: str
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)


class Patient(BaseModel):
    """A hospitalized patient. ``id`` is the national ID number (9 digits)."""

    id: str = Field(pattern=r"^\d{9}$")
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    sex: Sex
    birth_date: date
    health_plan: HealthPlan
    ward: Ward
    diagnosis: str = Field(min_length=1, max_length=200)
    admitted_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    medications: list[Medication] = Field(default_factory=list)
    vitals: list[VitalSigns] = Field(default_factory=list)
    timeline: list[TimelineEvent] = Field(default_factory=list)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self) -> int:
        return calculate_age(self.birth_date)

    @property
    def latest_vitals(self) -> VitalSigns | None:
        return max(self.vitals, key=lambda v: v.recorded_at, default=None)


class User(BaseModel):
    """A staff member who can log in."""

    username: str
    full_name: str
    role: Role
    password_hash: str


class PatientSummary(BaseModel):
    """Lightweight projection of a patient for the overview (main) page."""

    id: str
    full_name: str
    sex: Sex
    age: int
    ward: Ward
    health_plan: HealthPlan
    diagnosis: str
    last_vitals_at: datetime | None = None
    active_medications: int = 0


class WardGroup(BaseModel):
    """Patients of a single ward, as shown on the main page."""

    ward: Ward
    ward_name: str
    patients: list[PatientSummary]


def calculate_age(birth_date: date, today: date | None = None) -> int:
    """Full years between ``birth_date`` and ``today``."""
    today = today or date.today()
    had_birthday = (today.month, today.day) >= (birth_date.month, birth_date.day)
    return today.year - birth_date.year - (0 if had_birthday else 1)
