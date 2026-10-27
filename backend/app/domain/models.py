"""Domain entities and the input models used to create / change them.

A patient is stored as a single MongoDB document that embeds its medications, vitals and
timeline. This makes the patient page a single read, and lets every clinical action
(e.g. "mark medication as given" + "add timeline event") be one atomic document update.

Input models (``*Create`` / ``*Update``) hold the validation rules; the stored entities
extend them with server-controlled fields (ids, timestamps, who did it).
"""

from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

from app.domain.enums import HealthPlan, Role, Sex, TimelineEventType, Ward


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return uuid4().hex


def _not_in_future(value: date) -> date:
    if value > date.today():
        raise ValueError("birth_date cannot be in the future")
    return value


# ---------------------------------------------------------------- vitals

class VitalsCreate(BaseModel):
    """One set of vital-sign measurements. Ranges reject obvious typos, not clinical outliers."""

    heart_rate: int = Field(ge=20, le=250, description="Beats per minute", examples=[82])
    bp_systolic: int = Field(ge=50, le=260, description="mmHg", examples=[120])
    bp_diastolic: int = Field(ge=30, le=160, description="mmHg", examples=[80])
    temperature: float = Field(ge=30.0, le=45.0, description="Celsius", examples=[36.8])

    @model_validator(mode="after")
    def systolic_above_diastolic(self) -> "VitalsCreate":
        if self.bp_systolic <= self.bp_diastolic:
            raise ValueError("bp_systolic must be greater than bp_diastolic")
        return self


class VitalSigns(VitalsCreate):
    recorded_at: datetime = Field(default_factory=utcnow)
    recorded_by: str


# ---------------------------------------------------------------- medications

class MedicationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100, examples=["Amoxicillin"])
    dose: str = Field(min_length=1, max_length=50, examples=["500 mg"])
    frequency: str = Field(min_length=1, max_length=50, examples=["every 8 hours"])


class Medication(MedicationCreate):
    """A prescription. ``last_given_*`` tracks the most recent administration."""

    id: str = Field(default_factory=new_id)
    active: bool = True
    prescribed_by: str
    prescribed_at: datetime = Field(default_factory=utcnow)
    last_given_at: datetime | None = None
    last_given_by: str | None = None


# ---------------------------------------------------------------- timeline

class TimelineEvent(BaseModel):
    """One entry in the patient's chronological event feed."""

    id: str = Field(default_factory=new_id)
    type: TimelineEventType
    at: datetime = Field(default_factory=utcnow)
    by: str
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------- patients

class PatientInfo(BaseModel):
    """Personal / administrative details (maintained by the secretary)."""

    first_name: str = Field(min_length=1, max_length=50, examples=["Dana"])
    last_name: str = Field(min_length=1, max_length=50, examples=["Levi"])
    sex: Sex
    birth_date: date = Field(examples=["1985-04-12"])
    health_plan: HealthPlan
    ward: Ward

    @field_validator("birth_date")
    @classmethod
    def check_birth_date(cls, value: date) -> date:
        return _not_in_future(value)


class PatientCreate(PatientInfo):
    """Data needed to admit a new patient."""

    id: str = Field(pattern=r"^\d{9}$", description="National ID (9 digits)", examples=["123456789"])
    diagnosis: str = Field(min_length=1, max_length=200, examples=["Observation after fall"])


class PatientUpdate(BaseModel):
    """Partial update of personal details. Only the fields sent are changed.
    The diagnosis is deliberately not here — it has its own, doctor-only action."""

    first_name: str | None = Field(default=None, min_length=1, max_length=50)
    last_name: str | None = Field(default=None, min_length=1, max_length=50)
    sex: Sex | None = None
    birth_date: date | None = None
    health_plan: HealthPlan | None = None
    ward: Ward | None = None

    @field_validator("birth_date")
    @classmethod
    def check_birth_date(cls, value: date | None) -> date | None:
        return _not_in_future(value) if value is not None else value


class Patient(PatientCreate):
    """A hospitalized patient. ``id`` is the national ID number."""

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

    def find_medication(self, medication_id: str) -> Medication | None:
        return next((m for m in self.medications if m.id == medication_id), None)


# ---------------------------------------------------------------- users

class User(BaseModel):
    """A staff member who can log in."""

    username: str
    full_name: str
    role: Role
    password_hash: str


class AuthenticatedUser(BaseModel):
    """The user making the current request, as identified by their access token."""

    username: str
    full_name: str
    role: Role


# ---------------------------------------------------------------- overview

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
