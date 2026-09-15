/**
 * NSS ERP — Tier 4 Membership Verification UI
 *
 * Alpine.js data component. Fetches from /api/v1/membership/* endpoints.
 * No authentication. Read-only verification.
 *
 * Three-tier identity model:
 *   - Sangha Sevi ID (SS1) — NSS-wide, permanent
 *   - Sakha Sangha ID / Local Sakha ERP Number (ESS1192) — Sakha-scoped, auto-generated
 *   - Kendra Number (345/2026/2027) — Kendra-wide, annual
 *
 * Sections:
 *   1. Members (list with type/status filters + detail + sub-data)
 *   2. Search (trigram + prefix search across all 3 identity tiers + name)
 */

const MEMBERSHIP_API = "/api/v1/membership";

function membershipApp() {
    return {
        // Active tab
        activeTab: "members",

        // Health
        health: { loading: true, connected: false },

        // ── Members ───────────────────────────────────────────────
        members: [],
        membersLoading: true,
        membersError: false,
        selectedTypeFilter: "",
        selectedStatusFilter: "",

        // Detail
        selectedMember: null,
        detailLoading: false,

        // Sub-data
        affiliations: [],
        parichayaPatras: [],
        anumatiPatras: [],
        journeyEvents: [],

        // ── Search ─────────────────────────────────────────────────
        searchQuery: "",
        searchResults: [],
        searchLoading: false,
        searchError: false,
        searchExecuted: false,
        _searchDebounce: null,

        // ── Init ──────────────────────────────────────────────────

        async init() {
            await this.fetchHealth();
            await this.fetchMembers();
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

        // ── Tab switching ─────────────────────────────────────────

        async switchTab(tab) {
            this.activeTab = tab;
            if (tab === "members" && this.members.length === 0) {
                await this.fetchMembers();
            }
        },

        // ── Member list ───────────────────────────────────────────

        async fetchMembers() {
            this.membersLoading = true;
            this.membersError = false;
            this.selectedMember = null;
            this.affiliations = [];
            this.parichayaPatras = [];
            this.anumatiPatras = [];
            this.journeyEvents = [];

            try {
                let url = `${MEMBERSHIP_API}/members`;
                const params = [];
                if (this.selectedTypeFilter)
                    params.push(`type_code=${encodeURIComponent(this.selectedTypeFilter)}`);
                if (this.selectedStatusFilter)
                    params.push(`status_code=${encodeURIComponent(this.selectedStatusFilter)}`);
                if (params.length) url += `?${params.join("&")}`;

                const res = await fetch(url);
                if (!res.ok) throw new Error(res.statusText);
                this.members = await res.json();
            } catch {
                this.membersError = true;
            } finally {
                this.membersLoading = false;
            }
        },

        // ── Member detail ─────────────────────────────────────────

        async selectMember(member) {
            // Toggle off if clicking same row
            if (this.selectedMember?.sangha_sevi_pk === member.sangha_sevi_pk) {
                this.selectedMember = null;
                this.affiliations = [];
                this.parichayaPatras = [];
                this.anumatiPatras = [];
                this.journeyEvents = [];
                return;
            }

            this.detailLoading = true;
            this.selectedMember = member;
            this.affiliations = [];
            this.parichayaPatras = [];
            this.anumatiPatras = [];
            this.journeyEvents = [];

            const pk = member.sangha_sevi_pk;

            try {
                // Fetch all sub-data in parallel
                const [affRes, ppRes, apRes, journeyRes] = await Promise.all([
                    fetch(`${MEMBERSHIP_API}/members/${pk}/affiliations`),
                    fetch(`${MEMBERSHIP_API}/members/${pk}/parichaya-patra`),
                    fetch(`${MEMBERSHIP_API}/members/${pk}/anumati-patra`),
                    fetch(`${MEMBERSHIP_API}/members/${pk}/journey`),
                ]);

                if (affRes.ok) this.affiliations = await affRes.json();
                if (ppRes.ok) this.parichayaPatras = await ppRes.json();
                if (apRes.ok) this.anumatiPatras = await apRes.json();
                if (journeyRes.ok) this.journeyEvents = await journeyRes.json();
            } catch {
                // Non-fatal
            } finally {
                this.detailLoading = false;
            }
        },

        // ── Search ────────────────────────────────────────────────

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
                        `${MEMBERSHIP_API}/search?q=${encodeURIComponent(q)}`
                    );
                    if (!res.ok) throw new Error(res.statusText);
                    this.searchResults = await res.json();
                    // Auto-select if exactly one result
                    if (this.searchResults.length === 1) {
                        await this.selectMember(this.searchResults[0]);
                    }
                } catch {
                    this.searchError = true;
                } finally {
                    this.searchLoading = false;
                }
            }, 300);
        },

        // ── Helpers ───────────────────────────────────────────────

        formatName(m) {
            return [m.first_name, m.middle_name, m.last_name]
                .filter(Boolean)
                .join(" ");
        },

        typeBadgeClass(m) {
            return NSS.typeBadgeClass(m.membership_type_code);
        },

        /**
         * Badge class for member lifecycle status.
         * Delegates to shared NSS.statusBadgeClass().
         */
        statusBadgeClass(m) {
            const code = m.status_code || (m.is_active ? "ACTIVE" : "INACTIVE");
            return NSS.statusBadgeClass(code);
        },

        /**
         * Display name for membership type.
         * Delegates to shared NSS.typeDisplayName().
         * DB now stores "Darshaka" directly; override in
         * NSS config remains as safety net (MBR-007).
         */
        typeDisplayName(m) {
            return NSS.typeDisplayName(m.membership_type_code, m.membership_type_name);
        },

        affBadgeClass(a) {
            return NSS.affBadgeClass(a.affiliation_status);
        },

        docBadgeClass(doc) {
            return NSS.statusBadgeClass(doc.status);
        },
    };
}
