"""HTTP-level tests: authentication, permission enforcement and status codes.

The app's repositories are swapped for in-memory fakes via FastAPI dependency overrides,
and the TestClient is used without its context manager so the MongoDB startup hook never runs.
"""

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_patient_repository, get_user_repository
from app.core.config import Settings, get_settings
from app.main import app
from app.seed import DEMO_PASSWORD, build_patients, build_users
from tests.fakes import InMemoryPatientRepository, InMemoryUserRepository

PATIENT_ID = "301234567"
MEDICATION = {"name": "Amoxicillin", "dose": "500 mg", "frequency": "every 8 hours"}


@pytest.fixture
def client():
    patients = InMemoryPatientRepository(build_patients())
    users = InMemoryUserRepository(build_users())
    test_settings = Settings(jwt_secret="test-secret-that-is-at-least-32-bytes-long", patient_list_delay_seconds=0)

    app.dependency_overrides[get_patient_repository] = lambda: patients
    app.dependency_overrides[get_user_repository] = lambda: users
    app.dependency_overrides[get_settings] = lambda: test_settings
    yield TestClient(app)
    app.dependency_overrides.clear()


def _auth(client: TestClient, username: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": DEMO_PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_requests_without_token_get_401(client: TestClient) -> None:
    assert client.get(f"/api/patients/{PATIENT_ID}").status_code == 401


def test_nurse_cannot_prescribe_but_doctor_can(client: TestClient, audit_log) -> None:
    url = f"/api/patients/{PATIENT_ID}/medications"

    denied = client.post(url, json=MEDICATION, headers=_auth(client, "nurse_joy"))
    assert denied.status_code == 403
    assert ("permission_denied", "denied") in audit_log.events()

    allowed = client.post(url, json=MEDICATION, headers=_auth(client, "dr_house"))
    assert allowed.status_code == 201
    assert any(m["name"] == "Amoxicillin" for m in allowed.json()["medications"])


def test_secretary_can_create_and_delete_patient(client: TestClient) -> None:
    headers = _auth(client, "pam_beesly")
    body = {"id": "123456789", "first_name": "Dana", "last_name": "Levi", "sex": "female",
            "birth_date": "1985-04-12", "health_plan": "Clalit", "ward": "SURGERY", "diagnosis": "Observation"}

    assert client.post("/api/patients", json=body, headers=headers).status_code == 201
    assert client.post("/api/patients", json=body, headers=headers).status_code == 409
    assert client.delete("/api/patients/123456789", headers=headers).status_code == 204
    assert client.get("/api/patients/123456789", headers=headers).status_code == 404


def test_patient_list_is_grouped_by_ward(client: TestClient) -> None:
    response = client.get("/api/patients", headers=_auth(client, "nurse_joy"))

    assert response.status_code == 200
    groups = response.json()
    assert {g["ward"] for g in groups} == {"ER", "INTERNAL_A", "ICU", "PEDIATRICS"}
    assert sum(len(g["patients"]) for g in groups) == 14
