"""Role-based access control.

Endpoints check *permissions* (what an action requires), never roles directly. Roles are
just named sets of permissions defined in one table below, so adding a role or changing what
a role may do is a one-line change here (Open/Closed principle) — no endpoint code changes.
"""

from enum import Enum

from app.domain.enums import Role


class Permission(str, Enum):
    READ_PATIENTS = "read_patients"
    CREATE_PATIENT = "create_patient"
    UPDATE_PATIENT_INFO = "update_patient_info"
    DELETE_PATIENT = "delete_patient"
    PRESCRIBE_MEDICATION = "prescribe_medication"
    GIVE_MEDICATION = "give_medication"
    RECORD_VITALS = "record_vitals"
    CHANGE_DIAGNOSIS = "change_diagnosis"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.DOCTOR: frozenset({
        Permission.READ_PATIENTS,
        Permission.PRESCRIBE_MEDICATION,
        Permission.GIVE_MEDICATION,
        Permission.RECORD_VITALS,
        Permission.CHANGE_DIAGNOSIS,
    }),
    Role.NURSE: frozenset({
        Permission.READ_PATIENTS,
        Permission.GIVE_MEDICATION,
        Permission.RECORD_VITALS,
    }),
    # Assumption (not specified in the assignment): the secretary, who registers patients,
    # also maintains their administrative details. Diagnosis changes stay with doctors.
    Role.SECRETARY: frozenset({
        Permission.READ_PATIENTS,
        Permission.CREATE_PATIENT,
        Permission.UPDATE_PATIENT_INFO,
        Permission.DELETE_PATIENT,
    }),
}


def permissions_for(role: Role) -> frozenset[Permission]:
    return ROLE_PERMISSIONS.get(role, frozenset())


def has_permission(role: Role, permission: Permission) -> bool:
    return permission in permissions_for(role)
