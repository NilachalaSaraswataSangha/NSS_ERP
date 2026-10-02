"""
NSS ERP — Table sorting tests.

Covers the shared ORDER BY builder behind click-to-sort on table headers.

Two things are being guarded here, and the first one is the reason this
file exists at all:

  1. SAFETY. ORDER BY cannot be a bound parameter, so the column has to be
     interpolated into the statement. The whitelist is therefore the only
     thing standing between a query string and arbitrary SQL. If
     build_order_by ever passes an unknown value through, that is a SQL
     injection hole, not a cosmetic bug.

  2. ORDERING RULES. The same rules must hold in SQL and in the browser,
     or the same column sorts differently depending on which screen you
     are on:
       - blanks/NULLs last in BOTH directions
       - natural numeric ordering (SS2 before SS10)
       - a stable tiebreaker so paginated rows cannot repeat or vanish

Authority: Tier 5 design decision (2026-09-25) — every data table sorts
on header click; paginated tables sort in SQL, not in the page.
"""

import pathlib
import re

import pytest
from fastapi import HTTPException

from api.helpers import build_order_by, natural_sort_key, SORT_ASC, SORT_DESC

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


pytestmark = pytest.mark.integration


# A representative whitelist: a natural-sorted ID, an expression that
# CONTAINS COMMAS, and a plain column.
COLUMNS = {
    "person_id": natural_sort_key("p.person_id"),
    "person_name": "CONCAT_WS(' ', p.first_name, p.middle_name, p.last_name)",
    "created_at": "ua.created_at",
}
DEFAULT = "ua.created_at DESC"


# ── Safety ───────────────────────────────────────────────────────────────

class TestUnknownColumnsAreRejected:
    """The whitelist is the injection boundary."""

    @pytest.mark.parametrize("payload", [
        "p.person_id; DROP TABLE nss.person",
        "p.person_id, (SELECT password_hash FROM nss.user_account)",
        "1; DELETE FROM nss.user_account WHERE TRUE",
        "(SELECT 1)",
        "person_id DESC--",
        "P.PERSON_ID",          # case variants are not implicitly allowed
        "unknown_column",
        "",                     # falsy → default, must not raise
    ])
    def test_only_whitelisted_names_are_accepted(self, payload):
        if payload == "":
            # Empty means "no sort requested" — the default applies.
            assert build_order_by(payload, SORT_ASC, COLUMNS, DEFAULT) == DEFAULT
            return

        with pytest.raises(HTTPException) as exc:
            build_order_by(payload, SORT_ASC, COLUMNS, DEFAULT)
        assert exc.value.status_code == 422

    def test_rejection_message_is_readable_and_lists_the_options(self):
        """
        A mistyped column is a user-facing validation failure, so it must
        read as one rather than surfacing as a 500.
        """
        with pytest.raises(HTTPException) as exc:
            build_order_by("nope", SORT_ASC, COLUMNS, DEFAULT)
        detail = exc.value.detail
        assert isinstance(detail, str)
        assert "not a sortable column" in detail
        # Names the valid choices so the caller can correct itself.
        for name in COLUMNS:
            assert name in detail

    def test_direction_is_never_interpolated(self):
        """
        Anything that is not exactly 'desc' must fall back to ASC — the
        direction string must never reach the statement verbatim.
        """
        for payload in ["asc", "ASC", "desc; DROP TABLE x", "' OR 1=1", None, "", "banana"]:
            clause = build_order_by("created_at", payload, COLUMNS, DEFAULT)
            assert clause.count("ASC") + clause.count("DESC") >= 1
            assert "DROP" not in clause
            assert "OR 1=1" not in clause
            assert ";" not in clause


# ── Clause construction ──────────────────────────────────────────────────

