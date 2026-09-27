"""
NSS ERP — Self-Registration router.

Tier 5 endpoints:
  POST /api/v1/register — Self-register (creates person + pending account + claim)

Flow (POST /register):
  1. Validate input (person details, password policy)
  2. Generate person_id (P<next>) via id_sequence_master
  3. Insert person record
  4. Create user_account with account_status = 'PENDING_APPROVAL'
  5. Record password in password_history
  6. If membership details provided: insert registration_claim
  7. Return person_id only (no sangha_sevi_id — pending admin approval)

Business rules (AUTH-BR-081 through AUTH-BR-098):
  - Mobile OR email required (person CHECK constraint)
  - Registration creates person + user_account(PENDING_APPROVAL) only
  - No sangha_sevi or membership_sakha_affiliation created at registration
  - Membership intent stored in nss.registration_claim table
  - Local Sakha Number: required for non-Darshaka, optional for Darshaka
  - Local Sakha Number is NOT validated at registration (admin verifies)
  - PENDING_APPROVAL accounts cannot login
  - Sakha admin approves claim → creates membership records → activates account

Authority: SOL-AUTH-001, SOL-AUTH-002, SOL-AUTH-006, SOL-AUTH-007
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from api.config import settings
from api.database import get_connection, get_write_connection
from api.helpers import log_audit, next_id, resolve_or_create_city_village, resolve_or_create_postal_code, check_duplicate_contact, record_password_history, require_sakha_organization
from api.services.auth_service import hash_password, validate_password_policy

router = APIRouter(prefix="/api/v1/register", tags=["registration"])


# ── Request / Response schemas ──────────────────────────────────────────

class RegisterRequest(BaseModel):
    """POST /api/v1/register"""

    # Person fields
    first_name: str = Field(..., min_length=1, max_length=100)
    middle_name: str | None = Field(None, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: "date" = Field(..., description="Date of birth (YYYY-MM-DD)")
    gender_master_data_pk: str = Field(
        ..., min_length=1, description="UUID of gender master_data row"
    )
    marital_status_master_data_pk: str | None = Field(
        None, description="UUID of marital_status master_data row"
    )
    blood_group_master_data_pk: str | None = Field(
        None, description="UUID of blood_group master_data row"
    )

    # Contact
    country_phone_code: str | None = Field(None, max_length=10)
    mobile_number: str | None = Field(None, max_length=20)
    email: str | None = Field(None, max_length=255)

    # Address (optional)
    country_pk: str | None = Field(
        None, description="UUID of country",
    )
    state_pk: str | None = Field(
        None, description="UUID of state",
    )
    district_pk: str | None = Field(
        None, description="UUID of district",
    )
    city_village_name: str | None = Field(
        None, max_length=200,
        description="City/village name — lookup/create against Foundation table",
    )
    postal_code_pk: str | None = Field(
        None, description="UUID of postal_code (deprecated — use postal_code_value)",
    )
    postal_code_value: str | None = Field(
        None, max_length=20,
        description="PIN code as text — lookup/create against Foundation table",
    )

    # Membership claim (optional — "Not Applicable" toggle)
    has_membership: bool = Field(
        default=False,
        description="True if registering with membership claim details",
    )
    membership_type_master_data_pk: str | None = Field(
        None, description="UUID of membership_type master_data row",
    )
    organization_pk: str | None = Field(
        None, description="UUID of Sakha/org the member claims to belong to",
    )
    joining_date: Optional["date"] = None

    # Local Sakha Number (shown after sakha selection)
    claimed_local_sakha_number: str | None = Field(
        None, max_length=20,
        description="Local Sakha Number — required for non-Darshaka, optional for Darshaka",
    )

    # Darshak attendance at another Sangha (optional)
    is_attending_as_darshak: bool = Field(
        default=False,
        description="True if user is attending another Sangha as a Darshak",
    )
    darshak_organization_pk: str | None = Field(
        None, description="UUID of Sakha the user is attending as Darshak",
    )

    # Password
    password: str = Field(..., min_length=8, max_length=128)


class RegisterResponse(BaseModel):
    """Successful registration response."""
    person_pk: str
    person_id: str
    person_name: str
    message: str


from datetime import date  # noqa: E402 — needed for forward ref resolution


# ── GET /api/v1/register/check-duplicate ──────────────────────────────

@router.get("/check-duplicate")
def check_duplicate(
    mobile_number: str | None = Query(None, description="Mobile number to check"),
    country_phone_code: str | None = Query(None, description="Country phone code"),
    email: str | None = Query(None, description="Email to check"),
    conn=Depends(get_connection),
):
    """
    Check if a mobile number or email already exists in person table.

    Returns { mobile_exists: bool, email_exists: bool } so the
    registration form can warn the user on Step 1 before they fill
    the entire form.
    """
    result = {"mobile_exists": False, "email_exists": False}

    with conn.cursor() as cur:
        if mobile_number and country_phone_code:
            cur.execute(
                """
                SELECT 1 FROM nss.person
                WHERE country_phone_code = %s
                  AND mobile_number = %s
                  AND is_active = TRUE
                LIMIT 1
                """,
                (country_phone_code, mobile_number),
            )
            result["mobile_exists"] = cur.fetchone() is not None

        if email:
            cur.execute(
                """
                SELECT 1 FROM nss.person
                WHERE LOWER(email) = LOWER(%s)
                  AND is_active = TRUE
                LIMIT 1
                """,
                (email,),
            )
            result["email_exists"] = cur.fetchone() is not None

    return result


# ── POST /api/v1/register ──────────────────────────────────────────────

@router.post("", response_model=RegisterResponse, status_code=201)
def register(
    body: RegisterRequest,
    conn=Depends(get_write_connection),
) -> RegisterResponse:
    """
    Self-register as a new person.

    Creates person + user_account(PENDING_APPROVAL) in a single transaction.
    If membership details provided, stores a registration_claim for admin review.
    No sangha_sevi or membership records created at this stage.
    """

    # ── 1. Validate password policy ─────────────────────────────────────
    violations = validate_password_policy(body.password)
    if violations:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=violations,
        )

    # ── 2. Validate contact (mobile OR email required) ──────────────────
    if not body.mobile_number and not body.email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="At least one of mobile_number or email is required.",
        )

    # ── 3. Validate membership claim fields if has_membership ───────────
    if body.has_membership:
        missing = []
        if not body.membership_type_master_data_pk:
            missing.append("membership_type_master_data_pk")
        if not body.organization_pk:
            missing.append("organization_pk")
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Membership claim fields required: {', '.join(missing)}",
            )

    # ── 3b. Validate darshak attendance fields ──────────────────────────
    if body.is_attending_as_darshak and not body.darshak_organization_pk:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="darshak_organization_pk is required when is_attending_as_darshak is True.",
        )

    with conn.cursor() as cur:

        # ── 4. Check duplicate mobile + email ──────────────────────────
        check_duplicate_contact(
            cur,
            mobile_number=body.mobile_number,
            country_phone_code=body.country_phone_code,
            email=body.email,
        )

        # ── 5a. MBR-038A: claimed membership org must be a Sakha Sangha ──
        #   Enforce Sakha-only selection at submission time (fail fast with a
        #   clean 422) rather than letting a non-Sakha claim reach approval.
        #   Mirrors the DB trigger and the claim_approval / admin guards.
        if body.has_membership and body.organization_pk:
            require_sakha_organization(cur, body.organization_pk)

        # ── 5b. Determine if membership type is Darshaka (PROBATIONARY) ─
        is_darshaka = False
        if body.has_membership and body.membership_type_master_data_pk:
            cur.execute(
                """
                SELECT md.value_code
                FROM nss.master_data md
                WHERE md.master_data_pk = %s
                """,
                (body.membership_type_master_data_pk,),
            )
            mtype_row = cur.fetchone()
            if mtype_row:
                is_darshaka = mtype_row[0] == 'PROBATIONARY'

        # ── 5c. Validate Local Sakha Number requirement ─────────────────
        #   Non-Darshaka: required (AUTH-BR-086)
        #   Darshaka: optional
        if body.has_membership and not is_darshaka:
            if not body.claimed_local_sakha_number:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Local Sakha Number is required for non-Darshaka membership types.",
                )

        # ── 6. Generate person_id ───────────────────────────────────────
        person_id = next_id(cur, "PERSON")

        # ── 6b. Resolve city_village_name → city_village_pk ────────────
        city_village_pk = None
        if body.city_village_name and body.district_pk:
            cv_name = body.city_village_name.strip()
            if cv_name:
                city_village_pk = resolve_or_create_city_village(
                    cur, cv_name, body.district_pk,
                )

        # Resolve postal code from text value (lookup/create)
        resolved_postal_code_pk = body.postal_code_pk or None
        if body.postal_code_value and body.state_pk and body.country_pk:
            pc_val = body.postal_code_value.strip()
            if pc_val:
                resolved_postal_code_pk = resolve_or_create_postal_code(
                    cur, pc_val, body.state_pk, body.country_pk,
                )

        # ── 7. Insert person ────────────────────────────────────────────
        cur.execute(
            """
            INSERT INTO nss.person (
                person_id,
                first_name,
                middle_name,
                last_name,
                date_of_birth,
                gender_master_data_pk,
                marital_status_master_data_pk,
                blood_group_master_data_pk,
                country_phone_code,
                mobile_number,
                email,
                country_pk,
                state_pk,
                district_pk,
                city_village_pk,
                postal_code_pk
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING person_pk
            """,
            (
                person_id,
                body.first_name.strip().title(),
                body.middle_name.strip().title() if body.middle_name else None,
                body.last_name.strip().title() if body.last_name else None,
                body.date_of_birth,
                body.gender_master_data_pk,
                body.marital_status_master_data_pk,
                body.blood_group_master_data_pk,
                body.country_phone_code,
                body.mobile_number,
                body.email.strip().lower() if body.email else None,
                body.country_pk or None,
                body.state_pk or None,
                body.district_pk or None,
                city_village_pk,
                resolved_postal_code_pk,
            ),
        )
        person_pk = cur.fetchone()[0]

        log_audit(
            cur,
            action="CREATE",
            table_name="person",
            record_pk=str(person_pk),
            module="registration",
            summary=f"Self-registered person {body.first_name} {body.last_name}",
        )

        # ── 8. Create user_account (PENDING_APPROVAL) ──────────────────
        password_hash_val = hash_password(body.password)
        password_expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.PASSWORD_EXPIRY_DAYS
        )

        cur.execute(
            """
            INSERT INTO nss.user_account (
                person_pk,
                password_hash,
                account_status,
                force_password_change,
                password_expires_at
            ) VALUES (%s, %s, 'PENDING_APPROVAL', FALSE, %s)
            RETURNING user_account_pk
            """,
            (str(person_pk), password_hash_val, password_expires_at),
        )
        user_account_pk = cur.fetchone()[0]

        log_audit(
            cur,
            action="CREATE",
            table_name="user_account",
            record_pk=str(user_account_pk),
            actor_user_account_pk=str(user_account_pk),
            module="registration",
            summary="Created user account via self-registration",
        )

        # ── 9. Record initial password in history ───────────────────────
        record_password_history(cur, str(user_account_pk), password_hash_val, "INITIAL")

        # ── 10. Insert registration_claim if membership claimed ─────────
        if body.has_membership:
            cur.execute(
                """
                INSERT INTO nss.registration_claim (
                    user_account_pk,
                    person_pk,
                    claimed_organization_pk,
                    claimed_membership_type_master_data_pk,
                    claimed_local_sakha_number,
                    claimed_joining_date,
                    darshak_organization_pk,
                    claim_status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'PENDING')
                RETURNING registration_claim_pk
                """,
                (
                    str(user_account_pk),
                    str(person_pk),
                    body.organization_pk,
                    body.membership_type_master_data_pk,
                    body.claimed_local_sakha_number,
                    body.joining_date,
                    body.darshak_organization_pk if body.is_attending_as_darshak else None,
                ),
            )
            claim_pk = cur.fetchone()[0]

            log_audit(
                cur,
                action="CREATE",
                table_name="registration_claim",
                record_pk=str(claim_pk),
                actor_user_account_pk=str(user_account_pk),
                module="registration",
                summary=f"Submitted registration claim for {body.organization_pk}",
            )

    # ── Build response ──────────────────────────────────────────────────
    name_parts = [body.first_name.strip().title()]
    if body.middle_name:
        name_parts.append(body.middle_name.strip().title())
    if body.last_name:
        name_parts.append(body.last_name.strip().title())
    person_name = " ".join(name_parts)

    return RegisterResponse(
        person_pk=str(person_pk),
        person_id=person_id,
        person_name=person_name,
        message=(
            "Registration successful. Your registration is pending approval "
            "by your Sakha administrator. You will be able to log in once approved."
        ),
    )
