"""
NSS ERP — DB schema + resolver tests for the festival reference calendar
(SOL-ARCH-013, Festival Reference Calendar Architecture).

Guards the structural invariants and resolver-function contracts the
Dola Purnima credential-validity feature relies on:

  - nss.festival_master.festival_code / festival_name UNIQUE, soft-delete
    CHECK in place.
  - nss.festival_calendar_date: one row per (festival, calendar_year)
    (uq_festival_calendar_date_festival_year), calendar_year range CHECK,
    the EXTRACT(YEAR FROM observed_date) = calendar_year consistency CHECK
    (chk_festival_calendar_date_year_matches), FK to festival_master,
    soft-delete CHECK.
  - api.helpers.festival_date_for_year() / next_festival_date_on_or_after()
    never compute or guess a date — they return None (not a fallback date)
    when no confirmed row is on file, and festival_date_for_year() excludes
    is_confirmed = FALSE rows unless the caller explicitly opts out via
    require_confirmed=False.
  - api.helpers.dola_purnima_credential_validity_window() raises
    HTTPException 422 — never falls back to financial_year_bounds() — when
    the required Dola Purnima rows are missing/unconfirmed, and returns the
    correct "Dola Purnima membership year" window when they are present.

These read pg_catalog / information_schema and exercise the resolver
functions through the shared write_conn (module SAVEPOINT, auto-rolled
back) — a throwaway TEST_FESTIVAL_SCHEMA festival is used for the
resolver tests so the real seeded DOLA_PURNIMA data is left untouched.
"""

from datetime import date

import psycopg2
import pytest
from fastapi import HTTPException

from api.helpers import (
    dola_purnima_credential_validity_window,
    festival_date_for_year,
    next_festival_date_on_or_after,
)


pytestmark = [pytest.mark.db, pytest.mark.integration]


# ── Schema-introspection helpers (mirrors tests/db/test_credential_schema.py) ──

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


# ── UNIQUE / CHECK / FK constraints ─────────────────────────────────────

@pytest.mark.parametrize("constraint", [
    "uq_festival_master_code",                  # festival_code UNIQUE
    "uq_festival_master_name",                  # festival_name UNIQUE
    "chk_festival_master_soft_delete",
    "fk_festival_calendar_date_festival",        # FK to festival_master
    "uq_festival_calendar_date_festival_year",   # one row per festival/year
    "chk_festival_calendar_date_year_range",     # calendar_year 1900-2200
    "chk_festival_calendar_date_year_matches",   # EXTRACT(YEAR) = calendar_year
    "chk_festival_calendar_date_soft_delete",
])
def test_festival_constraint_exists(write_conn, constraint):
    assert _constraint_exists(write_conn, constraint), (
        f"Expected constraint nss.{constraint} to exist"
    )


# ── Constraint behaviour (actual bad-data INSERTs, not just existence) ──

@pytest.fixture
def test_festival_pk(write_conn):
    """
    A throwaway festival_master row for the constraint-behaviour tests
    below, inserted/rolled back within its own SAVEPOINT so it never
    touches the real DOLA_PURNIMA seed data.
    """
    cur = write_conn.cursor()
    cur.execute("SAVEPOINT test_festival_fixture")
    cur.execute(
        """
        INSERT INTO nss.festival_master (festival_code, festival_name)
        VALUES ('TEST_FESTIVAL_SCHEMA', 'Test Festival (schema tests)')
        RETURNING festival_master_pk
        """
    )
    pk = cur.fetchone()[0]
    yield str(pk)
    cur.execute("ROLLBACK TO SAVEPOINT test_festival_fixture")


def test_duplicate_festival_year_rejected(write_conn, test_festival_pk):
    """uq_festival_calendar_date_festival_year rejects a second row for
    the same (festival, calendar_year)."""
    cur = write_conn.cursor()
    cur.execute("SAVEPOINT test_dup_year")
    cur.execute(
        """
        INSERT INTO nss.festival_calendar_date
            (festival_master_pk, calendar_year, observed_date, is_confirmed)
        VALUES (%s, 2030, DATE '2030-03-01', TRUE)
        """,
        (test_festival_pk,),
    )
    cur.execute("RELEASE SAVEPOINT test_dup_year")

    cur.execute("SAVEPOINT test_dup_year_2")
    with pytest.raises(psycopg2.errors.UniqueViolation):
        cur.execute(
            """
            INSERT INTO nss.festival_calendar_date
                (festival_master_pk, calendar_year, observed_date, is_confirmed)
            VALUES (%s, 2030, DATE '2030-03-15', TRUE)
            """,
            (test_festival_pk,),
        )
    cur.execute("ROLLBACK TO SAVEPOINT test_dup_year_2")


def test_year_mismatch_rejected(write_conn, test_festival_pk):
    """chk_festival_calendar_date_year_matches rejects a calendar_year
    that doesn't match EXTRACT(YEAR FROM observed_date)."""
    cur = write_conn.cursor()
    cur.execute("SAVEPOINT test_year_mismatch")
    with pytest.raises(psycopg2.errors.CheckViolation):
        cur.execute(
            """
            INSERT INTO nss.festival_calendar_date
                (festival_master_pk, calendar_year, observed_date, is_confirmed)
            VALUES (%s, 2031, DATE '2030-03-01', TRUE)
            """,
            (test_festival_pk,),
        )
    cur.execute("ROLLBACK TO SAVEPOINT test_year_mismatch")


# ── Resolver functions: festival_date_for_year / next_festival_date_on_or_after ──

