"""
NSS ERP — Shared API helpers.

Cursor-to-Pydantic conversion functions used by all routers.
Extracted from per-router duplicates to ensure a single point of
maintenance for any future security hardening (e.g. column sanitisation).

Pagination constants are also centralised here so all list endpoints
share the same defaults and validation ranges.
"""

# ── Pagination defaults ──────────────────────────────────────────────────

DEFAULT_LIMIT = 100
MAX_LIMIT = 500


# ── Cursor → Pydantic helpers ────────────────────────────────────────────

def rows_to_models(cur, model_class):
    """Convert cursor results to a list of Pydantic models."""
    columns = [desc[0] for desc in cur.description]
    return [model_class(**dict(zip(columns, row))) for row in cur.fetchall()]


def row_to_model(cur, model_class):
    """Convert a single cursor result to a Pydantic model, or None."""
    columns = [desc[0] for desc in cur.description]
    row = cur.fetchone()
    if row is None:
        return None
    return model_class(**dict(zip(columns, row)))
