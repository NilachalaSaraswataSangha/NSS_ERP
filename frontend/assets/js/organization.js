/**
 * NSS ERP — Tier 2 Organization Verification UI
 *
 * Alpine.js data component. Fetches from /api/v1/organization/* endpoints.
 * No authentication. Read-only verification.
 *
 * Sections:
 *   1. Organization Types (8 frozen types)
 *   2. Organization Statuses (6 lifecycle statuses)
 *   3. Organizations (list with type/status context + hierarchy navigation)
 *   4. Hierarchy Tree (recursive CTE — full tree with depth)
 */

const ORG_API = "/api/v1/organization";

function organizationApp() {
    return {
        // Active tab
        activeTab: "reference",

        // Health (reuse bootstrap endpoint)
        health: { loading: true, connected: false },

        // ── Reference Data ──────────────────────────────────────────
        orgTypes: [],
        orgTypesLoading: true,
        orgTypesError: false,

        orgStatuses: [],
        orgStatusesLoading: true,
        orgStatusesError: false,

        // ── Organizations ───────────────────────────────────────────
        organizations: [],
        orgsLoading: true,
        orgsError: false,
        selectedTypeFilter: "",
        selectedStatusFilter: "",

        // Detail / children
        selectedOrg: null,
        orgChildren: [],
        childrenLoading: false,
        childrenError: false,

        // ── Hierarchy ───────────────────────────────────────────────
        hierarchy: [],
        hierarchyLoading: true,
        hierarchyError: false,

        // ── Init ─────────────────────────────────────────────────────

        async init() {
            await this.fetchHealth();
            await this.loadReferenceTab();
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

        // ── Tab switching ────────────────────────────────────────────

        async switchTab(tab) {
            this.activeTab = tab;
            if (tab === "reference") await this.loadReferenceTab();
            else if (tab === "organizations") await this.loadOrganizationsTab();
            else if (tab === "hierarchy") await this.loadHierarchyTab();
        },

        async loadReferenceTab() {
            if (this.orgTypes.length === 0) await this.fetchOrgTypes();
            if (this.orgStatuses.length === 0) await this.fetchOrgStatuses();
        },

        async loadOrganizationsTab() {
            if (this.organizations.length === 0) await this.fetchOrganizations();
        },

        async loadHierarchyTab() {
            if (this.hierarchy.length === 0) await this.fetchHierarchy();
        },

        // ── Reference Data fetchers ─────────────────────────────────

        async fetchOrgTypes() {
            this.orgTypesLoading = true;
            this.orgTypesError = false;
            try {
                const res = await fetch(`${ORG_API}/types`);
                if (!res.ok) throw new Error(res.statusText);
                this.orgTypes = await res.json();
            } catch {
                this.orgTypesError = true;
            } finally {
                this.orgTypesLoading = false;
            }
        },

        async fetchOrgStatuses() {
            this.orgStatusesLoading = true;
            this.orgStatusesError = false;
            try {
                const res = await fetch(`${ORG_API}/statuses`);
                if (!res.ok) throw new Error(res.statusText);
                this.orgStatuses = await res.json();
            } catch {
                this.orgStatusesError = true;
            } finally {
                this.orgStatusesLoading = false;
            }
        },

        // ── Organization fetchers ───────────────────────────────────

        async fetchOrganizations() {
            this.orgsLoading = true;
            this.orgsError = false;
            try {
                let url = `${ORG_API}/organizations`;
                const params = [];
                if (this.selectedTypeFilter)
                    params.push(`type_code=${encodeURIComponent(this.selectedTypeFilter)}`);
                if (this.selectedStatusFilter)
                    params.push(`status_code=${encodeURIComponent(this.selectedStatusFilter)}`);
                if (params.length) url += `?${params.join("&")}`;

                const res = await fetch(url);
                if (!res.ok) throw new Error(res.statusText);
                this.organizations = await res.json();
            } catch {
                this.orgsError = true;
            } finally {
                this.orgsLoading = false;
            }
        },

        async filterOrganizations() {
            this.organizations = [];
            await this.fetchOrganizations();
        },

        async selectOrganization(org) {
            if (this.selectedOrg?.organization_pk === org.organization_pk) {
                this.selectedOrg = null;
                this.orgChildren = [];
                return;
            }
            this.selectedOrg = org;
            this.childrenLoading = true;
            this.childrenError = false;
            this.orgChildren = [];

            try {
                const res = await fetch(
                    `${ORG_API}/organizations/${org.organization_pk}/children`
                );
                if (!res.ok) throw new Error(res.statusText);
                this.orgChildren = await res.json();
            } catch {
                this.childrenError = true;
            } finally {
                this.childrenLoading = false;
            }
        },

        // ── Hierarchy fetcher ───────────────────────────────────────

        async fetchHierarchy() {
            this.hierarchyLoading = true;
            this.hierarchyError = false;
            try {
                const res = await fetch(`${ORG_API}/hierarchy`);
                if (!res.ok) throw new Error(res.statusText);
                this.hierarchy = await res.json();
            } catch {
                this.hierarchyError = true;
            } finally {
                this.hierarchyLoading = false;
            }
        },

        // ── Helpers ─────────────────────────────────────────────────

        depthIndent(depth) {
            return `padding-left: ${depth * 1.5}rem`;
        },
    };
}
