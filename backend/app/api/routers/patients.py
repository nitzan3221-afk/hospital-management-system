"""Patient endpoints. Each route declares the permission it requires; business logic lives
in ``PatientService``."""

import asyncio
import logging

from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import get_patient_service, require_permission
from app.api.schemas import DiagnosisUpdate, PatientDetailResponse
from app.core.config import Settings, get_settings
from app.domain.models import (
    AuthenticatedUser,
    MedicationCreate,
    PatientCreate,
    PatientUpdate,
    VitalsCreate,
    WardGroup,
)
from app.domain.permissions import Permission
from app.services.patient_service import PatientService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/patients", tags=["patients"])

_read = require_permission(Permission.READ_PATIENTS)


@router.get("", response_model=list[WardGroup])
async def list_patients(
    _: AuthenticatedUser = Depends(_read),
    service: PatientService = Depends(get_patient_service),
    settings: Settings = Depends(get_settings),
) -> list[WardGroup]:
    """All patients grouped by ward (main page).

    **Deliberately slow**: an artificial delay (``PATIENT_LIST_DELAY_SECONDS``, default 4s)
    simulates the heavy aggregation query typical of hospital overview screens.
    """
    if settings.patient_list_delay_seconds > 0:
        logger.info("Simulating slow overview query", extra={"delay_seconds": settings.patient_list_delay_seconds})
        await asyncio.sleep(settings.patient_list_delay_seconds)
    return await service.list_by_ward()


@router.get("/{patient_id}", response_model=PatientDetailResponse)
async def get_patient(
    patient_id: str,
    _: AuthenticatedUser = Depends(_read),
    service: PatientService = Depends(get_patient_service),
) -> PatientDetailResponse:
    """Personal info, medical info, latest vitals and the chronological timeline."""
    return PatientDetailResponse.from_patient(await service.get(patient_id))


@router.post("", response_model=PatientDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    body: PatientCreate,
    user: AuthenticatedUser = Depends(require_permission(Permission.CREATE_PATIENT)),
    service: PatientService = Depends(get_patient_service),
) -> PatientDetailResponse:
    """Admit a new patient. Returns 409 if a patient with this ID already exists."""
    return PatientDetailResponse.from_patient(await service.create(body, user))


@router.patch("/{patient_id}", response_model=PatientDetailResponse)
async def update_patient(
    patient_id: str,
    body: PatientUpdate,
    user: AuthenticatedUser = Depends(require_permission(Permission.UPDATE_PATIENT_INFO)),
    service: PatientService = Depends(get_patient_service),
) -> PatientDetailResponse:
    """Update personal / administrative details. Send only the fields to change."""
    return PatientDetailResponse.from_patient(await service.update_info(patient_id, body, user))


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(
    patient_id: str,
    user: AuthenticatedUser = Depends(require_permission(Permission.DELETE_PATIENT)),
    service: PatientService = Depends(get_patient_service),
) -> Response:
    await service.delete(patient_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{patient_id}/diagnosis", response_model=PatientDetailResponse)
async def change_diagnosis(
    patient_id: str,
    body: DiagnosisUpdate,
    user: AuthenticatedUser = Depends(require_permission(Permission.CHANGE_DIAGNOSIS)),
    service: PatientService = Depends(get_patient_service),
) -> PatientDetailResponse:
    return PatientDetailResponse.from_patient(await service.change_diagnosis(patient_id, body.diagnosis, user))


@router.post("/{patient_id}/medications", response_model=PatientDetailResponse, status_code=status.HTTP_201_CREATED)
async def prescribe_medication(
    patient_id: str,
    body: MedicationCreate,
    user: AuthenticatedUser = Depends(require_permission(Permission.PRESCRIBE_MEDICATION)),
    service: PatientService = Depends(get_patient_service),
) -> PatientDetailResponse:
    return PatientDetailResponse.from_patient(await service.prescribe(patient_id, body, user))


@router.post("/{patient_id}/medications/{medication_id}/give", response_model=PatientDetailResponse)
async def give_medication(
    patient_id: str,
    medication_id: str,
    user: AuthenticatedUser = Depends(require_permission(Permission.GIVE_MEDICATION)),
    service: PatientService = Depends(get_patient_service),
) -> PatientDetailResponse:
    """Mark a dose of an active medication as given now."""
    return PatientDetailResponse.from_patient(await service.give_medication(patient_id, medication_id, user))


@router.post("/{patient_id}/vitals", response_model=PatientDetailResponse, status_code=status.HTTP_201_CREATED)
async def record_vitals(
    patient_id: str,
    body: VitalsCreate,
    user: AuthenticatedUser = Depends(require_permission(Permission.RECORD_VITALS)),
    service: PatientService = Depends(get_patient_service),
) -> PatientDetailResponse:
    return PatientDetailResponse.from_patient(await service.record_vitals(patient_id, body, user))
