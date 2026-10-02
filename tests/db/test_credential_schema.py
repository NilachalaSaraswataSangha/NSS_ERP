"""
NSS ERP — DB schema tests for the membership credential tables.

Guards the structural invariants the credential feature relies on, at the
schema level (catalog introspection — no seed data required):

  - nss.parichaya_patra.document_number is globally UNIQUE and NOT NULL
    VARCHAR(30); nss.anumati_patra.document_number is UNIQUE *per issuing
    Sakha* (composite UNIQUE(issuing_organization_pk, document_number)) and
    NOT NULL VARCHAR(30) — the format guard in issue_membership_credential()
    composes into this column, and duplicate document numbers must be
    rejected by the DB, not just the app. Anumati numbering is per-Sakha, so
    two Sakhas legitimately share a number; the composite scope prevents the
    cross-Sakha collision (409) the old single-column unique produced.
  - one active credential per member (partial unique indexes).
  - validity-range CHECK (valid_to > valid_from).
  - nss.credential_sequence_counter is unique per
    (credential_type, scope_organization_pk, financial_year_start) so the
    per-FY / per-scope sequence can never fork.

These read pg_catalog / information_schema through the shared write_conn,
so they pass regardless of how much demo data is seeded.
"""

import pytest


pytestmark = [pytest.mark.db, pytest.mark.integration]


def _constraint_exists(conn, name):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1
            FROM pg_constraint c
            JOIN pg_namespace n ON n.oid = c.connamespace
            WHERE n.nspname = 'nss' AND c.conname = %s
            """,
            (name,),
        )
        return cur.fetchone() is not None


def _unique_index_exists(conn, name):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT indexdef
            FROM pg_indexes
            WHERE schemaname = 'nss' AND indexname = %s
            """,
            (name,),
        )
        row = cur.fetchone()
    return row is not None and "UNIQUE" in row[0].upper()


def _column(conn, table, column):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT data_type, character_maximum_length, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'nss'
              AND table_name = %s AND column_name = %s
            """,
            (table, column),
        )
        return cur.fetchone()


def _constraint_columns(conn, name):
    """Return the set of column names a UNIQUE/PK constraint spans."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT a.attname
            FROM pg_constraint c
            JOIN pg_namespace n ON n.oid = c.connamespace
            JOIN pg_attribute a
              ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
            WHERE n.nspname = 'nss' AND c.conname = %s
            """,
            (name,),
        )
        return {row[0] for row in cur.fetchall()}


# ── UNIQUE / CHECK constraints ─────────────────────────────────────────

@pytest.mark.parametrize("constraint", [
    "uq_pp_document_number",       # parichaya_patra.document_number UNIQUE
    "uq_ap_document_number",       # anumati_patra.document_number UNIQUE
    "chk_pp_validity_range",       # parichaya valid_to > valid_from
    "chk_ap_validity_range",       # anumati valid_to > valid_from
    "uq_credential_sequence_scope",  # counter unique per (type, scope, fy_start)
])
def test_credential_constraint_exists(write_conn, constraint):
    assert _constraint_exists(write_conn, constraint), (
        f"Expected constraint nss.{constraint} to exist"
    )


# ── Uniqueness SCOPE (single-column vs per-Sakha composite) ────────────

@pytest.mark.parametrize("constraint,expected_columns", [
    # Parichaya Patra: one Kendra-wide counter → globally-unique number.
    ("uq_pp_document_number", {"document_number"}),
    # Anumati Patra: one counter PER issuing Sakha → number unique only
    # within a Sakha, so the unique must be composite. A regression to a
    # single-column unique here reintroduces the cross-Sakha 409 collision.
    ("uq_ap_document_number", {"issuing_organization_pk", "document_number"}),
])
def test_credential_unique_scope(write_conn, constraint, expected_columns):
    cols = _constraint_columns(write_conn, constraint)
    assert cols == expected_columns, (
        f"nss.{constraint} should span {expected_columns}, got {cols}"
    )


def test_anumati_issuing_org_is_not_null_uuid(write_conn):
    """anumati_patra.issuing_organization_pk is a NOT NULL UUID (FK to organization)."""
    col = _column(write_conn, "anumati_patra", "issuing_organization_pk")
    assert col is not None, "nss.anumati_patra.issuing_organization_pk should exist"
    data_type, _max_len, is_nullable = col
    assert data_type == "uuid", data_type
    assert is_nullable == "NO", is_nullable


# ── One active credential per member (partial unique indexes) ──────────

@pytest.mark.parametrize("index", [
    "uq_pp_active_per_member",
    "uq_ap_active_per_member",
])
def test_active_per_member_unique_index_exists(write_conn, index):
    assert _unique_index_exists(write_conn, index), (
        f"Expected unique index nss.{index} to exist"
    )


# ── document_number column shape ───────────────────────────────────────

@pytest.mark.parametrize("table", ["parichaya_patra", "anumati_patra"])
def test_document_number_is_not_null_varchar30(write_conn, table):
    col = _column(write_conn, table, "document_number")
    assert col is not None, f"nss.{table}.document_number should exist"
    data_type, max_len, is_nullable = col
    assert data_type == "character varying", (table, data_type)
    assert max_len == 30, (table, max_len)
    assert is_nullable == "NO", (table, is_nullable)


def test_credential_sequence_counter_current_value_exists(write_conn):
    """The counter carries a current_value column the atomic upsert bumps."""
    col = _column(write_conn, "credential_sequence_counter", "current_value")
    assert col is not None, "nss.credential_sequence_counter.current_value missing"
