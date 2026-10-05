"""
Pydantic response models for the Audit API (Tier 5).

Exposes the field-level change history stored in nss.field_change_log.
Audit columns are the payload here (not excluded, unlike other modules)
because the change log IS the audit trail.

Raw psycopg2 returns dictionaries — no ORM objects — so
ConfigDict(from_attributes=True) is unnecessary.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class FieldChangeLogResponse(BaseModel):
    """
    A single field-level change recorded by the DB audit trigger.

    One row per field per operation:
      action='CREATE' → old_value is None
      action='UPDATE' → both values present (new may be None if cleared)
      action='DELETE' → new_value is None

    Actor: both changed_by_sangha_sevi_pk and changed_by_user_account_pk
    are recorded, because an authenticated account does not always have
    a Sangha Sevi record. changed_by_sangha_sevi_id and changed_by_name
    are resolved via LEFT JOIN so callers get a human-readable actor
    without a second lookup. All actor fields are None when the change
    came from an unattributed context (public registration, seed, system).
    """

    field_change_log_pk: UUID
    action: str | None
    table_name: str
    record_pk: UUID
    field_name: str
    old_value: str | None
    new_value: str | None
    change_reason: str | None
    changed_at: datetime
    changed_by_sangha_sevi_pk: UUID | None
    changed_by_sangha_sevi_id: str | None
    changed_by_user_account_pk: UUID | None
    changed_by_name: str | None
