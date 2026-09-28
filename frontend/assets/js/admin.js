/**
 * NSS ERP — Admin Dashboard (Tier 5)
 *
 * Alpine.js component for user administration.
 * Tabs: Users list, User detail (with roles), Create user, Change password.
 * All API calls use NSSAuth.apiFetch() for automatic JWT handling.
 */

function adminApp() {
    return {
        // ── Shared layout (sidebar toggle, topbar user info) ──
        ...NSSLayout.mixin(),

        // ── Tab navigation ─────────────────────────────────────
        activeTab: "users",  // users | detail | create | createSS | password | organizations

        // ── Users list ─────────────────────────────────────────
        users: [],
        usersTotal: 0,
        usersPage: 1,
        usersPageSize: 20,
        usersSearch: "",
        usersStatusFilter: "",
        // Server-side sort state. Empty key = server default
        // (newest first), which is what the list showed before sorting
        // existed — so the initial view is unchanged.
        usersSortBy: "",
        usersSortDir: "asc",
        usersLoading: false,
        usersError: "",

        // ── User detail ────────────────────────────────────────
        selectedUser: null,
        detailLoading: false,
        detailError: "",

        // Role-assignment sorting. This list is sorted in the browser, not
        // on the server, and that is correct here: the detail response
        // carries every role the account has, so reordering what is on
        // screen reorders the whole set. (Contrast the paginated user list,
        // where the browser only ever holds one page.)
        rolesSortBy: "",
        rolesSortDir: "asc",

        // ── Create Person & Account ──────────────────────────────
        createForm: {
            person_pk: "", password: "", force_password_change: true,
            // Optional bundled Sangha Sevi creation (mirrors the standalone
            // Create Sangha Sevi tab — same Sakha auto-select/lock pattern,
            // ORG-BR-103).
            create_sangha_sevi: false, membership_type_pk: "",
            organization_pk: "", joining_date: "", local_sakha_number: "",
        },
        createLoading: false,
        createError: "",
        createSuccess: "",

        // ── Person search (for create user) ───────────────────
        personSearchQuery: "",
        personSearchResults: [],
        personSearchTotal: 0,
        personSearchLoading: false,
        personSearchDone: false,
        selectedPersonDisplay: {},

        // Search-result sorting (client-side — /person/search returns the
        // whole result set in one response, so what is on screen is all
        // there is). Empty means "keep relevance order", which is what the
        // search endpoint ranks by and usually the most useful default.
        personSearchSortBy: "",
        personSearchSortDir: "asc",
        ssPersonSearchSortBy: "",
        ssPersonSearchSortDir: "asc",

        // ── New person form (inline in create user) ───────────
        showNewPersonForm: false,
        newPersonForm: {
            first_name: "", middle_name: "", last_name: "",
            date_of_birth: "", gender_master_data_pk: "",
            country_phone_code: NSS.DEFAULT_COUNTRY_CODE,
            mobile_number: "", email: "",
        },
        newPersonLoading: false,
        // Live duplicate-contact lookup for the new-person form. Each holds
        // the conflicting person ({person_id, person_name}) or null.
        contactCheck: { mobile: null, email: null },
        _contactCheckTimer: null,

        // ── Reference data (loaded on init) ──────────────────
        genders: [],

        // ── Create Sangha Sevi ────────────────────────────────
        ssForm: {
            person_pk: "", membership_type_pk: "", organization_pk: "",
            joining_date: "", local_sakha_number: "",
            // Optional bundled login-account creation. Login is by
            // sangha_sevi_id, so the SS flow is the right place to offer it.
            create_user_account: false, password: "", force_password_change: true,
        },
        ssLoading: false,
        ssError: "",
        ssSuccess: "",
        ssPersonSearchQuery: "",
        ssPersonSearchResults: [],
        ssPersonSearchTotal: 0,
        ssPersonSearchLoading: false,
        ssPersonSearchDone: false,
        ssSelectedPerson: {},

        // Sakha auto-select/lock for member-attach forms (mirrors the
        // Kumari/Sevak parent-Sakha pattern): a single-Sakha admin gets
        // their Sakha auto-selected and the dropdown locked.
        sakhaScope: { mode: "choose", auto_select_pk: null, sakhas: [] },

        // ── Membership types (for SS creation) ────────────────
        membershipTypes: [],

        // ── Reset password ─────────────────────────────────────
        resetForm: { new_password: "", force_password_change: true },
        resetLoading: false,
        resetError: "",
        resetSuccess: "",
        showResetModal: false,
        resetTargetPk: null,
        resetTargetName: "",

        // ── Status change ──────────────────────────────────────
        statusLoading: false,
        statusError: "",
        showStatusModal: false,
        statusTargetPk: null,
        statusTargetName: "",
        statusNewValue: "ACTIVE",

        // ── Role assignment ────────────────────────────────────
        roleForm: { role_code: "", scope_level: "NSS-WIDE", organization_pk: "" },
        roleLoading: false,
        roleError: "",
        roleSuccess: "",
        showRoleModal: false,
        roleTargetPk: null,
        roleTargetName: "",

        // ── Available roles (fetched from bootstrap API) ───────
        availableRoles: [],

        // ── Available organizations (fetched for scope picker) ──
        organizations: [],

        // ── Change own password ────────────────────────────────
        pwForm: { current_password: "", new_password: "", confirm_password: "" },
        pwLoading: false,
        pwError: "",
        pwSuccess: "",

        // ── Toast ──────────────────────────────────────────────
        toast: "",
        toastType: "success",

        // ── Organization management ───────────────────────────
        orgsList: [],
        orgsTotal: 0,
        orgPage: 1,
        orgPageSize: 50,
        orgSearch: "",
        orgTypeFilter: "SAKHA_SANGHA",
        orgsLoading: false,
        // Organizations sorting. Empty keeps the server default
        // (organization_code), the order this list shipped with.
        orgsSortBy: "",
        orgsSortDir: "asc",
        editingOrgPk: null,
        editingShortCode: "",
        savingShortCode: false,
        inlineShortCodeCheck: { checking: false, conflict: null },

        // ── Organization detail editing ───────────────────────
        editOrgDetailPk: null,
        editOrgForm: {},
        savingOrgDetail: false,

        // ── Create Organization (NSS_ERP_ADMIN only) ─────────
        createOrgForm: {
            organization_name: "", organization_type_code: "",
            parent_organization_pk: "", organization_code: "", short_code: "",
            has_own_premises: false,
            address_line_1: "", city_village_name: "",
            country_pk: "", state_pk: "", district_pk: "", postal_code_value: "",
            phone_number: "", mobile_number: "", org_email: "",
            org_website_url: "", org_youtube_channel_url: "",
        },
        createOrgLoading: false,
        createOrgError: "",
        createOrgSuccess: "",
        orgTypes: [],
        createOrgCountries: [],
        createOrgStates: [],
        createOrgDistricts: [],
        // Kumari/Sevak Sakha-scoped parent selection (ORG-BR-101/102).
        // { mode: 'choose'|'locked', auto_select_pk, sakhas: [...] }
        kumariSevakScope: { mode: "choose", auto_select_pk: null, sakhas: [] },
        kumariSevakScopeLoading: false,

        // ── Auto-generated org code preview (ORG-BR-105) ─────────────
        // Live "what the code will be if submitted" value for the selected
        // non-wing type, peeked from the sequence (never consumed) via
        // GET /admin/organizations/next-code. Blank for wings/typeless.
        orgCodePreview: "",
        orgCodePreviewLoading: false,

        // ── Live duplicate check for organization_code / short_code ──
        // { checking, conflict, checkedValue } per field; _codeCheckTimers
        // holds the per-field debounce handles.
        orgCodeCheck: { checking: false, conflict: null },
        shortCodeCheck: { checking: false, conflict: null },
        _codeCheckTimers: {},

        // ── Location lookups (for org edit cascading dropdowns) ──
        locationCountries: [],
        locationStates: [],
        locationDistricts: [],

        // ── Computed helpers ───────────────────────────────────
        get totalPages() {
            return Math.max(1, Math.ceil(this.usersTotal / this.usersPageSize));
        },

        get canManageUsers() {
            return this.currentUser &&
                (this.currentUser.permissions.includes("ADMIN_USER_MANAGE") ||
                 this.currentUser.permissions.includes("PERSON_MANAGE"));
        },

        // ADMIN-BR-078: account provisioning is a scoped operation, not
        // reserved to the global authority. Any admin who can manage users
        // (ADMIN_USER_MANAGE or PERSON_MANAGE) may create accounts within
        // their scope; the API enforces the scope boundary.
        get canCreateAccounts() {
            return this.canManageUsers;
        },

        get canViewUsers() {
            return this.currentUser &&
                (this.currentUser.permissions.includes("ADMIN_USER_VIEW") ||
                 this.currentUser.permissions.includes("ADMIN_USER_MANAGE") ||
                 this.currentUser.permissions.includes("MEMBERSHIP_APPROVE"));
        },

        get canManageRoles() {
            return this.currentUser &&
                (this.currentUser.permissions.includes("ADMIN_ROLE_MANAGE"));
        },

        get canManageSettings() {
            return this.currentUser &&
                this.currentUser.permissions.includes("FOUNDATION_MANAGE");
        },

        get canManageMasterData() {
            return this.currentUser &&
                this.currentUser.permissions.includes("FOUNDATION_MANAGE");
        },

        get canApproveClaims() {
            return this.currentUser &&
                (this.currentUser.permissions.includes("MEMBERSHIP_APPROVE"));
        },

        get isNssAdmin() {
            return this.currentUser &&
                this.currentUser.scopes &&
                this.currentUser.scopes.some(s => s.role_code === "NSS_ERP_ADMIN");
        },

        canEditOrg(org) {
            if (!this.currentUser) return false;
            // ORGANIZATION_MANAGE = can edit any org (NSS Admin, Kendra Admin)
            if (this.currentUser.permissions.includes("ORGANIZATION_MANAGE")) return true;
            // Scoped admins: can edit only orgs matching their scope
            if (!this.currentUser.scopes) return false;
            return this.currentUser.scopes.some(
                s => s.organization_pk && s.organization_pk === org.organization_pk
            );
        },

        // Orgs filtered by the selected scope level in role assignment modal
        get scopeFilteredOrgs() {
            const level = this.roleForm.scope_level;
            if (!level || level === "NSS-WIDE") return [];
            // KENDRA_MAHILA_SANGHA is not its own organization_type_code —
            // it's the single MAHILA_SANGHA row whose parent is KENDRA
            // (see api/routers/admin.py's _ALLOWED_PARENT_TYPES comment).
            if (level === "KENDRA_MAHILA_SANGHA") {
                const kendra = this.organizations.find(o => o.organization_type_code === "KENDRA");
                return this.organizations.filter(
                    o => o.organization_type_code === "MAHILA_SANGHA" &&
                         kendra && o.parent_organization_pk === kendra.organization_pk
                );
            }
            // Map scope levels to org type codes
            const scopeToType = {
                KENDRA: ["KENDRA"],
                ZILLA: ["ZILLA_SANGHA"],
                ANCHALIKA: ["ANCHALIKA_SANGHA"],
                SAKHA: ["SAKHA_SANGHA"],
                PATHA_CHAKRA: ["PATHA_CHAKRA"],
            };
            const allowedTypes = scopeToType[level];
            if (!allowedTypes) return this.organizations;
            return this.organizations.filter(
                o => allowedTypes.includes(o.organization_type_code)
            );
        },

        // ── Initialization ─────────────────────────────────────

        async init() {
            const ok = await NSSLayout.initAuth(this);
            if (!ok) return;

            // ── Authorization guard: admin permissions required ────
            // Redirect non-admin users to the dashboard.
            const perms = this.currentUser.permissions || [];
            const hasAdminAccess = perms.some(p =>
                p.startsWith("ADMIN_") || p === "MEMBERSHIP_APPROVE"
            );
            if (!hasAdminAccess) {
                window.location.href = "/dashboard";
                return;
            }

            // Load reference data in parallel
            await Promise.all([
                this.fetchUsers(),
                this.fetchAvailableRoles(),
                this.fetchOrganizations(),
                this.fetchMembershipTypes(),
                this.loadOrgTypes(),
                this.loadClaimsPendingCount(),
                this.loadClaimSakhas(),
                this.loadGenders(),
                this.loadSakhaScope(),
            ]);

            // Handle hash-based tab navigation (e.g. /admin#claims, /admin#detail/uuid)
            const hash = window.location.hash.replace("#", "");
            if (hash.startsWith("detail/")) {
                const userPk = hash.substring("detail/".length);
                if (userPk) {
                    this.activeTab = "detail";
                    this.viewUser(userPk);
                }
            } else if (hash) {
                this.activeTab = hash;
                if (hash === "claims") this.loadClaims();
            }

            // Sync tab state to URL hash on every switch
            this.$watch("activeTab", (tab) => {
                // detail tab hash is managed by viewUser() to include the PK
                if (tab !== "detail") {
                    history.replaceState(null, "", `#${tab}`);
                }
            });
        },

        // ── Users list ─────────────────────────────────────────

        /**
         * Generic client-side sort state, keyed by list name.
         *
         * Used by the small fully-loaded lists — Reference Data values and
         * documents, Geography cities and postal codes. Each of those holds
         * its entire dataset in the browser, so reordering on screen
         * reorders the whole list and no request is needed. The named
         * per-list handlers above exist only where the list is paginated or
         * capped and the sort therefore has to happen in SQL.
         */
        clientSort: {},

        sortList(list, key) {
            const current = this.clientSort[list] || { key: "", dir: NSS.SORT_DIR_ASC };
            this.clientSort = {
                ...this.clientSort,
                [list]: NSS.toggleSort(current.key, current.dir, key),
            };
        },

        clientSortKey(list) {
            return (this.clientSort[list] || {}).key || "";
        },

        clientSortDir(list) {
            return (this.clientSort[list] || {}).dir || NSS.SORT_DIR_ASC;
        },

        sortedList(list, rows, accessor) {
            const state = this.clientSort[list];
            if (!state || !state.key) return rows || [];
            return NSS.sortRows(rows || [], state.key, state.dir, accessor);
        },

        /**
         * Value accessor for person rows.
         *
         * Needed because the Name column is not a field — the table
         * composes it from first/middle/last. Sorting on a non-existent
         * "person_name" property would compare undefined against
         * undefined and silently leave the rows in place, which looks
         * like a broken header rather than a missing accessor.
         */
        _personRowValue(row, key) {
            if (key === "person_name") {
                return [row.first_name, row.middle_name, row.last_name]
                    .filter(Boolean)
                    .join(" ");
            }
            return row ? row[key] : undefined;
        },

        sortPersonSearch(key) {
            const next = NSS.toggleSort(this.personSearchSortBy, this.personSearchSortDir, key);
            this.personSearchSortBy = next.key;
            this.personSearchSortDir = next.dir;
        },

        sortedPersonSearchResults() {
            if (!this.personSearchSortBy) return this.personSearchResults;
            return NSS.sortRows(
                this.personSearchResults, this.personSearchSortBy,
                this.personSearchSortDir, this._personRowValue,
            );
        },

        sortSsPersonSearch(key) {
            const next = NSS.toggleSort(this.ssPersonSearchSortBy, this.ssPersonSearchSortDir, key);
            this.ssPersonSearchSortBy = next.key;
            this.ssPersonSearchSortDir = next.dir;
        },

        sortedSsPersonSearchResults() {
            if (!this.ssPersonSearchSortBy) return this.ssPersonSearchResults;
            return NSS.sortRows(
                this.ssPersonSearchResults, this.ssPersonSearchSortBy,
                this.ssPersonSearchSortDir, this._personRowValue,
            );
        },

        /**
         * Header click on the Role Assignments table (client-side).
         */
        sortUserRoles(key) {
            const next = NSS.toggleSort(this.rolesSortBy, this.rolesSortDir, key);
            this.rolesSortBy = next.key;
            this.rolesSortDir = next.dir;
        },

        /**
         * Role rows in the currently requested order.
         *
         * Returns the untouched array when no column is selected, so the
         * order the API sent is preserved until the user asks otherwise.
         */
        sortedUserRoles() {
            const rows = this.selectedUser?.roles || [];
            if (!this.rolesSortBy) return rows;
            return NSS.sortRows(rows, this.rolesSortBy, this.rolesSortDir);
        },

        /**
         * Header click on the User Accounts table.
         *
         * Resets to page 1 deliberately: re-sorting while sitting on
         * page 3 would leave the user looking at rows 41-60 of a brand
         * new ordering, which reads as random data.
         */
        sortUsers(key) {
            const next = NSS.toggleSort(this.usersSortBy, this.usersSortDir, key);
            this.usersSortBy = next.key;
            this.usersSortDir = next.dir;
            this.usersPage = 1;
            this.fetchUsers();
        },

        async fetchUsers() {
            this.usersLoading = true;
            this.usersError = "";

            try {
                const params = new URLSearchParams({
                    page: this.usersPage,
                    page_size: this.usersPageSize,
                });
                if (this.usersSearch.trim()) params.set("search", this.usersSearch.trim());
                if (this.usersStatusFilter) params.set("account_status", this.usersStatusFilter);
                if (this.usersSortBy) {
                    params.set("sort_by", this.usersSortBy);
                    params.set("sort_dir", this.usersSortDir);
                }

                const res = await NSSAuth.apiFetch(`/api/v1/admin/users?${params}`);
                if (!res.ok) {
                    if (res.status === 403) {
                        this.usersError = "You do not have permission to view users.";
                        return;
                    }
                    throw new Error(await NSS.extractError(res));
                }
                const data = await res.json();
                this.users = data.users;
                this.usersTotal = data.total;
            } catch (err) {
                this.usersError = err.message || "Failed to load users.";
            } finally {
                this.usersLoading = false;
            }
        },

        searchUsers() {
            this.usersPage = 1;
            this.fetchUsers();
        },

        goToPage(page) {
            if (page < 1 || page > this.totalPages) return;
            this.usersPage = page;
            this.fetchUsers();
        },

        // ── User detail ────────────────────────────────────────

        async viewUser(userAccountPk) {
            this.activeTab = "detail";
            history.replaceState(null, "", `#detail/${userAccountPk}`);
            this.detailLoading = true;
            this.detailError = "";
            this.selectedUser = null;

            try {
                const res = await NSSAuth.apiFetch(`/api/v1/admin/users/${userAccountPk}`);
                if (!res.ok) throw new Error(await NSS.extractError(res));
                this.selectedUser = await res.json();
            } catch (err) {
                this.detailError = err.message || "Failed to load user detail.";
            } finally {
                this.detailLoading = false;
            }
        },

        backToList() {
            this.activeTab = "users";
            this.selectedUser = null;
        },

        // ── Create user ────────────────────────────────────────

        async searchPersons() {
            const q = this.personSearchQuery.trim();
            if (q.length < 2) return;
            this.personSearchLoading = true;
            this.personSearchResults = [];
            this.personSearchDone = false;

            try {
                const res = await NSSAuth.apiFetch(`/api/v1/person/search?q=${encodeURIComponent(q)}`);
                if (res.ok) {
                    const data = await res.json();
                    this.personSearchResults = data.persons;
                    this.personSearchTotal = data.total;
                }
            } catch (_) {}
            this.personSearchLoading = false;
            this.personSearchDone = true;
        },

        selectPerson(p) {
            this.createForm.person_pk = p.person_pk;
            this.selectedPersonDisplay = {
                person_pk: p.person_pk,
                person_id: p.person_id,
                person_name: p.person_name || [p.first_name, p.middle_name, p.last_name].filter(Boolean).join(" "),
                mobile_number: p.mobile_number,
                email: p.email,
                has_account: false,
            };
            this.showNewPersonForm = false;

            // Check if person already has a user account
            NSSAuth.apiFetch(`/api/v1/admin/users?search=${encodeURIComponent(p.person_id)}&page_size=1`)
                .then(res => res.ok ? res.json() : null)
                .then(data => {
                    if (data && data.users && data.users.some(u => u.person_pk === p.person_pk)) {
                        this.selectedPersonDisplay.has_account = true;
                    }
                })
                .catch(() => {});
        },

        clearSelectedPerson() {
            this.createForm.person_pk = "";
            this.selectedPersonDisplay = {};
        },

        async createNewPerson() {
            this.createError = "";
            this.newPersonLoading = true;

            try {
                const f = this.newPersonForm;

                // Validate mandatory fields
                if (!f.first_name.trim()) { this.createError = "First name is required."; return; }
                if (!f.last_name.trim()) { this.createError = "Last name is required."; return; }
                if (!f.date_of_birth) { this.createError = "Date of birth is required."; return; }
                if (!f.gender_master_data_pk) { this.createError = "Gender is required."; return; }

                const payload = {
                    first_name: f.first_name.trim(),
                    last_name: f.last_name.trim(),
                    date_of_birth: f.date_of_birth,
                    gender_master_data_pk: f.gender_master_data_pk,
                    password: crypto.randomUUID().slice(0, 12) + "Ax1!",  // Random throwaway — overwritten by createUser
                };
                if (f.middle_name.trim()) payload.middle_name = f.middle_name.trim();
                if (f.country_phone_code.trim()) payload.country_phone_code = f.country_phone_code.trim();
                if (f.mobile_number.trim()) payload.mobile_number = f.mobile_number.trim();
                if (f.email.trim()) payload.email = f.email.trim();

                // Use the registration endpoint to create person (admin bypass)
                const res = await NSSAuth.apiFetch("/api/v1/admin/persons", {
                    method: "POST",
                    body: JSON.stringify(payload),
                });

                if (!res.ok) {
                    const data = await res.json().catch(() => ({}));
                    this.createError = NSS.errorMessage(data, res.status);
                    return;
                }

                const data = await res.json();
                this.selectPerson({
                    person_pk: data.person_pk,
                    person_id: data.person_id,
                    person_name: data.person_name,
                    mobile_number: f.mobile_number.trim(),
                    email: f.email.trim(),
                    has_account: false,
                });
                this.showNewPersonForm = false;
                this.newPersonForm = {
                    first_name: "", middle_name: "", last_name: "",
                    date_of_birth: "", gender_master_data_pk: "",
                    country_phone_code: NSS.DEFAULT_COUNTRY_CODE,
                    mobile_number: "", email: "",
                };
                this.contactCheck = { mobile: null, email: null };
            } catch (err) {
                this.createError = err.message || "Failed to create person.";
            } finally {
                this.newPersonLoading = false;
            }
        },

        // Live, advisory duplicate-contact lookup for the new-person form.
        // Warns inline when the entered mobile/email already belongs to an
        // active person; the authoritative 409 still fires on submit.
        async checkNewPersonContact() {
            const f = this.newPersonForm;
            const mobile = (f.mobile_number || "").trim();
            const email = (f.email || "").trim();
            if (!mobile && !email) {
                this.contactCheck = { mobile: null, email: null };
                return;
            }
            const params = new URLSearchParams();
            if (mobile) {
                params.set("mobile_number", mobile);
                params.set("country_phone_code", (f.country_phone_code || "").trim());
            }
            if (email) params.set("email", email);
            try {
                const res = await NSSAuth.apiFetch(
                    `/api/v1/admin/persons/check-contact?${params.toString()}`
                );
                if (!res.ok) { this.contactCheck = { mobile: null, email: null }; return; }
                const data = await res.json();
                this.contactCheck = {
                    mobile: data?.mobile_conflict || null,
                    email: data?.email_conflict || null,
                };
            } catch (e) {
                this.contactCheck = { mobile: null, email: null };
            }
        },

        // Toggling the bundled-SS checkbox on the Create User form: apply
        // the Sakha lock/auto-select immediately so the field isn't blank
        // while the admin is looking at it; clear membership fields when
        // toggled off so a stale pick can't be silently resubmitted later.
        onToggleCreateSanghaSevi() {
            if (this.createForm.create_sangha_sevi) {
                this.applySakhaAutoSelect("createForm");
            } else {
                this.createForm.membership_type_pk = "";
                this.createForm.organization_pk = "";
                this.createForm.joining_date = "";
                this.createForm.local_sakha_number = "";
            }
        },

        async createUser() {
            this.createError = "";
            this.createSuccess = "";
            this.createLoading = true;

            try {
                const payload = {
                    person_pk: this.createForm.person_pk,
                    password: this.createForm.password,
                    force_password_change: this.createForm.force_password_change,
                };

                // Optional bundled Sangha Sevi creation (ORG-BR-103: same
                // Sakha auto-select/lock pattern as the standalone tab).
                if (this.createForm.create_sangha_sevi) {
                    payload.create_sangha_sevi = true;
                    payload.membership_type_pk = this.createForm.membership_type_pk;
                    payload.organization_pk = this.createForm.organization_pk;
                    payload.joining_date = this.createForm.joining_date;
                    const num = String(this.createForm.local_sakha_number || "").trim();
                    if (num) payload.local_sakha_erp_id = num;
                }

                const res = await NSSAuth.apiFetch("/api/v1/admin/users", {
                    method: "POST",
                    body: JSON.stringify(payload),
                });

                if (!res.ok) {
                    const data = await res.json().catch(() => ({}));
                    this.createError = NSS.errorMessage(data, res.status);
                    return;
                }

                const newUser = await res.json();
                this.createSuccess = `User account created for ${newUser.person_name || newUser.user_account_pk}.`;

                // Reset form
                this.createForm = {
                    person_pk: "", password: "", force_password_change: true,
                    create_sangha_sevi: false, membership_type_pk: "",
                    organization_pk: "", joining_date: "", local_sakha_number: "",
                };
                this.selectedPersonDisplay = {};
                this.personSearchResults = [];
                this.personSearchQuery = "";
                this.personSearchDone = false;
                this.applySakhaAutoSelect("createForm");

                this.fetchUsers();
            } catch (err) {
                this.createError = err.message || "Failed to create user.";
            } finally {
                this.createLoading = false;
            }
        },

        // ── Create Sangha Sevi ────────────────────────────────

        async searchPersonsForSS() {
            const q = this.ssPersonSearchQuery.trim();
            if (q.length < 2) return;
            this.ssPersonSearchLoading = true;
            this.ssPersonSearchResults = [];
            this.ssPersonSearchDone = false;

            try {
                const res = await NSSAuth.apiFetch(`/api/v1/person/search?q=${encodeURIComponent(q)}`);
                if (res.ok) {
                    const data = await res.json();
                    const persons = data.persons;
                    this.ssPersonSearchResults = persons;
                    this.ssPersonSearchTotal = data.total;

                    // Batch-check which persons already have a Sangha Sevi record
                    if (persons.length > 0) {
                        const pks = persons.map(p => p.person_pk);
                        try {
                            const checkRes = await NSSAuth.apiFetch("/api/v1/admin/sangha-sevi/check-batch", {
                                method: "POST",
                                body: JSON.stringify({ person_pks: pks }),
                            });
                            if (checkRes.ok) {
                                const ssMap = await checkRes.json();
                                this.ssPersonSearchResults = persons.map(p => {
                                    const info = ssMap[p.person_pk] || {};
                                    return {
                                        ...p,
                                        _already_ss: !!info.sangha_sevi_id,
                                        _existing_ss_id: info.sangha_sevi_id || null,
                                        _pending_claim: !!info.pending_claim_pk,
                                        _pending_claim_pk: info.pending_claim_pk || null,
                                        _pending_claim_org: info.pending_claim_org || null,
                                    };
                                });
                            }
                        } catch (_) {}
                    }
                }
            } catch (_) {}
            this.ssPersonSearchLoading = false;
            this.ssPersonSearchDone = true;
        },

        selectPersonForSS(p) {
            // Block selection if already flagged as existing SS from batch check
            if (p._already_ss) {
                this.ssError = `This person is already a Sangha Sevi (ID: ${p._existing_ss_id}). Cannot create another.`;
                return;
            }
            // Block selection if a pending registration claim exists
            if (p._pending_claim) {
                this.ssError = `This person has a pending registration claim. Approve or reject it first.`;
                return;
            }

            this.ssForm.person_pk = p.person_pk;
            this.ssSelectedPerson = {
                person_pk: p.person_pk,
                person_id: p.person_id,
                person_name: p.person_name || [p.first_name, p.middle_name, p.last_name].filter(Boolean).join(" "),
            };
            this.ssError = "";

            // Check if this person already has a Sangha Sevi record
            NSSAuth.apiFetch(`/api/v1/admin/sangha-sevi/check/${p.person_pk}`)
                .then(res => res.ok ? res.json() : null)
                .then(data => {
                    if (data && data.has_sangha_sevi) {
                        this.ssSelectedPerson.already_ss = true;
                        this.ssSelectedPerson.existing_ss_id = data.sangha_sevi_id;
                        this.ssError = `This person is already a Sangha Sevi (ID: ${data.sangha_sevi_id}). Cannot create another.`;
                    }
                })
                .catch(() => {});
        },

        // Fetch the caller's Sakha selection mode for member-attach forms.
        // mode="locked" → single eligible Sakha, auto-selected + dropdown
        // disabled; mode="choose" → NSS-wide or multi-Sakha admin picks.
        async loadSakhaScope() {
            try {
                const res = await NSSAuth.apiFetch("/api/v1/admin/sakha-scope-options");
                if (!res.ok) return;
                const data = await res.json();
                this.sakhaScope = {
                    mode: data.mode || "choose",
                    auto_select_pk: data.auto_select_pk || null,
                    sakhas: data.sakhas || [],
                };
                this.applySakhaAutoSelect();
            } catch (_) { /* non-fatal: dropdown stays in choose mode */ }
        },

        // Fill the locked Sakha into a member-attach form if nothing is
        // chosen yet. `formKey` names the reactive form ("ssForm" by
        // default, or "createForm" for the bundled Create-User+SS flow —
        // both use the same organization_pk field name).
        applySakhaAutoSelect(formKey = "ssForm") {
            const form = this[formKey];
            if (this.sakhaScope.mode === "locked" && this.sakhaScope.auto_select_pk
                && !form.organization_pk) {
                form.organization_pk = this.sakhaScope.auto_select_pk;
            }
        },

        async createSanghaSevi() {
            this.ssError = "";
            this.ssSuccess = "";
            this.ssLoading = true;

            try {
                const payload = {
                    person_pk: this.ssForm.person_pk,
                    membership_type_pk: this.ssForm.membership_type_pk,
                    organization_pk: this.ssForm.organization_pk,
                    joining_date: this.ssForm.joining_date,
                };
                // Send raw local number — backend composes <short_code><number>
                const num = String(this.ssForm.local_sakha_number || "").trim();
                if (num) {
                    payload.local_sakha_erp_id = num;
                }

                // Optional bundled login-account creation (requires the
                // caller to hold ADMIN_USER_MANAGE — the backend enforces it
                // and returns a clear 403 otherwise).
                if (this.ssForm.create_user_account) {
                    payload.create_user_account = true;
                    payload.password = this.ssForm.password;
                    payload.force_password_change = this.ssForm.force_password_change;
                }

                const res = await NSSAuth.apiFetch("/api/v1/admin/sangha-sevi", {
                    method: "POST",
                    body: JSON.stringify(payload),
                });

                if (!res.ok) {
                    const data = await res.json().catch(() => ({}));
                    this.ssError = NSS.errorMessage(data, res.status);
                    return;
                }

                const data = await res.json();
                this.ssSuccess = data.user_account_pk
                    ? `Sangha Sevi created — ID: ${data.sangha_sevi_id || data.sangha_sevi_pk}. Login account created (login with the Sangha Sevi ID).`
                    : `Sangha Sevi created — ID: ${data.sangha_sevi_id || data.sangha_sevi_pk}.`;

                // Reset form
                this.ssForm = {
                    person_pk: "", membership_type_pk: "", organization_pk: "",
                    joining_date: "", local_sakha_number: "",
                    create_user_account: false, password: "", force_password_change: true,
                };
                this.ssSelectedPerson = {};
                this.ssPersonSearchResults = [];
                this.ssPersonSearchQuery = "";
                this.ssPersonSearchDone = false;
                this.applySakhaAutoSelect();
            } catch (err) {
                this.ssError = err.message || "Failed to create Sangha Sevi.";
            } finally {
                this.ssLoading = false;
            }
        },

        // ── Reset password modal ───────────────────────────────

        openResetModal(user) {
            this.resetTargetPk = user.user_account_pk;
            this.resetTargetName = user.sangha_sevi_id || user.person_name || "User";
            this.resetForm = { new_password: "", force_password_change: true };
            this.resetError = "";
            this.resetSuccess = "";
            this.showResetModal = true;
        },

        async submitResetPassword() {
            this.resetError = "";
            this.resetSuccess = "";
            this.resetLoading = true;

            try {
                const res = await NSSAuth.apiFetch(
                    `/api/v1/admin/users/${this.resetTargetPk}/reset-password`,
                    {
                        method: "POST",
                        body: JSON.stringify(this.resetForm),
                    }
                );

                if (!res.ok) {
                    const data = await res.json().catch(() => ({}));
                    this.resetError = NSS.errorMessage(data, res.status);
                    return;
                }

                this.resetSuccess = "Password reset successfully.";
                setTimeout(() => { this.showResetModal = false; }, 1200);
            } catch (err) {
                this.resetError = err.message || "Failed to reset password.";
            } finally {
                this.resetLoading = false;
            }
        },

        // ── Status change modal ────────────────────────────────

        openStatusModal(user) {
            if (user.user_account_pk === this.currentUser?.user_account_pk) {
                NSSDialog.alert("You cannot change your own account status.");
                return;
            }
            this.statusTargetPk = user.user_account_pk;
            this.statusTargetName = user.sangha_sevi_id || user.person_name || "User";
            this.statusNewValue = user.account_status === "ACTIVE" ? "LOCKED" : "ACTIVE";
            this.statusError = "";
            this.showStatusModal = true;
        },

        async submitStatusChange() {
            if (this.statusTargetPk === this.currentUser?.user_account_pk) {
                this.statusError = "Cannot change your own account status.";
                return;
            }
            this.statusError = "";
            this.statusLoading = true;

            try {
                const res = await NSSAuth.apiFetch(
                    `/api/v1/admin/users/${this.statusTargetPk}/status`,
                    {
                        method: "PATCH",
                        body: JSON.stringify({ account_status: this.statusNewValue }),
                    }
                );

                if (!res.ok) {
                    const data = await res.json().catch(() => ({}));
                    this.statusError = NSS.errorMessage(data, res.status);
                    return;
                }

                this.showStatusModal = false;
                this.showToast(`Status changed to ${this.statusNewValue}.`);
                this.fetchUsers();
                // Refresh detail if viewing same user
                if (this.selectedUser && this.selectedUser.user_account_pk === this.statusTargetPk) {
                    this.viewUser(this.statusTargetPk);
                }
            } catch (err) {
                this.statusError = err.message || "Failed to update status.";
            } finally {
                this.statusLoading = false;
            }
        },

        // ── Role assignment modal ──────────────────────────────

        openRoleModal(user) {
            this.roleTargetPk = user.user_account_pk;
            this.roleTargetName = user.sangha_sevi_id || user.person_name || "User";
            this.roleForm = { role_code: "", scope_level: "NSS-WIDE", organization_pk: "" };
            this.roleError = "";
            this.roleSuccess = "";
            this.showRoleModal = true;
        },

        async submitAssignRole() {
            this.roleError = "";
            this.roleSuccess = "";
            this.roleLoading = true;

            try {
                const body = {
                    role_code: this.roleForm.role_code,
                    scope_level: this.roleForm.scope_level,
                    organization_pk: this.roleForm.scope_level === "NSS-WIDE"
                        ? null
                        : (this.roleForm.organization_pk || null),
                };

                const res = await NSSAuth.apiFetch(
                    `/api/v1/admin/users/${this.roleTargetPk}/roles`,
                    { method: "POST", body: JSON.stringify(body) }
                );

                if (!res.ok) {
                    const data = await res.json().catch(() => ({}));
                    this.roleError = NSS.errorMessage(data, res.status);
                    return;
                }

                this.roleSuccess = "Role assigned successfully.";
                setTimeout(() => { this.showRoleModal = false; }, 1200);
                // Refresh detail
                if (this.selectedUser && this.selectedUser.user_account_pk === this.roleTargetPk) {
                    this.viewUser(this.roleTargetPk);
                }
            } catch (err) {
                this.roleError = err.message || "Failed to assign role.";
            } finally {
                this.roleLoading = false;
            }
        },

        async revokeRole(userAccountPk, userRolePk) {
            if (userAccountPk === this.currentUser?.user_account_pk) {
                await NSSDialog.alert("You cannot revoke your own role — this would remove your own access.");
                return;
            }
            const ok = await NSSDialog.confirm(
                "Revoke this role assignment?",
                { title: "Revoke Role", confirmText: "Revoke", confirmClass: "btn-error" }
            );
            if (!ok) return;

            try {
                const res = await NSSAuth.apiFetch(
                    `/api/v1/admin/users/${userAccountPk}/roles/${userRolePk}`,
                    { method: "DELETE" }
                );
                if (!res.ok) {
                    const data = await res.json().catch(() => ({}));
                    await NSSDialog.alert(data.detail || "Failed to revoke role.");
                    return;
                }
                this.showToast("Role revoked.");
                this.viewUser(userAccountPk);
            } catch (err) {
                await NSSDialog.alert(err.message || "Failed to revoke role.");
            }
        },

        // ── Delete user ───────────────────────────────────────

        async deleteUser(userAccountPk, displayName) {
            if (userAccountPk === this.currentUser?.user_account_pk) {
                await NSSDialog.alert("You cannot delete your own account.");
                return;
            }
            const ok = await NSSDialog.confirm(
                `Permanently deactivate account for "${displayName}"? This will revoke all roles and disable login.`,
                { title: "Delete User Account", confirmText: "Delete", confirmClass: "btn-error" }
            );
            if (!ok) return;

            try {
                const res = await NSSAuth.apiFetch(
                    `/api/v1/admin/users/${userAccountPk}`,
                    { method: "DELETE" }
                );
                if (!res.ok) {
                    const data = await res.json().catch(() => ({}));
                    await NSSDialog.alert(data.detail || "Failed to delete user.");
                    return;
                }
                const data = await res.json();
                this.showToast(data.message || "User deleted.");
                // Go back to list and refresh
                if (this.activeTab === "detail") {
                    this.backToList();
                }
                this.fetchUsers();
            } catch (err) {
                await NSSDialog.alert(err.message || "Failed to delete user.");
            }
        },

        // ── Change own password ────────────────────────────────

        async changeOwnPassword() {
            this.pwError = "";
            this.pwSuccess = "";

            if (this.pwForm.new_password !== this.pwForm.confirm_password) {
                this.pwError = "Passwords do not match.";
                return;
            }

            this.pwLoading = true;

            try {
                const res = await NSSAuth.apiFetch("/api/v1/auth/change-password", {
                    method: "POST",
                    body: JSON.stringify({
                        current_password: this.pwForm.current_password,
                        new_password: this.pwForm.new_password,
                    }),
                });

                if (!res.ok) {
                    const data = await res.json().catch(() => ({}));
                    this.pwError = NSS.errorMessage(data, res.status);
                    return;
                }

                this.pwSuccess = "Password changed successfully.";
                this.pwForm = { current_password: "", new_password: "", confirm_password: "" };
            } catch (err) {
                this.pwError = err.message || "Failed to change password.";
            } finally {
                this.pwLoading = false;
            }
        },

        // ── Reference data ─────────────────────────────────────

        async fetchAvailableRoles() {
            try {
                const res = await fetch("/api/v1/bootstrap/roles");
                if (res.ok) this.availableRoles = await res.json();
            } catch { /* non-critical */ }
        },

        async fetchMembershipTypes() {
            try {
                const res = await NSSAuth.apiFetch("/api/v1/foundation/master-data?category_code=MEMBERSHIP_TYPE");
                if (res.ok) this.membershipTypes = await res.json();
            } catch { /* non-critical */ }
        },

        async loadGenders() {
            try {
                const res = await NSSAuth.apiFetch("/api/v1/foundation/master-data?category_code=GENDER");
                if (res.ok) this.genders = await res.json();
            } catch { /* non-critical */ }
        },

        async fetchOrganizations() {
            try {
                const res = await NSSAuth.apiFetch(`/api/v1/organization/organizations?limit=${NSS.MAX_PAGE_SIZE}`);
                if (res.ok) {
                    const data = await res.json();
                    this.organizations = data.organizations || data || [];
                } else {
                    console.error("fetchOrganizations: API returned", res.status);
                }
            } catch (err) {
                console.error("fetchOrganizations: fetch error", err);
            }
        },

        // ── Organization short code management ─────────────────

        sortOrgs(key) {
            const next = NSS.toggleSort(this.orgsSortBy, this.orgsSortDir, key);
            this.orgsSortBy = next.key;
            this.orgsSortDir = next.dir;
            this.orgPage = 1;
            this.loadOrganizations();
        },

        async loadOrganizations() {
            this.orgsLoading = true;
            try {
                const params = new URLSearchParams({
                    page: this.orgPage,
                    page_size: this.orgPageSize,
                });
                if (this.orgTypeFilter) params.set("type_code", this.orgTypeFilter);
                if (this.orgSearch.trim()) params.set("search", this.orgSearch.trim());
                if (this.orgsSortBy) {
                    params.set("sort_by", this.orgsSortBy);
                    params.set("sort_dir", this.orgsSortDir);
                }

                const res = await NSSAuth.apiFetch(`/api/v1/admin/organizations?${params}`);
                if (res.ok) {
                    const data = await res.json();
                    this.orgsList = data.organizations;
                    this.orgsTotal = data.total;
                }
            } catch (err) {
                console.error("Failed to load organizations:", err);
            } finally {
                this.orgsLoading = false;
            }
        },

        startEditShortCode(org) {
            this.editingOrgPk = org.organization_pk;
            this.editingShortCode = org.short_code || "";
            this.inlineShortCodeCheck = { checking: false, conflict: null };
            this.$nextTick(() => {
                const input = this.$refs.shortCodeInput;
                if (input) input.focus();
            });
        },

        async saveShortCode(org) {
            if (this.inlineShortCodeCheck.conflict) {
                this.showToast(
                    `Short Code is already used by ${this.inlineShortCodeCheck.conflict.organization_name}.`,
                    "error"
                );
                return;
            }
            this.savingShortCode = true;
            const code = this.editingShortCode.trim().toUpperCase() || null;
            try {
                const res = await NSSAuth.apiFetch(
                    `/api/v1/admin/organizations/${org.organization_pk}/short-code`,
                    {
                        method: "PATCH",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ short_code: code }),
                    }
                );
                if (res.ok) {
                    const data = await res.json();
                    org.short_code = data.short_code;
                    this.editingOrgPk = null;
                    this.inlineShortCodeCheck = { checking: false, conflict: null };
                    this.showToast(data.message);
                } else {
                    const err = await res.json().catch(() => ({}));
                    this.showToast(err.detail || "Failed to update short code.", "error");
                }
            } catch (err) {
                this.showToast("Network error. Try again.", "error");
            } finally {
                this.savingShortCode = false;
            }
        },

        // ── Organization detail editing ───────────────────────

        startEditOrgDetail(org) {
            this.editOrgDetailPk = org.organization_pk;
            this.editOrgForm = {
                organization_name: org.organization_name || "",
                address_line_1: org.address_line_1 || "",
                phone_number: org.phone_number || "",
                mobile_number: org.mobile_number || "",
                org_email: org.org_email || "",
                country_pk: org.country_pk || "",
                state_pk: org.state_pk || "",
                district_pk: org.district_pk || "",
                city_village_name: org.city_village_name || "",
                postal_code_value: org.postal_code || "",
            };
            // Load cascading location lookups
            this.loadLocationCountries();
            if (org.country_pk) this.loadLocationStates(org.country_pk);
            if (org.state_pk) {
                this.loadLocationDistricts(org.state_pk);
            }
        },

        // ── Org-edit location cascade (shared utility) ──────────────

        _editLocCascade: NSSLocation.create({
            fetchFn: (...args) => NSSAuth.apiFetch(...args),
            arrays: {
                countries: 'locationCountries',
                states: 'locationStates',
                districts: 'locationDistricts',
            },
            form: 'editOrgForm',
        }),

        async loadLocationCountries() { await this._editLocCascade.loadCountries(this); },
        async loadLocationStates(pk)   { await this._editLocCascade.loadStates(this, pk); },
        async loadLocationDistricts(pk){ await this._editLocCascade.loadDistricts(this, pk); },
        onCountryChange()              { this._editLocCascade.onCountryChange(this); },
        onStateChange()                { this._editLocCascade.onStateChange(this); },
        onDistrictChange()             { this._editLocCascade.onDistrictChange(this); },

        cancelEditOrgDetail() {
            this.editOrgDetailPk = null;
            this.editOrgForm = {};
        },

        // ── Create Organization ──────────────────────────────

        // Parent orgs: dynamic based on selected org type (hierarchy rules)
        get parentOrgs() {
            const typeCode = this.createOrgForm.organization_type_code;
            if (!typeCode) return [];

            // Hierarchy: which parent types are allowed for each org type
            // (frozen NSS Bye-Law hierarchy — see api/routers/admin.py's
            // _ALLOWED_PARENT_TYPES for the authoritative comment).
            // Note: on the Create-Org form, ANCHALIKA_SANGHA/ZILLA_SANGHA/
            // PATHA_CHAKRA (ORG-BR-100, auto-resolved) and KUMARI_SANGHA/
            // SEVAK_SANGHA (ORG-BR-101/102, Sakha-scoped dropdown) are
            // rendered via dedicated UI paths and never reach this getter
            // for their own parent selection — those entries below stay for
            // completeness/parity with the backend map, not because this
            // form dispatches through them.
            const allowedParentTypes = {
                ANCHALIKA_SANGHA: ["KENDRA"],
                ZILLA_SANGHA: ["KENDRA"],
                PATHA_CHAKRA: ["KENDRA"],
                PARIBARIK_SANGHA: ["KENDRA"],
                SAKHA_SANGHA: ["ANCHALIKA_SANGHA", "ZILLA_SANGHA"],
                SAKHA_ASANA: ["ANCHALIKA_SANGHA", "ZILLA_SANGHA"],
                KUMARI_SANGHA: ["SAKHA_SANGHA"],
                SEVAK_SANGHA: ["SAKHA_SANGHA"],
                MAHILA_SANGHA: ["KENDRA", "SAKHA_SANGHA"],
                PARIBARIK_ASANA: ["SAKHA_SANGHA"],
            };

            const allowed = allowedParentTypes[typeCode];
            if (!allowed) return [];

            return this.organizations.filter(
                o => allowed.includes(o.organization_type_code)
            );
        },

        /**
         * Organization types that are never offered when a user is
         * *selecting* or *filtering by* an organization type.
         *
         * Basis — an operational convention, NOT an enforced invariant:
         *
         *   NILACHALA_KUTIRA, SMRUTI_MANDIRA — unique singleton
         *     institutions (Eternal Abode, Puri / Nigamananda Smruti
         *     Mandir), outside the membership hierarchy by convention.
         *
         *   KUMARI_SANGHA, SEVAK_SANGHA, MAHILA_SANGHA — wing bodies
         *     that hang off a Sakha Sangha (see the parent-type map in
         *     `parentOrgs`); membership is conventionally held at the
         *     Sakha, so the Sakha is the unit of selection.
         *
         *   PARIBARIK_ASANA — attaches to a `sangha_sevi`, not to an
         *     organization (ORG-BR-094); its `parent_organization_pk` is
         *     an explicitly labelled implementation proxy.
         *
         * IMPORTANT CAVEAT — do not read this list as a guarantee that
         * no member can sit on these types. Nothing enforces that:
         * `sangha_sevi.organization_pk` and
         * `membership_sakha_affiliation.organization_pk` are bare FKs to
         * nss.organization with no type CHECK, no trigger, and no API
         * validation (contrast family.py, which DOES validate
         * SAKHA_SANGHA). The bootstrap admin member SS1 in fact sits on
         * the KENDRA org, and admin.py defaults claim-less members to
         * KEN. So excluding a type here removes the ability to FILTER by
         * it; members on such an org remain visible under "All".
         *
         * OPEN: if these types must genuinely never hold members, that
         * belongs in a DB CHECK / API validation, not in a dropdown.
         *
         * This governs selection/filter dropdowns only. It is NOT an
         * authorization boundary and NOT applied to the Create
         * Organization type list — these organizations still exist and
         * are still reachable in the Organizations list and hierarchy.
         */
        nonSelectableOrgTypes: [
            "NILACHALA_KUTIRA",
            "SMRUTI_MANDIRA",
            "KUMARI_SANGHA",
            "SEVAK_SANGHA",
            "MAHILA_SANGHA",
            "PARIBARIK_ASANA",
        ],

        /**
         * The org types offered in every "pick / filter by an org type"
         * dropdown. Single source for the Organizations list filter and
         * the Member Directory Org Type filter, so the two can no longer
         * drift apart.
         */
        get selectableOrgTypes() {
            return this.orgTypes.filter(
                t => !this.nonSelectableOrgTypes.includes(t.value_code)
            );
        },

        // Org types for Create Org. ORG-BR-096: only these four are
        // creatable directly through the standard flow. Apex peers
        // (KENDRA / NILACHALA_KUTIRA / SMRUTI_MANDIRA) are singletons that
        // are never created; MAHILA_SANGHA is auto-created with its parent
        // Sakha; SAKHA_ASANA is not a distinct type (it is a SAKHA_SANGHA
        // with has_own_premises = FALSE, ORG-BR-098).
        get creatableOrgTypes() {
            const standard = ["ANCHALIKA_SANGHA", "ZILLA_SANGHA", "PATHA_CHAKRA", "SAKHA_SANGHA"];
            const allowed = [...standard];
            // Kumari/Sevak Sangha follow a Sakha-gated creation path
            // (ORG-BR-096, ORG-BR-101/102): offered only to NSS admins or
            // Sakha-scoped admins, parented by a Sakha the operator is
            // scoped to (see loadKumariSevakScope + backend gate).
            const hasSakhaScope = (this.currentUser?.scopes || []).some(
                s => s.scope_level === "SAKHA"
            );
            if (this.isNssAdmin || hasSakhaScope) {
                allowed.push("KUMARI_SANGHA", "SEVAK_SANGHA");
            }
            return this.orgTypes.filter(t => allowed.includes(t.value_code));
        },

        // ── Create-Org type-driven form behaviour (ORG-BR-098/099/100) ──
        // Shared by both the create form and the org-detail edit form so
        // the two stay consistent with the DB trigger (ORG-BR-099).
        // ORG-BR-099 was narrowed (2026-09-28): these 3 types may still
        // never carry a physical PREMISES address (address_line_1,
        // city_village_pk, postal_code_pk, latitude, longitude), but
        // country/state/district are administrative JURISDICTION, not a
        // premises, and are now allowed for every type — see the separate,
        // unconditional Country/State/District block in both forms.
        addressProhibitedForType(typeCode) {
            return ["ANCHALIKA_SANGHA", "ZILLA_SANGHA", "PATHA_CHAKRA"].includes(typeCode);
        },
        // ORG-BR-098: only SAKHA_SANGHA carries a premises attribute.
        get orgTypeHasPremises() {
            return this.createOrgForm.organization_type_code === "SAKHA_SANGHA";
        },
        // ORG-BR-099: premises-address columns (not country/state/district)
        // must stay NULL for these types.
        get orgTypeProhibitsAddress() {
            return this.addressProhibitedForType(this.createOrgForm.organization_type_code);
        },
        // ORG-BR-100: single-instance types are parented by the sole KENDRA;
        // the parent is auto-resolved and locked (operator does not choose).
        get isParentAutoResolved() {
            return this.addressProhibitedForType(this.createOrgForm.organization_type_code);
        },
        // ORG-BR-101/102: Kumari/Sevak Sangha are parented by a scoped Sakha.
        get isKumariSevakType() {
            return ["KUMARI_SANGHA", "SEVAK_SANGHA"].includes(
                this.createOrgForm.organization_type_code
            );
        },
        // The sole KENDRA org (parent for auto-resolved single-instance types).
        get kendraOrg() {
            return this.organizations.find(
                o => o.organization_type_code === "KENDRA"
            ) || null;
        },

        // Sakha orgs only (for SS creation dropdown), scoped by admin's org
        get sakhaOrgs() {
            const allSakha = this.organizations.filter(
                o => o.organization_type_code === "SAKHA_SANGHA"
            );
            // NSS-WIDE or full admin: show all
            if (this.isNssAdmin || !this.currentUser?.scopes) return allSakha;
            const isNssWide = this.currentUser.scopes.some(s => s.scope_level === "NSS-WIDE");
            if (isNssWide) return allSakha;
            // Scoped admin: filter to only their assigned org(s)
            const scopedPks = new Set(
                this.currentUser.scopes
                    .filter(s => s.organization_pk)
                    .map(s => s.organization_pk)
            );
            if (scopedPks.size === 0) return allSakha;
            return allSakha.filter(o => scopedPks.has(o.organization_pk));
        },

        async loadCreateOrgData() {
            // Load org types + countries if not already loaded
            await Promise.all([
                this.loadOrgTypes(),
                this.loadCreateOrgCountries(),
            ]);
        },

        // Handles every type-driven side effect on the Create Org form
        // (ORG-BR-098/099/100/101/102): reset stale parent/premises state,
        // lock the parent for single-instance-parent types, and fetch the
        // Kumari/Sevak Sakha-scope options when applicable.
        onCreateOrgTypeChange() {
            this.createOrgForm.parent_organization_pk = "";
            this.createOrgForm.has_own_premises = false;

            // ORG-BR-105: show the auto-generated org code preview for the
            // newly-selected type. Wings return no code (handled server-side);
            // non-wing types get a live "what the code will be" value.
            this.fetchOrgCodePreview();

            if (this.isParentAutoResolved) {
                // ORG-BR-100: single legal parent instance (the sole Kendra) —
                // resolved and locked here rather than left for the operator
                // to pick from a one-item list.
                if (this.kendraOrg) {
                    this.createOrgForm.parent_organization_pk = this.kendraOrg.organization_pk;
                }
                this.kumariSevakScope = { mode: "choose", auto_select_pk: null, sakhas: [] };
                return;
            }

            if (this.isKumariSevakType) {
                this.loadKumariSevakScope(this.createOrgForm.organization_type_code);
                return;
            }

            this.kumariSevakScope = { mode: "choose", auto_select_pk: null, sakhas: [] };
        },

        // ORG-BR-105: fetch a read-only preview of the org code that will be
        // minted for the selected type on submit. Peeked (not consumed) via
        // GET /admin/organizations/next-code, so opening the form never burns
        // a sequence number. Wings and typeless states resolve to a blank
        // preview. The authoritative code is assigned only on submit.
        async fetchOrgCodePreview() {
            const typeCode = this.createOrgForm.organization_type_code;
            if (!typeCode) {
                this.orgCodePreview = "";
                this.orgCodePreviewLoading = false;
                return;
            }
            this.orgCodePreviewLoading = true;
            try {
                const res = await NSSAuth.apiFetch(
                    `/api/v1/admin/organizations/next-code?organization_type_code=${encodeURIComponent(typeCode)}`
                );
                if (!res.ok) {
                    this.orgCodePreview = "";
                    return;
                }
                const data = await res.json();
                this.orgCodePreview = data?.next_code || "";
            } catch (e) {
                // Non-fatal: the code is authoritatively generated on submit
                // regardless. Leave the preview blank on failure.
                this.orgCodePreview = "";
            } finally {
                this.orgCodePreviewLoading = false;
            }
        },

        // ORG-BR-101/102: fetch the caller's Sakha selection mode for
        // Kumari/Sevak Sangha creation and auto-fill/lock the parent field
        // when unambiguous. Mirrors loadSakhaScope for member-attach forms.
        async loadKumariSevakScope(typeCode) {
            this.kumariSevakScopeLoading = true;
            try {
                const res = await NSSAuth.apiFetch(
                    `/api/v1/admin/organizations/kumari-sevak-sakha-options?type_code=${encodeURIComponent(typeCode)}`
                );
                if (!res.ok) {
                    this.kumariSevakScope = { mode: "choose", auto_select_pk: null, sakhas: [] };
                    return;
                }
                const data = await res.json();
                this.kumariSevakScope = {
                    mode: data.mode || "choose",
                    auto_select_pk: data.auto_select_pk || null,
                    sakhas: data.sakhas || [],
                };
                if (this.kumariSevakScope.mode === "locked" && this.kumariSevakScope.auto_select_pk) {
                    this.createOrgForm.parent_organization_pk = this.kumariSevakScope.auto_select_pk;
                }
            } catch (_) {
                this.kumariSevakScope = { mode: "choose", auto_select_pk: null, sakhas: [] };
            } finally {
                this.kumariSevakScopeLoading = false;
            }
        },

        async loadOrgTypes() {
            if (this.orgTypes.length === 0) {
                try {
                    const res = await NSSAuth.apiFetch("/api/v1/foundation/master-data?category_code=ORGANIZATION_TYPE");
                    if (res.ok) {
                        this.orgTypes = await res.json();
                    } else {
                        console.error("loadOrgTypes: API returned", res.status);
                    }
                } catch (err) {
                    console.error("loadOrgTypes: fetch error", err);
                }
            }
        },

        // ── Create-org location cascade (shared utility) ────────────

        _createLocCascade: NSSLocation.create({
            fetchFn: fetch,
            arrays: {
                countries: 'createOrgCountries',
                states: 'createOrgStates',
                districts: 'createOrgDistricts',
            },
            form: 'createOrgForm',
        }),

        async loadCreateOrgCountries() {
            if (this.createOrgCountries.length === 0) {
                await this._createLocCascade.loadCountries(this);
            }
        },
        async loadCreateOrgStates(pk)      { await this._createLocCascade.loadStates(this, pk); },
        async loadCreateOrgDistricts(pk)   { await this._createLocCascade.loadDistricts(this, pk); },
        onCreateOrgCountryChange()         { this._createLocCascade.onCountryChange(this); },
        onCreateOrgStateChange()           { this._createLocCascade.onStateChange(this); },
        onCreateOrgDistrictChange()        { this._createLocCascade.onDistrictChange(this); },

        // ── Live duplicate check for organization_code / short_code ──
        // Debounced per field. `field` is "organization_code" or
        // "short_code"; `stateKey` names the reactive slot to write into
        // ("orgCodeCheck" / "shortCodeCheck" / "inlineShortCodeCheck").
        // `excludePk` skips the row being edited (null on the create form).
        // Mirrors the server's GET /admin/organizations/code-availability,
        // which itself matches the DB uniqueness constraints (all rows,
        // active or not). `stateKey` also selects which form field to read
        // back for the staleness check — "inlineShortCodeCheck" reads the
        // inline-edit's `editingShortCode` rather than createOrgForm.
        onCodeInput(field, stateKey, rawValue, excludePk = null) {
            const slot = this[stateKey];
            // Both codes are stored/submitted uppercased (short_code by the
            // DB CHECK, organization_code by submitCreateOrg), so check
            // against the uppercased value to match what will actually land.
            const value = (rawValue || "").trim().toUpperCase();

            // Clear any stale result immediately; empty value = nothing to check.
            slot.conflict = null;
            if (!value) {
                slot.checking = false;
                if (this._codeCheckTimers[stateKey]) clearTimeout(this._codeCheckTimers[stateKey]);
                return;
            }

            slot.checking = true;
            if (this._codeCheckTimers[stateKey]) clearTimeout(this._codeCheckTimers[stateKey]);
            this._codeCheckTimers[stateKey] = setTimeout(async () => {
                try {
                    const params = new URLSearchParams({ field, value });
                    if (excludePk) params.set("exclude_pk", excludePk);
                    const res = await NSSAuth.apiFetch(
                        `/api/v1/admin/organizations/code-availability?${params}`
                    );
                    if (!res.ok) { slot.checking = false; slot.conflict = null; return; }
                    const data = await res.json();
                    // Ignore a stale response if the field changed meanwhile.
                    const current = stateKey === "inlineShortCodeCheck"
                        ? (this.editingShortCode || "").trim().toUpperCase()
                        : field === "short_code"
                            ? (this.createOrgForm.short_code || "").trim().toUpperCase()
                            : (this.createOrgForm.organization_code || "").trim().toUpperCase();
                    if (current !== data.value) return;
                    slot.conflict = data.available ? null : data.conflict;
                } catch (_e) {
                    slot.conflict = null;
                } finally {
                    slot.checking = false;
                }
            }, 350);
        },

        async submitCreateOrg() {
            this.createOrgError = "";
            this.createOrgSuccess = "";

            // Block submit on a known code/short-code conflict; the DB would
            // reject it anyway, but this gives a clean message up front.
            if (this.orgCodeCheck.conflict) {
                this.createOrgError = `Organization Code is already used by ${this.orgCodeCheck.conflict.organization_name}.`;
                return;
            }
            if (this.shortCodeCheck.conflict) {
                this.createOrgError = `Short Code is already used by ${this.shortCodeCheck.conflict.organization_name}.`;
                return;
            }

            this.createOrgLoading = true;

            try {
                const f = this.createOrgForm;
                const payload = {
                    organization_name: f.organization_name.trim(),
                    organization_type_code: f.organization_type_code,
                };

                if (f.parent_organization_pk) payload.parent_organization_pk = f.parent_organization_pk;
                // ORG-BR-098: has_own_premises is only meaningful for
                // SAKHA_SANGHA; send the operator's choice for that type,
                // otherwise omit and let the backend default apply.
                if (this.orgTypeHasPremises) payload.has_own_premises = !!f.has_own_premises;
                // KUMARI_SANGHA/SEVAK_SANGHA inherit their organization_code
                // and all location/contact detail from the parent Sakha
                // server-side — never send operator-entered values for these
                // two types (the backend ignores them regardless).
                if (!this.isKumariSevakType) {
                    if (f.organization_code.trim()) payload.organization_code = f.organization_code.trim().toUpperCase();
                    if (f.short_code.trim()) payload.short_code = f.short_code.trim().toUpperCase();
                    if (f.address_line_1.trim()) payload.address_line_1 = f.address_line_1.trim();
                    if (f.country_pk) payload.country_pk = f.country_pk;
                    if (f.state_pk) payload.state_pk = f.state_pk;
                    if (f.district_pk) payload.district_pk = f.district_pk;
                    if (f.city_village_name.trim()) payload.city_village_name = f.city_village_name.trim();
                    if (f.postal_code_value.trim()) payload.postal_code_value = f.postal_code_value.trim();
                    if (f.phone_number.trim()) payload.phone_number = f.phone_number.trim();
                    if (f.mobile_number.trim()) payload.mobile_number = f.mobile_number.trim();
                    if (f.org_email.trim()) payload.org_email = f.org_email.trim();
                    if (f.org_website_url.trim()) payload.org_website_url = f.org_website_url.trim();
                    if (f.org_youtube_channel_url.trim()) payload.org_youtube_channel_url = f.org_youtube_channel_url.trim();
                }

                const res = await NSSAuth.apiFetch("/api/v1/admin/organizations", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                });

                if (!res.ok) {
                    const data = await res.json().catch(() => ({}));
                    this.createOrgError = NSS.errorMessage(data, res.status);
                    return;
                }

                const data = await res.json();
                this.createOrgSuccess = data.organization_code
                    ? `Organization "${data.organization_name}" created successfully (code: ${data.organization_code}).`
                    : `Organization "${data.organization_name}" created successfully (wing of its parent Sakha — no separate code).`;

                // Reset form
                this.createOrgForm = {
                    organization_name: "", organization_type_code: "",
                    parent_organization_pk: "", has_own_premises: false,
                    organization_code: "", short_code: "",
                    address_line_1: "", city_village_name: "",
                    country_pk: "", state_pk: "", district_pk: "", postal_code_value: "",
                    phone_number: "", mobile_number: "", org_email: "",
                    org_website_url: "", org_youtube_channel_url: "",
                };
                this.orgCodeCheck = { checking: false, conflict: null };
                this.shortCodeCheck = { checking: false, conflict: null };
                this.orgCodePreview = "";
                this.orgCodePreviewLoading = false;
                this.kumariSevakScope = { mode: "choose", auto_select_pk: null, sakhas: [] };

                // Refresh the organizations list reference data
                this.fetchOrganizations();
                // The Organization Hierarchy tab caches its tree for the whole
                // session (orgTreeLoaded guard) — invalidate it so a newly
                // created org shows up next time that tab is viewed, instead
                // of requiring a full page reload.
                this.orgTreeLoaded = false;
                this.orgTree = [];
            } catch (err) {
                this.createOrgError = err.message || "Failed to create organization.";
            } finally {
                this.createOrgLoading = false;
            }
        },

        async saveOrgDetail(org) {
            this.savingOrgDetail = true;
            try {
                const body = {};
                if (this.editOrgForm.organization_name !== (org.organization_name || ""))
                    body.organization_name = this.editOrgForm.organization_name;

                // ORG-BR-099 (narrowed): address_line_1/city_village/postal_code
                // are premises-only and still prohibited for these types — the
                // DB trigger rejects them, and the fields are hidden in the UI,
                // but guard here too in case editOrgForm still holds stale
                // values from before the row was opened. Country/state/district
                // are jurisdiction fields, not premises, so they're always sent.
                if (!this.addressProhibitedForType(org.organization_type_code)) {
                    if (this.editOrgForm.address_line_1 !== (org.address_line_1 || ""))
                        body.address_line_1 = this.editOrgForm.address_line_1;

                    // City/Village — text name, lookup/create on backend
                    if (this.editOrgForm.city_village_name !== (org.city_village_name || ""))
                        body.city_village_name = this.editOrgForm.city_village_name;

                    // PIN Code — text value, lookup/create on backend
                    if (this.editOrgForm.postal_code_value !== (org.postal_code || ""))
                        body.postal_code_value = this.editOrgForm.postal_code_value;
                }

                // Location FK fields (except city_village and postal_code — sent as text)
                for (const fk of ["country_pk", "state_pk", "district_pk"]) {
                    if (this.editOrgForm[fk] !== (org[fk] || ""))
                        body[fk] = this.editOrgForm[fk];
                }

                if (this.editOrgForm.phone_number !== (org.phone_number || ""))
                    body.phone_number = this.editOrgForm.phone_number;
                if (this.editOrgForm.mobile_number !== (org.mobile_number || ""))
                    body.mobile_number = this.editOrgForm.mobile_number;
                if (this.editOrgForm.org_email !== (org.org_email || ""))
                    body.org_email = this.editOrgForm.org_email;

                if (Object.keys(body).length === 0) {

                    this.showToast("No changes to save.", "error");
                    this.savingOrgDetail = false;
                    return;
                }

                const res = await NSSAuth.apiFetch(
                    `/api/v1/admin/organizations/${org.organization_pk}`,
                    {
                        method: "PATCH",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(body),
                    }
                );
                if (res.ok) {
                    // Apply changes locally
                    for (const [k, v] of Object.entries(body)) {
                        org[k] = v;
                    }
                    // Update display names for location fields
                    if (body.country_pk !== undefined) {
                        const c = this.locationCountries.find(x => x.country_pk === this.editOrgForm.country_pk);
                        org.country_name = c ? c.country_name : null;
                    }
                    if (body.state_pk !== undefined) {
                        const s = this.locationStates.find(x => x.state_pk === this.editOrgForm.state_pk);
                        org.state_name = s ? s.state_name : null;
                    }
                    if (body.district_pk !== undefined) {
                        const d = this.locationDistricts.find(x => x.district_pk === this.editOrgForm.district_pk);
                        org.district_name = d ? d.district_name : null;
                    }
                    if (body.city_village_name !== undefined) {
                        org.city_village_name = this.editOrgForm.city_village_name || null;
                    }
                    if (body.postal_code_value !== undefined) {
                        org.postal_code = this.editOrgForm.postal_code_value || null;
                    }
                    this.editOrgDetailPk = null;
                    this.showToast("Organization updated.");
                } else {
                    const err = await res.json().catch(() => ({}));
                    this.showToast(err.detail || "Failed to update.", "error");
                }
            } catch (err) {
                this.showToast("Network error. Try again.", "error");
            } finally {
                this.savingOrgDetail = false;
            }
        },

        // ── Toast helper ───────────────────────────────────────

        showToast(msg, type = "success") {
            this.toast = msg;
            this.toastType = type;
            setTimeout(() => { this.toast = ""; }, 3000);
        },

        // ── Formatting helpers ─────────────────────────────────

        formatDate(iso) {
            return NSS.formatDateTime(iso);
        },

        statusBadgeClass(status) {
            const map = {
                ACTIVE: "badge-success",
                SUSPENDED: "badge-error",
                DEACTIVATED: "badge-ghost",
            };
            return map[status] || "badge-ghost";
        },

        async logout() {
            await NSSAuth.logout();
        },

        // ── Registration Claims (merged from claim-approval) ──────

        // Claims data
        claims: [],
        claimsTotal: 0,
        claimsPage: 1,
        claimsPageSize: 20,
        claimsLoading: false,
        claimsStatusFilter: "PENDING",
        claimsPendingCount: 0,

        // Claims sorting. Empty claimsSortBy means "leave the server's
        // default" — oldest-first, because this is an approval queue.
        claimsSortBy: "",
        claimsSortDir: "asc",

        // Claim detail
        selectedClaim: null,
        adminRemarks: "",
        claimActionLoading: false,
        claimActionError: "",

        // Claim edit
        claimEditing: false,
        claimEditForm: {},
        claimEditLoading: false,
        claimEditError: "",

        // Claim sakhas lookup
        claimSakhas: [],

        formatPhone(code, number) {
            return NSS.formatPhone(code, number);
        },

        sortClaims(key) {
            const next = NSS.toggleSort(this.claimsSortBy, this.claimsSortDir, key);
            this.claimsSortBy = next.key;
            this.claimsSortDir = next.dir;
            // Back to page 1: the requested order changes which rows belong
            // on any given page, so staying on page 3 would show an
            // arbitrary slice of the new ordering.
            this.claimsPage = 1;
            this.loadClaims();
        },

        async loadClaims() {
            this.claimsLoading = true;
            try {
                const params = new URLSearchParams({
                    claim_status: this.claimsStatusFilter,
                    page: this.claimsPage,
                    page_size: this.claimsPageSize,
                });
                if (this.claimsSortBy) {
                    params.set("sort_by", this.claimsSortBy);
                    params.set("sort_dir", this.claimsSortDir);
                }
                const res = await NSSAuth.apiFetch(`/api/v1/admin/claims?${params}`);
                if (res.ok) {
                    const data = await res.json();
                    this.claims = data.claims;
                    this.claimsTotal = data.total;
                } else if (res.status === 403) {
                    this.claims = [];
                    this.claimsTotal = 0;
                }
            } catch (err) {
                console.error("Failed to load claims:", err);
            } finally {
                this.claimsLoading = false;
            }
        },

        async loadClaimsPendingCount() {
            try {
                const res = await NSSAuth.apiFetch("/api/v1/admin/claims?claim_status=PENDING&page_size=1");
                if (res.ok) {
                    const data = await res.json();
                    this.claimsPendingCount = data.total;
                }
            } catch { /* ignore */ }
        },

        async loadClaimSakhas() {
            try {
                const res = await NSSAuth.apiFetch(
                    `/api/v1/organization/organizations?type_code=SAKHA_SANGHA&limit=${NSS.MAX_PAGE_SIZE}`
                );
                if (res.ok) {
                    const data = await res.json();
                    this.claimSakhas = Array.isArray(data) ? data : (data.organizations || []);
                }
            } catch { /* non-critical */ }
        },

        async viewClaim(claimPk) {
            this.claimActionError = "";
            this.adminRemarks = "";
            this.claimEditing = false;
            this.claimEditError = "";
            try {
                const res = await NSSAuth.apiFetch(`/api/v1/admin/claims/${claimPk}`);
                if (res.ok) {
                    this.selectedClaim = await res.json();
                } else {
                    const data = await res.json().catch(() => ({}));
                    await NSSDialog.alert(data.detail || "Failed to load claim details.");
                }
            } catch {
                await NSSDialog.alert("Failed to load claim details.");
            }
        },

        async approveClaim() {
            this.claimActionError = "";
            this.claimActionLoading = true;
            try {
                const res = await NSSAuth.apiFetch(
                    `/api/v1/admin/claims/${this.selectedClaim.registration_claim_pk}/approve`,
                    {
                        method: "POST",
                        body: JSON.stringify({ admin_remarks: this.adminRemarks.trim() || null }),
                    }
                );
                if (res.ok) {
                    const data = await res.json();
                    const ssId = data.sangha_sevi_id || "";
                    await NSSDialog.alert(
                        `Claim approved successfully.${ssId ? `\nSangha Sevi ID: ${ssId}` : ""}\n\nThe user account is now ACTIVE — the member can log in using the password they set during registration.`
                    );
                    this.selectedClaim = null;
                    this.adminRemarks = "";
                    await this.loadClaims();
                    await this.loadClaimsPendingCount();
                    this.fetchUsers();
                } else {
                    const data = await res.json().catch(() => ({}));
                    this.claimActionError = data.detail || "Approval failed.";
                }
            } catch {
                this.claimActionError = "Unable to connect to server.";
            } finally {
                this.claimActionLoading = false;
            }
        },

        async rejectClaim() {
            if (!this.adminRemarks.trim()) {
                this.claimActionError = "Rejection reason is required.";
                return;
            }
            this.claimActionError = "";
            this.claimActionLoading = true;
            try {
                const res = await NSSAuth.apiFetch(
                    `/api/v1/admin/claims/${this.selectedClaim.registration_claim_pk}/reject`,
                    {
                        method: "POST",
                        body: JSON.stringify({ admin_remarks: this.adminRemarks.trim() }),
                    }
                );
                if (res.ok) {
                    this.selectedClaim = null;
                    this.adminRemarks = "";
                    await this.loadClaims();
                    await this.loadClaimsPendingCount();
                } else {
                    const data = await res.json().catch(() => ({}));
                    this.claimActionError = data.detail || "Rejection failed.";
                }
            } catch {
                this.claimActionError = "Unable to connect to server.";
            } finally {
                this.claimActionLoading = false;
            }
        },

        startClaimEdit() {
            if (!this.selectedClaim) return;
            const c = this.selectedClaim;
            const nameParts = (c.person_name || "").split(/\s+/);

            // Pre-populate form with current claim values
            const formData = {
                first_name: nameParts[0] || "",
                middle_name: nameParts.length > 2 ? nameParts.slice(1, -1).join(" ") : "",
                last_name: nameParts.length > 1 ? nameParts[nameParts.length - 1] : "",
                claimed_organization_pk: c.claimed_organization_pk || "",
                claimed_membership_type_master_data_pk: c.claimed_membership_type_master_data_pk || "",
                claimed_local_sakha_number: c.claimed_local_sakha_number || "",
                claimed_joining_date: c.claimed_joining_date || "",
                country_phone_code: c.country_phone_code || NSS.DEFAULT_COUNTRY_CODE,
                mobile_number: c.mobile_number || "",
                email: c.email || "",
            };

            this.claimEditForm = formData;
            this.claimEditError = "";
            this.claimEditing = true;

            // Re-apply form values after DOM renders the <select> elements
            // (x-if creates DOM fresh; x-model on <select> can lose the
            // initial value if the options aren't yet present in the same tick)
            this.$nextTick(() => {
                this.claimEditForm.claimed_organization_pk = formData.claimed_organization_pk;
                this.claimEditForm.claimed_membership_type_master_data_pk = formData.claimed_membership_type_master_data_pk;
            });
        },

        cancelClaimEdit() {
            this.claimEditing = false;
            this.claimEditError = "";
        },

        async saveClaimEdit() {
            this.claimEditError = "";
            this.claimEditLoading = true;
            try {
                const payload = {};
                const c = this.selectedClaim;
                const f = this.claimEditForm;

                if (f.claimed_organization_pk !== c.claimed_organization_pk)
                    payload.claimed_organization_pk = f.claimed_organization_pk;
                if (f.claimed_membership_type_master_data_pk !== (c.claimed_membership_type_master_data_pk || ""))
                    payload.claimed_membership_type_master_data_pk = f.claimed_membership_type_master_data_pk;
                if (f.claimed_local_sakha_number !== (c.claimed_local_sakha_number || ""))
                    payload.claimed_local_sakha_number = f.claimed_local_sakha_number;
                if (f.claimed_joining_date !== (c.claimed_joining_date || ""))
                    payload.claimed_joining_date = f.claimed_joining_date;

                const nameParts = (c.person_name || "").split(/\s+/);
                const origFirst = nameParts[0] || "";
                const origLast = nameParts.length > 1 ? nameParts[nameParts.length - 1] : "";
                if (f.first_name.trim() !== origFirst) payload.first_name = f.first_name;
                if (f.last_name.trim() !== origLast) payload.last_name = f.last_name;
                if (f.country_phone_code !== (c.country_phone_code || ""))
                    payload.country_phone_code = f.country_phone_code;
                if (f.mobile_number !== (c.mobile_number || ""))
                    payload.mobile_number = f.mobile_number;
                if (f.email.toLowerCase() !== (c.email || "").toLowerCase())
                    payload.email = f.email;

                if (Object.keys(payload).length === 0) {
                    this.claimEditing = false;
                    return;
                }

                const res = await NSSAuth.apiFetch(
                    `/api/v1/admin/claims/${c.registration_claim_pk}`,
                    { method: "PATCH", body: JSON.stringify(payload) }
                );

                if (!res.ok) {
                    const data = await res.json().catch(() => ({}));
                    this.claimEditError = NSS.errorMessage(data, res.status);
                    return;
                }

                this.claimEditing = false;
                await this.viewClaim(c.registration_claim_pk);
            } catch {
                this.claimEditError = "Unable to connect to server.";
            } finally {
                this.claimEditLoading = false;
            }
        },

        // ═══════════════════════════════════════════════════════
        //  PERSON DIRECTORY  (Tier-3 parity — replaces /person page)
        // ═══════════════════════════════════════════════════════
        pdPersons: [],
        pdTotal: 0,
        pdLoading: false,
        pdError: "",
        pdGenderFilter: "",
        pdMaritalFilter: "",
        pdBloodFilter: "",
        pdGenderOptions: [],
        pdMaritalOptions: [],
        pdBloodOptions: [],
        pdSelected: null,
        pdAddresses: [],
        pdDetailLoading: false,
        pdOptionsLoaded: false,

        // Person Directory sorting. Empty means "keep the server default"
        // (first name, last name), which is the order this list has always
        // shown, so the initial view is unchanged.
        pdSortBy: "",
        pdSortDir: "asc",

        /**
         * Sort-bar click on the Person Directory.
         *
         * Re-queries rather than reordering in place: the endpoint caps the
         * response at 500 rows, so the browser does not hold the full set
         * and sorting locally would order an arbitrary subset.
         */
        sortPersonDir(key) {
            const next = NSS.toggleSort(this.pdSortBy, this.pdSortDir, key);
            this.pdSortBy = next.key;
            this.pdSortDir = next.dir;
            this.fetchPersonDirectory();
        },

        /**
         * True when any Person Directory filter or sort is active.
         * Drives the Clear button's disabled state.
         */
        get pdFiltersActive() {
            return Boolean(
                this.pdGenderFilter || this.pdMaritalFilter ||
                this.pdBloodFilter || this.pdSortBy
            );
        },

        /**
         * Clear button — resets the Person Directory to its opening state:
         * all three filters, the sort order, and the open detail row
         * (fetchPersonDirectory clears pdSelected).
         */
        clearPersonDirFilters() {
            this.pdGenderFilter = "";
            this.pdMaritalFilter = "";
            this.pdBloodFilter = "";
            this.pdSortBy = "";
            this.pdSortDir = "asc";
            return this.fetchPersonDirectory();
        },

        async loadPersonDirectory() {
            if (!this.pdOptionsLoaded) {
                this.pdOptionsLoaded = true;
                const cats = ["GENDER", "MARITAL_STATUS", "BLOOD_GROUP"];
                const [g, m, b] = await Promise.all(cats.map(c =>
                    NSSAuth.apiFetch(`/api/v1/foundation/master-data?category_code=${c}`)
                        .then(r => r.ok ? r.json() : []).catch(() => [])
                ));
                this.pdGenderOptions = g;
                this.pdMaritalOptions = m;
                this.pdBloodOptions = b;
            }
            await this.fetchPersonDirectory();
        },

        async fetchPersonDirectory() {
            this.pdLoading = true;
            this.pdError = "";
            this.pdSelected = null;
            try {
                const params = new URLSearchParams({ limit: NSS.MAX_PAGE_SIZE });
                if (this.pdGenderFilter) params.set("gender_code", this.pdGenderFilter);
                if (this.pdMaritalFilter) params.set("marital_status_code", this.pdMaritalFilter);
                if (this.pdBloodFilter) params.set("blood_group_code", this.pdBloodFilter);
                if (this.pdSortBy) {
                    params.set("sort_by", this.pdSortBy);
                    params.set("sort_dir", this.pdSortDir);
                }
                const res = await NSSAuth.apiFetch(`/api/v1/person/persons?${params}`);
                if (res.status === 403) { this.pdError = "You do not have permission to view persons."; return; }
                if (!res.ok) throw new Error(await NSS.extractError(res));
                const data = await res.json();
                this.pdPersons = data.persons;
                this.pdTotal = data.total;
            } catch (err) {
                this.pdError = err.message || "Failed to load persons.";
            } finally {
                this.pdLoading = false;
            }
        },

        async viewPerson(person) {
            // Toggle: clicking the already-selected row closes it.
            if (this.pdSelected && this.pdSelected.person_pk === person.person_pk) {
                this.pdSelected = null;
                this.pdAddresses = [];
                return;
            }
            this.pdSelected = person;
            this.pdAddresses = [];
            this.pdDetailLoading = true;
            try {
                const [detailRes, addrRes] = await Promise.all([
                    NSSAuth.apiFetch(`/api/v1/person/persons/${person.person_pk}`),
                    NSSAuth.apiFetch(`/api/v1/person/persons/${person.person_pk}/addresses`),
                ]);
                if (detailRes.ok) this.pdSelected = await detailRes.json();
                if (addrRes.ok) this.pdAddresses = await addrRes.json();
            } catch { /* keep summary on failure */ } finally {
                this.pdDetailLoading = false;
            }
        },

        pdFullName(p) {
            return [p.first_name, p.middle_name, p.last_name].filter(Boolean).join(" ");
        },

        // ═══════════════════════════════════════════════════════
        //  MEMBER DIRECTORY  (Tier-4 parity — replaces /membership page)
        // ═══════════════════════════════════════════════════════
        mdMembers: [],
        mdTotal: 0,
        mdLoading: false,
        mdError: "",
        mdTypeFilter: "",
        mdStatusFilter: "",
        mdOrgTypeFilter: "",
        mdOrgFilter: "",
        mdTypeOptions: [],
        mdStatusOptions: [],
        // No mdOrgTypeOptions — the Org Type dropdown reads the shared
        // `selectableOrgTypes` getter instead of a private copy.
        mdOrgOptions: [],
        mdOrgsLoading: false,
        mdSelected: null,
        mdDetailLoading: false,
        mdAffiliations: [],
        mdParichaya: [],
        mdAnumati: [],
        mdJourney: [],
        mdOptionsLoaded: false,

        // Member Directory sorting — server-side for the same reason as the
        // Person Directory: the response is capped, so the browser never
        // holds the whole list.
        mdSortBy: "",
        mdSortDir: "asc",

        sortMemberDir(key) {
            const next = NSS.toggleSort(this.mdSortBy, this.mdSortDir, key);
            this.mdSortBy = next.key;
            this.mdSortDir = next.dir;
            this.fetchMemberDirectory();
        },

        async loadMemberDirectory() {
            if (!this.mdOptionsLoaded) {
                this.mdOptionsLoaded = true;
                // Organization types are NOT fetched here — loadOrgTypes()
                // already populates `orgTypes` from init(), and the Org Type
                // dropdown reads it through `selectableOrgTypes`. Fetching a
                // second private copy is what let this filter's option list
                // drift out of step with the Organizations list filter.
                const [t, s] = await Promise.all([
                    NSSAuth.apiFetch("/api/v1/foundation/master-data?category_code=MEMBERSHIP_TYPE")
                        .then(r => r.ok ? r.json() : []).catch(() => []),
                    NSSAuth.apiFetch("/api/v1/foundation/master-data?category_code=STATUS")
                        .then(r => r.ok ? r.json() : []).catch(() => []),
                    this.loadOrgTypes(),
                ]);
                this.mdTypeOptions = t;
                this.mdStatusOptions = s;
                await this.mdLoadOrgs();
            }
            await this.fetchMemberDirectory();
        },

        // Load the Org Name dropdown, scoped to the selected Org Type (if any).
        async mdLoadOrgs() {
            this.mdOrgsLoading = true;
            try {
                const params = new URLSearchParams({ page_size: 200 });
                if (this.mdOrgTypeFilter) params.set("type_code", this.mdOrgTypeFilter);
                const res = await NSSAuth.apiFetch(`/api/v1/admin/organizations?${params}`);
                if (res.ok) {
                    const data = await res.json();
                    this.mdOrgOptions = data.organizations || [];
                } else {
                    this.mdOrgOptions = [];
                }
            } catch {
                this.mdOrgOptions = [];
            } finally {
                this.mdOrgsLoading = false;
            }
        },

        /**
         * The Org Name dropdown is only a meaningful choice once an Org
         * Type narrows it, and it stops being a choice at all when the
         * chosen type has exactly one organization.
         *
         *   no type selected ("All") → disabled. Picking one name out of
         *     every organization of every type is not a filter the
         *     directory is built around, and it contradicts the Org Type
         *     field sitting right next to it reading "All".
         *   type with exactly one org (today only KENDRA, whose sole
         *     organization is Nilachala Saraswata Sangha) → disabled,
         *     with that organization already selected by
         *     mdSyncSingletonOrg(). There is nothing to choose.
         *
         * Derived from the loaded option list rather than a hardcoded
         * type list, so it stays correct if the seed changes.
         */
        get mdOrgSelectDisabled() {
            if (this.mdOrgsLoading) return true;
            if (!this.mdOrgTypeFilter) return true;
            return this.mdOrgOptions.length === 1;
        },

        /**
         * Hint shown under the Org Name dropdown explaining why it is
         * locked, so a disabled control never looks like a bug.
         */
        get mdOrgSelectHint() {
            if (this.mdOrgsLoading) return "";
            if (!this.mdOrgTypeFilter) return "Select an Org Type first";
            if (this.mdOrgOptions.length === 1) return "Only one organization of this type";
            return "";
        },

        /**
         * When the selected Org Type has exactly one organization, select
         * it automatically — the user's only possible answer.
         */
        mdSyncSingletonOrg() {
            if (this.mdOrgTypeFilter && this.mdOrgOptions.length === 1) {
                this.mdOrgFilter = this.mdOrgOptions[0].organization_code;
            } else if (!this.mdOrgTypeFilter) {
                this.mdOrgFilter = "";
            }
        },

        // Org Type changed → reset the Org Name selection, reload the org list,
        // re-apply the singleton auto-select, refetch.
        async mdOnOrgTypeChange() {
            this.mdOrgFilter = "";
            await this.mdLoadOrgs();
            this.mdSyncSingletonOrg();
            await this.fetchMemberDirectory();
        },

        /**
         * True when any Member Directory filter or sort is active.
         * Drives the Clear button's disabled state so the control is
         * visibly inert when there is nothing to clear.
         */
        get mdFiltersActive() {
            return Boolean(
                this.mdTypeFilter || this.mdStatusFilter ||
                this.mdOrgTypeFilter || this.mdOrgFilter || this.mdSortBy
            );
        },

        /**
         * Clear button — resets the Member Directory to its opening state:
         * all four filters, the sort order, and the open detail row.
         * mdOrgTypeFilter is cleared first so mdLoadOrgs() reloads the
         * unscoped organization list, otherwise the Org Name dropdown
         * would keep showing only the previously selected type's orgs.
         */
        async clearMemberDirFilters() {
            this.mdTypeFilter = "";
            this.mdStatusFilter = "";
            this.mdOrgTypeFilter = "";
            this.mdOrgFilter = "";
            this.mdSortBy = "";
            this.mdSortDir = "asc";
            await this.mdLoadOrgs();
            this.mdSyncSingletonOrg();
            await this.fetchMemberDirectory();
        },

        async fetchMemberDirectory() {
            this.mdLoading = true;
            this.mdError = "";
            this.mdSelected = null;
            try {
                const params = new URLSearchParams({ limit: NSS.MAX_PAGE_SIZE });
                if (this.mdTypeFilter) params.set("type_code", this.mdTypeFilter);
                if (this.mdStatusFilter) params.set("status_code", this.mdStatusFilter);
                if (this.mdOrgTypeFilter) params.set("org_type_code", this.mdOrgTypeFilter);
                if (this.mdOrgFilter) params.set("org_code", this.mdOrgFilter);
                if (this.mdSortBy) {
                    params.set("sort_by", this.mdSortBy);
                    params.set("sort_dir", this.mdSortDir);
                }
                const res = await NSSAuth.apiFetch(`/api/v1/membership/members?${params}`);
                if (res.status === 403) { this.mdError = "You do not have permission to view members."; return; }
                if (!res.ok) throw new Error(await NSS.extractError(res));
                const data = await res.json();
                this.mdMembers = data.members;
                this.mdTotal = data.total;
            } catch (err) {
                this.mdError = err.message || "Failed to load members.";
            } finally {
                this.mdLoading = false;
            }
        },

        async viewMember(member) {
            // Toggle: clicking the already-selected row closes it.
            if (this.mdSelected && this.mdSelected.sangha_sevi_pk === member.sangha_sevi_pk) {
                this.mdSelected = null;
                this.mdAffiliations = [];
                this.mdParichaya = [];
                this.mdAnumati = [];
                this.mdJourney = [];
                return;
            }
            this.mdSelected = member;
            this.mdAffiliations = [];
            this.mdParichaya = [];
            this.mdAnumati = [];
            this.mdJourney = [];
            this.mdDetailLoading = true;
            const pk = member.sangha_sevi_pk;
            try {
                const [aff, pp, ap, jr] = await Promise.all([
                    NSSAuth.apiFetch(`/api/v1/membership/members/${pk}/affiliations`).then(r => r.ok ? r.json() : []).catch(() => []),
                    NSSAuth.apiFetch(`/api/v1/membership/members/${pk}/parichaya-patra`).then(r => r.ok ? r.json() : []).catch(() => []),
                    NSSAuth.apiFetch(`/api/v1/membership/members/${pk}/anumati-patra`).then(r => r.ok ? r.json() : []).catch(() => []),
                    NSSAuth.apiFetch(`/api/v1/membership/members/${pk}/journey`).then(r => r.ok ? r.json() : []).catch(() => []),
                ]);
                this.mdAffiliations = aff;
                this.mdParichaya = pp;
                this.mdAnumati = ap;
                this.mdJourney = jr;
            } catch { /* non-fatal */ } finally {
                this.mdDetailLoading = false;
            }
        },

        mdMemberName(m) {
            return [m.first_name, m.middle_name, m.last_name].filter(Boolean).join(" ");
        },

        // ═══════════════════════════════════════════════════════
        //  REFERENCE DATA  (Tier-1 parity — master data + documents)
        // ═══════════════════════════════════════════════════════
        rdCategories: [],
        rdSelectedCategory: "",
        rdValues: [],
        rdLoading: false,
        rdValuesLoading: false,
        rdError: "",
        rdDocuments: [],
        rdDocsLoading: false,
        rdView: "master",   // master | documents
        rdLoaded: false,

        async loadReferenceData() {
            if (this.rdLoaded) return;
            this.rdLoaded = true;
            this.rdLoading = true;
            try {
                const res = await NSSAuth.apiFetch("/api/v1/foundation/categories");
                if (res.status === 403) { this.rdError = "You do not have permission to view reference data."; return; }
                if (res.ok) this.rdCategories = await res.json();
            } catch (err) {
                this.rdError = "Failed to load categories.";
            } finally {
                this.rdLoading = false;
            }
        },

        async loadMasterValues() {
            this.rdValues = [];
            if (!this.rdSelectedCategory) return;
            this.rdValuesLoading = true;
            try {
                const res = await NSSAuth.apiFetch(`/api/v1/foundation/master-data?category_code=${encodeURIComponent(this.rdSelectedCategory)}`);
                if (res.ok) this.rdValues = await res.json();
            } catch { /* non-fatal */ } finally {
                this.rdValuesLoading = false;
            }
        },

        async loadDocuments() {
            if (this.rdDocuments.length) return;
            this.rdDocsLoading = true;
            try {
                const res = await NSSAuth.apiFetch("/api/v1/foundation/documents");
                if (res.ok) this.rdDocuments = await res.json();
            } catch { /* non-fatal */ } finally {
                this.rdDocsLoading = false;
            }
        },

        // ── Master-data value add/edit modal ────────────────────────
        mdModalOpen: false,
        mdModalMode: "edit",     // "edit" | "add"
        mdModalSaving: false,
        mdModalError: "",
        mdForm: { master_data_pk: "", category_code: "", value_code: "", value_name: "", description: "", display_order: 0 },
        mdExamples: [],          // existing values of the selected category, used as live examples
        mdExamplesLoading: false,

        openAddValue() {
            this.mdModalMode = "add";
            this.mdModalError = "";
            this.mdExamples = [];
            this.mdForm = {
                master_data_pk: "",
                category_code: this.rdSelectedCategory || "",
                value_code: "",
                value_name: "",
                description: "",
                display_order: 0,
            };
            this.mdModalOpen = true;
            if (this.mdForm.category_code) this.mdLoadExamples();
        },

        // Load a few existing values from the chosen category to show as live examples.
        async mdLoadExamples() {
            this.mdExamples = [];
            const cat = (this.mdForm.category_code || "").trim();
            if (!cat) return;
            this.mdExamplesLoading = true;
            try {
                const res = await NSSAuth.apiFetch(`/api/v1/foundation/master-data?category_code=${encodeURIComponent(cat)}`);
                if (res.ok) {
                    const vals = await res.json();
                    this.mdExamples = vals.slice(0, 3).map(v => ({ value_code: v.value_code, value_name: v.value_name }));
                }
            } catch { /* non-fatal */ } finally {
                this.mdExamplesLoading = false;
            }
        },

        mdCodePlaceholder() {
            return this.mdExamples.length ? ("e.g. " + this.mdExamples[0].value_code) : "e.g. ID_PROOF";
        },
        mdNamePlaceholder() {
            return this.mdExamples.length ? ("e.g. " + this.mdExamples[0].value_name) : "e.g. Identity Proof";
        },
        mdExamplesHint() {
            if (!this.mdExamples.length) return "";
            return "Existing values: " + this.mdExamples.map(e => `${e.value_code} — ${e.value_name}`).join(", ");
        },

        openEditValue(v) {
            this.mdModalMode = "edit";
            this.mdModalError = "";
            this.mdForm = {
                master_data_pk: v.master_data_pk,
                category_code: v.category_code,
                value_code: v.value_code,
                value_name: v.value_name,
                description: v.description || "",
                display_order: v.display_order ?? 0,
            };
            this.mdModalOpen = true;
        },

        closeMdModal() {
            this.mdModalOpen = false;
        },

        async saveMasterData() {
            this.mdModalError = "";
            const name = (this.mdForm.value_name || "").trim();
            if (!name) { this.mdModalError = "Value name is required."; return; }
            if (this.mdModalMode === "add") {
                if (!(this.mdForm.category_code || "").trim()) { this.mdModalError = "Category is required."; return; }
                if (!(this.mdForm.value_code || "").trim()) { this.mdModalError = "Value code is required."; return; }
            }
            const order = parseInt(this.mdForm.display_order, 10);
            this.mdModalSaving = true;
            try {
                let res;
                if (this.mdModalMode === "add") {
                    res = await NSSAuth.apiFetch("/api/v1/foundation/master-data", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            category_code: this.mdForm.category_code.trim(),
                            value_code: this.mdForm.value_code.trim(),
                            value_name: name,
                            description: this.mdForm.description.trim() || null,
                            display_order: Number.isNaN(order) ? 0 : order,
                        }),
                    });
                } else {
                    res = await NSSAuth.apiFetch(`/api/v1/foundation/master-data/${encodeURIComponent(this.mdForm.master_data_pk)}`, {
                        method: "PATCH",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            value_name: name,
                            description: this.mdForm.description.trim(),
                            display_order: Number.isNaN(order) ? 0 : order,
                        }),
                    });
                }
                if (!res.ok) {
                    const data = await res.json().catch(() => ({}));
                    this.mdModalError = NSS.errorMessage(data, res.status);
                    return;
                }
                // Ensure the list reflects the category we just changed
                if (this.mdModalMode === "add") this.rdSelectedCategory = this.mdForm.category_code.trim();
                this.mdModalOpen = false;
                await this.loadMasterValues();
                this.showToast(this.mdModalMode === "add" ? "Value added." : "Value updated.");
            } catch (err) {
                this.mdModalError = err.message || "Failed to save value.";
            } finally {
                this.mdModalSaving = false;
            }
        },

        // ═══════════════════════════════════════════════════════
        //  SYSTEM SETTINGS  (Tier-1 parity — settings + sequences)
        // ═══════════════════════════════════════════════════════
        ssSettings: [],
        ssSequences: [],
        ssSettingsLoading: false,
        ssError: "",
        ssLoaded: false,

        async loadSystemSettings() {
            if (this.ssLoaded) return;
            this.ssLoaded = true;
            await this.reloadSettings();
        },

        async reloadSettings() {
            this.ssSettingsLoading = true;
            try {
                const [setRes, seqRes] = await Promise.all([
                    NSSAuth.apiFetch("/api/v1/foundation/settings"),
                    NSSAuth.apiFetch("/api/v1/foundation/sequences"),
                ]);
                if (setRes.status === 403 || seqRes.status === 403) {
                    this.ssError = "You do not have permission to view system settings.";
                    return;
                }
                if (setRes.ok) this.ssSettings = await setRes.json();
                if (seqRes.ok) this.ssSequences = await seqRes.json();
            } catch (err) {
                this.ssError = "Failed to load system settings.";
            } finally {
                this.ssSettingsLoading = false;
            }
        },

        // ── Setting add/edit modal ──────────────────────────────────
        ssModalOpen: false,
        ssModalMode: "edit",     // "edit" | "add"
        ssModalSaving: false,
        ssModalError: "",
        ssForm: { setting_key: "", setting_value: "", description: "", data_type: "STRING" },

        openEditSetting(s) {
            this.ssModalMode = "edit";
            this.ssModalError = "";
            this.ssForm = {
                setting_key: s.setting_key,
                setting_value: s.setting_value,
                description: s.description || "",
                data_type: s.data_type || "STRING",
            };
            this.ssModalOpen = true;
        },

        openAddSetting() {
            this.ssModalMode = "add";
            this.ssModalError = "";
            this.ssForm = { setting_key: "", setting_value: "", description: "", data_type: "STRING" };
            this.ssModalOpen = true;
        },

        closeSettingModal() {
            this.ssModalOpen = false;
        },

        async saveSetting() {
            this.ssModalError = "";
            const val = (this.ssForm.setting_value || "").trim();
            if (!val) { this.ssModalError = "Value is required."; return; }
            if (this.ssModalMode === "add" && !(this.ssForm.setting_key || "").trim()) {
                this.ssModalError = "Key is required."; return;
            }
            this.ssModalSaving = true;
            try {
                let res;
                if (this.ssModalMode === "add") {
                    res = await NSSAuth.apiFetch("/api/v1/foundation/settings", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            setting_key: this.ssForm.setting_key.trim(),
                            setting_value: val,
                            data_type: this.ssForm.data_type,
                            description: this.ssForm.description.trim() || null,
                        }),
                    });
                } else {
                    res = await NSSAuth.apiFetch(`/api/v1/foundation/settings/${encodeURIComponent(this.ssForm.setting_key)}`, {
                        method: "PATCH",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            setting_value: val,
                            description: this.ssForm.description.trim() || null,
                        }),
                    });
                }
                if (!res.ok) {
                    const data = await res.json().catch(() => ({}));
                    this.ssModalError = NSS.errorMessage(data, res.status);
                    return;
                }
                this.ssModalOpen = false;
                await this.reloadSettings();
                this.showToast(this.ssModalMode === "add" ? "Setting added." : "Setting updated.");
            } catch (err) {
                this.ssModalError = err.message || "Failed to save setting.";
            } finally {
                this.ssModalSaving = false;
            }
        },

        // ── Sequence add/edit modal ─────────────────────────────────
        seqModalOpen: false,
        seqModalMode: "edit",     // "edit" | "add"
        seqModalSaving: false,
        seqModalError: "",
        seqForm: { sequence_code: "", sequence_name: "", prefix: "", padding_length: 8, description: "" },

        openEditSequence(q) {
            this.seqModalMode = "edit";
            this.seqModalError = "";
            this.seqForm = {
                sequence_code: q.sequence_code,
                sequence_name: q.sequence_name || "",
                prefix: q.prefix || "",
                padding_length: (q.padding_length ?? 0),
                description: q.description || "",
            };
            this.seqModalOpen = true;
        },

        openAddSequence() {
            this.seqModalMode = "add";
            this.seqModalError = "";
            this.seqForm = { sequence_code: "", sequence_name: "", prefix: "", padding_length: 8, description: "" };
            this.seqModalOpen = true;
        },

        closeSequenceModal() {
            this.seqModalOpen = false;
        },

        // Preview of the next identifier the sequence would mint, e.g. SKH00001.
        seqPreview() {
            const p = (this.seqForm.prefix || "").trim().toUpperCase();
            const pad = Number(this.seqForm.padding_length) || 0;
            return p + String(1).padStart(pad, "0");
        },

        async saveSequence() {
            this.seqModalError = "";
            const name = (this.seqForm.sequence_name || "").trim();
            const prefix = (this.seqForm.prefix || "").trim();
            const pad = Number(this.seqForm.padding_length);
            if (!name) { this.seqModalError = "Sequence name is required."; return; }
            if (!prefix) { this.seqModalError = "Prefix is required."; return; }
            if (!Number.isInteger(pad) || pad < 0 || pad > 12) {
                this.seqModalError = "Padding must be a whole number between 0 and 12."; return;
            }
            if (this.seqModalMode === "add" && !(this.seqForm.sequence_code || "").trim()) {
                this.seqModalError = "Sequence code is required."; return;
            }
            this.seqModalSaving = true;
            try {
                let res;
                if (this.seqModalMode === "add") {
                    res = await NSSAuth.apiFetch("/api/v1/foundation/sequences", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            sequence_code: this.seqForm.sequence_code.trim(),
                            sequence_name: name,
                            prefix: prefix,
                            padding_length: pad,
                            description: this.seqForm.description.trim() || null,
                        }),
                    });
                } else {
                    res = await NSSAuth.apiFetch(`/api/v1/foundation/sequences/${encodeURIComponent(this.seqForm.sequence_code)}`, {
                        method: "PATCH",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            sequence_name: name,
                            prefix: prefix,
                            padding_length: pad,
                            description: this.seqForm.description.trim() || null,
                        }),
                    });
                }
                if (!res.ok) {
                    const data = await res.json().catch(() => ({}));
                    this.seqModalError = NSS.errorMessage(data, res.status);
                    return;
                }
                this.seqModalOpen = false;
                await this.reloadSettings();
                this.showToast(this.seqModalMode === "add" ? "Sequence added." : "Sequence updated.");
            } catch (err) {
                this.seqModalError = err.message || "Failed to save sequence.";
            } finally {
                this.seqModalSaving = false;
            }
        },

        // ═══════════════════════════════════════════════════════
        //  GEOGRAPHY  (Tier-1 parity — country → state → district → city)
        // ═══════════════════════════════════════════════════════
        geoCountries: [],
        geoStates: [],
        geoDistricts: [],
        geoCities: [],
        geoPostalCodes: [],
        geoCountryPk: "",
        geoStatePk: "",
        geoDistrictPk: "",
        geoLoading: false,
        geoError: "",
        geoLoaded: false,

        async loadGeography() {
            if (this.geoLoaded) return;
            this.geoLoaded = true;
            this.geoLoading = true;
            try {
                const res = await NSSAuth.apiFetch("/api/v1/foundation/countries");
                if (res.status === 403) { this.geoError = "You do not have permission to view geography data."; return; }
                if (res.ok) this.geoCountries = await res.json();
            } catch (err) {
                this.geoError = "Failed to load countries.";
            } finally {
                this.geoLoading = false;
            }
        },

        async geoSelectCountry(countryPk) {
            this.geoCountryPk = countryPk;
            this.geoStatePk = "";
            this.geoDistrictPk = "";
            this.geoStates = [];
            this.geoDistricts = [];
            this.geoCities = [];
            this.geoPostalCodes = [];
            if (!countryPk) return;
            // Only load the next level (states). Postal codes wait for a state selection.
            const res = await NSSAuth.apiFetch(`/api/v1/foundation/states?country_pk=${countryPk}`);
            this.geoStates = res.ok ? await res.json() : [];
        },

        async geoSelectState(statePk) {
            this.geoStatePk = statePk;
            this.geoDistrictPk = "";
            this.geoDistricts = [];
            this.geoCities = [];
            this.geoPostalCodes = [];
            if (!statePk) return;
            // Load this state's districts and its postal codes (scoped to the state).
            const [dist, pc] = await Promise.all([
                NSSAuth.apiFetch(`/api/v1/foundation/districts?state_pk=${statePk}`).then(r => r.ok ? r.json() : []).catch(() => []),
                NSSAuth.apiFetch(`/api/v1/foundation/postal-codes?state_pk=${statePk}`).then(r => r.ok ? r.json() : []).catch(() => []),
            ]);
            this.geoDistricts = dist;
            this.geoPostalCodes = pc;
        },

        async geoSelectDistrict(districtPk) {
            this.geoDistrictPk = districtPk;
            this.geoCities = [];
            if (!districtPk) return;
            const res = await NSSAuth.apiFetch(`/api/v1/foundation/cities?district_pk=${districtPk}`);
            this.geoCities = res.ok ? await res.json() : [];
        },

        // ═══════════════════════════════════════════════════════
        //  ORGANIZATION HIERARCHY  (Tier-2 parity — full tree)
        // ═══════════════════════════════════════════════════════
        orgTree: [],
        orgTreeLoading: false,
        orgTreeError: "",
        orgTreeLoaded: false,

        // Drill-down navigation state (breadcrumb of node objects; empty = top level)
        orgDrillPath: [],
        orgDrillSelect: "",

        async loadOrgHierarchy() {
            if (this.orgTreeLoaded) return;
            this.orgTreeLoaded = true;
            this.orgTreeLoading = true;
            try {
                const res = await NSSAuth.apiFetch(`/api/v1/organization/hierarchy?limit=${NSS.MAX_PAGE_SIZE}`);
                if (res.status === 403) { this.orgTreeError = "You do not have permission to view the hierarchy."; return; }
                if (res.ok) this.orgTree = await res.json();
            } catch (err) {
                this.orgTreeError = "Failed to load hierarchy.";
            } finally {
                this.orgTreeLoading = false;
            }
        },

        // Direct children of a given parent pk (null pk = top-level roots)
        orgChildrenOf(parentPk) {
            return this.orgTree.filter(n => n.parent_organization_pk === parentPk);
        },
        // Nodes to display at the current drill level
        orgLevelNodes() {
            const parent = this.orgDrillPath.length ? this.orgDrillPath[this.orgDrillPath.length - 1] : null;
            return this.orgChildrenOf(parent ? parent.organization_pk : null);
        },
        orgChildCount(node) {
            return this.orgChildrenOf(node.organization_pk).length;
        },
        orgHasChildren(node) {
            return this.orgChildCount(node) > 0;
        },
        // Drill into a node (only if it has children)
        orgDrillInto(node) {
            if (!this.orgHasChildren(node)) return;
            this.orgDrillPath.push(node);
            this.orgDrillSelect = "";
        },
        // Jump via the dropdown selection (value = organization_pk)
        orgDrillPick() {
            if (!this.orgDrillSelect) return;
            const node = this.orgLevelNodes().find(n => n.organization_pk === this.orgDrillSelect);
            if (node) this.orgDrillInto(node);
            this.orgDrillSelect = "";
        },
        // Breadcrumb navigation: index -1 = top level, else truncate path to that node
        orgDrillTo(index) {
            this.orgDrillPath = index < 0 ? [] : this.orgDrillPath.slice(0, index + 1);
            this.orgDrillSelect = "";
        },
    };
}
