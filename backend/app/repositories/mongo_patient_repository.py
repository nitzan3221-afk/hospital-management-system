"""MongoDB implementation of ``PatientRepository``.

Collection ``patients`` — one document per patient, ``_id`` = national ID.
Medications, vitals and timeline are embedded arrays.
"""

from datetime import date, datetime, time, timezone
from typing import Any

from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import DuplicateKeyError

from app.domain.enums import Ward
from app.domain.errors import AlreadyExistsError
from app.domain.models import (
    Medication,
    Patient,
    PatientSummary,
    TimelineEvent,
    VitalSigns,
    WardGroup,
    calculate_age,
)

# Fields needed for the overview page. Large arrays are reduced server-side.
_SUMMARY_PIPELINE: list[dict[str, Any]] = [
    {
        "$project": {
            "first_name": 1,
            "last_name": 1,
            "sex": 1,
            "birth_date": 1,
            "ward": 1,
            "health_plan": 1,
            "diagnosis": 1,
            "last_vitals_at": {"$max": "$vitals.recorded_at"},
            "active_medications": {
                "$size": {
                    "$filter": {
                        "input": {"$ifNull": ["$medications", []]},
                        "as": "m",
                        "cond": "$$m.active",
                    }
                }
            },
        }
    },
    {"$sort": {"last_name": 1, "first_name": 1}},
    {"$group": {"_id": "$ward", "patients": {"$push": "$$ROOT"}}},
]

# Display order of wards on the main page
_WARD_ORDER = {ward: index for index, ward in enumerate(Ward)}


def _date_to_datetime(value: date) -> datetime:
    """BSON has no pure date type, so dates are stored as midnight UTC."""
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def _to_date(value: date | datetime) -> date:
    return value.date() if isinstance(value, datetime) else value


def patient_to_document(patient: Patient) -> dict[str, Any]:
    doc = patient.model_dump()
    doc["_id"] = doc.pop("id")
    doc["birth_date"] = _date_to_datetime(patient.birth_date)
    return doc


def document_to_patient(doc: dict[str, Any]) -> Patient:
    data = dict(doc)
    data["id"] = data.pop("_id")
    data["birth_date"] = _to_date(data["birth_date"])
    return Patient.model_validate(data)


def _document_to_summary(doc: dict[str, Any]) -> PatientSummary:
    return PatientSummary(
        id=doc["_id"],
        full_name=f"{doc['first_name']} {doc['last_name']}",
        sex=doc["sex"],
        age=calculate_age(_to_date(doc["birth_date"])),
        ward=doc["ward"],
        health_plan=doc["health_plan"],
        diagnosis=doc["diagnosis"],
        last_vitals_at=doc.get("last_vitals_at"),
        active_medications=doc.get("active_medications", 0),
    )


class MongoPatientRepository:
    def __init__(self, db: AsyncDatabase) -> None:
        self._collection: AsyncCollection = db["patients"]

    async def ensure_indexes(self) -> None:
        await self._collection.create_index("ward")
        await self._collection.create_index([("last_name", 1), ("first_name", 1)])

    async def list_grouped_by_ward(self) -> list[WardGroup]:
        cursor = await self._collection.aggregate(_SUMMARY_PIPELINE)
        groups: list[WardGroup] = []
        async for group in cursor:
            ward = Ward(group["_id"])
            groups.append(
                WardGroup(
                    ward=ward,
                    ward_name=ward.display_name,
                    patients=[_document_to_summary(p) for p in group["patients"]],
                )
            )
        return sorted(groups, key=lambda g: _WARD_ORDER[g.ward])

    async def get(self, patient_id: str) -> Patient | None:
        doc = await self._collection.find_one({"_id": patient_id})
        return document_to_patient(doc) if doc else None

    async def create(self, patient: Patient) -> None:
        try:
            await self._collection.insert_one(patient_to_document(patient))
        except DuplicateKeyError as exc:
            raise AlreadyExistsError(f"Patient {patient.id} already exists") from exc

    async def update_fields(self, patient_id: str, fields: dict[str, Any], event: TimelineEvent) -> bool:
        to_set = dict(fields)
        if isinstance(to_set.get("birth_date"), date) and not isinstance(to_set["birth_date"], datetime):
            to_set["birth_date"] = _date_to_datetime(to_set["birth_date"])
        to_set["updated_at"] = event.at
        result = await self._collection.update_one(
            {"_id": patient_id},
            {"$set": to_set, "$push": {"timeline": event.model_dump()}},
        )
        return result.matched_count == 1

    async def delete(self, patient_id: str) -> bool:
        result = await self._collection.delete_one({"_id": patient_id})
        return result.deleted_count == 1

    async def add_medication(self, patient_id: str, medication: Medication, event: TimelineEvent) -> bool:
        result = await self._collection.update_one(
            {"_id": patient_id},
            {
                "$push": {"medications": medication.model_dump(), "timeline": event.model_dump()},
                "$set": {"updated_at": event.at},
            },
        )
        return result.matched_count == 1

    async def mark_medication_given(
        self,
        patient_id: str,
        medication_id: str,
        given_at: datetime,
        given_by: str,
        event: TimelineEvent,
    ) -> bool:
        # The filter matches only an *active* medication; "$" targets that array element.
        # Medication update + timeline event happen in a single atomic document write.
        result = await self._collection.update_one(
            {"_id": patient_id, "medications": {"$elemMatch": {"id": medication_id, "active": True}}},
            {
                "$set": {
                    "medications.$.last_given_at": given_at,
                    "medications.$.last_given_by": given_by,
                    "updated_at": event.at,
                },
                "$push": {"timeline": event.model_dump()},
            },
        )
        return result.matched_count == 1

    async def add_vitals(self, patient_id: str, vitals: VitalSigns, event: TimelineEvent) -> bool:
        result = await self._collection.update_one(
            {"_id": patient_id},
            {
                "$push": {"vitals": vitals.model_dump(), "timeline": event.model_dump()},
                "$set": {"updated_at": event.at},
            },
        )
        return result.matched_count == 1
