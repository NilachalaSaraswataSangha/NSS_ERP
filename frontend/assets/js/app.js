/**
 * NSS ERP — Tier 0 Bootstrap Verification UI
 *
 * Alpine.js data component. Fetches from /api/v1/bootstrap/* endpoints.
 * No authentication. Read-only.
 */

const API_BASE = "/api/v1/bootstrap";

function bootstrapApp() {
    return {
        // Health
        health: { loading: true, connected: false },

        // Roles
        roles: [],
        rolesLoading: true,
        rolesError: false,

        // Permissions
        permissions: [],
        permissionsLoading: true,
        permissionsError: false,

        // Role permissions (interactive)
        selectedRole: null,
        rolePermissions: [],
        rolePermsLoading: false,
        rolePermsError: false,

        async init() {
            await Promise.all([
                this.fetchHealth(),
                this.fetchRoles(),
                this.fetchPermissions(),
            ]);
        },

        async fetchHealth() {
            this.health.loading = true;
            try {
                const res = await fetch(`${API_BASE}/health`);
                if (!res.ok) throw new Error(res.statusText);
                const data = await res.json();
                this.health.connected = data.database === "connected";
            } catch {
                this.health.connected = false;
            } finally {
                this.health.loading = false;
            }
        },

        async fetchRoles() {
            this.rolesLoading = true;
            this.rolesError = false;
            try {
                const res = await fetch(`${API_BASE}/roles`);
                if (!res.ok) throw new Error(res.statusText);
                this.roles = await res.json();
            } catch {
                this.rolesError = true;
            } finally {
                this.rolesLoading = false;
            }
        },

        async fetchPermissions() {
            this.permissionsLoading = true;
            this.permissionsError = false;
            try {
                const res = await fetch(`${API_BASE}/permissions`);
                if (!res.ok) throw new Error(res.statusText);
                this.permissions = await res.json();
            } catch {
                this.permissionsError = true;
            } finally {
                this.permissionsLoading = false;
            }
        },

        async selectRole(role) {
            // Toggle off if clicking the same role
            if (this.selectedRole?.role_master_pk === role.role_master_pk) {
                this.selectedRole = null;
                this.rolePermissions = [];
                return;
            }

            this.selectedRole = role;
            this.rolePermsLoading = true;
            this.rolePermsError = false;
            this.rolePermissions = [];

            try {
                const res = await fetch(
                    `${API_BASE}/roles/${role.role_master_pk}/permissions`
                );
                if (!res.ok) throw new Error(res.statusText);
                this.rolePermissions = await res.json();
            } catch {
                this.rolePermsError = true;
            } finally {
                this.rolePermsLoading = false;
            }
        },
    };
}
