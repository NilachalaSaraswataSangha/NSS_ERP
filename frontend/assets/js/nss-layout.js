/**
 * NSS ERP — Shared layout mixin for authenticated pages.
 *
 * Provides:
 *   - sidebarOpen toggle
 *   - currentUser loaded from /api/v1/auth/me
 *   - Topbar user-info HTML (rendered via Alpine x-html)
 *   - Sidebar footer user-info HTML
 *   - Shared logout
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

            /**
             * Topbar user-info HTML.
             * Shows: person name, SS ID, sakha ERP ID, sakha name, role badges.
             */
            topbarUserInfo() {
                const u = this.currentUser;
                if (!u) return "";
                let html = "";

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

                // Role badges
                if (u.scopes && u.scopes.length) {
                    for (const scope of u.scopes) {
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

        try {
            const res = await NSSAuth.apiFetch("/api/v1/auth/me");
            if (!res.ok) throw new Error("Auth failed");
            component.currentUser = await res.json();
            NSSAuth.setCachedUser(component.currentUser);
        } catch {
            NSSAuth.clearTokens();
            window.location.href = opts.redirectUrl || "/login";
            component.authLoading = false;
            return false;
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
