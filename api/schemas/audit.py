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

    changed_by_sangha_sevi_id is resolved via LEFT JOIN so callers see the
    human-readable actor id without a second lookup; it is None when the
    change was made by an unattributed/system context.
    """

    field_change_log_pk: UUID
    table_name: str
    record_pk: UUID
    field_name: str
    old_value: str | None
    new_value: str | None
    change_reason: str | None
    changed_at: datetime
    changed_by_sangha_sevi_pk: UUID | None
    changed_by_sangha_sevi_id: str | None
