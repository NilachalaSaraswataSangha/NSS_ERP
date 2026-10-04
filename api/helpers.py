"""
NSS ERP — Shared API helpers.

Cursor-to-Pydantic conversion functions used by all routers.
Extracted from per-router duplicates to ensure a single point of
maintenance for any future security hardening (e.g. column sanitisation).

Pagination constants are also centralised here so all list endpoints
share the same defaults and validation ranges.

Shared DB helpers:
  - next_id()                    — atomic ID sequence increment
  - get_system_setting()         — nss.system_setting value lookup
  - resolve_or_create_city_village() — lookup/create city_village record
  - get_active_status_pk()       — ACTIVE status master_data PK lookup
  - log_audit()                  — centralized audit trail (system_event_log)
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status

import psycopg2.errors

logger = logging.getLogger(__name__)


# ── Pagination defaults ──────────────────────────────────────────────────

DEFAULT_LIMIT = 100
MAX_LIMIT = 500


# ── Sorting ──────────────────────────────────────────────────────────────
#
# Click-to-sort on a table header sends sort_by/sort_dir. For a paginated
# endpoint the sort MUST happen in SQL: sorting one page client-side
# reorders only the rows already fetched, which shows the user "A–Z" while
# actually giving them A–Z within page 3. That is wrong, not merely
# partial, so ordering belongs in the query.
#
# ORDER BY cannot be a bound parameter — it is part of the statement, not
# a value. So the column has to be interpolated, and the ONLY safe way to
# do that is to never let a caller-supplied string reach the SQL. Each
# endpoint declares a whitelist mapping the public field name to a fixed
# SQL expression it controls; anything not in that map is rejected. No
# caller input is ever concatenated into the statement.

SORT_ASC = "asc"
SORT_DESC = "desc"


def natural_sort_key(column: str) -> list[str]:
    """
    SQL terms that order 'prefix + trailing digits' IDs the way a person
    reads them: SS2 before SS10, AMSAS9 before AMSAS100.

    Plain text collation gets this backwards ('AMSAS100' < 'AMSAS9'
    because '1' < '9'), and every business identifier in this system has
    that shape — person_id P7, sangha_sevi_id SS10,
    local_sakha_erp_id AMSAS9456831. It also keeps SQL ordering
    consistent with the frontend's client-side sort, which is
    numeric-aware; otherwise the same column would order differently
    depending on which table you were looking at.

    Returns two terms: the non-numeric stem, then the trailing number as
    an integer. The regexp yields '' for a value with no trailing digits,
    so NULLIF guards the cast.

    `column` must be a literal chosen by this codebase, never caller
    input — see the module note above.
    """
    return [
        f"regexp_replace({column}, '[0-9]+$', '')",
        f"NULLIF(regexp_replace({column}, '^.*?([0-9]*)$', '\\1'), '')::bigint",
    ]


def build_order_by(
    sort_by: str | None,
    sort_dir: str | None,
    allowed: dict[str, str | list[str]],
    default: str,
) -> str:
    """
    Build a validated ORDER BY clause for a list endpoint.

    Args:
        sort_by:  public field name from the query string, or None
        sort_dir: "asc" | "desc" (case-insensitive), or None
        allowed:  {public field name: SQL term, or list of SQL terms}.
                  Terms are author-controlled — build them with
                  natural_sort_key() or write them literally. NEVER put
                  caller input in here. A list is used rather than a
                  comma-joined string because real expressions contain
                  commas of their own (CONCAT_WS(' ', a, b)), which a
                  split would shred into invalid SQL.
        default:  full ORDER BY body used when sort_by is absent, e.g.
                  "ua.created_at DESC".

    Returns:
        The clause body WITHOUT the leading "ORDER BY".

    Raises:
        HTTPException 422 with a readable message naming the sortable
        columns, so an unknown field is a normal validation failure
        rather than a 500.

    NULLS LAST is applied in both directions to match the frontend rule
    that a blank cell sinks to the bottom — a missing value is not the
    smallest value. A stable tiebreaker is appended so rows with equal
    keys keep a fixed relative order across pages; without it, the same
    row can appear on two pages or on none.
    """
    if not sort_by:
        return default

    expression = allowed.get(sort_by)
    if expression is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"'{sort_by}' is not a sortable column here. "
                f"Sortable columns are: {', '.join(sorted(allowed))}."
            ),
        )

    direction = "DESC" if (sort_dir or "").lower() == SORT_DESC else "ASC"

    terms = [expression] if isinstance(expression, str) else list(expression)
    ordered = ", ".join(f"{term} {direction} NULLS LAST" for term in terms)
    return f"{ordered}, {default}"


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


# ── ID sequence generation ───────────────────────────────────────────────

def next_id(cur, sequence_code: str, *, actor_pk: str | None = None) -> str:
    """
    Atomically increment id_sequence_master and return the new business ID.

    Uses UPDATE ... RETURNING to prevent race conditions.
    Returns: prefix + next_value (e.g. "P3", "SS12", "SAKHA-005").

    *actor_pk* is accepted for call-site compatibility but not written
    to the table (id_sequence_master has no audit-actor column; the DB
    audit trigger records changes automatically).

    Raises HTTPException 500 if the sequence_code does not exist.
    """
    cur.execute(
        """
        UPDATE nss.id_sequence_master
        SET current_value = current_value + 1,
            updated_at = NOW()
        WHERE sequence_code = %s
        RETURNING prefix, current_value
        """,
        (sequence_code,),
    )
    row = cur.fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ID sequence '{sequence_code}' not found.",
        )
    return f"{row[0]}{row[1]}"


def peek_next_id(cur, sequence_code: str) -> str | None:
    """
    Return the business ID that *next_id* WOULD mint next — without
    consuming (incrementing) the sequence.

    This is a read-only preview: it reads the current counter and returns
    ``prefix + (current_value + 1)``, exactly matching next_id's own
    format (which likewise applies no zero-padding). Used by the Create
    Organization form to show "what the org code will be if submitted";
    the authoritative value is only ever minted on submit via next_id, so
    a preview never burns a number and concurrent creates simply mean the
    real value may differ from a stale preview.

    Returns None if the sequence_code does not exist (so callers can treat
    "no sequence for this type" as "no previewable code" rather than error).
    """
    cur.execute(
        """
        SELECT prefix, current_value + 1
        FROM nss.id_sequence_master
        WHERE sequence_code = %s
        """,
        (sequence_code,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return f"{row[0]}{row[1]}"


# ── Credential (Parichaya/Anumati Patra) numbering (MBR-010/014/030A) ────

# Kendra Number format enforced on every parichaya_patra/anumati_patra
# document_number: a legacy credential number (admin/registrant-supplied)
# is stored verbatim, exactly as written on the old paper register —
# no format or year is required or validated (decided 2026-10-01: no one,
# legacy or new, is ever asked to supply a year — new numbers are
# auto-minted as <seq>/<fy_start>/<fy_end> by next_credential_document_number()
# below, legacy numbers are whatever the historical record says, which
# varies across decades and Kendras and is not a fixed shape).


# ── Contact validation (mobile / email) ──────────────────────────────────
#
# Per-country mobile rules. Keyed by dial code (the stored
# person.country_phone_code, e.g. "+91"). Each rule bounds the national
# number's DIGIT COUNT and may add an exact pattern. An unknown dial code
# falls back to the permissive 7–15 range the DB CHECK already allows
# (chk_person_mobile_number_format), so a code we have not catalogued is
# never harder-rejected than the schema itself.
#
# IMPORTANT: this table is mirrored on the frontend in nss-config.js
# (NSS.COUNTRY_PHONE_RULES). Keep the two in sync — there is no build step
# that could share one source across Python and the browser.
COUNTRY_PHONE_RULES: dict[str, dict] = {
    "+91":  {"name": "India",        "min": 10, "max": 10, "pattern": r"^[6-9]\d{9}$", "hint": "10 digits, starting 6–9"},
    "+1":   {"name": "US/Canada",    "min": 10, "max": 10, "pattern": r"^[2-9]\d{9}$", "hint": "10 digits"},
    "+44":  {"name": "UK",           "min": 10, "max": 10, "hint": "10 digits"},
    "+971": {"name": "UAE",          "min": 9,  "max": 9,  "hint": "9 digits"},
    "+65":  {"name": "Singapore",    "min": 8,  "max": 8,  "pattern": r"^[689]\d{7}$", "hint": "8 digits"},
    "+61":  {"name": "Australia",    "min": 9,  "max": 9,  "hint": "9 digits"},
    "+966": {"name": "Saudi Arabia", "min": 9,  "max": 9,  "hint": "9 digits"},
    "+974": {"name": "Qatar",        "min": 8,  "max": 8,  "hint": "8 digits"},
    "+973": {"name": "Bahrain",      "min": 8,  "max": 8,  "hint": "8 digits"},
    "+968": {"name": "Oman",         "min": 8,  "max": 8,  "hint": "8 digits"},
    "+60":  {"name": "Malaysia",     "min": 9,  "max": 10, "hint": "9–10 digits"},
    "+49":  {"name": "Germany",      "min": 10, "max": 11, "hint": "10–11 digits"},
    "+33":  {"name": "France",       "min": 9,  "max": 9,  "hint": "9 digits"},
    "+81":  {"name": "Japan",        "min": 10, "max": 10, "hint": "10 digits"},
    "+86":  {"name": "China",        "min": 11, "max": 11, "hint": "11 digits"},
    "+880": {"name": "Bangladesh",   "min": 10, "max": 10, "hint": "10 digits"},
    "+977": {"name": "Nepal",        "min": 10, "max": 10, "hint": "10 digits"},
    "+94":  {"name": "Sri Lanka",    "min": 9,  "max": 9,  "hint": "9 digits"},
    "+975": {"name": "Bhutan",       "min": 8,  "max": 8,  "hint": "8 digits"},
}
DEFAULT_PHONE_RULE = {"name": None, "min": 7, "max": 15, "hint": "7–15 digits"}

COUNTRY_PHONE_CODE_PATTERN = re.compile(r"^\+[0-9]{1,4}$")
# Pragmatic email format — one @, a dotted domain, a 2+ char alphabetic TLD,
# no whitespace. Mirrors the tightened DB CHECK and the frontend regex.
EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


def validate_mobile(country_phone_code: str | None, mobile_number: str | None) -> None:
    """
    Validate a mobile number against its country's rule (MBR-CONTACT-01).

    No-op when no number is supplied (the mobile-or-email presence rule is
    enforced separately by the callers). When a number IS supplied the code
    must be present and well-formed, the number must be digits only, and its
    length/pattern must satisfy the per-country rule (or the permissive
    fallback for an uncatalogued dial code).

    Raises HTTPException 422 on any violation.
    """
    if not mobile_number:
        return
    if not country_phone_code:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A country phone code (e.g. +91) is required with a mobile number.",
        )
    if not COUNTRY_PHONE_CODE_PATTERN.match(country_phone_code):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Country phone code '{country_phone_code}' is invalid — expected a form like +91.",
        )
    if not mobile_number.isdigit():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Mobile number must contain digits only (no spaces, dashes, or country code).",
        )

    rule = COUNTRY_PHONE_RULES.get(country_phone_code, DEFAULT_PHONE_RULE)
    label = rule["name"] or "This"
    n = len(mobile_number)
    if n < rule["min"] or n > rule["max"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{label} ({country_phone_code}) mobile number must be {rule['hint']} — got {n} digits.",
        )
    pattern = rule.get("pattern")
    if pattern and not re.match(pattern, mobile_number):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"'{mobile_number}' is not a valid {label} ({country_phone_code}) mobile number — expected {rule['hint']}.",
        )


def validate_email(email: str | None) -> None:
    """
    Validate email format (MBR-CONTACT-02). No-op when email is absent.
    Raises HTTPException 422 on an invalid address.
    """
    if not email:
        return
    if len(email) > 254 or not EMAIL_PATTERN.match(email):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"'{email}' is not a valid email address.",
        )


def financial_year_bounds(as_of: date) -> tuple[int, int, date, date]:
    """
    India's NSS financial year: 1 April – 31 March.

    Returns (fy_start_year, fy_end_year, valid_from, valid_to) for the FY
    containing *as_of* — e.g. any date in Sep 2026 through Mar 2027 maps to
    (2026, 2027, 2026-04-01, 2027-03-31).
    """
    fy_start = as_of.year if as_of.month >= 4 else as_of.year - 1
    fy_end = fy_start + 1
    return fy_start, fy_end, date(fy_start, 4, 1), date(fy_end, 3, 31)


def next_credential_document_number(
    cur, credential_type: str, scope_organization_pk, as_of: date | None = None,
) -> str:
    """
    Atomically mint the next Parichaya/Anumati Patra document_number
    ("Kendra Number") for the financial year containing *as_of*
    (default: today) — MBR-030A format ``<seq>/<fy_start>/<fy_end>``
    (e.g. "345/2026/2027").

    *credential_type* is "PARICHAYA_PATRA" or "ANUMATI_PATRA".
    *scope_organization_pk* is the Kendra org for PARICHAYA_PATRA (one
    Kendra-wide counter — the Kendra Sangha issues every Parichaya Patra
    itself) or the issuing Sakha's org for ANUMATI_PATRA (one counter per
    Sakha — each Sakha issues its own Anumati Patra numbers).

    Rows in nss.credential_sequence_counter are created on demand (upsert)
    and the counter resets to 1 every FY, since it's keyed by
    (credential_type, scope_organization_pk, financial_year_start).

    Returns document_number only. Financial-year numbering and
    credential-validity windows are deliberately decoupled (SOL-ARCH-013
    FC-DECISION-01): document_number stays FY-based (MBR-030A, unchanged
    by this function), while valid_from/valid_to are now derived from the
    Dola Purnima reference calendar by the caller — see
    next_festival_date_on_or_after() / festival_date_for_year() below.
    """
    as_of = as_of or date.today()
    fy_start, fy_end, _, _ = financial_year_bounds(as_of)
    cur.execute(
        """
        INSERT INTO nss.credential_sequence_counter
            (credential_type, scope_organization_pk, financial_year_start, current_value)
        VALUES (%s, %s, %s, 1)
        ON CONFLICT (credential_type, scope_organization_pk, financial_year_start)
        DO UPDATE SET current_value = nss.credential_sequence_counter.current_value + 1,
                      updated_at = NOW()
        RETURNING current_value
        """,
        (credential_type, str(scope_organization_pk), fy_start),
    )
    seq = cur.fetchone()[0]
    return f"{seq}/{fy_start}/{fy_end}"


def get_master_data_pk(cur, category_code: str, value_code: str) -> str:
    """
    Resolve a master_data row to its PK by (category_code, value_code) —
    e.g. ("ADDRESS_TYPE", "PERMANENT").

    Raises HTTPException 500 when the value is absent, because a missing
    seeded master_data value is a build/seed defect, not a client error.
    """
    cur.execute(
        """
        SELECT md.master_data_pk
        FROM nss.master_data md
        JOIN nss.master_category mc
          ON mc.master_category_pk = md.master_category_pk
        WHERE mc.category_code = %s
          AND md.value_code = %s
          AND md.is_active = TRUE
        """,
        (category_code, value_code),
    )
    row = cur.fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Master data value {category_code}/{value_code} is missing. "
                f"The database seed is incomplete."
            ),
        )
    return str(row[0])


def parse_optional_date(value, field_label: str) -> date | None:
    """
    Parse an optional ISO date coming off a request body.

    Treats None and "" (what an untouched UI date field actually sends) alike
    as "not provided" -> None, so a NULL reaches the column instead of an
    empty string Postgres would choke on. A non-empty but malformed value is a
    client error, so it raises a clean 422 rather than escaping as a 500 from
    date.fromisoformat().
    """
    if value is None:
        return None
    if isinstance(value, date):
        return value
    value = str(value).strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_label} must be a valid date in YYYY-MM-DD form.",
        )


def patra_year_pair(issue_date: date) -> tuple[int, int]:
    """
    MBR-030H: the authoritative year pair for a Patra issued on *issue_date*
    is the calendar year of the issue date and the year after it.

    A Patra issued any time in 2026 — including a March 2026 Dola Purnima —
    carries 2026/2027. A March-issued Parichaya Patra opens the INCOMING
    membership year, not the outgoing financial year its March date falls in.

    This is exactly what financial_year_bounds(date(issue_date.year, 4, 1))
    yields; expressed directly here so the rule is readable on its own and so
    both the minting path and the validation path cannot drift apart.
    """
    return issue_date.year, issue_date.year + 1


def normalize_patra_document_number(
    supplied: str | None, issue_date: date, card_type: str,
) -> str | None:
    """
    MBR-030H — normalize/validate a Parichaya or Anumati Patra number that a
    human typed, for *any* entry point (registration, claim approval, member
    creation, admin correction).

    Supersedes the retired 2026-10-01 note "no one, legacy or new, is ever
    asked to supply a year" (user decision, 2026-10-03). Nobody is *required*
    to type a year, but anyone may:

        "1"            -> "1/2026/2027"   (year appended automatically)
        "1/2026/2027"  -> "1/2026/2027"   (year verified, kept as given)
        "1/2025/2026"  -> HTTP 422        (wrong year, names the right one)

    Returns None when nothing was supplied, which signals the caller to
    auto-mint from the sequence counter instead (MBR-030A).

    A supplied sequence number is TRUSTED as typed and is NOT replaced by the
    counter's next value — the approving admin is responsible for its
    correctness and can correct it later. Genuine duplicates are still caught
    by the document_number unique constraint.
    """
    if supplied is None:
        return None
    supplied = supplied.strip()
    if not supplied:
        return None

    label = card_type.replace("_", " ").title()
    fy_start, fy_end = patra_year_pair(issue_date)

    def _reject(detail: str):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail,
        )

    parts = [p.strip() for p in supplied.split("/")]
    seq = parts[0]

    if not seq.isdigit():
        _reject(
            f"{label} number '{supplied}' is not valid. Enter just the number "
            f"(e.g. 1), or the full number with its year "
            f"(e.g. 1/{fy_start}/{fy_end})."
        )

    # Number only — append the correct year pair.
    if len(parts) == 1:
        return f"{int(seq)}/{fy_start}/{fy_end}"

    # Number with a year — verify it against the issue date before storing.
    if len(parts) != 3 or not all(p.isdigit() for p in parts[1:]):
        _reject(
            f"{label} number '{supplied}' is not valid. Use the form "
            f"<number>/<year>/<year> — for a Patra issued on "
            f"{issue_date.strftime('%d/%m/%Y')} that is "
            f"{int(seq)}/{fy_start}/{fy_end}."
        )

    given_start, given_end = int(parts[1]), int(parts[2])
    if (given_start, given_end) != (fy_start, fy_end):
        _reject(
            f"{label} number '{supplied}' carries the wrong year. A {label} "
            f"issued on {issue_date.strftime('%d/%m/%Y')} belongs to "
            f"{fy_start}/{fy_end}. Please supply that year's {label} number "
            f"— for example {int(seq)}/{fy_start}/{fy_end}."
        )

    return f"{int(seq)}/{fy_start}/{fy_end}"


# ── Festival reference calendar (SOL-ARCH-013) ──────────────────────────

def festival_date_for_year(
    cur, festival_code: str, calendar_year: int, require_confirmed: bool = True,
) -> date | None:
    """
    Look up the authoritative observed date for *festival_code* in
    *calendar_year* (e.g. "DOLA_PURNIMA", 2026).

    Returns None if no row is on file for that festival/year, or if a row
    exists but is only provisional (is_confirmed = FALSE) and
    *require_confirmed* is True (the default). Never computes or guesses a
    date — SOL-ARCH-013 §3. Callers must treat None as "data missing" and
    raise their own 422, not silently fall back to a different date source
    (e.g. financial_year_bounds()).
    """
    cur.execute(
        """
        SELECT fcd.observed_date, fcd.is_confirmed
        FROM nss.festival_calendar_date fcd
        JOIN nss.festival_master fm ON fm.festival_master_pk = fcd.festival_master_pk
        WHERE fm.festival_code = %s AND fcd.calendar_year = %s AND fcd.is_active = TRUE
        """,
        (festival_code, calendar_year),
    )
    row = cur.fetchone()
    if row is None:
        return None
    observed_date, is_confirmed = row
    if require_confirmed and not is_confirmed:
        return None
    return observed_date


def next_festival_date_on_or_after(
    cur, festival_code: str, as_of: date, require_confirmed: bool = True,
) -> date | None:
    """
    Next observed date for *festival_code* that falls on or after *as_of*
    — the MBR-011A / MBR-029 / credential-validity primitive (SOL-ARCH-013
    §12).

    Looks at *as_of*'s calendar year first, then the following year, since
    Dola Purnima (the only festival in scope today) never straddles
    1 January (OPEN-FC-04). Returns None — never a computed/guessed date —
    if neither year has a usable row; the caller must raise its own 422.
    """
    candidate = festival_date_for_year(cur, festival_code, as_of.year, require_confirmed)
    if candidate is not None and candidate >= as_of:
        return candidate
    return festival_date_for_year(cur, festival_code, as_of.year + 1, require_confirmed)


def previous_festival_date_on_or_before(
    cur, festival_code: str, as_of: date, require_confirmed: bool = True,
) -> date | None:
    """
    Most recent observed date for *festival_code* that falls on or before
    *as_of* — the mirror of next_festival_date_on_or_after(), and the
    primitive that answers "which membership year is *as_of* inside?"
    (SOL-ARCH-013 §12).

    Looks at *as_of*'s calendar year first, then the preceding year, since
    Dola Purnima (the only festival in scope today) never straddles
    1 January (OPEN-FC-04). Returns None — never a computed/guessed date —
    if neither year has a usable row; the caller must raise its own 422.
    """
    candidate = festival_date_for_year(cur, festival_code, as_of.year, require_confirmed)
    if candidate is not None and candidate <= as_of:
        return candidate
    return festival_date_for_year(cur, festival_code, as_of.year - 1, require_confirmed)


def dola_purnima_credential_validity_window(
    cur, issue_date: date, card_type: str,
) -> tuple[date, date]:
    """
    Parichaya Patra / Anumati Patra validity window (SOL-ARCH-013
    FC-DECISION-01, refined 2026-10-03): *valid_from* is *issue_date*
    itself. *valid_to* depends on *card_type* ("PARICHAYA_PATRA" or
    "ANUMATI_PATRA") — the two credential types reach this function with
    very differently shaped *issue_date*, by design (decided 2026-10-03),
    and that difference means they need two different (not one shared)
    rules for *valid_to*:

      - PARICHAYA_PATRA — issued/reissued ONLY on a Dola Purnima; the
        caller resolves *issue_date* to one before calling this. *valid_to*
        is simply the NEXT Dola Purnima after *issue_date* — one Dola
        cycle, however long that cycle naturally runs. This matters
        because consecutive Dola Purnimas are NOT always ~365 days apart
        (lunar calendar drift — e.g. 2027-03-22 → 2028-03-11 is only 354
        days); a "+1 year, then next Dola" rule would wrongly skip that
        next festival and jump to the one after, producing a ~2-year card.
        Taking "the next one" directly avoids that: issued on Dola Purnima
        2026 (2026-03-03) → valid [2026-03-03, 2027-03-22).
      - ANUMATI_PATRA — may be issued any day of the year, whenever a
        probationary member actually applies, so *issue_date* is a real
        application date, not a festival date. Here *valid_to* is the
        first Dola Purnima falling AT LEAST ONE FULL YEAR after
        *issue_date* — a mid-year applicant must legitimately serve past
        the next Dola Purnima and only renews at the one after that (no
        mid-year renewal): applying 2026-10-03 → one year on is
        2027-10-03, already past Dola Purnima 2027 (2027-03-22), so the
        window runs to Dola Purnima 2028 (2028-03-11) → valid
        [2026-10-03, 2028-03-11). (Deferred to a future tier, not
        implemented here: the Sakha President may be able to authorise an
        exception that lets an applicant count the nearer, "too soon"
        Dola Purnima instead — out of scope for this pass.)

    Raises HTTPException 422 if the required Dola Purnima date is not on
    file / not yet confirmed — never silently falls back to a computed
    date.
    """
    if card_type == "PARICHAYA_PATRA":
        search_from = issue_date + timedelta(days=1)
    else:
        try:
            search_from = issue_date.replace(year=issue_date.year + 1)
        except ValueError:
            # 29 February — the following year is not a leap year.
            search_from = issue_date.replace(year=issue_date.year + 1, day=28)
    valid_to = next_festival_date_on_or_after(cur, "DOLA_PURNIMA", search_from)
    if valid_to is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Cannot determine the credential validity window: no confirmed "
                f"Dola Purnima date is on file on or after {search_from.isoformat()}. "
                "An administrator must enter/confirm it in the festival reference "
                "calendar (SOL-ARCH-013) before this credential can be issued."
            ),
        )
    return issue_date, valid_to


# ── System settings ─────────────────────────────────────────────────────

def get_system_setting(cur, setting_key: str) -> str | None:
    """
    Return the active nss.system_setting value for *setting_key*, or None.

    Callers that cannot safely proceed without the value must treat None as a
    configuration error and fail — see compose_local_sakha_erp_id(), where a
    missing marker would silently compose an ID into the wrong namespace.
    """
    cur.execute(
        """
        SELECT setting_value
        FROM   nss.system_setting
        WHERE  setting_key = %s AND is_active = TRUE
        """,
        (setting_key,),
    )
    row = cur.fetchone()
    return row[0] if row else None


# ── Local Sakha ERP ID composition ──────────────────────────────────────

# MBR-030C — Tier 2 local numbering is namespace-separated by membership
# state. The marker that separates the two namespaces is configuration, not
# code: it lives in nss.system_setting so an admin can change it through
# System Settings without a deploy, and so it appears in exactly one place.
DARSHAK_LOCAL_ID_MARKER_SETTING = "MEMBERSHIP_DARSHAK_LOCAL_ID_MARKER"

# The Bye-Law membership type whose local numbers live in the Darshak
# namespace. PROBATIONARY is the authoritative stored code (MBR-006);
# "Darshak" is a UI label only and is never a stored membership type
# (MBR-007), so the namespace decision keys off the official code.
PROBATIONARY_MEMBERSHIP_TYPE_CODE = "PROBATIONARY"


def is_probationary_membership_type(cur, membership_type_pk: str | None) -> bool:
    """
    True when *membership_type_pk* resolves to the PROBATIONARY membership type.

    Used to choose the local-number namespace (MBR-030C). Returns False for a
    NULL/unknown PK: callers use this only to *add* the Darshak marker, and the
    conservative direction is to compose in the Regular namespace, where the
    existing uniqueness constraint will still reject a genuine duplicate.
    """
    if not membership_type_pk:
        return False
    cur.execute(
        "SELECT value_code FROM nss.master_data WHERE master_data_pk = %s",
        (str(membership_type_pk),),
    )
    row = cur.fetchone()
    return bool(row) and row[0] == PROBATIONARY_MEMBERSHIP_TYPE_CODE


def compose_local_sakha_erp_id(
    cur, org_pk: str, local_number: str, *, is_darshak: bool = False
) -> str:
    """
    Build a Tier 2 Local Sakha ERP ID (MBR-030, MBR-030C).

        Regular / Associate:    <short_code><local_number>          ESS000123
        Darshak / Probationary: <short_code><marker><local_number>  ESSD000045

    Looks up the short_code for the given organization PK.
    If short_code is NULL (not yet assigned by admin), raises 422
    so the caller knows to assign it first.

    When *is_darshak* is true the namespace marker is read from
    nss.system_setting (DARSHAK_LOCAL_ID_MARKER_SETTING). A missing or blank
    marker raises 500 rather than defaulting: composing without the marker
    would place a Darshak identifier inside the Regular namespace, where it
    could collide with a Regular member's number and be indistinguishable
    from one afterwards. Failing loudly is the safe direction.

    Because the marker is part of the string, ESS000001 and ESSD000001 are
    distinct values — the two namespaces coexist under the existing
    uq_mem_sakha_aff_local_id constraint with no schema change.
    """
    cur.execute(
        "SELECT short_code, organization_name FROM nss.organization WHERE organization_pk = %s",
        (str(org_pk),),
    )
    row = cur.fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization '{org_pk}' not found.",
        )
    short_code, org_name = row[0], row[1]
    if not short_code:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Organization '{org_name}' does not have a short_code assigned yet. "
                "An admin must set the short_code before members can be enrolled."
            ),
        )
    num = str(local_number).strip()
    if not num:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Local Sakha number is required for non-Darshaka members.",
        )

    marker = ""
    if is_darshak:
        marker = (get_system_setting(cur, DARSHAK_LOCAL_ID_MARKER_SETTING) or "").strip()
        if not marker:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "Darshak local-number namespace marker is not configured. "
                    f"Set the '{DARSHAK_LOCAL_ID_MARKER_SETTING}' system setting "
                    "before enrolling Darshak/Probationary members."
                ),
            )

    return f"{short_code}{marker}{num}"


# ── Sakha-only membership guard (API mirror of MBR-038A trigger) ─────────

def require_sakha_organization(cur, organization_pk: str) -> None:
    """
    Enforce MBR-038A at the API layer: a Member's organizational
    association must reference an organization of type SAKHA_SANGHA.

    This mirrors the database triggers in
    05_membership/14_sakha_only_membership_trigger.sql. The DB is the
    airtight backstop; this helper exists so callers get a clean 422 that
    names the problem instead of a raw trigger exception surfacing as 500.

    The single system-account exception (is_system_account = TRUE, the
    seeded SS1 → Kendra) is deliberately NOT reachable here: the API never
    creates the system account, so every member created through these
    endpoints must be tied to a Sakha, with no exception.

    Raises: HTTPException 422 if organization_pk is not a SAKHA_SANGHA.
    """
    if organization_pk is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "A membership must be tied to a Sakha Sangha (MBR-038A). "
                "No organization was supplied."
            ),
        )

    cur.execute(
        """
        SELECT md.value_code, o.organization_name
        FROM nss.organization o
        JOIN nss.master_data md
            ON md.master_data_pk = o.organization_type_master_data_pk
        WHERE o.organization_pk = %s
        """,
        (str(organization_pk),),
    )
    row = cur.fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The specified organization does not exist.",
        )

    org_type_code, org_name = row
    if org_type_code != "SAKHA_SANGHA":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"A member can only be associated with a Sakha Sangha "
                f"(MBR-038A). '{org_name}' is of type {org_type_code}, "
                "not SAKHA_SANGHA."
            ),
        )


def resolve_kumari_sevak_parent_sakha(
    cur,
    *,
    user,
    organization_type_code: str,
    requested_parent_pk: str | None,
) -> str:
    """
    Resolve/validate the parent Sakha for a KUMARI_SANGHA/SEVAK_SANGHA
    create-or-update (ORG-BR-101/102).

    - NSS-wide NSS_ERP_ADMIN: requested_parent_pk must be supplied by the
      caller (any active Sakha is legal); returned unchanged.
    - NSS_ERP_SAKHA_ADMIN scoped to exactly one Sakha: that Sakha is
      auto-selected and returned, overriding/ignoring a mismatched
      requested_parent_pk is rejected rather than silently overridden.
    - NSS_ERP_SAKHA_ADMIN scoped to more than one Sakha: if the caller
      didn't specify a Sakha, auto-select the one (and only one) of their
      scoped Sakhas that currently lacks an active organization of this
      type; otherwise require an explicit, in-scope selection.
    - A Sakha admin may never act on a Sakha outside their own admin_scope.

    Raises HTTPException (403/422) on any authority or selection failure.
    """
    is_nss_admin = any(s.role_code == "NSS_ERP_ADMIN" for s in user.scopes)
    if is_nss_admin:
        if not requested_parent_pk:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="parent_organization_pk (the target Sakha) is required.",
            )
        return requested_parent_pk

    scoped_sakha_pks = sorted({
        str(s.organization_pk)
        for s in user.scopes
        if s.role_code == "NSS_ERP_SAKHA_ADMIN" and s.organization_pk
    })

    if not scoped_sakha_pks:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Only NSS_ERP_ADMIN or the Sakha's own NSS_ERP_SAKHA_ADMIN "
                "may create or update a Kumari/Sevak Sangha (ORG-BR-101)."
            ),
        )

    if requested_parent_pk:
        if str(requested_parent_pk) not in scoped_sakha_pks:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "A Sakha admin may only act on a Sakha within their own "
                    "admin_scope (ORG-BR-101)."
                ),
            )
        return requested_parent_pk

    if len(scoped_sakha_pks) == 1:
        return scoped_sakha_pks[0]

    # Multiple scoped Sakhas, no explicit selection: auto-select the one
    # (and only one) that lacks an active org of this type (ORG-BR-102).
    cur.execute(
        """
        SELECT o.parent_organization_pk
        FROM nss.organization o
        JOIN nss.master_data md ON md.master_data_pk = o.organization_type_master_data_pk
        WHERE o.parent_organization_pk = ANY(%s::uuid[])
          AND md.value_code = %s
          AND o.is_active = TRUE
        """,
        (scoped_sakha_pks, organization_type_code),
    )
    already_has = {str(r[0]) for r in cur.fetchall()}
    lacking = [pk for pk in scoped_sakha_pks if pk not in already_has]

    if len(lacking) == 1:
        return lacking[0]

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=(
            "You administer more than one Sakha and it isn't unambiguous "
            "which one this applies to — specify parent_organization_pk "
            f"explicitly (ORG-BR-102). Your Sakhas: {', '.join(scoped_sakha_pks)}."
        ),
    )


def resolve_scoped_sakha(
    cur,
    *,
    user,
    requested_organization_pk: str | None,
) -> str:
    """
    Resolve/validate the Sakha an admin is attaching a member-scoped record
    to (Sangha Sevi, a user's membership, etc.) using the standard
    scope-select pattern — the member-attach analogue of
    resolve_kumari_sevak_parent_sakha, but WITHOUT any one-per-Sakha
    cardinality (a Sakha holds many members, so there is nothing to
    auto-disambiguate for a multi-Sakha admin):

      - NSS-wide admin: requested_organization_pk is mandatory (any active
        Sakha is legal); returned unchanged.
      - Admin scoped to exactly one Sakha: that Sakha is auto-selected; a
        mismatched explicit pick is rejected, never silently overridden.
      - Admin scoped to more than one Sakha: an in-scope explicit pick is
        required.

    Authorization mirrors UserContext.has_scope_for_org (exact-match, NOT
    hierarchical): the eligible Sakhas are exactly the caller's SAKHA-level
    scopes, plus every Sakha for an NSS-wide caller. The type check
    (SAKHA_SANGHA) is still the caller's responsibility via
    require_sakha_organization — this helper only settles *which* Sakha.

    Returns the resolved organization_pk (str). Raises HTTPException
    (403/422) on any authority or selection failure.
    """
    if user.is_nss_wide():
        if not requested_organization_pk:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="organization_pk (the target Sakha) is required.",
            )
        return str(requested_organization_pk)

    scoped_sakha_pks = sorted({
        str(s.organization_pk)
        for s in user.scopes
        if s.scope_level == "SAKHA" and s.organization_pk
    })

    if not scoped_sakha_pks:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You are not scoped to any Sakha, so no target Sakha can be "
                "resolved. Supply organization_pk for a Sakha within your scope."
            ),
        )

    if requested_organization_pk:
        if str(requested_organization_pk) not in scoped_sakha_pks:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "You may only act on a Sakha within your own admin_scope."
                ),
            )
        return str(requested_organization_pk)

    if len(scoped_sakha_pks) == 1:
        return scoped_sakha_pks[0]

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=(
            "You are scoped to more than one Sakha — specify organization_pk "
            f"explicitly. Your Sakhas: {', '.join(scoped_sakha_pks)}."
        ),
    )


# ── Sakha affiliation insert (single owner for the uniqueness rule) ──────

def insert_sakha_affiliation(
    cur,
    *,
    sangha_sevi_pk: str,
    organization_pk: str,
    local_number: str,
    effective_from,
    is_darshak: bool = False,
) -> str:
    """
    Insert a nss.membership_sakha_affiliation row for a member's local number.

    Single owner for this write — create_user() and create_sangha_sevi() both
    route through here so the composition rule and the duplicate-number
    response stay identical.

    *is_darshak* selects the Darshak/Probationary local-number namespace
    (MBR-030C); see compose_local_sakha_erp_id().

    Enforces MBR-038A (Sakha-only) via require_sakha_organization() before the
    insert, mirroring the DB trigger so a non-Sakha org yields a clean 422
    rather than a raw trigger exception.

    nss.membership_sakha_affiliation carries
        CONSTRAINT uq_mem_sakha_aff_local_id UNIQUE (organization_pk, local_sakha_erp_id)
    Without handling, a reused number raises psycopg2.errors.UniqueViolation,
    which escapes as an unhandled 500 with no usable `detail` — the caller sees
    only "Failed (500)". This converts it to a 409 naming the number and Sakha.

    The INSERT runs inside a SAVEPOINT. That matters: once PostgreSQL raises
    inside a transaction, the whole transaction is aborted and every later
    statement fails with InFailedSqlTransaction. Rolling back to the savepoint
    leaves the connection usable, so the caller can still raise a clean
    HTTPException (and so test suites sharing one connection do not cascade).

    Returns: membership_sakha_affiliation_pk as a string.
    Raises: HTTPException 409 if the number is already taken in that Sakha,
            HTTPException 422 if organization_pk is not a SAKHA_SANGHA.
    """
    require_sakha_organization(cur, organization_pk)

    composed_id = compose_local_sakha_erp_id(
        cur, organization_pk, local_number, is_darshak=is_darshak
    )

    cur.execute("SAVEPOINT sakha_affiliation_insert")
    try:
        cur.execute(
            """
            INSERT INTO nss.membership_sakha_affiliation (
                sangha_sevi_pk, organization_pk,
                local_sakha_erp_id, effective_from,
                affiliation_status, source_event_type
            ) VALUES (%s, %s, %s, COALESCE(%s, CURRENT_DATE), 'ACTIVE', 'ENROLLMENT')
            RETURNING membership_sakha_affiliation_pk
            """,
            (str(sangha_sevi_pk), str(organization_pk), composed_id, effective_from),
        )
        aff_pk = cur.fetchone()[0]
    except psycopg2.errors.UniqueViolation:
        cur.execute("ROLLBACK TO SAVEPOINT sakha_affiliation_insert")
        cur.execute(
            "SELECT organization_name FROM nss.organization WHERE organization_pk = %s",
            (str(organization_pk),),
        )
        row = cur.fetchone()
        sakha_name = row[0] if row and row[0] else "this Sakha"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Local Sakha number '{str(local_number).strip()}' is already "
                f"assigned to another member of {sakha_name} "
                f"(ID {composed_id}). Local numbers are never reassigned — "
                "please use a different number."
            ),
        )
    cur.execute("RELEASE SAVEPOINT sakha_affiliation_insert")
    return str(aff_pk)


def issue_membership_credential(
    cur,
    *,
    sangha_sevi_pk: str,
    membership_type_pk: str | None,
    organization_pk: str,
    document_number: str | None = None,
    issue_date: date | None = None,
    issue_year: int | None = None,
    valid_from: date | None = None,
    valid_to: date | None = None,
    joining_date: date | None = None,
    date_of_birth: date | None = None,
    president_override: bool = False,
) -> tuple[str, str, str]:
    """
    Issue the mandatory credential for a newly-created Sangha Sevi
    (MBR-010/014/019A/B): an Anumati Patra for a PROBATIONARY member,
    a Parichaya Patra for everyone else (REGULAR/ASSOCIATE).

    Single owner for this write — create_sangha_sevi() and create_user()'s
    bundled-SS branch both route through here, mirroring
    insert_sakha_affiliation()'s convention just above.

    Two paths, selected by whether *document_number* is provided:
      - Omitted: mints a new number for the current membership year via
        next_credential_document_number() (Kendra-wide sequence for
        Parichaya Patra, Sakha-wide for Anumati Patra — MBR-030A). The
        number is stamped <seq>/<CY>/<CY+1> where CY is the calendar year
        of *issue_date* — so a Parichaya Patra renewed on Dola Purnima
        2026 (2026-03-03) is numbered .../2026/2027 (the INCOMING membership
        year it opens), never .../2025/2026, even though that March date
        sits in the outgoing financial year. An Anumati Patra applied for
        on any day of calendar 2026 is likewise numbered .../2026/2027.
      - Provided: records an already-issued legacy credential as-is.
    *valid_from*/*valid_to* default to the Dola Purnima validity window
    (SOL-ARCH-013 FC-DECISION-01): *valid_from* = *issue_date*; *valid_to*
    = the first Dola Purnima at least one year later. Decoupled from the
    financial year — only numbering follows the FY-style stamp.

    *issue_date* is resolved by credential type (decided 2026-10-03):
      - PARICHAYA_PATRA — issued/reissued ONLY on a Dola Purnima. Defaults
        to the most recent Dola Purnima on/before today (or, if *issue_year*
        is explicitly passed, that year's Dola Purnima). 422 if that date
        is not confirmed in the festival reference calendar.
      - ANUMATI_PATRA — may be issued ANY day, whenever the probationary
        member actually applies. Defaults to date.today().
    An explicit *issue_date* always wins over both.

    Rules enforced here (shared across all call sites):
      - MBR-030H (new 2026-10-03, SUPERSEDES the retired MBR-030D "stored
        verbatim" rule): a supplied *document_number* is normalized and
        validated by normalize_patra_document_number(). A bare number gets
        the correct year pair appended; a number supplied WITH a year is
        verified against the issue date and refused (422) if the year is
        wrong. The sequence number itself is trusted as typed and is never
        replaced by the counter. Omit *document_number* entirely to auto-mint
        (MBR-030A).
      - MBR-030E (joining-date gate) and MBR-030F (min-age-10 gate) are
        RETIRED (2026-10-03): in practice there is no reliable joining date,
        and no minimum-age rule applies. *joining_date* / *date_of_birth*
        remain in the signature for call-site compatibility but no longer
        gate issuance.
      - MBR-030G (new 2026-10-03) — a lapsed Parichaya Patra cannot be
        renewed late. If the member's most recent Parichaya Patra expired
        before today, a fresh one is refused (422); the member must re-enter
        the cycle via a new Anumati Patra. The Sakha President may authorise
        an exception by setting *president_override*=True.

    Returns (card_type, credential_pk, document_number) —
    card_type is "ANUMATI_PATRA" or "PARICHAYA_PATRA".

    Raises HTTPException 409 if document_number collides with an existing
    credential, or this member already holds an active one of this type.
    Raises HTTPException 422 if a supplied document_number carries a year
    that does not match the issue date (MBR-030H).
    """
    is_probationary = is_probationary_membership_type(cur, membership_type_pk)
    card_type = "ANUMATI_PATRA" if is_probationary else "PARICHAYA_PATRA"

    # issue_date resolution is card-type-specific (decided 2026-10-03):
    # a Parichaya Patra is only ever issued/reissued ON a Dola Purnima, so it
    # defaults to the most recent one on/before today (or an explicit
    # issue_year's Dola Purnima); an Anumati Patra may be issued any day,
    # whenever the probationary member actually applies, so it defaults to
    # today. An explicit issue_date, when given, always wins. Dola Purnima
    # dates come from the festival reference calendar only — never computed.
    if issue_date is None:
        if card_type == "PARICHAYA_PATRA":
            if issue_year is not None:
                issue_date = festival_date_for_year(cur, "DOLA_PURNIMA", issue_year)
                if issue_date is None:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=(
                            f"No confirmed Dola Purnima date is on file for {issue_year}. "
                            "An administrator must enter/confirm it in the festival "
                            "reference calendar (SOL-ARCH-013) before a Parichaya Patra "
                            "can be issued for that year."
                        ),
                    )
            else:
                issue_date = previous_festival_date_on_or_before(
                    cur, "DOLA_PURNIMA", date.today(),
                )
                if issue_date is None:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=(
                            "No confirmed Dola Purnima date is on file on or before "
                            f"{date.today().isoformat()}. An administrator must "
                            "enter/confirm it in the festival reference calendar "
                            "(SOL-ARCH-013) before a Parichaya Patra can be issued."
                        ),
                    )
        else:  # ANUMATI_PATRA — issued any day, whenever applied for.
            issue_date = date.today()

    # Validity window — the rule differs by card_type (see
    # dola_purnima_credential_validity_window's docstring): Parichaya takes
    # the NEXT Dola Purnima outright; Anumati takes the first Dola Purnima
    # at least one year out. SOL-ARCH-013 FC-DECISION-01.
    if valid_from is None or valid_to is None:
        window_from, window_to = dola_purnima_credential_validity_window(
            cur, issue_date, card_type,
        )
        valid_from = valid_from or window_from
        valid_to = valid_to or window_to

    # MBR-030G (new 2026-10-03) — a lapsed Parichaya Patra cannot be renewed
    # late: a member who missed their Dola Purnima renewal must re-enter the
    # cycle via a fresh Anumati Patra. Only guards the fresh (auto-numbered)
    # Parichaya path — legacy imports are recorded verbatim. The Sakha
    # President may authorise an exception via president_override.
    if card_type == "PARICHAYA_PATRA" and not document_number and not president_override:
        cur.execute(
            "SELECT MAX(valid_to) FROM nss.parichaya_patra WHERE sangha_sevi_pk = %s",
            (str(sangha_sevi_pk),),
        )
        row = cur.fetchone()
        prior_valid_to = row[0] if row else None
        if prior_valid_to is not None and prior_valid_to < date.today():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"This member's Parichaya Patra lapsed on "
                    f"{prior_valid_to.isoformat()} and cannot be renewed late. "
                    "The member must re-apply for an Anumati Patra to re-enter "
                    "the membership cycle, unless the Sakha President authorises "
                    "an exception."
                ),
            )

    # MBR-030H (user, 2026-10-03): whoever typed this number may have typed
    # it with or without a year. Normalize/validate it HERE — this is the one
    # choke point every entry path (registration, claim approval, admin member
    # creation) funnels through, so no caller can bypass the rule. Returns
    # None when nothing was supplied, falling through to auto-mint below.
    document_number = normalize_patra_document_number(
        document_number, issue_date, card_type,
    )

    if not document_number:
        # Auto-mint for the membership year this Patra opens — stamped
        # <seq>/<CY>/<CY+1> for CY = issue_date's calendar year (MBR-030A,
        # year pair per MBR-030H / patra_year_pair()).
        scope_organization_pk = (
            organization_pk if card_type == "ANUMATI_PATRA"
            else get_kendra_organization_pk(cur)
        )
        if scope_organization_pk is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Cannot auto-generate a Parichaya Patra number: no active KENDRA organization exists.",
            )
        document_number = next_credential_document_number(
            cur, card_type, scope_organization_pk,
            as_of=date(issue_date.year, 4, 1),
        )

    table = "anumati_patra" if card_type == "ANUMATI_PATRA" else "parichaya_patra"
    pk_column = f"{table}_pk"
    cur.execute(f"SAVEPOINT {table}_insert")
    try:
        if card_type == "ANUMATI_PATRA":
            cur.execute(
                f"""
                INSERT INTO nss.{table} (
                    sangha_sevi_pk, issuing_organization_pk, document_number,
                    issue_date, valid_from, valid_to
                ) VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING {pk_column}
                """,
                (str(sangha_sevi_pk), str(organization_pk), document_number,
                 issue_date, valid_from, valid_to),
            )
        else:
            cur.execute(
                f"""
                INSERT INTO nss.{table} (
                    sangha_sevi_pk, document_number, issue_date, valid_from, valid_to,
                    affiliated_organization_pk
                ) VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING {pk_column}
                """,
                (str(sangha_sevi_pk), document_number, issue_date, valid_from, valid_to, str(organization_pk)),
            )
        credential_pk = cur.fetchone()[0]
    except psycopg2.errors.UniqueViolation as exc:
        cur.execute(f"ROLLBACK TO SAVEPOINT {table}_insert")
        # Two very different failures land here; conflating them makes the
        # cause undiagnosable from the response alone, so name the one that
        # actually fired rather than reporting both as a possibility.
        constraint = getattr(getattr(exc, "diag", None), "constraint_name", None) or ""
        label = card_type.replace("_", " ").title()
        if "active_per_member" in constraint:
            detail = f"This member already holds an active {label}."
        elif "document_number" in constraint:
            detail = f"{label} number '{document_number}' is already in use."
        else:
            detail = (
                f"Could not issue this {label}: a uniqueness constraint "
                f"({constraint or 'unknown'}) was violated."
            )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
    cur.execute(f"RELEASE SAVEPOINT {table}_insert")
    return card_type, str(credential_pk), document_number


def fetch_person_date_of_birth(cur, person_pk: str) -> date | None:
    """
    Look up a person's date_of_birth by person_pk.

    Small shared lookup for issue_membership_credential()'s MBR-030F
    (min-age-10) check — callers that only have person_pk on hand
    (admin create-SS, claim approval) use this instead of threading the
    value through their own request payload.
    """
    cur.execute(
        "SELECT date_of_birth FROM nss.person WHERE person_pk = %s",
        (str(person_pk),),
    )
    row = cur.fetchone()
    return row[0] if row else None


# ── City/Village lookup or create ────────────────────────────────────────

def resolve_or_create_city_village(cur, name: str, district_pk: str, *, actor_pk: str | None = None) -> str:
    """
    Resolve a city/village by name + district, creating it if not found.

    Lookup is case-insensitive. On create, generates a code from the
    uppercase name (max 20 chars) and defaults city_village_type to 'CITY'.

    *actor_pk* is accepted for call-site compatibility but not written
    to the table (the DB audit trigger records the actor automatically).

    Returns: city_village_pk as a string.
    """
    cv_name = name.strip()
    cur.execute(
        """
        SELECT city_village_pk FROM nss.city_village
        WHERE LOWER(city_village_name) = LOWER(%s)
          AND district_pk = %s
          AND is_active = TRUE
        LIMIT 1
        """,
        (cv_name, district_pk),
    )
    row = cur.fetchone()
    if row:
        return str(row[0])

    # Create new city_village record
    cv_code = cv_name.upper().replace(" ", "_")[:20]
    cur.execute(
        """
        INSERT INTO nss.city_village (
            district_pk, city_village_code, city_village_name,
            city_village_type
        ) VALUES (%s, %s, %s, 'CITY')
        RETURNING city_village_pk
        """,
        (district_pk, cv_code, cv_name),
    )
    return str(cur.fetchone()[0])


# ── Postal code lookup or create ────────────────────────────────────────

def resolve_or_create_postal_code(cur, postal_code_value: str, state_pk: str, country_pk: str, *, actor_pk: str | None = None) -> str:
    """
    Resolve a postal code by value, creating it if not found.

    Simplified Geography Model (2026-10-02): nss.postal_code is unique
    on postal_code alone — one row per PIN globally, carrying a
    pre-resolved dominant state_pk. So the lookup must NOT be scoped by
    state: a PIN that already exists under a different dominant state is
    still the same row, and re-scoping the lookup would miss it and then
    trip the unique constraint on insert.

    *state_pk* is used only when creating a genuinely new PIN.
    *country_pk* is accepted for call-site compatibility but no longer
    stored (it's derived via state.country_pk).

    *actor_pk* is accepted for call-site compatibility but not written
    to the table (the DB audit trigger records the actor automatically).

    Returns: postal_code_pk as a string.
    """
    code = postal_code_value.strip()
    cur.execute(
        """
        SELECT postal_code_pk FROM nss.postal_code
        WHERE postal_code = %s
          AND is_active = TRUE
        LIMIT 1
        """,
        (code,),
    )
    row = cur.fetchone()
    if row:
        return str(row[0])

    # Create new postal_code record
    cur.execute(
        """
        INSERT INTO nss.postal_code (
            state_pk, postal_code
        ) VALUES (%s, %s)
        RETURNING postal_code_pk
        """,
        (state_pk, code),
    )
    return str(cur.fetchone()[0])


# ── Post office lookup or create ────────────────────────────────────────

def resolve_or_create_post_office(cur, name: str, postal_code_pk: str, *, actor_pk: str | None = None) -> str:
    """
    Resolve a post office by name + PIN, creating it if not found.

    Mirrors resolve_or_create_city_village — case-insensitive exact match
    scoped to the given postal_code_pk. On create, the row lands as
    entry_status='APPROVED' by column default (same as city_village and
    postal_code), consistent with the registration-time auto-create path;
    it is NOT routed through the member-authenticated PENDING "propose"
    flow (api/routers/foundation.py propose_post_office), since a person
    registering has no JWT yet.

    *actor_pk* is accepted for call-site compatibility but not written
    to the table (the DB audit trigger records the actor automatically).

    Returns: post_office_pk as a string.
    """
    po_name = name.strip()
    cur.execute(
        """
        SELECT post_office_pk FROM nss.post_office
        WHERE LOWER(post_office_name) = LOWER(%s)
          AND postal_code_pk = %s
          AND is_active = TRUE
        LIMIT 1
        """,
        (po_name, postal_code_pk),
    )
    row = cur.fetchone()
    if row:
        return str(row[0])

    # Create new post_office record
    cur.execute(
        """
        INSERT INTO nss.post_office (
            postal_code_pk, post_office_name
        ) VALUES (%s, %s)
        RETURNING post_office_pk
        """,
        (postal_code_pk, po_name),
    )
    return str(cur.fetchone()[0])


# ── ACTIVE status master_data PK ────────────────────────────────────────

def get_active_status_pk(cur) -> str:
    """
    Look up the master_data_pk for STATUS / ACTIVE.

    Returns: master_data_pk as a string.
    Raises HTTPException 500 if not found (seed data problem).
    """
    cur.execute(
        """
        SELECT md.master_data_pk
        FROM nss.master_data md
        JOIN nss.master_category mc ON mc.master_category_pk = md.master_category_pk
        WHERE mc.category_code = 'STATUS'
          AND md.value_code = 'ACTIVE'
          AND md.is_active = TRUE
        LIMIT 1
        """,
    )
    row = cur.fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ACTIVE status not found in master_data.",
        )
    return str(row[0])


def get_kendra_organization_pk(cur) -> str | None:
    """
    Look up the single active KENDRA organization's pk.

    Shared by create_organization's single-instance-parent auto-resolution
    and the credential-issuance flow (Parichaya Patra numbering is
    Kendra-wide — MBR-030A) — previously duplicated inline in the former.
    Returns None if no active KENDRA row exists.
    """
    cur.execute(
        """
        SELECT o.organization_pk
        FROM nss.organization o
        JOIN nss.master_data md ON md.master_data_pk = o.organization_type_master_data_pk
        WHERE md.value_code = 'KENDRA' AND o.is_active = TRUE
        LIMIT 1
        """
    )
    row = cur.fetchone()
    return str(row[0]) if row else None


# ── Centralized audit trail ─────────────────────────────────────────────

def log_audit(
    cur,
    *,
    action: str,
    table_name: str,
    record_pk: str,
    actor_pk: str | None = None,
    actor_user_account_pk: str | None = None,
    module: str | None = None,
    summary: str | None = None,
    detail: dict[str, Any] | None = None,
    is_success: bool | None = True,
) -> None:
    """
    Insert one row into ``nss.system_event_log``.

    This is the single entry-point for all audit logging.  Every
    authenticated write operation (INSERT, UPDATE, soft-DELETE, APPROVE,
    REJECT, STATUS_CHANGE, PASSWORD_CHANGE, etc.) should call this
    immediately after the business SQL succeeds.

    Parameters
    ----------
    cur : psycopg2 cursor (must be inside an open transaction)
    action : verb — CREATE, UPDATE, DELETE, APPROVE, REJECT,
             STATUS_CHANGE, PASSWORD_CHANGE, LOGIN, etc.
    table_name : affected table, e.g. ``'person'``, ``'sangha_sevi'``
    record_pk : PK of the affected row (as string UUID)
    actor_pk : ``sangha_sevi_pk`` of the person performing the action
    actor_user_account_pk : ``user_account_pk`` — useful for login events
               or when sangha_sevi doesn't exist yet
    module : functional area, e.g. ``'admin'``, ``'auth'``,
             ``'claim_approval'``, ``'family'``, ``'registration'``
    summary : one-line human description
    detail : optional dict (stored as JSONB) — changed fields,
             before/after values, request context, etc.
    is_success : True (default), False, or None
    """
    try:
        cur.execute(
            """
            INSERT INTO nss.system_event_log
                (action, table_name, record_pk,
                 actor_sangha_sevi_pk, actor_user_account_pk,
                 module, summary, detail, is_success)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                action,
                table_name,
                record_pk,
                actor_pk,
                actor_user_account_pk,
                module,
                summary,
                json.dumps(detail) if detail else None,
                is_success,
            ),
        )
    except Exception:
        # Audit logging must NEVER break the business transaction.
        # Log the failure and continue.
        logger.exception("Failed to write audit log: action=%s table=%s record=%s", action, table_name, record_pk)


# ── Entity existence check ─────────────────────────────────────────────

def require_entity(
    cur,
    table: str,
    pk_value: str,
    *,
    label: str = "Record",
    pk_column: str | None = None,
    status_code: int = 404,
) -> None:
    """
    Assert that an active row exists in ``nss.<table>``.

    By convention, PK column = ``<table>_pk``.  Override with *pk_column*
    when the table name doesn't match (e.g. ``master_data``).

    Raises HTTPException(<status_code>) if not found.
    """
    col = pk_column or f"{table}_pk"
    # Using format for table/column identifiers is safe here — the caller
    # controls these values (never user input).
    cur.execute(
        f"SELECT 1 FROM nss.{table} WHERE {col} = %s AND is_active = TRUE",
        (str(pk_value),),
    )
    if cur.fetchone() is None:
        raise HTTPException(
            status_code=status_code,
            detail=f"{label} not found.",
        )


def require_self_or_permission(
    resource_pk,
    self_pk,
    permission_code: str,
    user,
    *,
    detail: str,
) -> None:
    """
    403 unless the caller holds *permission_code*, or *resource_pk* is their
    own (*self_pk* — e.g. UserContext.person_pk/sangha_sevi_pk). Shared
    control flow behind person.py's _require_person_view and membership.py's
    _require_member_view: without a self-access carve-out, a regular
    member's own dashboard (no admin permissions) can't load its own
    person/membership record — mirrors the ownership pattern family.py
    already uses for /families.
    """
    if user.has_permission(permission_code):
        return
    if self_pk is not None and str(resource_pk) == str(self_pk):
        return
    raise HTTPException(status_code=403, detail=detail)



# ── Duplicate contact check ────────────────────────────────────────────

def check_duplicate_contact(
    cur,
    *,
    mobile_number: str | None = None,
    country_phone_code: str | None = None,
    email: str | None = None,
    exclude_person_pk: str | None = None,
) -> None:
    """
    Raise HTTP 409 if a person with the same mobile or email already exists.

    *exclude_person_pk* is used for UPDATE flows (don't conflict with self).
    """
    if mobile_number and country_phone_code:
        sql = (
            "SELECT person_pk FROM nss.person "
            "WHERE country_phone_code = %s AND mobile_number = %s AND is_active = TRUE"
        )
        params: list = [country_phone_code, mobile_number]
        if exclude_person_pk:
            sql += " AND person_pk != %s"
            params.append(exclude_person_pk)
        cur.execute(sql, params)
        if cur.fetchone():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A person with this mobile number already exists.",
            )

    if email:
        sql = (
            "SELECT person_pk FROM nss.person "
            "WHERE LOWER(email) = LOWER(%s) AND is_active = TRUE"
        )
        params = [email]
        if exclude_person_pk:
            sql += " AND person_pk != %s"
            params.append(exclude_person_pk)
        cur.execute(sql, params)
        if cur.fetchone():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A person with this email already exists.",
            )


# ── Person profile update (self-service + admin) ───────────────────────

# person column -> master_category.category_code it must belong to.
PERSON_MASTER_DATA_FIELDS = {
    "gender_master_data_pk": "GENDER",
    "marital_status_master_data_pk": "MARITAL_STATUS",
    "blood_group_master_data_pk": "BLOOD_GROUP",
    "emergency_relationship_master_data_pk": "RELATIONSHIP",
}


def _validate_master_data_category(cur, master_data_pk, expected_category_code: str) -> None:
    """Raise 422 unless *master_data_pk* is an active value in the expected
    master-data category (the FK alone can't stop e.g. a blood-group pk being
    stored in the gender column)."""
    cur.execute(
        """
        SELECT 1
        FROM   nss.master_data md
        JOIN   nss.master_category mc ON mc.master_category_pk = md.master_category_pk
        WHERE  md.master_data_pk = %s
          AND  mc.category_code = %s
          AND  md.is_active = TRUE
        """,
        (str(master_data_pk), expected_category_code),
    )
    if cur.fetchone() is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid value for {expected_category_code.lower().replace('_', ' ')}.",
        )


def apply_person_profile_update(
    cur,
    *,
    person_pk: str,
    body,
    updated_by_sangha_sevi_pk: str | None = None,
) -> bool:
    """
    Validate and apply a partial personal-info update to nss.person.

    Shared by the self-service (PATCH /auth/profile) and admin
    (PATCH /admin/persons/{pk}) edit surfaces so both enforce identical rules
    (SOL-PERSON full personal-info edit, 2026-10-03). *body* is any object
    exposing the Update*Request attributes; only attributes that are present
    AND non-None are applied (PATCH semantics).

    Returns True if a row was updated, False if there was nothing to update,
    and raises HTTPException on a validation failure. The CALLER is
    responsible for permission / scope gating before invoking this; name is
    editable here (both surfaces permit it).
    """
    updates: dict[str, object] = {}

    # ── Name (first_name is NOT NULL — editable but may not be blanked) ──
    if getattr(body, "first_name", None) is not None:
        fn = body.first_name.strip()
        if not fn:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="First name cannot be blank.",
            )
        updates["first_name"] = fn.title()
    if getattr(body, "middle_name", None) is not None:
        updates["middle_name"] = body.middle_name.strip().title() or None
    if getattr(body, "last_name", None) is not None:
        updates["last_name"] = body.last_name.strip().title() or None

    # ── Contact ──
    if getattr(body, "mobile_number", None) is not None:
        updates["mobile_number"] = body.mobile_number.strip() or None
    if getattr(body, "country_phone_code", None) is not None:
        updates["country_phone_code"] = body.country_phone_code.strip() or None
    if getattr(body, "email", None) is not None:
        updates["email"] = body.email.strip() or None
    if getattr(body, "date_of_birth", None) is not None:
        updates["date_of_birth"] = body.date_of_birth.strip() or None

    # ── Emergency contact + remarks ──
    if getattr(body, "emergency_contact_name", None) is not None:
        updates["emergency_contact_name"] = body.emergency_contact_name.strip().title() or None
    if getattr(body, "emergency_contact_phone", None) is not None:
        updates["emergency_contact_phone"] = body.emergency_contact_phone.strip() or None
    if getattr(body, "remarks", None) is not None:
        updates["remarks"] = body.remarks.strip() or None

    # ── Demographics + relationship (master_data FKs, category-validated) ──
    for field, category_code in PERSON_MASTER_DATA_FIELDS.items():
        val = getattr(body, field, None)
        if val is not None:
            _validate_master_data_category(cur, val, category_code)
            updates[field] = str(val)

    if not updates:
        return False

    # ── Contact validation on EFFECTIVE values (mirror self-service rules) ──
    if "email" in updates:
        validate_email(updates["email"])
    if "mobile_number" in updates or "country_phone_code" in updates:
        cur.execute(
            "SELECT country_phone_code, mobile_number FROM nss.person WHERE person_pk = %s",
            (str(person_pk),),
        )
        cur_contact = cur.fetchone() or (None, None)
        eff_code = updates["country_phone_code"] if "country_phone_code" in updates else cur_contact[0]
        eff_mobile = updates["mobile_number"] if "mobile_number" in updates else cur_contact[1]
        validate_mobile(eff_code, eff_mobile)

    if any(k in updates for k in ("mobile_number", "country_phone_code", "email")):
        check_duplicate_contact(
            cur,
            mobile_number=updates.get("mobile_number"),
            country_phone_code=updates.get("country_phone_code"),
            email=updates.get("email"),
            exclude_person_pk=str(person_pk),
        )

    # ── Build + execute UPDATE ──
    set_parts = ["updated_at = NOW()"]
    params: list = []
    if updated_by_sangha_sevi_pk is not None:
        set_parts.append("updated_by_sangha_sevi_pk = %s")
        params.append(str(updated_by_sangha_sevi_pk))
    for col, val in updates.items():
        set_parts.append(f"{col} = %s")
        params.append(val)
    params.append(str(person_pk))

    cur.execute(
        f"UPDATE nss.person SET {', '.join(set_parts)} "
        f"WHERE person_pk = %s AND is_active = TRUE",
        params,
    )
    return cur.rowcount > 0


# ── Password history ───────────────────────────────────────────────────

def record_password_history(
    cur,
    user_account_pk: str,
    password_hash: str,
    reason: str = "CHANGE",
    *,
    actor_pk: str | None = None,
) -> None:
    """
    Insert a row into ``nss.password_history``.

    *actor_pk* is accepted for call-site compatibility but not written
    to the table (the DB audit trigger records the actor automatically).
    """
    cur.execute(
        """
        INSERT INTO nss.password_history (
            user_account_pk, password_hash, changed_reason
        ) VALUES (%s, %s, %s)
        """,
        (str(user_account_pk), password_hash, reason),
    )


# ── Password validate + hash + expiry ──────────────────────────────────

def validate_and_hash_password(password: str) -> tuple[str, datetime]:
    """
    Validate password against policy, hash it, compute expiry.

    Returns ``(password_hash, password_expires_at)``.
    Raises HTTPException 422 if policy violations exist.
    """
    from api.services.auth_service import hash_password, validate_password_policy
    from api.config import settings

    violations = validate_password_policy(password)
    if violations:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=violations,
        )
    pw_hash = hash_password(password)
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.PASSWORD_EXPIRY_DAYS
    )
    return pw_hash, expires_at


# ── FAM-036: family majority-rule "effective Sakha" CTE ──────────────────
# Shared between api/routers/family.py's _FAMILY_SELECT (single-family
# reads, incl. /sakha-alignment) and api/routers/organization.py's
# _CHILDREN_STATS_SQL (aggregate counts across a whole org subtree) — both
# need "which Sakha does the majority of this family's active-affiliation
# members belong to." Previously duplicated byte-for-byte in both files
# (a real, previously-tracked gap — see CLAUDE.md's Deferred Items); this
# is the one shared copy. No trailing comma — the CTE-list comma/closing
# paren is the caller's responsibility, since the two callers splice it
# into different positions inside their own WITH clauses.
FAMILY_MAJORITY_CTE_SQL = """
    family_majority AS (
        SELECT fr.family_group_pk,
               aff.organization_pk  AS sakha_pk,
               COUNT(*)             AS cnt,
               ROW_NUMBER() OVER (
                   PARTITION BY fr.family_group_pk
                   ORDER BY COUNT(*) DESC
               ) AS rn
        FROM   nss.family_relationship fr
        JOIN   nss.sangha_sevi ss
               ON ss.person_pk = fr.person_pk AND ss.is_active = TRUE
        JOIN   nss.membership_sakha_affiliation aff
               ON aff.sangha_sevi_pk = ss.sangha_sevi_pk
              AND aff.effective_to IS NULL
        WHERE  fr.is_current = TRUE
        GROUP BY fr.family_group_pk, aff.organization_pk
    )
"""

# ── Shared nss.organization address-JOIN chain ────────────────────────────
# Used by organization.py's _ORG_SELECT and admin.py's
# list_organizations_admin — previously duplicated with different table
# aliases in each (co/st/dt vs c/s/d), now one shared copy. The caller's
# base query must alias the organization row as "o"; this fragment always
# uses c/s/d/cv/pc for country/state/district/city_village/postal_code.
ORGANIZATION_ADDRESS_JOINS_SQL = """
    LEFT JOIN nss.district d
           ON d.district_pk = o.district_pk
    LEFT JOIN nss.state s
           ON s.state_pk = o.state_pk
    LEFT JOIN nss.country c
           ON c.country_pk = o.country_pk
    LEFT JOIN nss.city_village cv
           ON cv.city_village_pk = o.city_village_pk
    LEFT JOIN nss.postal_code pc
           ON pc.postal_code_pk = o.postal_code_pk
"""

# ── Shared nss.person gender/marital-status/blood-group JOIN triple ──────
# Used by person.py's _PERSON_SUMMARY_SELECT and _PERSON_COUNT_SELECT
# (previously byte-identical copies of each other — the file's own comment
# called this "this file's existing DETAIL/SUMMARY duplication style") and
# as the base _PERSON_DETAIL_SELECT builds on with one more join
# (emergency_relationship). Caller's base query must alias the person row
# as "p".
PERSON_MASTER_DATA_JOINS_SQL = """
    LEFT JOIN nss.master_data g
           ON g.master_data_pk = p.gender_master_data_pk
    LEFT JOIN nss.master_data ms
           ON ms.master_data_pk = p.marital_status_master_data_pk
    LEFT JOIN nss.master_data bg
           ON bg.master_data_pk = p.blood_group_master_data_pk
"""

# ── Shared nss.sangha_sevi membership JOIN chain ──────────────────────────
# Used by membership.py's _MEMBER_SELECT and _MEMBER_COUNT_SELECT
# (previously byte-identical copies of each other — same "count mirrors
# select" pattern as PERSON_MASTER_DATA_JOINS_SQL above). Caller's base
# query must alias sangha_sevi as "ss".
#
# `aff` is scoped to the home organization (organization_pk = ss.organization_pk)
# — a member can now simultaneously hold a second active affiliation at a
# darshak (cross-Sakha attendance) org (see uq_mem_sakha_aff_active,
# narrowed to (sangha_sevi_pk, organization_pk) in
# database/ddl/05_membership/06_membership_sakha_affiliation.sql), and an
# unscoped join here would fan this row out to one-row-per-affiliation.
# `daff`/`dorg` resolve that second, cross-Sakha affiliation (if any) for
# darshak_organization_pk/darshak_organization_name/darshak_local_sakha_number.
MEMBER_JOINS_SQL = """
    JOIN   nss.person p
           ON p.person_pk = ss.person_pk
    JOIN   nss.master_data mt
           ON mt.master_data_pk = ss.membership_type_master_data_pk
    JOIN   nss.master_data ms
           ON ms.master_data_pk = ss.membership_status_master_data_pk
    JOIN   nss.organization o
           ON o.organization_pk = ss.organization_pk
    LEFT JOIN nss.master_data ot
           ON ot.master_data_pk = o.organization_type_master_data_pk
    LEFT JOIN nss.membership_sakha_affiliation aff
           ON aff.sangha_sevi_pk = ss.sangha_sevi_pk
          AND aff.organization_pk = ss.organization_pk
          AND aff.effective_to IS NULL
    LEFT JOIN nss.membership_sakha_affiliation daff
           ON daff.sangha_sevi_pk = ss.sangha_sevi_pk
          AND daff.organization_pk != ss.organization_pk
          AND daff.effective_to IS NULL
    LEFT JOIN nss.organization dorg
           ON dorg.organization_pk = daff.organization_pk
"""

# ── Shared nss.user_account -> membership-context JOIN chain ─────────────
# Used by admin.py's list_users() and get_user() (previously byte-identical
# copies of each other). Resolves, for one user_account row: the person's
# active sangha_sevi (if any) + its home organization, the ACTIVE/REACTIVATED
# home membership_sakha_affiliation (for local_sakha_erp_id), the member's
# cross-Sakha darshak attendance — a second, simultaneous active
# membership_sakha_affiliation row at a different org (for
# darshak_local_number/darshak_organization_name; NOT
# nss.darshak_attendance_registration, which nothing in this codebase ever
# writes to), the still-PENDING registration_claim (for claimed_* fallbacks
# when no sangha_sevi exists yet), and — via master_data — the home
# membership type's value_code (COALESCE'd between the live sangha_sevi and
# the pending claim) so callers can label a Darshaka home affiliation
# correctly instead of assuming every local_sakha_erp_id is "Regular".
# Caller's base query must alias user_account as "ua" and join person as "p".
USER_ACCOUNT_MEMBERSHIP_JOINS_SQL = """
    LEFT JOIN nss.sangha_sevi ss ON ss.person_pk = ua.person_pk
          AND ss.is_active = TRUE
    LEFT JOIN nss.organization o ON o.organization_pk = ss.organization_pk
          AND o.is_active = TRUE
    LEFT JOIN nss.membership_sakha_affiliation msa
          ON msa.sangha_sevi_pk = ss.sangha_sevi_pk
          AND msa.organization_pk = ss.organization_pk
          AND msa.affiliation_status IN ('ACTIVE', 'REACTIVATED')
          AND msa.effective_to IS NULL
    LEFT JOIN nss.membership_sakha_affiliation dmsa
          ON dmsa.sangha_sevi_pk = ss.sangha_sevi_pk
          AND dmsa.organization_pk != ss.organization_pk
          AND dmsa.affiliation_status IN ('ACTIVE', 'REACTIVATED')
          AND dmsa.effective_to IS NULL
    LEFT JOIN nss.organization dorg2
          ON dorg2.organization_pk = dmsa.organization_pk
    LEFT JOIN nss.registration_claim rc
          ON rc.person_pk = ua.person_pk
          AND rc.claim_status = 'PENDING'
          AND rc.is_active = TRUE
    LEFT JOIN nss.organization co
          ON co.organization_pk = rc.claimed_organization_pk
          AND co.is_active = TRUE
    LEFT JOIN nss.master_data mt
          ON mt.master_data_pk = COALESCE(
              ss.membership_type_master_data_pk,
              rc.claimed_membership_type_master_data_pk
          )
"""