class TestClauseConstruction:

    def test_no_sort_requested_uses_the_default(self):
        assert build_order_by(None, None, COLUMNS, DEFAULT) == DEFAULT

    def test_direction_maps_to_asc_or_desc(self):
        assert "ua.created_at ASC" in build_order_by("created_at", "asc", COLUMNS, DEFAULT)
        assert "ua.created_at DESC" in build_order_by("created_at", "desc", COLUMNS, DEFAULT)
        # Case-insensitive.
        assert "ua.created_at DESC" in build_order_by("created_at", "DESC", COLUMNS, DEFAULT)

    def test_nulls_last_in_both_directions(self):
        """
        A blank cell sinks to the bottom either way — a missing value is
        not the smallest value. This mirrors the frontend rule.
        """
        for direction in (SORT_ASC, SORT_DESC):
            clause = build_order_by("person_name", direction, COLUMNS, DEFAULT)
            assert "NULLS LAST" in clause

    def test_comma_bearing_expression_is_not_split(self):
        """
        The regression this guards: CONCAT_WS(' ', a, b, c) contains
        commas, and an earlier version split terms on ',' — which turned
        one valid expression into three fragments of invalid SQL.
        """
        clause = build_order_by("person_name", SORT_ASC, COLUMNS, DEFAULT)
        assert "CONCAT_WS(' ', p.first_name, p.middle_name, p.last_name) ASC" in clause

    def test_multi_term_natural_key_gets_direction_on_every_term(self):
        """
        A natural key is two terms. If only the last carried the
        direction, a DESC sort would order the stem ascending and quietly
        produce the wrong result.
        """
        clause = build_order_by("person_id", SORT_DESC, COLUMNS, DEFAULT)
        assert clause.count("DESC NULLS LAST") == 2, clause

    def test_default_is_appended_as_a_stable_tiebreaker(self):
        """
        Without a deterministic tiebreaker, rows with equal sort keys can
        appear on two pages or on none as the user pages through.
        """
        clause = build_order_by("account_status", SORT_ASC,
                                {**COLUMNS, "account_status": "ua.account_status"},
                                DEFAULT)
        assert clause.endswith(DEFAULT)


# ── The generated SQL must actually run ──────────────────────────────────

