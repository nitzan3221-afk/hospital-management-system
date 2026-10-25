"""Repository interfaces (Dependency Inversion).

The service layer depends only on these protocols, never on MongoDB directly. That keeps
business logic testable with an in-memory implementation and lets the storage engine be
swapped without touching services.

Every mutating method that represents a clinical action receives the ``TimelineEvent`` to
record, so the implementation can persist the change and the event atomically.
"""

from datetime import datetime
from typing import Any, Protocol

from app.domain.models import Medication, Patient, TimelineEvent, User, VitalSigns, WardGroup


class PatientRepository(Protocol):
    async def list_grouped_by_ward(self) -> list[WardGroup]:
        """Patient summaries grouped by ward (the overview query)."""
        ...

    async def get(self, patient_id: str) -> Patient | None: ...

    async def create(self, patient: Patient) -> None:
        """Insert a patient. Raises ``AlreadyExistsError`` if the ID is taken."""
        ...

    async def update_fields(self, patient_id: str, fields: dict[str, Any], event: TimelineEvent) -> bool:
        """Set top-level fields and append ``event``. Returns False if the patient was not found."""
        ...

    async def delete(self, patient_id: str) -> bool: ...

    async def add_medication(self, patient_id: str, medication: Medication, event: TimelineEvent) -> bool: ...

    async def mark_medication_given(
        self,
        patient_id: str,
        medication_id: str,
        given_at: datetime,
        given_by: str,
        event: TimelineEvent,
    ) -> bool:
        """Mark an *active* medication as given. Returns False if no such active medication."""
        ...

    async def add_vitals(self, patient_id: str, vitals: VitalSigns, event: TimelineEvent) -> bool: ...


class UserRepository(Protocol):
    async def get_by_username(self, username: str) -> User | None: ...

    async def create(self, user: User) -> None: ...

    async def count(self) -> int: ...
