/**
 * NSS ERP — Shared layout mixin for authenticated pages.
 *
 * Provides:
 *   - sidebarOpen toggle
 *   - currentUser loaded from /api/v1/auth/me
 *   - Topbar user-info HTML (rendered via Alpine x-html)
 *   - Sidebar footer user-info HTML
 *   - Shared logout
 *   - Collapsible sidebar nav groups (navGroupsCollapsed / isNavGroupCollapsed /
 *     toggleNavGroup), persisted to localStorage
 *
 * Usage in Alpine component:
 *   function myPageApp() {
 *       return {
 *           ...NSSLayout.mixin(),
 *           // page-specific data...
 *           async init() {
 *               await NSSLayout.initAuth(this);
 *               if (!this.currentUser) return;
 *               // page-specific init...
 *           },
 *       };
 *   }
 *
 * In HTML topbar:
 *   <div class="topbar-user-info" x-show="currentUser" x-html="topbarUserInfo()"></div>
 *
 * In HTML sidebar footer:
 *   <div class="sidebar-footer" x-show="currentUser" x-html="sidebarFooterInfo()"></div>
 */

// localStorage key for which sidebar nav groups the user has folded shut.
// Shared across admin.html/dashboard.html so a collapse choice made on one
// page persists when navigating to the other.
const NSS_NAV_GROUPS_STORAGE_KEY = "nss_nav_groups_collapsed";

function _loadCollapsedNavGroups() {
    try {
        const raw = localStorage.getItem(NSS_NAV_GROUPS_STORAGE_KEY);
        const parsed = raw ? JSON.parse(raw) : [];
        return Array.isArray(parsed) ? parsed : [];
    } catch {
        return [];
    }
}