class TestGeneratedSqlIsValid:
    """
    A clause that looks right but does not parse is worthless, so these
    execute it against the real database.
    """

    @pytest.mark.parametrize("column", ["person_id", "person_name", "created_at"])
    @pytest.mark.parametrize("direction", [SORT_ASC, SORT_DESC])
    def test_clause_executes(self, write_conn, column, direction):
        clause = build_order_by(column, direction, COLUMNS, DEFAULT)
        with write_conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT p.person_id
                FROM nss.user_account ua
                JOIN nss.person p ON p.person_pk = ua.person_pk
                ORDER BY {clause}
                LIMIT 5
                """
            )
            cur.fetchall()   # raises if the clause is not valid SQL

    def test_natural_key_orders_ids_the_way_people_read_them(self, write_conn):
        """
        Plain text collation puts 'SS100' before 'SS9'. The natural key
        must not, or the ID column reads as noise.
        """
        terms = natural_sort_key("v")
        order = ", ".join(f"{t} ASC NULLS LAST" for t in terms)
        with write_conn.cursor() as cur:
            cur.execute(
                f"""
                WITH t(v) AS (
                    VALUES ('SS10'), ('SS2'), ('SS100'), ('SS1'),
                           ('AMSAS100'), ('AMSAS9'), ('NODIGITS'), (NULL)
                )
                SELECT v FROM t ORDER BY {order}
                """
            )
            values = [r[0] for r in cur.fetchall()]

        assert values.index("SS1") < values.index("SS2") < values.index("SS10") < values.index("SS100")
        assert values.index("AMSAS9") < values.index("AMSAS100")
        assert values[-1] is None, f"NULL must sort last, got {values}"


# ── Every registered whitelist must reference real, in-scope columns ──────

class TestEachRouterWhitelistRunsAgainstItsOwnSelect:
    """
    A whitelist entry is written by hand against the aliases of one
    particular SELECT. Nothing in build_order_by can tell that
    'g.value_name' is wrong if that SELECT never joined 'g' — only the
    database can. So every advertised column of every list endpoint that
    exposes its SELECT as a module constant is executed here.

    This is the test that catches a typo'd alias or a column that was
    renamed out from under the whitelist. Without it, the failure surfaces
    as a 500 the first time a user clicks that particular header.
    """

    @staticmethod
    def _cases():
        from api.routers.membership import _MEMBER_SELECT, _MEMBER_SORT_COLUMNS
        from api.routers.person import (
            _PERSON_SORT_COLUMNS,
            _PERSON_SUMMARY_SELECT,
        )

        return [
            ("person", _PERSON_SUMMARY_SELECT, _PERSON_SORT_COLUMNS,
             "p.first_name, p.last_name", "p.is_active = TRUE"),
            ("membership", _MEMBER_SELECT, _MEMBER_SORT_COLUMNS,
             "p.first_name, p.last_name", "ss.is_active = TRUE"),
        ]

    @pytest.mark.parametrize("direction", [SORT_ASC, SORT_DESC])
    def test_every_column_of_every_whitelist_is_valid_sql(self, write_conn, direction):
        failures = []
        for name, select, columns, default, where in self._cases():
            for column in sorted(columns):
                clause = build_order_by(column, direction, columns, default)
                sql = f"{select} WHERE {where} ORDER BY {clause} LIMIT 5"
                try:
                    with write_conn.cursor() as cur:
                        cur.execute(sql)
                        cur.fetchall()
                except Exception as exc:                      # noqa: BLE001
                    write_conn.rollback()
                    failures.append(f"{name}.{column} ({direction}): {exc}")

        assert not failures, "Whitelisted columns that do not run:\n" + "\n".join(failures)


# ── The headers on screen must match the whitelists on the server ─────────

class TestEveryClickableHeaderMapsToARealColumn:
    """
    A sortable header sends a column name to the API. If that name is not
    in the endpoint's whitelist, the click produces a 422 and the list
    appears to break — and nothing else in the codebase connects the two
    sides, because one is HTML and the other is Python.

    So this test reads the actual templates, pulls out every server-side
    sort handler call, and checks the key against the whitelist that
    endpoint really uses. It is the only thing that catches a renamed
    column or a typo in a header before a user clicks it.
    """

    # handler name in the template → (template file, whitelist)
    @staticmethod
    def _bindings():
        from api.routers.admin import _ORG_SORT_COLUMNS, _USER_SORT_COLUMNS
        from api.routers.claim_approval import _CLAIM_SORT_COLUMNS
        from api.routers.membership import _MEMBER_SORT_COLUMNS
        from api.routers.person import _PERSON_SORT_COLUMNS

        return {
            "sortUsers": ("frontend/admin.html", _USER_SORT_COLUMNS),
            "sortClaims": ("frontend/admin.html", _CLAIM_SORT_COLUMNS),
            "sortOrgs": ("frontend/admin.html", _ORG_SORT_COLUMNS),
            "sortPersonDir": ("frontend/admin.html", _PERSON_SORT_COLUMNS),
            "sortMemberDir": ("frontend/admin.html", _MEMBER_SORT_COLUMNS),
            # Member Search on the dashboard now reads /membership/search, which
            # returns relevance-ordered rows with NO server-side sort params —
            # sortMemberSearch() sorts the returned slice CLIENT-side. So its
            # headers aren't bound to any endpoint whitelist; they're validated
            # against the set of fields the client-side sort actually handles
            # (account_status maps to the membership status_name in the JS).
            "sortMemberSearch": ("frontend/dashboard.html", {
                "sangha_sevi_id", "person_name", "organization_name",
                "local_sakha_erp_id", "account_status",
            }),
        }

    def test_no_header_sends_a_column_the_endpoint_rejects(self):
        failures = []
        checked = 0

        for handler, (template, allowed) in self._bindings().items():
            path = REPO_ROOT / template
            assert path.exists(), f"template missing: {path}"
            html = path.read_text(encoding="utf-8")

            keys = set(re.findall(rf"{handler}\('([a-z_]+)'\)", html))
            assert keys, f"{handler} is wired in JS but no header calls it"

            for key in sorted(keys):
                checked += 1
                if key not in allowed:
                    failures.append(
                        f"{template}: {handler}('{key}') — not in the whitelist "
                        f"({', '.join(sorted(allowed))})"
                    )

        assert not failures, "Headers that would 422 on click:\n" + "\n".join(failures)
        assert checked >= 30, f"expected the full header sweep, only saw {checked}"

    def test_each_handler_exists_in_its_page_script(self):
        """
        The mirror failure: a header that calls a method Alpine does not
        have fails silently — the click does nothing at all, with no
        console error visible to the user.
        """
        scripts = {
            "frontend/admin.html": "frontend/assets/js/admin.js",
            "frontend/dashboard.html": "frontend/assets/js/dashboard.js",
        }
        sources = {
            page: (REPO_ROOT / js).read_text(encoding="utf-8")
            for page, js in scripts.items()
        }

        missing = [
            f"{handler} called in {template} but not defined in {scripts[template]}"
            for handler, (template, _) in self._bindings().items()
            if f"{handler}(key)" not in sources[template]
        ]
        assert not missing, "\n".join(missing)
