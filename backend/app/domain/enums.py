"""Enumerations shared across the application."""

from enum import Enum


class Role(str, Enum):
    DOCTOR = "doctor"
    NURSE = "nurse"
    SECRETARY = "secretary"


class Ward(str, Enum):
    ER = "ER"
    INTERNAL_A = "INTERNAL_A"
    INTERNAL_B = "INTERNAL_B"
    ICU = "ICU"
    SURGERY = "SURGERY"
    PEDIATRICS = "PEDIATRICS"

    @property
    def display_name(self) -> str:
        return WARD_DISPLAY_NAMES[self]


WARD_DISPLAY_NAMES: dict[Ward, str] = {
    Ward.ER: "Emergency (ER)",
    Ward.INTERNAL_A: "Internal Medicine A",
    Ward.INTERNAL_B: "Internal Medicine B",
    Ward.ICU: "ICU",
    Ward.SURGERY: "Surgery / Post-Op",
    Ward.PEDIATRICS: "Pediatrics",
}


class HealthPlan(str, Enum):
    CLALIT = "Clalit"
    MACCABI = "Maccabi"
    MEUHEDET = "Meuhedet"
    LEUMIT = "Leumit"


class Sex(str, Enum):
    MALE = "male"
    FEMALE = "female"


class TimelineEventType(str, Enum):
    ADMITTED = "admitted"
    DOCTOR_VISIT = "doctor_visit"
    MEDICATION_PRESCRIBED = "medication_prescribed"
    MEDICATION_GIVEN = "medication_given"
    VITALS_RECORDED = "vitals_recorded"
    DIAGNOSIS_CHANGED = "diagnosis_changed"
    PATIENT_UPDATED = "patient_updated"