const NSSLayout = {
    /**
     * Returns the shared Alpine data properties to spread into your component.
     *
     * NOTE: JS spread operator {...obj} does NOT preserve getters — it evaluates
     * them once and copies the value. So we use regular methods instead of getters.
     * In HTML, use x-html="topbarUserInfo()" (with parentheses).
     */
    mixin() {
        return {
            sidebarOpen: false,
            authLoading: true,
            currentUser: null,
            // Set when the profile could not be refreshed but the session is
            // still valid (rate limited / server blip) — see initAuth.
            authWarning: null,

            // ── Collapsible sidebar nav groups ──────────────────
            // Folded-group keys, persisted to localStorage so the layout
            // stays how the user left it across reloads/tabs.
            navGroupsCollapsed: _loadCollapsedNavGroups(),

            isNavGroupCollapsed(key) {
                return this.navGroupsCollapsed.includes(key);
            },

            toggleNavGroup(key) {
                const idx = this.navGroupsCollapsed.indexOf(key);
                if (idx === -1) this.navGroupsCollapsed.push(key);
                else this.navGroupsCollapsed.splice(idx, 1);
                try {
                    localStorage.setItem(
                        NSS_NAV_GROUPS_STORAGE_KEY,
                        JSON.stringify(this.navGroupsCollapsed)
                    );
                } catch {
                    // Private-mode/quota errors are non-fatal — the fold
                    // just won't persist across reloads.
                }
            },

            /**
             * Topbar user-info HTML.
             * Shows: avatar initials, person name, SS ID, sakha ERP ID,
             * sakha name, role badges.
             *
             * The avatar lives here (not just in the Personal tab's own
             * identity card) so every tab shows who's logged in — the
             * Personal tab used to repeat a near-identical banner above
             * every single tab, which was the duplication being fixed.
             */
            topbarUserInfo() {
                const u = this.currentUser;
                if (!u) return "";
                let html = "";

                // Avatar initials — same first+last-initial convention as
                // the Personal tab's identity strip (dashboard.js
                // _computeInitials), kept here too since this function is
                // shared across pages that don't have that helper.
                if (u.person_name) {
                    const parts = u.person_name.trim().split(/\s+/);
                    const initials = parts.length >= 2
                        ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
                        : parts[0].substring(0, 2).toUpperCase();
                    html += `<span class="user-avatar">${this._esc(initials)}</span>`;
                }

                // Person name
                if (u.person_name) {
                    html += `<span class="user-name">${this._esc(u.person_name)}</span>`;
                }

                // Sangha Sevi ID (e.g. SS1)
                if (u.sangha_sevi_id) {
                    html += `<span class="user-ss-id">${this._esc(u.sangha_sevi_id)}</span>`;
                }

                // Sakha ERP ID (e.g. ESS123)
                if (u.local_sakha_erp_id) {
                    html += `<span class="user-sakha-id">${this._esc(u.local_sakha_erp_id)}</span>`;
                }

                // Sakha name
                if (u.sakha_name) {
                    html += `<span class="user-sakha-name">${this._esc(u.sakha_name)}</span>`;
                }

                // Role badges — ONE per distinct role type. A user may hold
                // the same ORGANIZATIONAL role at several orgs (the frozen
                // RBAC allows, e.g., Sakha Admin over three Sakhas — one
                // user_role row each), but repeating "Sakha Administrator"
                // three times in the topbar is noise, not information. Collapse
                // to unique role_codes; the per-org scope is shown where it
                // matters (the org switcher / admin tabs), not the identity bar.
                //
                // Also collapse SYSTEM roles that another held role already
                // subsumes: NSS_ERP_ADMIN is a strict permission superset of
                // NSS_ERP_AUDITOR and NSS_ERP_REPORT_VIEWER (all three are
                // fixed scope_level='NSS-WIDE'), so badging all three said the
                // same thing three times and pushed the bar onto a second row.
                // The user_role rows are untouched and the Auditor / Report
                // Viewer dashboards still get their own admin tabs — this is a
                // display-only collapse of redundant identity badges.
                if (u.scopes && u.scopes.length) {
                    const seenRoles = new Set();
                    for (const scope of u.scopes) {
                        seenRoles.add(scope.role_code);
                    }
                    const suppressed = new Set();
                    if (seenRoles.has("NSS_ERP_ADMIN")) {
                        suppressed.add("NSS_ERP_AUDITOR");
                        suppressed.add("NSS_ERP_REPORT_VIEWER");
                    }
                    const rendered = new Set();
                    for (const scope of u.scopes) {
                        if (rendered.has(scope.role_code)) continue;
                        if (suppressed.has(scope.role_code)) continue;
                        rendered.add(scope.role_code);
                        const label = scope.role_name || scope.role_code;
                        html += `<span class="role-badge">${this._esc(label)}</span>`;
                    }
                }

                return html;
            },

            /**
             * Sidebar footer user-info HTML.
             * Shows: avatar initials, person name, SS ID, logout button.
             */
            sidebarFooterInfo() {
                const u = this.currentUser;
                if (!u) return "";
                const initials = (u.person_name || "U").substring(0, 2).toUpperCase();
                const name = this._esc(u.person_name || "Loading...");
                const ssId = this._esc(u.sangha_sevi_id || "");

                return `
                    <div class="avatar">${initials}</div>
                    <div class="user-info">
                        <div class="user-name">${name}</div>
                        <div class="user-id">${ssId}</div>
                    </div>
                    <button class="logout-btn" type="button" data-nss-action="logout" title="Sign out">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" width="18" height="18">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 9V5.25A2.25 2.25 0 0 1 10.5 3h6a2.25 2.25 0 0 1 2.25 2.25v13.5A2.25 2.25 0 0 1 16.5 21h-6a2.25 2.25 0 0 1-2.25-2.25V15m-3 0-3-3m0 0 3-3m-3 3H15" />
                        </svg>
                    </button>
                `;
            },

            /**
             * Simple HTML escaper to prevent XSS from user data.
             */
            _esc(str) {
                if (!str) return "";
                const div = document.createElement("div");
                div.textContent = str;
                return div.innerHTML;
            },

            logout() {
                NSSAuth.logout();
            },
        };
    },

    /**
     * Shared auth initialization. Call from init().
     * Loads /api/v1/auth/me and sets this.currentUser.
     * Returns true if auth succeeded, false if redirected to login.
     *
     * Only a genuine authentication/authorization refusal (401/403) ends the
     * session. A 429 from the rate limiter, a 5xx, or a dropped connection are
     * transient: the credentials are still good, so the session is kept and the
     * cached profile (nss_user) renders the layout instead. Treating those as
     * "session invalid" cleared the tokens and dumped the user back on /login
     * mid-task — reachable in normal use, because the default limiter allows
     * 60 requests/minute per IP and a few quick tab switches exceed that.
     *
     * @param {Object} component - The Alpine component (this)
     * @param {Object} [opts] - Options
     * @param {string[]} [opts.requiredPermissions] - At least one required
     * @param {string} [opts.redirectUrl] - Where to send unauthorized users (default: /login)
     */
    async initAuth(component, opts = {}) {
        if (!NSSAuth.requireAuth()) {
            component.authLoading = false;
            return false;
        }

        const endSession = () => {
            NSSAuth.clearTokens();
            window.location.href = opts.redirectUrl || "/login";
            component.authLoading = false;
            return false;
        };

        try {
            let res = await NSSAuth.apiFetch("/api/v1/auth/me");

            if (res.status === 429) {
                // One polite retry, honouring Retry-After when the server
                // sends one (slowapi does), capped so init cannot hang.
                const after = parseInt(
                    (res.headers && res.headers.get("Retry-After")) || "", 10
                );
                const waitMs = Math.min(
                    Number.isFinite(after) ? after * 1000 : 1000, 5000
                );
                await new Promise(r => setTimeout(r, waitMs));
                res = await NSSAuth.apiFetch("/api/v1/auth/me");
            }

            if (res.ok) {
                component.currentUser = await res.json();
                NSSAuth.setCachedUser(component.currentUser);
            } else if (res.status === 401 || res.status === 403) {
                return endSession();
            } else {
                // Transient (429 after retry, 5xx). Keep the session and fall
                // back to the last known profile so the page still renders.
                const cached = NSSAuth.getCachedUser();
                if (!cached) return endSession();
                component.currentUser = cached;
                component.authWarning =
                    "Could not refresh your profile just now — showing the last " +
                    "loaded version. Reload in a moment to update it.";
            }
        } catch {
            // Network-level failure: apiFetch only throws once it has already
            // decided the session is unrecoverable, or the request never left
            // the browser. Without a cached profile there is nothing to render.
            const cached = NSSAuth.getCachedUser();
            if (!cached || !NSSAuth.isLoggedIn()) return endSession();
            component.currentUser = cached;
            component.authWarning =
                "Could not reach the server — showing the last loaded version " +
                "of your profile.";
        } finally {
            component.authLoading = false;
        }

        // Permission guard
        if (opts.requiredPermissions && opts.requiredPermissions.length) {
            const perms = component.currentUser.permissions || [];
            const hasAny = opts.requiredPermissions.some(p => perms.includes(p));
            if (!hasAny) {
                window.location.href = opts.redirectUrl || "/dashboard";
                return false;
            }
        }

        return true;
    },
};

/**
 * Delegated handler for layout actions rendered through Alpine's x-html.
 *
 * The sidebar footer markup is injected as an HTML string, so it cannot carry
 * an inline onclick= handler: the Content-Security-Policy script-src directive
 * deliberately omits 'unsafe-inline' (see
 * docs/03_Solution/security/TIER5_SECURITY_AUDIT.md item A2). A single
 * document-level listener keyed on data-nss-action is also independent of
 * whether Alpine initialises directives inside x-html content.
 *
 * Add new layout actions here rather than reintroducing inline handlers.
 */
document.addEventListener("click", (event) => {
    const target = event.target.closest("[data-nss-action]");
    if (!target) return;

    if (target.dataset.nssAction === "logout") {
        event.preventDefault();
        NSSAuth.logout();
    }
});
