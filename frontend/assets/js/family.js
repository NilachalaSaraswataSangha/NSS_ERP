/**
 * NSS ERP — Tier 4 Family Verification UI
 *
 * Alpine.js data component. Fetches from /api/v1/family/* endpoints.
 * No authentication. Read-only verification.
 *
 * Sections:
 *   - Family list (with detail panel)
 *   - Family members (relationships)
 *   - Family head history
 */

const FAMILY_API = "/api/v1/family";

function familyApp() {
    return {
        // Health
        health: { loading: true, connected: false },

        // ── Families ──────────────────────────────────────────────
        families: [],
        familiesLoading: true,
        familiesError: false,

        // Detail
        selectedFamily: null,
        detailLoading: false,

        // Members
        familyMembers: [],
        membersLoading: false,

        // Head history
        headHistory: [],
        headLoading: false,

        // ── Init ──────────────────────────────────────────────────

        async init() {
            await this.fetchHealth();
            await this.fetchFamilies();
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

        // ── Family list ───────────────────────────────────────────

        async fetchFamilies() {
            this.familiesLoading = true;
            this.familiesError = false;
            try {
                const res = await fetch(`${FAMILY_API}/families`);
                if (!res.ok) throw new Error(res.statusText);
                this.families = await res.json();
            } catch {
                this.familiesError = true;
            } finally {
                this.familiesLoading = false;
            }
        },

        // ── Family detail ─────────────────────────────────────────

        async selectFamily(family) {
            // Toggle off if clicking same row
            if (this.selectedFamily?.family_group_pk === family.family_group_pk) {
                this.selectedFamily = null;
                this.familyMembers = [];
                this.headHistory = [];
                return;
            }

            this.detailLoading = true;
            this.selectedFamily = family;
            this.familyMembers = [];
            this.headHistory = [];

            try {
                // Fetch members and head history in parallel
                const [membersRes, headRes] = await Promise.all([
                    fetch(`${FAMILY_API}/families/${family.family_group_pk}/members`),
                    fetch(`${FAMILY_API}/families/${family.family_group_pk}/head-history`),
                ]);

                if (membersRes.ok) {
                    this.familyMembers = await membersRes.json();
                }
                if (headRes.ok) {
                    this.headHistory = await headRes.json();
                }
            } catch {
                // Non-fatal — family detail still shows
            } finally {
                this.detailLoading = false;
            }
        },

        // ── Helpers ───────────────────────────────────────────────

        formatMemberName(m) {
            return [m.first_name, m.middle_name, m.last_name]
                .filter(Boolean)
                .join(" ");
        },
    };
}
