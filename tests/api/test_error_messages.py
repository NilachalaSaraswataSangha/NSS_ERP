"""
NSS ERP — User-facing error message tests.

Guards the rule that a failed request must come back with a readable
`detail` STRING, never a raw status code and never a structure the UI can
only stringify.

Background — the three failure modes these tests lock down:
  1. Pydantic returned `detail` as a list of dicts, so the browser showed
     the literal text "[object Object] [object Object]".
  2. psycopg2 constraint violations were caught nowhere in api/, so they
     escaped as a 500 whose body has no `detail` at all, and the UI fell
     through to "Failed (500)."
  3. Any other unexpected exception, likewise.

Authority: Tier 5 design decision (2026-09-25).
"""

import pytest
import psycopg2

from api.error_handlers import (
    humanize_field,
    _sentence_for,
    integrity_error_handler,
    unhandled_exception_handler,
)


pytestmark = pytest.mark.integration


# ── Through the real API ─────────────────────────────────────────────────

class TestValidationErrorsAreReadable:
    """
    Uses POST /api/v1/auth/login — unauthenticated, so the request reaches
    body validation without an auth dependency short-circuiting it first.
    """

    def test_detail_is_a_string_not_a_list(self, client):
        """
        The regression that mattered: a list `detail` renders in the UI as
        "[object Object]" because every error slot is a string binding.
        """
        response = client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422
        detail = response.json()["detail"]
        assert isinstance(detail, str), (
            f"detail must be a string for the UI to render it, got "
            f"{type(detail).__name__}: {detail!r}"
        )
        assert "object Object" not in detail

    def test_missing_fields_are_named_in_plain_language(self, client):
        """Message should say which field, in words, and that it's required."""
        response = client.post("/api/v1/auth/login", json={})
        detail = response.json()["detail"]
        assert "required" in detail.lower(), detail
        # Must not leak schema plumbing into the sentence.
        assert "_pk" not in detail, detail
        assert "master_data" not in detail, detail
        assert "loc" not in detail, detail

    def test_no_bare_status_code_as_the_whole_message(self, client):
        """A readable message, not a number the user has to interpret."""
        response = client.post("/api/v1/auth/login", json={})
        detail = response.json()["detail"]
        assert len(detail) > 20, f"Message is too terse to be useful: {detail!r}"
        assert detail.strip().endswith("."), detail

    def test_deliberate_http_exception_is_not_overridden(self, client):
        """
        An endpoint's own HTTPException must still win — these handlers are
        a safety net, not a replacement for specific endpoint messages.
        """
        response = client.post(
            "/api/v1/auth/login",
            json={"login_id": "NO_SUCH_USER_XYZ", "password": "WrongPass1"},
        )
        assert response.status_code in (401, 403, 404, 422, 429)
        detail = response.json().get("detail")
        assert isinstance(detail, str) and detail, response.text


# ── Field humanisation ───────────────────────────────────────────────────

class TestHumanizeField:

    @pytest.mark.parametrize("raw,expected", [
        ("date_of_birth", "Date of birth"),
        ("first_name", "First name"),
        ("gender_master_data_pk", "Gender"),
        ("organization_pk", "Organization"),
        ("local_sakha_erp_id", "Local Sakha number"),
        ("login_id", "Login ID"),
    ])
    def test_known_and_generic_names(self, raw, expected):
        assert humanize_field(raw) == expected

    def test_surrogate_key_suffixes_are_stripped(self):
        """'_pk' is plumbing — it must never reach the user."""
        assert "_pk" not in humanize_field("some_new_table_pk")
        assert humanize_field("some_new_table_pk") == "Some new table"

    def test_never_returns_empty(self):
        assert humanize_field("_pk") == "Value"
        assert humanize_field("") == "Value"


class TestSentenceFor:

    def test_missing_field(self):
        sentence = _sentence_for({
            "type": "missing",
            "loc": ["body", "date_of_birth"],
            "msg": "Field required",
        })
        assert sentence == "Date of birth is required."

    def test_too_long_includes_the_limit(self):
        sentence = _sentence_for({
            "type": "string_too_long",
            "loc": ["body", "short_code"],
            "msg": "String should have at most 5 characters",
            "ctx": {"max_length": 5},
        })
        assert "Short code" in sentence and "5" in sentence

    def test_list_index_reports_the_parent_field(self):
        """A numeric loc segment is an index, not a field name."""
        sentence = _sentence_for({
            "type": "missing",
            "loc": ["body", "contacts", 0],
            "msg": "Field required",
        })
        assert "0" not in sentence, sentence
        assert "Contacts" in sentence

    def test_unknown_type_still_produces_a_sentence(self):
        sentence = _sentence_for({
            "type": "some_future_pydantic_type",
            "loc": ["body", "first_name"],
            "msg": "is somehow wrong",
        })
        assert sentence.startswith("First name")
        assert sentence.endswith(".")


# ── Integrity errors ─────────────────────────────────────────────────────

class _FakeRequest:
    """Minimal stand-in — the handlers only read method and url.path."""
    method = "POST"

    class url:
        path = "/api/v1/test"


async def _detail_of(handler, exc):
    response = await handler(_FakeRequest(), exc)
    import json
    return response.status_code, json.loads(response.body)["detail"]


class TestIntegrityErrorMessages:
    """
    Driven directly, because a UniqueViolation raised inside a request
    would also poison the shared test transaction.
    """

    @pytest.mark.anyio
    async def test_unique_violation_is_a_409_in_plain_language(self):
        code, detail = await _detail_of(
            integrity_error_handler, psycopg2.errors.UniqueViolation("dup key")
        )
        assert code == 409
        assert isinstance(detail, str)
        assert "already" in detail.lower()
        # Internal identifiers must not leak.
        assert "constraint" not in detail.lower()
        assert "nss." not in detail

    @pytest.mark.anyio
    async def test_foreign_key_violation_explains_the_cause(self):
        code, detail = await _detail_of(
            integrity_error_handler,
            psycopg2.errors.ForeignKeyViolation("fk fail"),
        )
        assert code == 422
        assert "does not exist" in detail.lower()

    @pytest.mark.anyio
    async def test_check_violation_does_not_expose_the_constraint(self):
        code, detail = await _detail_of(
            integrity_error_handler, psycopg2.errors.CheckViolation("chk fail")
        )
        assert code == 422
        assert "chk_" not in detail
        assert "not allowed" in detail.lower()


class TestUnhandledExceptionMessage:

    @pytest.mark.anyio
    async def test_500_is_readable_and_carries_a_reference(self):
        """
        The user gets something actionable and a short code to quote;
        the traceback stays in the server log.
        """
        response = await unhandled_exception_handler(
            _FakeRequest(), RuntimeError("internal detail that must not leak")
        )
        import json
        body = json.loads(response.body)
        assert response.status_code == 500
        assert isinstance(body["detail"], str)
        assert "internal detail that must not leak" not in body["detail"]
        assert "RuntimeError" not in body["detail"]
        assert body["reference"] in body["detail"]
        assert len(body["reference"]) == 8
