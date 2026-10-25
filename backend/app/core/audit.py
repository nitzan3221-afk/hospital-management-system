"""Audit log for security- and clinically-relevant actions.

All critical actions go through ``audit()`` so they share one logger name and one set of
field names — making them easy to filter, alert on and retain separately in production.

Example line:
    {"timestamp": "...", "level": "INFO", "logger": "hospital.audit",
     "message": "medication_given: success", "event": "medication_given",
     "outcome": "success", "actor": "nurse_joy", "role": "nurse",
     "patient_id": "301234567", "medication_id": "...", "request_id": "..."}
"""

import logging
from typing import Any

audit_logger = logging.getLogger("hospital.audit")

SUCCESS = "success"
FAILURE = "failure"
DENIED = "denied"


def audit(event: str, outcome: str = SUCCESS, **fields: Any) -> None:
    """Write one audit record. Failures and denials are logged at WARNING level."""
    level = logging.INFO if outcome == SUCCESS else logging.WARNING
    audit_logger.log(level, "%s: %s", event, outcome, extra={"event": event, "outcome": outcome, **fields})