@pytest.fixture
def seeded_test_dates(write_conn, test_festival_pk):
    """
    Seeds the throwaway TEST_FESTIVAL_SCHEMA festival with a confirmed
    2031 date and an unconfirmed (provisional) 2032 date, for the
    resolver-contract tests below. Rolled back with the enclosing
    test_festival_pk SAVEPOINT.
    """
    cur = write_conn.cursor()
    cur.execute(
        """
        INSERT INTO nss.festival_calendar_date
            (festival_master_pk, calendar_year, observed_date, is_confirmed)
        VALUES
            (%s, 2031, DATE '2031-03-10', TRUE),
            (%s, 2032, DATE '2032-03-01', FALSE)
        """,
        (test_festival_pk, test_festival_pk),
    )
    return test_festival_pk


def test_festival_date_for_year_hit(write_conn, seeded_test_dates):
    cur = write_conn.cursor()
    result = festival_date_for_year(cur, "TEST_FESTIVAL_SCHEMA", 2031)
    assert result == date(2031, 3, 10)


def test_festival_date_for_year_miss_returns_none(write_conn, seeded_test_dates):
    """No row at all for the year — never a computed/guessed fallback."""
    cur = write_conn.cursor()
    assert festival_date_for_year(cur, "TEST_FESTIVAL_SCHEMA", 2099) is None


def test_festival_date_for_year_unconfirmed_excluded_by_default(write_conn, seeded_test_dates):
    """A provisional (is_confirmed = FALSE) row is treated as missing data
    unless the caller explicitly opts in via require_confirmed=False."""
    cur = write_conn.cursor()
    assert festival_date_for_year(cur, "TEST_FESTIVAL_SCHEMA", 2032) is None
    assert festival_date_for_year(
        cur, "TEST_FESTIVAL_SCHEMA", 2032, require_confirmed=False,
    ) == date(2032, 3, 1)


def test_next_festival_date_on_or_after_same_year(write_conn, seeded_test_dates):
    """as_of before the observed date in the same calendar year returns
    that date."""
    cur = write_conn.cursor()
    result = next_festival_date_on_or_after(
        cur, "TEST_FESTIVAL_SCHEMA", date(2031, 1, 1),
    )
    assert result == date(2031, 3, 10)


def test_next_festival_date_on_or_after_boundary_rolls_to_next_year(write_conn, seeded_test_dates):
    """as_of after the current year's observed date — and the following
    year's row is unconfirmed — returns None, not a stale/past date."""
    cur = write_conn.cursor()
    result = next_festival_date_on_or_after(
        cur, "TEST_FESTIVAL_SCHEMA", date(2031, 6, 1),
    )
    assert result is None


def test_next_festival_date_on_or_after_missing_data_returns_none(write_conn, test_festival_pk):
    """Nothing seeded at all — resolver returns None, never a computed date."""
    cur = write_conn.cursor()
    result = next_festival_date_on_or_after(
        cur, "TEST_FESTIVAL_SCHEMA", date(2050, 1, 1),
    )
    assert result is None


# ── dola_purnima_credential_validity_window() ───────────────────────────

def test_validity_window_raises_422_when_dates_missing(write_conn, test_festival_pk):
    """
    Uses the real DOLA_PURNIMA festival code but an as_of date far outside
    the seeded 2024-2028 range, so no confirmed row can resolve — must
    raise 422, never fall back to financial_year_bounds().
    """
    cur = write_conn.cursor()
    with pytest.raises(HTTPException) as exc_info:
        dola_purnima_credential_validity_window(cur, date(2099, 1, 1), "ANUMATI_PATRA")
    assert exc_info.value.status_code == 422


def test_validity_window_anumati_mid_year_application(write_conn):
    """
    Anumati Patra: issue_date is a real (non-festival) application date, so
    valid_from is that date itself, and valid_to is the first Dola Purnima
    at least one year later — applying 2026-03-10 means one year on is
    2027-03-10, which is still before Dola Purnima 2027 (2027-03-22), so
    that is the window close.
    """
    cur = write_conn.cursor()
    valid_from, valid_to = dola_purnima_credential_validity_window(
        cur, date(2026, 3, 10), "ANUMATI_PATRA",
    )
    assert valid_from == date(2026, 3, 10)
    assert valid_to == date(2027, 3, 22)


def test_validity_window_anumati_skips_a_too_close_dola_purnima(write_conn):
    """
    An Anumati Patra applicant close enough to an upcoming Dola Purnima
    that it is LESS than a year away must skip it and wait for the one
    after — no mid-year renewal. Applying 2024-03-26 (the day after Dola
    Purnima 2024): one year on is 2025-03-26, which is already past Dola
    Purnima 2025 (2025-03-14, only 353 days after application), so that
    one is too soon to count and the window must run to the NEXT Dola
    Purnima after that, 2026-03-03.
    """
    cur = write_conn.cursor()
    valid_from, valid_to = dola_purnima_credential_validity_window(
        cur, date(2024, 3, 26), "ANUMATI_PATRA",
    )
    assert valid_from == date(2024, 3, 26)
    assert valid_to == date(2026, 3, 3)


def test_validity_window_parichaya_takes_the_very_next_dola_purnima(write_conn):
    """
    Parichaya Patra: issue_date is itself a Dola Purnima (the caller always
    resolves it to one). valid_to is simply the NEXT Dola Purnima — not
    "+1 year, then next Dola" — because consecutive Dola Purnimas are not
    always ~365 days apart (lunar drift): 2027-03-22 -> 2028-03-11 is only
    354 days, which a "+1 year" rule would wrongly skip past, landing on
    2029 instead of 2028.
    """
    cur = write_conn.cursor()
    valid_from, valid_to = dola_purnima_credential_validity_window(
        cur, date(2027, 3, 22), "PARICHAYA_PATRA",
    )
    assert valid_from == date(2027, 3, 22)
    assert valid_to == date(2028, 3, 11)

