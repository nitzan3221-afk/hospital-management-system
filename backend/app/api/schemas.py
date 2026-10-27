"""Request / response bodies of the HTTP API (separate from domain entities)."""

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.domain.enums import HealthPlan, Role, Sex, Ward
from app.domain.models import AuthenticatedUser, Medication, Patient, TimelineEvent, VitalSigns
from app.domain.permissions import Permission, permissions_for


# ---------- Auth ----------

class LoginRequest(BaseModel):
    username: str = Field(min_length=1, examples=["dr_house"])
    password: str = Field(min_length=1, examples=["password123"])


class UserResponse(BaseModel):
    username: str
    full_name: str
    role: Role
    permissions: list[Permission]

    @classmethod
    def from_user(cls, user: AuthenticatedUser) -> "UserResponse":
        return cls(
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            permissions=sorted(permissions_for(user.role), key=lambda p: p.value),
        )


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserResponse


# ---------- Patients ----------

class DiagnosisUpdate(BaseModel):
    diagnosis: str = Field(min_length=1, max_length=200, examples=["Bacterial pneumonia"])


class PatientDetailResponse(BaseModel):
    """Everything the patient page needs, in one response."""

    id: str
    first_name: str
    last_name: str
    full_name: str
    sex: Sex
    birth_date: date
    age: int
    health_plan: HealthPlan
    ward: Ward
    ward_name: str
    diagnosis: str
    admitted_at: datetime
    updated_at: datetime
    latest_vitals: VitalSigns | None
    vitals: list[VitalSigns] = Field(description="Oldest first")
    medications: list[Medication]
    timeline: list[TimelineEvent] = Field(description="Chronological (oldest first)")

    @classmethod
    def from_patient(cls, patient: Patient) -> "PatientDetailResponse":
        return cls(
            **patient.model_dump(exclude={"vitals", "medications", "timeline"}),
            full_name=patient.full_name,
            age=patient.age,
            ward_name=patient.ward.display_name,
            latest_vitals=patient.latest_vitals,
            vitals=sorted(patient.vitals, key=lambda v: v.recorded_at),
            medications=patient.medications,
            timeline=patient.timeline,
        )
