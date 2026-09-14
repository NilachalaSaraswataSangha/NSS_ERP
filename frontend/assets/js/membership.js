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
            const code = m.membership_type_code;
            if (code === "REGULAR") return "badge-type-regular";
            if (code === "PROBATIONARY") return "badge-type-probationary";
            if (code === "ASSOCIATE") return "badge-type-associate";
            if (code === "HONORARY") return "badge-type-honorary";
            return "badge-ghost";
        },

        /**
         * Badge class for member lifecycle status.
         * Maps status_code to badge-status-* CSS classes.
         * Covers all 11 membership-applicable unified statuses.
         */
        statusBadgeClass(m) {
            const code = m.status_code || (m.is_active ? "ACTIVE" : "INACTIVE");
            if (code === "ACTIVE") return "badge-status-active";
            if (code === "INACTIVE") return "badge-status-inactive";
            if (code === "SUSPENDED") return "badge-status-suspended";
            if (code === "LAPSED") return "badge-status-lapsed";
            if (code === "TRANSFERRED") return "badge-status-transferred";
            if (code === "RESIGNED") return "badge-status-resigned";
            if (code === "EXPELLED") return "badge-status-expelled";
            if (code === "ARCHIVED") return "badge-status-archived";
            if (code === "RENEWAL_PENDING") return "badge-status-renewal-pending";
            if (code === "ON_HOLD") return "badge-status-on-hold";
            if (code === "DISCIPLINARY_REVIEW") return "badge-status-disciplinary-review";
            return "badge-ghost";
        },

        /**
         * Display name for membership type.
         * PROBATIONARY → "Darshaka" (operational UI label — MBR-007).
         * Database stores PROBATIONARY; portal shows Darshaka.
         */
        typeDisplayName(m) {
            const code = m.membership_type_code;
            if (code === "PROBATIONARY") return "Darshaka";
            return m.membership_type_name;
        },

        affBadgeClass(a) {
            if (a.affiliation_status === "ACTIVE") return "badge-aff-active";
            if (a.affiliation_status === "ARCHIVED") return "badge-aff-archived";
            if (a.affiliation_status === "REACTIVATED") return "badge-aff-reactivated";
            return "badge-ghost";
        },

        docBadgeClass(doc) {
            if (doc.status === "ACTIVE") return "badge-status-active";
            if (doc.status === "EXPIRED") return "badge-status-expired";
            if (doc.status === "CANCELLED") return "badge-status-cancelled";
            if (doc.status === "REPLACED") return "badge-status-replaced";
            return "badge-ghost";
        },
    };
}
