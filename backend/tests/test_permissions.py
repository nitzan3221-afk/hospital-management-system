"""The role -> permission table must match the assignment exactly."""

import pytest

from app.domain.enums import Role
from app.domain.permissions import Permission, has_permission

P = Permission

# Expected permissions per role, straight from the assignment's table
EXPECTED = {
    Role.DOCTOR: {P.READ_PATIENTS, P.PRESCRIBE_MEDICATION, P.GIVE_MEDICATION, P.RECORD_VITALS, P.CHANGE_DIAGNOSIS},
    Role.NURSE: {P.READ_PATIENTS, P.GIVE_MEDICATION, P.RECORD_VITALS},
    Role.SECRETARY: {P.READ_PATIENTS, P.CREATE_PATIENT, P.UPDATE_PATIENT_INFO, P.DELETE_PATIENT},
}


@pytest.mark.parametrize("role", list(Role))
@pytest.mark.parametrize("permission", list(Permission))
def test_role_permission_matrix(role: Role, permission: Permission) -> None:
    assert has_permission(role, permission) == (permission in EXPECTED[role])


def test_only_doctor_can_prescribe_or_change_diagnosis() -> None:
    for permission in (P.PRESCRIBE_MEDICATION, P.CHANGE_DIAGNOSIS):
        assert [r for r in Role if has_permission(r, permission)] == [Role.DOCTOR]
