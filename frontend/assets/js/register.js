/**
 * NSS ERP — Registration Page (Tier 5)
 *
 * Alpine.js component for multi-step registration form.
 * Steps:
 *   1. Personal details (name, DOB, gender, contact)
 *   2. Membership claim details (optional toggle)
 *      - Select Sakha first, then Local Sakha Number appears
 *      - Darshaka: Local Sakha Number optional
 *      - Non-Darshaka: Local Sakha Number required
 *      - Optional: attending another Sangha as Darshak
 *   3. Password creation
 *   4. Success screen (Person ID only — pending admin approval)
 *
 * Calls POST /api/v1/register (public — no auth required).
 * Loads dropdown data from Foundation master_data API.
 *
 * Authority: SOL-AUTH-006 (Registration Claim Business Rules)
 */

function registerApp() {
    return {
        step: 1,
        loading: false,
        error: "",
        showPassword: false,
        confirmPassword: "",

        // Dropdown data
        genders: [],
        maritalStatuses: [],
        bloodGroups: [],
        membershipTypes: [],
        sakhas: [],

        // Address lookup data
        regCountries: [],
        regStates: [],
        regDistricts: [],
        regPostalCodes: [],

        // Form data
        form: {
            first_name: "",
            middle_name: "",
            last_name: "",
            date_of_birth: "",
            gender_master_data_pk: "",
            marital_status_master_data_pk: "",
            blood_group_master_data_pk: "",
            country_phone_code: NSS.DEFAULT_COUNTRY_CODE,
            mobile_number: "",
            email: "",
            // Address
            country_pk: "",
            state_pk: "",
            district_pk: "",
            city_village_name: "",
            postal_code_value: "",
            // Membership
            has_membership: false,
            membership_type_master_data_pk: "",
            organization_pk: "",
            joining_date: "",
            claimed_local_sakha_number: "",
            is_attending_as_darshak: false,
            darshak_organization_pk: "",
            password: "",
        },

        // Registration result
        result: {
            person_pk: "",
            person_id: "",
            person_name: "",
            message: "",
        },

        async init() {
            // Redirect if already logged in
            NSSAuth.redirectIfLoggedIn("/dashboard");

            // Load dropdown data in parallel
            await Promise.all([
                this.loadMasterData("GENDER", "genders"),
                this.loadMasterData("MARITAL_STATUS", "maritalStatuses"),
                this.loadMasterData("BLOOD_GROUP", "bloodGroups"),
                this.loadMasterData("MEMBERSHIP_TYPE", "membershipTypes"),
                this.loadSakhas(),
                this.loadRegCountries(),
            ]);
        },

        async loadMasterData(categoryCode, targetProp) {
            try {
                const res = await fetch(
                    `/api/v1/foundation/master-data?category_code=${categoryCode}`
                );
                if (res.ok) {
                    this[targetProp] = await res.json();
                }
            } catch (err) {
                console.error(`Failed to load ${categoryCode}:`, err);
            }
        },

        async loadSakhas() {
            try {
                // Fetch Sakha-type organizations
                const res = await fetch(
                    `/api/v1/organization/organizations?type_code=SAKHA_SANGHA&limit=${NSS.MAX_PAGE_SIZE}`
                );
                if (res.ok) {
                    const data = await res.json();
                    this.sakhas = Array.isArray(data) ? data : (data.organizations || []);
                }
            } catch (err) {
                console.error("Failed to load Sakhas:", err);
            }
        },

        // ── Address cascade (shared utility) ────────────────────────────

        _locCascade: NSSLocation.create({
            fetchFn: fetch,
            arrays: {
                countries: 'regCountries',
                states: 'regStates',
                districts: 'regDistricts',
                postalCodes: 'regPostalCodes',
            },
            form: 'form',
        }),

        async loadRegCountries() { await this._locCascade.loadCountries(this); },
        onRegCountryChange()     { this._locCascade.onCountryChange(this); },
        onRegStateChange()       { this._locCascade.onStateChange(this); },
        onRegDistrictChange()    { this._locCascade.onDistrictChange(this); },

        // ── Title Case helper ─────────────────────────────────────────

        /**
         * Capitalize first letter of every word (Title Case).
         * Applied live on name fields for UX; also enforced server-side.
         */
        toTitleCase(str) {
            return str.replace(/\b\w/g, c => c.toUpperCase());
        },

        onNameInput(field) {
            this.form[field] = this.toTitleCase(this.form[field]);
        },

        // ── Computed helpers ──────────────────────────────────────────

        /**
         * Check if the selected membership type is PROBATIONARY (Darshaka).
         */
        isDarshaka() {
            if (!this.form.membership_type_master_data_pk) return false;
            const selected = this.membershipTypes.find(
                t => t.master_data_pk === this.form.membership_type_master_data_pk
            );
            return selected && selected.value_code === "PROBATIONARY";
        },

        /**
         * Get membership type display name for a given pk.
         */
        membershipTypeName(pk) {
            const t = this.membershipTypes.find(m => m.master_data_pk === pk);
            if (!t) return "";
            return t.value_code === "PROBATIONARY" ? "Darshaka" : t.value_name;
        },

        // ── Step navigation with validation ────────────────────────

        async goStep2() {
            this.error = "";

            if (!this.form.first_name.trim()) {
                this.error = "First name is required.";
                return;
            }

            if (!this.form.last_name.trim()) {
                this.error = "Last name is required.";
                return;
            }

            if (!this.form.date_of_birth) {
                this.error = "Date of birth is required.";
                return;
            }

            if (!this.form.gender_master_data_pk) {
                this.error = "Gender is required.";
                return;
            }

            if (!this.form.mobile_number && !this.form.email) {
                this.error = "At least one of mobile number or email is required.";
                return;
            }

            // Validate mobile format if provided
            if (this.form.mobile_number) {
                if (!this.form.country_phone_code) {
                    this.error = "Country phone code is required with mobile number.";
                    return;
                }
                if (!/^\+[0-9]{1,4}$/.test(this.form.country_phone_code)) {
                    this.error = "Invalid country code format (e.g. +91).";
                    return;
                }
                if (!/^[0-9]{7,15}$/.test(this.form.mobile_number)) {
                    this.error = "Mobile number must be 7–15 digits.";
                    return;
                }
            }

            // Validate email format if provided
            if (this.form.email) {
                if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(this.form.email)) {
                    this.error = "Invalid email format.";
                    return;
                }
            }

            // ── Check for duplicate mobile/email before proceeding ────
            try {
                const params = new URLSearchParams();
                if (this.form.mobile_number && this.form.country_phone_code) {
                    params.set("mobile_number", this.form.mobile_number);
                    params.set("country_phone_code", this.form.country_phone_code);
                }
                if (this.form.email) {
                    params.set("email", this.form.email.trim());
                }

                const res = await fetch(`/api/v1/register/check-duplicate?${params}`);
                if (res.ok) {
                    const data = await res.json();
                    const errors = [];
                    if (data.mobile_exists) {
                        errors.push("A person with this mobile number already exists.");
                    }
                    if (data.email_exists) {
                        errors.push("A person with this email already exists.");
                    }
                    if (errors.length > 0) {
                        this.error = errors.join(" ");
                        return;
                    }
                }
            } catch (_) {
                // Non-blocking — if the check fails, the backend will catch it on submit
            }

            this.step = 2;
        },

        goStep3() {
            this.error = "";

            if (this.form.has_membership) {
                if (!this.form.membership_type_master_data_pk) {
                    this.error = "Membership type is required.";
                    return;
                }
                if (!this.form.organization_pk) {
                    this.error = "Sakha selection is required.";
                    return;
                }

                // Non-Darshaka: Local Sakha Number is required (AUTH-BR-086)
                if (!this.isDarshaka()) {
                    if (!this.form.claimed_local_sakha_number.trim()) {
                        this.error = "Local Sakha Number is required for non-Darshaka members.";
                        return;
                    }
                }

                // Darshak attendance: must have org selected
                if (this.form.is_attending_as_darshak && !this.form.darshak_organization_pk) {
                    this.error = "Select the Sakha you are attending as Darshak.";
                    return;
                }
            }

            this.step = 3;
        },

        // ── Reset membership-dependent fields when type changes ────

        onMembershipTypeChange() {
            // Reset Local Sakha Number when switching types
            this.form.claimed_local_sakha_number = "";
            // Reset darshak fields
            this.form.is_attending_as_darshak = false;
            this.form.darshak_organization_pk = "";
        },

        // ── Password validation ────────────────────────────────────

        isPasswordValid() {
            const pw = this.form.password;
            return (
                pw.length >= NSS.PASSWORD_MIN_LENGTH &&
                /[A-Z]/.test(pw) &&
                /\d/.test(pw) &&
                this.confirmPassword === pw
            );
        },

        // ── Submit registration ────────────────────────────────────

        async register() {
            this.error = "";

            if (!this.isPasswordValid()) {
                this.error = "Please fix password issues before submitting.";
                return;
            }

            this.loading = true;

            try {
                // Build payload — only send non-empty optional fields
                const payload = {
                    first_name: this.form.first_name.trim(),
                    password: this.form.password,
                    has_membership: this.form.has_membership,
                };

                if (this.form.middle_name) payload.middle_name = this.form.middle_name.trim();
                if (this.form.last_name) payload.last_name = this.form.last_name.trim();
                if (this.form.date_of_birth) payload.date_of_birth = this.form.date_of_birth;
                if (this.form.gender_master_data_pk) payload.gender_master_data_pk = this.form.gender_master_data_pk;
                if (this.form.marital_status_master_data_pk) payload.marital_status_master_data_pk = this.form.marital_status_master_data_pk;
                if (this.form.blood_group_master_data_pk) payload.blood_group_master_data_pk = this.form.blood_group_master_data_pk;

                // Contact
                if (this.form.mobile_number) {
                    payload.country_phone_code = this.form.country_phone_code;
                    payload.mobile_number = this.form.mobile_number;
                }
                if (this.form.email) payload.email = this.form.email.trim();

                // Address
                if (this.form.country_pk) payload.country_pk = this.form.country_pk;
                if (this.form.state_pk) payload.state_pk = this.form.state_pk;
                if (this.form.district_pk) payload.district_pk = this.form.district_pk;
                if (this.form.city_village_name.trim()) payload.city_village_name = this.form.city_village_name.trim();
                if (this.form.postal_code_value.trim()) payload.postal_code_value = this.form.postal_code_value.trim();

                // Membership claim
                if (this.form.has_membership) {
                    payload.membership_type_master_data_pk = this.form.membership_type_master_data_pk;
                    payload.organization_pk = this.form.organization_pk;
                    if (this.form.joining_date) {
                        payload.joining_date = this.form.joining_date;
                    }

                    // Local Sakha Number (claim — not validated)
                    if (this.form.claimed_local_sakha_number.trim()) {
                        payload.claimed_local_sakha_number = this.form.claimed_local_sakha_number.trim();
                    }

                    // Darshak attendance
                    if (this.form.is_attending_as_darshak && this.form.darshak_organization_pk) {
                        payload.is_attending_as_darshak = true;
                        payload.darshak_organization_pk = this.form.darshak_organization_pk;
                    }
                }

                const res = await fetch("/api/v1/register", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                });

                if (!res.ok) {
                    const data = await res.json().catch(() => ({}));
                    this.error = NSS.errorMessage(data, res.status);
                    return;
                }

                const data = await res.json();
                this.result = {
                    person_pk: data.person_pk,
                    person_id: data.person_id,
                    person_name: data.person_name,
                    message: data.message,
                };
                this.step = 4;

            } catch (err) {
                this.error = "Unable to connect to server. Please try again.";
            } finally {
                this.loading = false;
            }
        },
    };
}
