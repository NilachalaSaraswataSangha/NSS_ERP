/**
 * NSS ERP — Tier 3 Person Verification UI
 *
 * Alpine.js data component. Fetches from /api/v1/person/* and
 * /api/v1/foundation/master-data endpoints.
 * No authentication. Read-only verification.
 *
 * Sections:
 *   1. Persons (list with gender/marital-status/blood-group filters + detail + addresses)
 *   2. Search (trigram fuzzy search on name, person_id, mobile)
 */

const PERSON_API = "/api/v1/person";
const FOUNDATION_API = "/api/v1/foundation";

function personApp() {
    return {
        // Active tab
        activeTab: "persons",

        // Health (reuse bootstrap endpoint)
        health: { loading: true, connected: false },

        // ── Filter options (from Foundation master-data) ────────────
        genderOptions: [],
        maritalStatusOptions: [],
        bloodGroupOptions: [],

        // ── Persons ────────────────────────────────────────────────
        persons: [],
        personsLoading: true,
        personsError: false,
        selectedGenderFilter: "",
        selectedMaritalFilter: "",
        selectedBloodGroupFilter: "",

        // Detail
        selectedPerson: null,
        detailLoading: false,
        detailError: false,

        // Addresses
        personAddresses: [],
        addressesLoading: false,
        addressesError: false,

        // ── Search ─────────────────────────────────────────────────
        searchQuery: "",
        searchResults: [],
        searchLoading: false,
        searchError: false,
        searchExecuted: false,
        _searchDebounce: null,

        // ── Init ────────────────────────────────────────────────────

        async init() {
            await this.fetchHealth();
            await Promise.all([
                this.fetchFilterOptions(),
                this.fetchPersons(),
            ]);
        },

        async fetchHealth() {
            this.health.loading = true;
            try {
                const res = await fetch("/api/v1/bootstrap/health");
                if (!res.ok) throw new Error(res.statusText);
                const data = await res.json();
                this.health.connected = data.database === "connected";
            } catch {
                this.health.connected = false;
            } finally {
                this.health.loading = false;
            }
        },

        // ── Filter option loaders ──────────────────────────────────

        async fetchFilterOptions() {
            const categories = ["GENDER", "MARITAL_STATUS", "BLOOD_GROUP"];
            const results = await Promise.allSettled(
                categories.map(cat =>
                    fetch(`${FOUNDATION_API}/master-data?category_code=${cat}`)
                        .then(r => r.ok ? r.json() : [])
                )
            );
            this.genderOptions = results[0].status === "fulfilled" ? results[0].value : [];
            this.maritalStatusOptions = results[1].status === "fulfilled" ? results[1].value : [];
            this.bloodGroupOptions = results[2].status === "fulfilled" ? results[2].value : [];
        },

        // ── Tab switching ──────────────────────────────────────────

        async switchTab(tab) {
            this.activeTab = tab;
            if (tab === "persons" && this.persons.length === 0) {
                await this.fetchPersons();
            }
        },

        // ── Person list ────────────────────────────────────────────

        async fetchPersons() {
            this.personsLoading = true;
            this.personsError = false;
            try {
                let url = `${PERSON_API}/persons`;
                const params = [];
                if (this.selectedGenderFilter)
                    params.push(`gender_code=${encodeURIComponent(this.selectedGenderFilter)}`);
                if (this.selectedMaritalFilter)
                    params.push(`marital_status_code=${encodeURIComponent(this.selectedMaritalFilter)}`);
                if (this.selectedBloodGroupFilter)
                    params.push(`blood_group_code=${encodeURIComponent(this.selectedBloodGroupFilter)}`);
                if (params.length) url += `?${params.join("&")}`;

                const res = await fetch(url);
                if (!res.ok) throw new Error(res.statusText);
                this.persons = await res.json();
            } catch {
                this.personsError = true;
            } finally {
                this.personsLoading = false;
            }
        },

        async filterPersons() {
            // Clear detail panel — previous selection may not exist in new filter results
            this.selectedPerson = null;
            this.personAddresses = [];
            this.persons = [];
            await this.fetchPersons();

            // Auto-select if filter yields exactly one result
            if (this.persons.length === 1) {
                await this.selectPerson(this.persons[0]);
            }
        },

        // ── Person detail ──────────────────────────────────────────

        async selectPerson(personSummary) {
            // Toggle off if clicking the same row
            if (this.selectedPerson?.person_pk === personSummary.person_pk) {
                this.selectedPerson = null;
                this.personAddresses = [];
                return;
            }

            this.detailLoading = true;
            this.detailError = false;
            this.selectedPerson = null;
            this.personAddresses = [];

            try {
                // Fetch full detail and addresses in parallel
                const [detailRes, addrRes] = await Promise.all([
                    fetch(`${PERSON_API}/persons/${personSummary.person_pk}`),
                    fetch(`${PERSON_API}/persons/${personSummary.person_pk}/addresses`),
                ]);

                if (!detailRes.ok) throw new Error(detailRes.statusText);
                this.selectedPerson = await detailRes.json();

                if (addrRes.ok) {
                    this.personAddresses = await addrRes.json();
                }
                // Addresses may legitimately be empty — don't fail detail for it
            } catch {
                this.detailError = true;
            } finally {
                this.detailLoading = false;
            }
        },

        /**
         * Select a person by PK (used when clicking a search result).
         * Loads the person list if not already loaded, then selects.
         */
        async selectPersonByPk(pk) {
            if (this.persons.length === 0) {
                // Reset filters so the full list is available
                this.selectedGenderFilter = "";
                this.selectedMaritalFilter = "";
                this.selectedBloodGroupFilter = "";
                await this.fetchPersons();
            }
            const match = this.persons.find(p => p.person_pk === pk);
            if (match) {
                await this.selectPerson(match);
            } else {
                // Person may be filtered out — fetch detail directly
                await this.selectPerson({ person_pk: pk });
            }
        },

        // ── Search ─────────────────────────────────────────────────

        async executeSearch() {
            const q = this.searchQuery.trim();
            if (q.length < 2) {
                this.searchResults = [];
                this.searchExecuted = false;
                return;
            }

            // Debounce: wait 300ms after last keystroke
            if (this._searchDebounce) clearTimeout(this._searchDebounce);
            this._searchDebounce = setTimeout(async () => {
                this.searchLoading = true;
                this.searchError = false;
                this.searchExecuted = true;
                try {
                    const res = await fetch(
                        `${PERSON_API}/search?q=${encodeURIComponent(q)}`
                    );
                    if (!res.ok) throw new Error(res.statusText);
                    this.searchResults = await res.json();
                } catch {
                    this.searchError = true;
                } finally {
                    this.searchLoading = false;
                }
            }, 300);
        },

        // ── Helpers ────────────────────────────────────────────────

        /**
         * Format full name from first/middle/last parts.
         */
        formatName(p) {
            return [p.first_name, p.middle_name, p.last_name]
                .filter(Boolean)
                .join(" ");
        },

        /**
         * Format phone with country code prefix if present.
         */
        formatPhone(p) {
            if (!p.mobile_number) return "—";
            if (p.country_phone_code) return `${p.country_phone_code} ${p.mobile_number}`;
            return p.mobile_number;
        },

        /**
         * Person lifecycle status label:
         * - ACTIVE (is_active=true, no date_of_death)
         * - ACTIVE-DECEASED (is_active=true, date_of_death set)
         * - INACTIVE (is_active=false)
         */
        statusLabel(p) {
            if (!p.is_active) return "Inactive";
            if (p.date_of_death) return "Deceased";
            return "Active";
        },

        /**
         * Badge CSS class for person lifecycle status.
         */
        statusBadgeClass(p) {
            if (!p.is_active) return "badge-status-inactive";
            if (p.date_of_death) return "badge-status-deceased";
            return "badge-status-active";
        },
    };
}
