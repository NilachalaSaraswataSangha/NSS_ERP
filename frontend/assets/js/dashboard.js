/**
 * NSS ERP — Dashboard Page (Tier 5)
 *
 * Alpine.js component for the member dashboard.
 * Calls GET /api/v1/auth/me for user context + roles,
 * then fetches person, membership, and family data via existing APIs.
 *
 * Admin tabs are dynamically added based on role scopes.
 *
 * Family tree uses the /graph endpoint for dynamic relationship
 * computation — same logic as family.html but embedded inline.
 */

/* ── Admin tab definitions ─────────────────────────────────────
 * Maps role_code → tab metadata. Only roles present in the
 * user's scopes appear in the sidebar.
 */
const ADMIN_TAB_MAP = {
    NSS_ERP_ADMIN: {
        label: "System Administration",
        description: "Full system access — users, roles, settings",
        adminUrl: "/admin",
    },
    NSS_ERP_KENDRA_ADMIN: {
        label: "Kendra Management",
        description: "Manage Kendra-level operations and oversight",
        adminUrl: "/admin",
    },
    NSS_ERP_ANCHALIKA_ADMIN: {
        label: "Anchalika Management",
        description: "Manage Anchalika-level coordination",
        adminUrl: "/admin",
    },
    NSS_ERP_ZILLA_ADMIN: {
        label: "Zilla Management",
        description: "Manage Zilla-level operations",
        adminUrl: "/admin",
    },
    NSS_ERP_SAKHA_ADMIN: {
        label: "Sakha Management",
        description: "Manage Sakha members, attendance, and records",
        adminUrl: "/admin",
    },
    NSS_ERP_PATHA_CHAKRA_ADMIN: {
        label: "Patha Chakra Management",
        description: "Manage Patha Chakra sessions and curriculum",
        adminUrl: "/admin",
    },
    NSS_ERP_AUDITOR: {
        label: "Audit & Compliance",
        description: "View audit trails, compliance reports",
        adminUrl: "/admin",
    },
    NSS_ERP_REPORT_VIEWER: {
        label: "Reports",
        description: "Access membership and organizational reports",
        adminUrl: "/admin",
    },
};

/* ── Tab labels for top bar ────────────────────────────────── */
const TAB_LABELS = {
    personal: "Personal Information",
    membership: "Membership Details",
    family: "Family",
    attendance: "Attendance",
    governance: "Governance",
    documents: "Documents",
};

/* ── Roles that get the org-level family browser ──────────── */
const FAMILY_BROWSER_ROLES = new Set([
    "NSS_ERP_ADMIN", "NSS_ERP_KENDRA_ADMIN",
    "NSS_ERP_ANCHALIKA_ADMIN", "NSS_ERP_ZILLA_ADMIN",
    "NSS_ERP_SAKHA_ADMIN",
]);

/* ── Family tree constants (ported from family.js) ──────────── */
const SPOUSE_LABELS = new Set(["Husband", "Wife"]);
const PARENT_LABELS = new Set(["Father", "Mother", "Step-Father", "Step-Mother"]);
const GEN_LABELS = {
    "-3": "Great-Grandparents",
    "-2": "Grandparents",
    "-1": "Parents",
    "0":  "Self & Siblings",
    "1":  "Children",
    "2":  "Grandchildren",
    "3":  "Great-Grandchildren",
};

function _avatarClass(gen, isHead, isSpouse) {
    if (isSpouse)  return "av-spouse";
    switch (gen) {
        case -2: return "av-grandparent";
        case -1: return "av-parent";
        case 0:  return "av-sibling";
        case 1:  return "av-child";
        case 2:  return "av-grandchild";
        default: return "av-other";
    }
}


function dashboardApp() {
    return {
        // ── Shared layout (sidebar toggle, topbar user info) ──
        ...NSSLayout.mixin(),

        // ── State ─────────────────────────────────────────
        loading: true,
        error: "",
        tab: sessionStorage.getItem('nss_dashboard_tab') || "personal",

        // Core data
        user: {},       // from /me
        person: {},     // from /person/persons/{pk}
        member: {},     // from /membership/search
        addresses: [],  // from /person/persons/{pk}/addresses

        // Membership sub-data
        affiliations: [],
        parichayaPatras: [],
        anumatiPatras: [],
        journeyEvents: [],

        // Family data
        family: null,           // FamilyGroupResponse (primary family)
        ownFamily: null,        // User's own family (preserved for "Back" navigation)
        familyMembers: [],      // FamilyMemberResponse[]
        familyHeadHistory: [],  // FamilyHeadHistoryResponse[]
        familyAdmins: [],       // FamilyAdminResponse[] (current admins)
        familyMemberSummaries: {},  // { person_pk: PersonMembershipSummaryResponse }
        familyLoading: false,

        // Family tree (graph)
        viewerPersonPk: null,
        graphMembers: [],
        graphLoading: false,
        graphError: false,
        treeHead: null,
        treeSpouse: null,
        treeNodes: [],
        _allTreePersons: [],

        // Selected person (clicked in tree or member list)
        selectedPerson: null,
        selectedPersonDetail: null,
        selectedPersonLoading: false,
        selectedPersonMembership: null,
        selectedPersonMembershipLoading: false,

        // Add member modal
        showAddMemberModal: false,
        addMemberSearch: "",
        addMemberSearching: false,
        addMemberResults: [],
        addMemberSearchTotal: 0,
        addMemberSelected: null,
        addMemberRelType: "",
        addMemberLinkType: "",
        addMemberLinkTarget: "",
        addMemberRemarks: "",
        addMemberSaving: false,
        addMemberError: "",
        _addMemberDebounce: null,
        addMemberInferredLinks: [],  // auto-inferred family_link edges
        addMemberInlawSpouse: "",       // for in-law: which existing member is the spouse connector
        addMemberInlawSpouseNotInTree: false,  // "Spouse not in Family Tree" toggle
        addMemberExistingFamilies: [],  // families the selected person already belongs to

        // Create family modal
        showCreateFamilyModal: false,
        createFamilyName: "",
        createFamilySakhaPk: "",
        createFamilyFormedDate: "",
        createFamilyRemarks: "",
        createFamilySubmitting: false,
        createFamilyError: "",
        createFamilySakhaList: [],
        createFamilySakhaLoading: false,

        // Remove member
        removeMemberLoading: false,

        // Edit profile
        editingProfile: false,
        profileForm: { mobile_number: "", country_phone_code: "", email: "", date_of_birth: "" },
        profileSaving: false,
        profileError: "",
        profileSuccess: "",

        // ── Org-level family browser (admin view) ────────
        orgFamilyBrowser: false,       // is the org family browser active?
        orgBreadcrumb: [],             // [{organization_pk, organization_name, organization_type_name, organization_code}]
        orgChildren: [],               // child org nodes at current level
        orgChildrenLoading: false,
        orgChildrenStats: {},          // {organization_pk: {family_count, member_count, person_count}}
        orgFamilies: [],               // families at current Sakha level
        orgFamiliesLoading: false,
        orgSelectedSakhaCode: null,    // when a Sakha is selected
        orgSelectedFamily: null,       // FamilyGroupResponse of the selected family
        orgFamilyMembers: [],          // members of the selected family
        orgFamilyHeadHistory: [],      // head history of the selected family
        orgFamilyLoading: false,
        orgGraphMembers: [],           // graph response for org-viewed family
        orgGraphLoading: false,
        orgGraphError: false,
        orgViewerPersonPk: null,       // viewer for the org tree ("View As")
        orgTreeHead: null,
        orgTreeSpouse: null,
        orgTreeNodes: [],
        _orgAllTreePersons: [],
        orgSelectedPerson: null,       // clicked person in org tree
        orgSelectedPersonDetail: null,
        orgSelectedPersonLoading: false,
        orgSelectedPersonMembership: null,
        orgSelectedPersonMembershipLoading: false,
        orgFamilyMemberSummaries: {},

        // ── Member search (admin tab) ───────────────────
        memberSearchQuery: "",
        memberSearchResults: [],
        memberSearchLoading: false,
        memberSearchError: "",
        // Empty keeps the server default (newest account first).
        memberSearchSortBy: "",
        memberSearchSortDir: "asc",

        // Add-member search results are sorted in the browser — that request
        // returns the whole result set, unlike Member Search above.
        addMemberSortBy: "",
        addMemberSortDir: "asc",

        _personRowValue(row, key) {
            if (key === "person_name") {
                return [row.first_name, row.middle_name, row.last_name]
                    .filter(Boolean)
                    .join(" ");
            }
            return row ? row[key] : undefined;
        },

        sortAddMember(key) {
            const next = NSS.toggleSort(this.addMemberSortBy, this.addMemberSortDir, key);
            this.addMemberSortBy = next.key;
            this.addMemberSortDir = next.dir;
        },

        sortedAddMemberResults() {
            if (!this.addMemberSortBy) return this.addMemberResults;
            return NSS.sortRows(
                this.addMemberResults, this.addMemberSortBy,
                this.addMemberSortDir, this._personRowValue,
            );
        },

        // Computed
        adminTabs: [],
        adminStats: {},
        initials: "",

        // ── Init ──────────────────────────────────────────
        async init() {
            if (!NSSAuth.requireAuth()) return;

            this.loading = true;
            this.error = "";

            try {
                // Step 1: Get user context (profile + RBAC)
                const meRes = await NSSAuth.apiFetch("/api/v1/auth/me");
                if (!meRes.ok) throw new Error("Failed to load user profile.");
                this.user = await meRes.json();

                // Shared layout needs currentUser for topbar/sidebar
                this.currentUser = this.user;

                // Cache user for other pages
                NSSAuth.setCachedUser(this.user);

                // Compute initials
                this.initials = this._computeInitials(this.user.person_name);

                // Build admin tabs from scopes
                this._buildAdminTabs();
                this._buildAdminStats();

                // Fetch real dashboard stats (non-blocking)
                this._loadAdminStats();

                // Step 2: Fetch person + membership + family data in parallel
                const fetches = [];

                // Person details
                if (this.user.person_pk) {
                    fetches.push(
                        NSSAuth.apiFetch(`/api/v1/person/persons/${this.user.person_pk}`)
                            .then(r => r.ok ? r.json() : null)
                            .catch(() => null)
                    );
                    // Addresses
                    fetches.push(
                        NSSAuth.apiFetch(`/api/v1/person/persons/${this.user.person_pk}/addresses`)
                            .then(r => r.ok ? r.json() : [])
                            .catch(() => [])
                    );
                } else {
                    fetches.push(Promise.resolve(null));
                    fetches.push(Promise.resolve([]));
                }

                // Membership search by Sangha Sevi ID
                if (this.user.sangha_sevi_id) {
                    fetches.push(
                        NSSAuth.apiFetch(`/api/v1/membership/search?q=${encodeURIComponent(this.user.sangha_sevi_id)}`)
                            .then(r => r.ok ? r.json() : { members: [] })
                            .then(data => data.members || [])
                            .catch(() => [])
                    );
                } else {
                    fetches.push(Promise.resolve([]));
                }

                // Person's families
                if (this.user.person_pk) {
                    fetches.push(
                        NSSAuth.apiFetch(`/api/v1/family/person/${this.user.person_pk}/families`)
                            .then(r => r.ok ? r.json() : [])
                            .catch(() => [])
                    );
                } else {
                    fetches.push(Promise.resolve([]));
                }

                const [personData, addressData, memberResults, familiesData] = await Promise.all(fetches);

                // Process person
                if (personData) {
                    personData.display_name = this._buildDisplayName(personData);
                    this.person = personData;
                }

                // Process addresses
                this.addresses = Array.isArray(addressData) ? addressData : [];

                // Process membership — find exact match
                if (Array.isArray(memberResults) && memberResults.length > 0) {
                    const exact = memberResults.find(
                        m => m.sangha_sevi_id === this.user.sangha_sevi_id
                    );
                    this.member = exact || memberResults[0] || {};
                }

                // Process family — use first family
                if (Array.isArray(familiesData) && familiesData.length > 0) {
                    this.family = familiesData[0];
                    this.ownFamily = familiesData[0];
                }

            } catch (err) {
                this.error = err.message || "An unexpected error occurred.";
            } finally {
                this.loading = false;
            }

            // Step 3: Fetch detail data after main loading completes
            await Promise.all([
                this._fetchMembershipDetail(),
                this._fetchFamilyDetail(),
            ]);
        },

        // ── Membership sub-data fetch ────────────────────
        async _fetchMembershipDetail() {
            if (!this.member.sangha_sevi_pk) return;
            const pk = this.member.sangha_sevi_pk;
            try {
                const [affRes, ppRes, apRes, journeyRes] = await Promise.all([
                    NSSAuth.apiFetch(`/api/v1/membership/members/${pk}/affiliations`)
                        .then(r => r.ok ? r.json() : []).catch(() => []),
                    NSSAuth.apiFetch(`/api/v1/membership/members/${pk}/parichaya-patra`)
                        .then(r => r.ok ? r.json() : []).catch(() => []),
                    NSSAuth.apiFetch(`/api/v1/membership/members/${pk}/anumati-patra`)
                        .then(r => r.ok ? r.json() : []).catch(() => []),
                    NSSAuth.apiFetch(`/api/v1/membership/members/${pk}/journey`)
                        .then(r => r.ok ? r.json() : []).catch(() => []),
                ]);
                this.affiliations = affRes;
                this.parichayaPatras = ppRes;
                this.anumatiPatras = apRes;
                this.journeyEvents = journeyRes;
            } catch (err) {
                console.error("[Dashboard] _fetchMembershipDetail failed:", err);
            }
        },

        // ── Family detail fetch ──────────────────────────
        async _fetchFamilyDetail() {
            if (!this.family) return;
            this.familyLoading = true;
            try {
                const [membersRes, headRes, adminsRes] = await Promise.all([
                    NSSAuth.apiFetch(`/api/v1/family/families/${this.family.family_group_pk}/members`)
                        .then(r => r.ok ? r.json() : []).catch(() => []),
                    NSSAuth.apiFetch(`/api/v1/family/families/${this.family.family_group_pk}/head-history`)
                        .then(r => r.ok ? r.json() : []).catch(() => []),
                    NSSAuth.apiFetch(`/api/v1/family/families/${this.family.family_group_pk}/admins?current_only=true`)
                        .then(r => r.ok ? r.json() : []).catch(() => []),
                ]);
                this.familyMembers = membersRes;
                this.familyHeadHistory = headRes;
                this.familyAdmins = adminsRes;
            } catch (err) {
                console.error("[Dashboard] _fetchFamilyDetail failed:", err);
            } finally {
                this.familyLoading = false;
            }

            // Fetch summaries + graph in parallel (non-blocking)
            this._fetchFamilyMemberSummaries();
            this._fetchFamilyGraph();
        },

        // ── Family member membership summaries ──────────
        async _fetchFamilyMemberSummaries() {
            if (!this.familyMembers.length) return;
            const summaries = {};
            await Promise.all(
                this.familyMembers.map(m =>
                    NSSAuth.apiFetch(`/api/v1/family/person/${m.person_pk}/membership-summary`)
                        .then(r => r.ok ? r.json() : null)
                        .then(data => { if (data) summaries[m.person_pk] = data; })
                        .catch(() => {})
                )
            );
            this.familyMemberSummaries = summaries;
        },

        getMemberSummary(personPk) {
            return this.familyMemberSummaries[personPk] || null;
        },

        // ═══════════════════════════════════════════════════
        //  FAMILY TREE — Graph API + recursive tree builder
        // ═══════════════════════════════════════════════════

        async _fetchFamilyGraph() {
            if (!this.family) return;

            // Viewer is always the logged-in user's person_pk.
            // They may not be in familyMembers (e.g. viewing a departed
            // family via ghost node click), but the graph API includes
            // them as a departed member so BFS still works.
            this.viewerPersonPk = this.user.person_pk;

            await this._loadGraph();
        },

        async _loadGraph() {
            if (!this.family || !this.viewerPersonPk) return;
            this.graphLoading = true;
            this.graphError = false;
            try {
                const url = `/api/v1/family/families/${this.family.family_group_pk}/graph?viewer_person_pk=${this.viewerPersonPk}`;
                const res = await NSSAuth.apiFetch(url);
                if (!res.ok) throw new Error(res.statusText);
                this.graphMembers = await res.json();
                this._buildTree();
            } catch {
                this.graphError = true;
            } finally {
                this.graphLoading = false;
            }
        },

        _buildTree() {
            const members = this.graphMembers;
            this.treeHead = null;
            this.treeSpouse = null;
            this.treeNodes = [];
            this._allTreePersons = [];

            // Viewer node (synthesized — not in graphMembers since BFS
            // skips the root).  Look in familyMembers first; if the
            // viewer isn't a current member (departed family view),
            // build a minimal node from the person record.
            let viewerMember = this.familyMembers.find(
                m => m.person_pk === this.viewerPersonPk
            );
            if (!viewerMember && this.person && this.person.person_pk === this.viewerPersonPk) {
                viewerMember = {
                    person_pk: this.person.person_pk,
                    person_id: this.person.person_id,
                    first_name: this.person.first_name,
                    middle_name: this.person.middle_name,
                    last_name: this.person.last_name,
                    gender_code: this.person.gender_code,
                };
            }
            const viewerSpouseGraph = members.find(
                m => SPOUSE_LABELS.has(m.relationship_label) && m.generation === 0
            );
            const viewerParentPks = members
                .filter(m => PARENT_LABELS.has(m.relationship_label))
                .map(m => m.person_pk);

            if (viewerMember) {
                this.treeHead = {
                    ...viewerMember,
                    relationship_label: "You",
                    generation: 0,
                    _isViewer: true,
                    _avatarClass: "av-viewer",
                    spouse_person_pk: viewerSpouseGraph ? viewerSpouseGraph.person_pk : null,
                    parent_person_pks: viewerParentPks,
                };
            }
            this.treeSpouse = viewerSpouseGraph || null;

            // Assign avatar classes
            for (const m of members) {
                const isSpouse = SPOUSE_LABELS.has(m.relationship_label);
                m._avatarClass = _avatarClass(m.generation, m.is_head, isSpouse);
            }

            // All persons
            const allPersons = [];
            if (this.treeHead) allPersons.push(this.treeHead);
            for (const m of members) allPersons.push(m);
            this._allTreePersons = allPersons;

            const personMap = new Map();
            for (const p of allPersons) personMap.set(p.person_pk, p);

            // Group into couples
            const usedInCouple = new Set();
            const coupleMap = new Map();
            const allCouples = [];

            for (const p of allPersons) {
                if (usedInCouple.has(p.person_pk)) continue;
                usedInCouple.add(p.person_pk);
                let spouse = null;
                if (p.spouse_person_pk) {
                    const s = personMap.get(p.spouse_person_pk);
                    if (s && !usedInCouple.has(s.person_pk)) {
                        spouse = s;
                        usedInCouple.add(s.person_pk);
                    }
                }
                if (!spouse) {
                    for (const s of allPersons) {
                        if (s.spouse_person_pk === p.person_pk && !usedInCouple.has(s.person_pk)) {
                            spouse = s;
                            usedInCouple.add(s.person_pk);
                            break;
                        }
                    }
                }
                const couple = {
                    couple: !!spouse,
                    members: spouse ? [p, spouse] : [p],
                    children: [],
                    gen: p.generation,
                };
                for (const m of couple.members) coupleMap.set(m.person_pk, couple);
                allCouples.push(couple);
            }

            // Parent → child-couple map
            const childCouplesOf = new Map();
            const rootCouples = [];
            for (const c of allCouples) {
                let parentCouple = null;
                for (const m of c.members) {
                    for (const ppk of (m.parent_person_pks || [])) {
                        const pc = coupleMap.get(ppk);
                        if (pc && pc !== c) { parentCouple = pc; break; }
                    }
                    if (parentCouple) break;
                }
                if (parentCouple) {
                    if (!childCouplesOf.has(parentCouple)) childCouplesOf.set(parentCouple, []);
                    childCouplesOf.get(parentCouple).push(c);
                } else {
                    rootCouples.push(c);
                }
            }

            function attach(node) {
                const kids = childCouplesOf.get(node) || [];
                kids.sort((a, b) => (a.members[0].first_name || "").localeCompare(b.members[0].first_name || ""));
                node.children = kids;
                for (const kid of kids) attach(kid);
            }
            for (const root of rootCouples) attach(root);

            // Orphan rescue: if an orphan couple's generation matches a
            // non-root level, graft it as a sibling at that level.
            // This prevents in-laws from floating to the top of the tree.
            if (rootCouples.length > 1) {
                const minGen = Math.min(...rootCouples.map(c => c.gen));
                const trueRoots = [];
                const orphans = [];
                for (const c of rootCouples) {
                    if (c.gen <= minGen) trueRoots.push(c);
                    else orphans.push(c);
                }
                // For each orphan, find a parent-level couple in the tree
                // and graft the orphan as their child
                for (const orphan of orphans) {
                    const targetGen = orphan.gen - 1;
                    let grafted = false;
                    // BFS through tree to find a couple at targetGen
                    const bfsQueue = [...trueRoots];
                    while (bfsQueue.length > 0 && !grafted) {
                        const node = bfsQueue.shift();
                        if (node.gen === targetGen) {
                            node.children.push(orphan);
                            grafted = true;
                        }
                        for (const kid of (node.children || [])) bfsQueue.push(kid);
                    }
                    if (!grafted) trueRoots.push(orphan); // fallback: keep as root
                }
                this.treeNodes = trueRoots;
            } else {
                this.treeNodes = rootCouples;
            }
        },

        // ── Tree rendering (x-html) ─────────────────────
        renderTree() {
            if (!this.treeNodes?.length) return "";
            return this._renderSubtree(this.treeNodes, true);
        },

        _renderSubtree(nodes, isRoot) {
            if (!nodes.length) return "";
            const gen = nodes[0].gen;
            const genLabel = GEN_LABELS[String(gen)] || (gen < 0 ? "Ancestors (" + Math.abs(gen) + ")" : "Descendants (" + gen + ")");
            let h = "";
            if (!isRoot) h += '<div class="conn-v"></div>';
            h += '<div class="gen-divider"><div class="gen-divider-line"></div><span class="gen-divider-text">' + genLabel + '</span><div class="gen-divider-line"></div></div>';
            if (nodes.length === 1) {
                h += '<div class="gen-row">' + this._renderCouple(nodes[0]) + '</div>';
                if (nodes[0].children.length) h += this._renderSubtree(nodes[0].children, false);
            } else {
                const w = (nodes.length - 1) * 8;
                h += '<div class="bracket-wrap"><div class="conn-h" style="width:' + w + 'rem"></div><div class="bracket-row">';
                for (const node of nodes) {
                    const hasKids = node.children.length > 0;
                    h += '<div class="bracket-item' + (hasKids ? " flex flex-col items-center" : "") + '">';
                    h += this._renderCouple(node);
                    if (hasKids) h += this._renderSubtree(node.children, false);
                    h += '</div>';
                }
                h += '</div></div>';
            }
            return h;
        },

        _renderCouple(node) {
            if (node.couple) {
                return '<div class="couple-group">' + this._renderPerson(node.members[0]) + '<div class="couple-join-line"></div>' + this._renderPerson(node.members[1]) + '</div>';
            }
            return this._renderPerson(node.members[0]);
        },

        _renderPerson(m) {
            const av = m._avatarClass || "av-other";
            const ini = this._esc(this._getInitials(m));
            const nm = this._esc(this.formatFamilyName(m));
            const rl = m._isViewer ? "<strong>You</strong>" : this._esc(m.relationship_label || "");
            const sel = this.selectedPerson?.person_pk === m.person_pk ? " is-selected" : "";
            const vr = m._isViewer ? " is-viewer" : "";
            const dep = m.is_departed ? " is-departed" : "";
            let ind = "";
            if (m._isViewer)
                ind = '<span class="node-indicator indicator-viewer">&#128065;</span>';
            else if (m.is_head)
                ind = '<span class="node-indicator indicator-head">&#9733;</span>';
            let depInfo = "";
            if (m.is_departed) {
                const fn = this._esc(m.departed_family_name || "");
                const sn = this._esc(m.departed_sakha_name || "");
                depInfo = '<div class="departed-info" title="Click to view ' + fn + ' family">'
                    + (fn ? '<div class="departed-family">' + fn + '</div>' : '')
                    + (sn ? '<div class="departed-sakha">' + sn + '</div>' : '')
                    + '</div>';
            }
            return '<div class="tree-node' + sel + dep + '" title="' + (m.is_departed ? 'Click to visit ' + this._esc(m.departed_family_name || 'their') + ' family' : '') + '" data-person-pk="' + m.person_pk + '">'
                 + '<div class="node-avatar ' + av + '">' + ini + ind + '</div>'
                 + '<div class="node-name">' + nm + '</div>'
                 + '<div class="node-role' + vr + '">' + rl + '</div>'
                 + depInfo
                 + '</div>';
        },

        _esc(s) {
            return NSS.escapeHtml(s);
        },

        _getInitials(m) {
            const first = (m.first_name || "")[0] || "";
            const last = (m.last_name || "")[0] || "";
            return (first + last).toUpperCase() || "?";
        },

        getAvatarClass(m) {
            if (!m) return "av-other";
            if (m._avatarClass) return m._avatarClass;
            if (m._isViewer) return "av-viewer";
            if (m.person_pk === this.viewerPersonPk) return "av-viewer";
            const gm = this.graphMembers.find(g => g.person_pk === m.person_pk);
            if (gm?._avatarClass) return gm._avatarClass;
            return "av-other";
        },

        isViewingForeignFamily() {
            if (!this.family || !this.ownFamily) return false;
            return this.family.family_group_pk !== this.ownFamily.family_group_pk;
        },

        async goBackToOwnFamily() {
            if (!this.ownFamily) return;
            this.family = this.ownFamily;
            this.selectedPerson = null;
            this.selectedPersonDetail = null;
            this.selectedPersonMembership = null;
            await this._fetchFamilyDetail();
        },

        handleTreeClick(event) {
            const el = event.target.closest("[data-person-pk]");
            if (!el) return;
            const pk = el.dataset.personPk;
            const member = this._allTreePersons?.find(m => m.person_pk === pk);
            if (!member) return;

            // Ghost node click: navigate only when viewing own family
            // When viewing a foreign family, ghosts are non-interactive (use Back banner)
            if (member.is_departed && member.departed_family_group_pk) {
                if (this.isViewingForeignFamily()) return; // not clickable in foreign view
                this._navigateToDepartedFamily(member.departed_family_group_pk);
                return;
            }
            this.selectTreePerson(member);
        },

        async _navigateToDepartedFamily(familyGroupPk) {
            try {
                const res = await NSSAuth.apiFetch(`/api/v1/family/families/${familyGroupPk}`);
                if (!res.ok) throw new Error("Family not found");
                const familyData = await res.json();
                this.family = familyData;
                this.selectedPerson = null;
                this.selectedPersonDetail = null;
                this.selectedPersonMembership = null;
                await this._fetchFamilyDetail();
            } catch (err) {
                console.error("[Dashboard] Navigate to departed family failed:", err);
            }
        },

        displayRelationship(m) {
            if (m._isViewer) return "You";
            if (m.person_pk === this.viewerPersonPk) return "You";
            if (m.relationship_label) return m.relationship_label;
            const gm = this.graphMembers.find(g => g.person_pk === m.person_pk);
            if (gm?.relationship_label) return gm.relationship_label;
            if (m.is_head) return "Head of Family";
            return m.relationship_type_name || m.relationship_type_code || "—";
        },

        sortedFamilyMembers() {
            const ORDER = {
                'Grandfather': 1, 'Grandmother': 1, 'Grandparent': 1,
                'Father': 2, 'Mother': 2,
                'Wife': 4, 'Husband': 4, 'Spouse': 4,
                'Brother': 5, 'Sister': 5, 'Brother-in-Law': 5, 'Sister-in-Law': 5, 'Sibling': 5,
                'Son': 6, 'Daughter': 6, 'Child': 6,
                'Grandson': 7, 'Granddaughter': 7, 'Grandchild': 7
            };
            const self = this;
            function relOrder(m) {
                if (m.person_pk === self.viewerPersonPk) return 3;
                // Try graph member label first (computed by BFS)
                var gm = self.graphMembers.find(function(g) { return g.person_pk === m.person_pk; });
                var label = (gm && gm.relationship_label) || m.relationship_label || m.relationship_type_name || '';
                return ORDER[label] || 8;
            }
            return [...this.familyMembers].sort(function(a, b) { return relOrder(a) - relOrder(b); });
        },

        // ── Person selection (from tree click or member list) ─
        async selectTreePerson(member) {
            if (this.selectedPerson?.person_pk === member.person_pk) {
                this.selectedPerson = null;
                this.selectedPersonDetail = null;
                this.selectedPersonMembership = null;
                return;
            }
            this.selectedPerson = member;
            this.selectedPersonDetail = null;
            this.selectedPersonLoading = true;
            this.selectedPersonMembership = null;
            this.selectedPersonMembershipLoading = true;

            const [personData, membershipData] = await Promise.all([
                NSSAuth.apiFetch(`/api/v1/person/persons/${member.person_pk}`)
                    .then(r => r.ok ? r.json() : null).catch(() => null),
                NSSAuth.apiFetch(`/api/v1/family/person/${member.person_pk}/membership-summary`)
                    .then(r => r.ok ? r.json() : null).catch(() => null),
            ]);

            this.selectedPersonDetail = personData;
            this.selectedPersonLoading = false;
            this.selectedPersonMembership = membershipData;
            this.selectedPersonMembershipLoading = false;
        },

        getSpouseName(personPk) {
            const gm = this.graphMembers.find(g => g.person_pk === personPk);
            if (gm && gm.spouse_person_pk) {
                const spouse = this.graphMembers.find(g => g.person_pk === gm.spouse_person_pk)
                    || this.familyMembers.find(m => m.person_pk === gm.spouse_person_pk);
                if (spouse) return this.formatFamilyName(spouse);
            }
            if (personPk === this.viewerPersonPk && this.treeSpouse) {
                return this.formatFamilyName(this.treeSpouse);
            }
            return null;
        },

        getSpouseInitials(personPk) {
            const gm = this.graphMembers.find(g => g.person_pk === personPk);
            if (gm && gm.spouse_person_pk) {
                const spouse = this.graphMembers.find(g => g.person_pk === gm.spouse_person_pk)
                    || this.familyMembers.find(m => m.person_pk === gm.spouse_person_pk);
                if (spouse) return this._getInitials(spouse);
            }
            if (personPk === this.viewerPersonPk && this.treeSpouse) return this._getInitials(this.treeSpouse);
            return "?";
        },

        selectSpouse(personPk) {
            const gm = this.graphMembers.find(g => g.person_pk === personPk);
            const spousePk = gm?.spouse_person_pk || (personPk === this.viewerPersonPk && this.treeSpouse ? this.treeSpouse.person_pk : null);
            if (!spousePk) return;
            const spouseMember = this.graphMembers.find(g => g.person_pk === spousePk) || this.familyMembers.find(m => m.person_pk === spousePk);
            if (spouseMember) this.selectTreePerson(spouseMember);
        },

        // ── Add member — search ──────────────────────────
        openAddMemberModal() {
            this.showAddMemberModal = true;
            this.addMemberSearch = "";
            this.addMemberResults = [];
            this.addMemberSearchTotal = 0;
            this.addMemberSelected = null;
            this.addMemberRelType = "";
            this.addMemberLinkType = "";
            this.addMemberLinkTarget = "";
            this.addMemberRemarks = "";
            this.addMemberError = "";
            this.addMemberInferredLinks = [];
            this.addMemberInlawSpouse = "";
            this.addMemberInlawSpouseNotInTree = false;
            this.addMemberExistingFamilies = [];
            if (this._addMemberDebounce) clearTimeout(this._addMemberDebounce);
        },

        closeAddMemberModal() {
            this.showAddMemberModal = false;
            this.addMemberInlawSpouse = "";
            this.addMemberInlawSpouseNotInTree = false;
            this.addMemberExistingFamilies = [];
            if (this._addMemberDebounce) clearTimeout(this._addMemberDebounce);
        },

        // Enhancement 1: Debounced auto-search (300ms, same as person.js / membership.js)
        searchPersonForAdd() {
            const q = (this.addMemberSearch || "").trim();
            if (q.length < 2) { this.addMemberResults = []; this.addMemberSearchTotal = 0; return; }
            if (this._addMemberDebounce) clearTimeout(this._addMemberDebounce);
            this._addMemberDebounce = setTimeout(async () => {
                this.addMemberSearching = true;
                this.addMemberError = "";
                try {
                    const res = await NSSAuth.apiFetch(
                        `/api/v1/person/search?q=${encodeURIComponent(q)}`
                    );
                    if (!res.ok) throw new Error("Search failed");
                    const data = await res.json();
                    const results = data.persons;
                    this.addMemberSearchTotal = data.total;
                    // Exclude persons already in this family (current members only)
                    const existingPks = new Set(this.familyMembers.map(m => m.person_pk));
                    let filtered = results.filter(r => !existingPks.has(r.person_pk));

                    // Enhancement 4: Smart spouse filtering
                    if (this.addMemberRelType === "SPOUSE") {
                        filtered = this._filterForSpouse(filtered);
                    }

                    this.addMemberResults = filtered;
                } catch (err) {
                    this.addMemberError = err.message || "Search failed";
                    this.addMemberResults = [];
                    this.addMemberSearchTotal = 0;
                } finally {
                    this.addMemberSearching = false;
                }
            }, 300);
        },

        selectPersonForAdd(person) {
            this.addMemberSelected = person;
            // Reset relationship when person changes (gender may differ)
            this.addMemberRelType = "";
            this.addMemberLinkType = "";
            this.addMemberLinkTarget = "";
            this.addMemberInferredLinks = [];
            this.addMemberInlawSpouse = "";
            this.addMemberInlawSpouseNotInTree = false;
            this.addMemberExistingFamilies = [];

            // Fetch existing family memberships for this person
            this._fetchExistingFamilies(person.person_pk);
        },

        async _fetchExistingFamilies(personPk) {
            try {
                const res = await NSSAuth.apiFetch(`/api/v1/family/person/${personPk}/families`);
                if (res.ok) {
                    const families = await res.json();
                    this.addMemberExistingFamilies = families;
                }
            } catch (e) {
                this.addMemberExistingFamilies = [];
            }
        },

        // Gender-based relationship type filtering
        // Returns list of {value, label, group} for the selected person's gender
        getGenderFilteredRelTypes() {
            const gender = this.addMemberSelected?.gender_code || this.addMemberSelected?.gender_name?.toUpperCase();
            // All relationship types grouped
            const ALL_RELS = [
                { group: "Immediate Family", items: [
                    { value: "SPOUSE", label: "Spouse", gender: null },
                    { value: "FATHER", label: "Father", gender: "MALE" },
                    { value: "MOTHER", label: "Mother", gender: "FEMALE" },
                    { value: "SON", label: "Son", gender: "MALE" },
                    { value: "DAUGHTER", label: "Daughter", gender: "FEMALE" },
                    { value: "BROTHER", label: "Brother", gender: "MALE" },
                    { value: "SISTER", label: "Sister", gender: "FEMALE" },
                ]},
                { group: "In-Laws", items: [
                    { value: "FATHER_IN_LAW", label: "Father-in-Law", gender: "MALE" },
                    { value: "MOTHER_IN_LAW", label: "Mother-in-Law", gender: "FEMALE" },
                    { value: "SON_IN_LAW", label: "Son-in-Law", gender: "MALE" },
                    { value: "DAUGHTER_IN_LAW", label: "Daughter-in-Law", gender: "FEMALE" },
                    { value: "BROTHER_IN_LAW", label: "Brother-in-Law", gender: "MALE" },
                    { value: "SISTER_IN_LAW", label: "Sister-in-Law", gender: "FEMALE" },
                ]},
                { group: "Grandparents / Grandchildren", items: [
                    { value: "GRANDFATHER", label: "Grandfather", gender: "MALE" },
                    { value: "GRANDMOTHER", label: "Grandmother", gender: "FEMALE" },
                    { value: "GRANDSON", label: "Grandson", gender: "MALE" },
                    { value: "GRANDDAUGHTER", label: "Granddaughter", gender: "FEMALE" },
                ]},
                { group: "Step Relations", items: [
                    { value: "STEP_FATHER", label: "Step-Father", gender: "MALE" },
                    { value: "STEP_MOTHER", label: "Step-Mother", gender: "FEMALE" },
                    { value: "STEP_SON", label: "Step-Son", gender: "MALE" },
                    { value: "STEP_DAUGHTER", label: "Step-Daughter", gender: "FEMALE" },
                ]},
                { group: "Other", items: [
                    { value: "UNCLE", label: "Uncle", gender: "MALE" },
                    { value: "AUNT", label: "Aunt", gender: "FEMALE" },
                    { value: "NEPHEW", label: "Nephew", gender: "MALE" },
                    { value: "NIECE", label: "Niece", gender: "FEMALE" },
                    { value: "COUSIN", label: "Cousin", gender: null },
                    { value: "GUARDIAN", label: "Guardian", gender: null },
                    { value: "WARD", label: "Ward", gender: null },
                    { value: "OTHER", label: "Other Relative", gender: null },
                ]},
            ];

            // Filter by gender if known
            return ALL_RELS.map(g => ({
                group: g.group,
                items: g.items.filter(r => !gender || !r.gender || r.gender === gender),
            })).filter(g => g.items.length > 0);
        },

        // Hide/show <option> elements by gender using hidden+disabled attributes
        // Called via x-effect when addMemberSelected changes
        updateRelTypeOptions(selectEl, _person) {
            if (!selectEl) return;
            const gender = this.addMemberSelected?.gender_code
                || (this.addMemberSelected?.gender_name || "").toUpperCase()
                || null;

            // Singular relationships — only one person can hold the role.
            // Map: relationship_type_code → graph label to check.
            // If the label already exists in graphMembers, hide that option.
            const SINGULAR_MAP = {
                FATHER:         "Father",
                MOTHER:         "Mother",
                SPOUSE:         "Husband",   // check both
                GRANDFATHER:    "Grandfather",
                GRANDMOTHER:    "Grandmother",
                FATHER_IN_LAW:  "Father-in-Law",
                MOTHER_IN_LAW:  "Mother-in-Law",
                STEP_FATHER:    "Step-Father",
                STEP_MOTHER:    "Step-Mother",
            };
            // Spouse can be Husband or Wife
            const graph = this.graphMembers || [];
            // Only check non-departed (current) members for singularity
            const currentGraph = graph.filter(g => !g.is_departed);
            const existingLabels = new Set(currentGraph.map(g => g.relationship_label));
            // Build set of codes already filled
            const filledCodes = new Set();
            for (const [code, label] of Object.entries(SINGULAR_MAP)) {
                if (code === "SPOUSE") {
                    if (existingLabels.has("Husband") || existingLabels.has("Wife")) {
                        filledCodes.add(code);
                    }
                } else if (existingLabels.has(label)) {
                    filledCodes.add(code);
                }
            }

            for (const opt of selectEl.querySelectorAll("option[value]")) {
                const val = opt.value;
                if (!val) continue; // skip placeholder

                const genderMismatch = opt.dataset.gender && gender && opt.dataset.gender !== gender;
                const alreadyFilled = filledCodes.has(val);

                if (genderMismatch || alreadyFilled) {
                    opt.hidden = true;
                    opt.disabled = true;
                } else {
                    opt.hidden = false;
                    opt.disabled = false;
                }
            }
            // Hide empty optgroups
            for (const og of selectEl.querySelectorAll("optgroup")) {
                const visible = [...og.querySelectorAll("option")].some(o => !o.hidden);
                og.hidden = !visible;
            }
        },

        // Check if the currently selected relationship type is an in-law type
        isInlawRelType() {
            const INLAW_TYPES = new Set([
                "FATHER_IN_LAW", "MOTHER_IN_LAW", "SON_IN_LAW", "DAUGHTER_IN_LAW",
                "BROTHER_IN_LAW", "SISTER_IN_LAW",
            ]);
            return INLAW_TYPES.has(this.addMemberRelType);
        },

        // Get candidate existing members who could be the "spouse connector" for an in-law.
        // e.g., adding a Sister-in-Law → which Brother or which Spouse links her?
        getInlawSpouseCandidates() {
            const relType = this.addMemberRelType;
            const graph = this.graphMembers;
            const findByRelLabel = (label) => graph.filter(g => g.relationship_label === label);

            // For each in-law type, which existing member role is the "connector"?
            switch (relType) {
                case "SISTER_IN_LAW":
                    // SIL = brother's wife OR spouse's sister
                    // Candidates: all Brothers (she marries one) + all Spouses (she's their sister)
                    return [
                        ...findByRelLabel("Brother").map(m => ({ ...m, _inlawPath: "sibling_spouse", _desc: `${this.formatFamilyName(m)}'s wife (Brother's wife)` })),
                    ];
                case "BROTHER_IN_LAW":
                    // BIL = sister's husband OR spouse's brother
                    return [
                        ...findByRelLabel("Sister").map(m => ({ ...m, _inlawPath: "sibling_spouse", _desc: `${this.formatFamilyName(m)}'s husband (Sister's husband)` })),
                    ];
                case "SON_IN_LAW":
                    // Son-in-law marries daughter
                    return [
                        ...findByRelLabel("Daughter").map(m => ({ ...m, _inlawPath: "child_spouse", _desc: `${this.formatFamilyName(m)}'s husband (Daughter's husband)` })),
                    ];
                case "DAUGHTER_IN_LAW":
                    // Daughter-in-law marries son
                    return [
                        ...findByRelLabel("Son").map(m => ({ ...m, _inlawPath: "child_spouse", _desc: `${this.formatFamilyName(m)}'s wife (Son's wife)` })),
                    ];
                case "FATHER_IN_LAW":
                    // Father-in-law = spouse's father
                    return [
                        ...findByRelLabel("Wife").concat(findByRelLabel("Husband")).map(m => ({ ...m, _inlawPath: "spouse_parent", _desc: `${this.formatFamilyName(m)}'s father (Spouse's father)` })),
                    ];
                case "MOTHER_IN_LAW":
                    // Mother-in-law = spouse's mother
                    return [
                        ...findByRelLabel("Wife").concat(findByRelLabel("Husband")).map(m => ({ ...m, _inlawPath: "spouse_parent", _desc: `${this.formatFamilyName(m)}'s mother (Spouse's mother)` })),
                    ];
                default:
                    return [];
            }
        },

        // When in-law spouse selection changes, re-compute links
        onInlawSpouseChange() {
            this.addMemberInferredLinks = [];
            this.addMemberLinkType = "";
            this.addMemberLinkTarget = "";

            const relType = this.addMemberRelType;
            if (!relType) return;

            // "Spouse not in Family Tree" — create parent links so the person appears at correct level
            if (this.addMemberInlawSpouseNotInTree) {
                const inferred = [];
                const graph = this.graphMembers;
                const findByRelLabel = (label) => graph.filter(g => g.relationship_label === label);

                if (relType === "SISTER_IN_LAW" || relType === "BROTHER_IN_LAW") {
                    // Place at gen 0 by linking to parents (same as siblings)
                    const fathers = findByRelLabel("Father");
                    const mothers = findByRelLabel("Mother");
                    for (const parent of [...fathers, ...mothers]) {
                        inferred.push({
                            type: "PARENT_OF",
                            description: `${this.formatFamilyName(parent)} (${parent.relationship_label}) is parent (placed as sibling-level)`,
                            person_a_pk: parent.person_pk,
                            person_b_pk: null,
                        });
                    }
                } else if (relType === "SON_IN_LAW" || relType === "DAUGHTER_IN_LAW") {
                    // Place at gen +1 by linking viewer as parent
                    const viewerPk = this.viewerPersonPk;
                    inferred.push({
                        type: "PARENT_OF",
                        description: `You are parent (placed at children level)`,
                        person_a_pk: viewerPk,
                        person_b_pk: null,
                    });
                    // Also add spouse as parent if exists
                    const spouses = findByRelLabel("Wife").concat(findByRelLabel("Husband"));
                    if (spouses.length > 0) {
                        inferred.push({
                            type: "PARENT_OF",
                            description: `${this.formatFamilyName(spouses[0])} (${spouses[0].relationship_label}) is also parent`,
                            person_a_pk: spouses[0].person_pk,
                            person_b_pk: null,
                        });
                    }
                } else if (relType === "FATHER_IN_LAW" || relType === "MOTHER_IN_LAW") {
                    // Place at gen -1 — no direct link possible without spouse
                    // Use viewer's spouse if available, otherwise leave manual
                    const spouses = findByRelLabel("Wife").concat(findByRelLabel("Husband"));
                    if (spouses.length > 0) {
                        this.addMemberLinkType = "PARENT_OF";
                        this.addMemberLinkTarget = spouses[0].person_pk;
                    }
                }
                this.addMemberInferredLinks = inferred;
                return;
            }

            // Normal in-law spouse selected — compute SPOUSE_OF link + parent inferred links
            const selectedPk = this.addMemberInlawSpouse;
            if (!selectedPk) return;

            const candidates = this.getInlawSpouseCandidates();
            const chosen = candidates.find(c => c.person_pk === selectedPk);
            if (!chosen) return;

            const inferred = [];

            if (chosen._inlawPath === "sibling_spouse") {
                // SIL/BIL = sibling's spouse → SPOUSE_OF the sibling
                this.addMemberLinkType = "SPOUSE_OF";
                this.addMemberLinkTarget = chosen.person_pk;
            } else if (chosen._inlawPath === "child_spouse") {
                // Son-in-Law/Daughter-in-Law = child's spouse → SPOUSE_OF the child
                this.addMemberLinkType = "SPOUSE_OF";
                this.addMemberLinkTarget = chosen.person_pk;
            } else if (chosen._inlawPath === "spouse_parent") {
                // Father-in-Law/Mother-in-Law = spouse's parent → PARENT_OF the spouse
                this.addMemberLinkType = "PARENT_OF";
                this.addMemberLinkTarget = chosen.person_pk;

                // Also infer SPOUSE_OF with existing opposite in-law
                const graph = this.graphMembers;
                const oppositeLabel = relType === "FATHER_IN_LAW" ? "Mother-in-Law" : "Father-in-Law";
                const existingOpposite = graph.filter(g => g.relationship_label === oppositeLabel);
                if (existingOpposite.length > 0) {
                    inferred.push({
                        type: "SPOUSE_OF",
                        description: `Spouse of ${this.formatFamilyName(existingOpposite[0])} (${oppositeLabel})`,
                        person_a_pk: null,
                        person_b_pk: existingOpposite[0].person_pk,
                    });
                }
            }

            this.addMemberInferredLinks = inferred;
        },

        // Enhancement 2 & 3: When relationship type changes, auto-infer complementary relations and links
        onRelTypeChange() {
            this.addMemberInferredLinks = [];
            this.addMemberLinkType = "";
            this.addMemberLinkTarget = "";
            this.addMemberInlawSpouse = "";
            this.addMemberInlawSpouseNotInTree = false;

            if (!this.addMemberRelType) return;

            // For in-law types, defer link computation to onInlawSpouseChange()
            // User must first select which existing member is the spouse connector
            if (this.isInlawRelType()) {
                // Auto-select if only one candidate
                const candidates = this.getInlawSpouseCandidates();
                if (candidates.length === 1) {
                    this.addMemberInlawSpouse = candidates[0].person_pk;
                    this.onInlawSpouseChange();
                }
                return;
            }

            const relType = this.addMemberRelType;
            const graph = this.graphMembers;
            const viewerPk = this.viewerPersonPk;

            // Helper: find existing members by their relationship label from graph
            const findByRelLabel = (label) => {
                return graph.filter(g => g.relationship_label === label);
            };

            const inferred = [];

            // ── FATHER / MOTHER ──────────────────────────────
            // Main link: new parent PARENT_OF viewer
            // Inferred: SPOUSE_OF with existing opposite parent
            // Inferred: PARENT_OF each sibling
            if (relType === "FATHER" || relType === "MOTHER") {
                this.addMemberLinkType = "PARENT_OF";
                this.addMemberLinkTarget = viewerPk;

                // Spouse with existing opposite parent
                const oppositeLabel = relType === "FATHER" ? "Mother" : "Father";
                const existingOpposite = findByRelLabel(oppositeLabel);
                if (existingOpposite.length > 0) {
                    inferred.push({
                        type: "SPOUSE_OF",
                        description: `Spouse of ${this.formatFamilyName(existingOpposite[0])} (${oppositeLabel})`,
                        person_a_pk: null, // will be new person
                        person_b_pk: existingOpposite[0].person_pk,
                    });
                }

                // PARENT_OF viewer's siblings (new parent is their parent too)
                const siblings = findByRelLabel("Brother").concat(findByRelLabel("Sister"));
                for (const sib of siblings) {
                    inferred.push({
                        type: "PARENT_OF",
                        description: `Parent of ${this.formatFamilyName(sib)} (${sib.relationship_label})`,
                        person_a_pk: null, // will be new person
                        person_b_pk: sib.person_pk,
                    });
                }

                this.addMemberInferredLinks = inferred;
            }

            // ── SPOUSE ───────────────────────────────────────
            // Main link: new person SPOUSE_OF viewer
            if (relType === "SPOUSE") {
                this.addMemberLinkType = "SPOUSE_OF";
                this.addMemberLinkTarget = viewerPk;
                // Re-trigger search with spouse filter
                this.searchPersonForAdd();
            }

            // ── BROTHER / SISTER ─────────────────────────────
            // A sibling shares the same parents as the viewer.
            // Inferred: each existing parent PARENT_OF new sibling
            // (new person is person_b — child)
            if (relType === "BROTHER" || relType === "SISTER") {
                const fathers = findByRelLabel("Father");
                const mothers = findByRelLabel("Mother");
                const parents = [...fathers, ...mothers];

                if (parents.length > 0) {
                    // Use first parent as the main link
                    this.addMemberLinkType = "PARENT_OF";
                    // Direction: person_a (new member) is parent of person_b (target)
                    // BUT siblings are CHILDREN of the parent, not parents themselves.
                    // The main link creates: new_person PARENT_OF target — wrong direction!
                    // We need: parent PARENT_OF new_sibling
                    // So DON'T use the main link — use inferred links for all parents.
                    this.addMemberLinkType = "";
                    this.addMemberLinkTarget = "";

                    for (const parent of parents) {
                        inferred.push({
                            type: "PARENT_OF",
                            description: `${this.formatFamilyName(parent)} (${parent.relationship_label}) is parent of new ${relType.toLowerCase()}`,
                            person_a_pk: parent.person_pk, // existing parent
                            person_b_pk: null, // will be new person
                        });
                    }
                }

                this.addMemberInferredLinks = inferred;
            }

            // ── SON / DAUGHTER ────────────────────────────────
            // Inferred: viewer PARENT_OF new child
            // Inferred: viewer's spouse PARENT_OF new child (if spouse exists)
            if (relType === "SON" || relType === "DAUGHTER") {
                // Can't use main link (it puts new member as person_a = parent, wrong direction)
                // Use inferred links instead
                inferred.push({
                    type: "PARENT_OF",
                    description: `You are parent of new ${relType.toLowerCase()}`,
                    person_a_pk: viewerPk, // viewer is parent
                    person_b_pk: null, // will be new person
                });

                // If viewer has a spouse, they're also a parent
                const spouseLabels = findByRelLabel("Wife").concat(findByRelLabel("Husband"));
                if (spouseLabels.length > 0) {
                    const spouse = spouseLabels[0];
                    inferred.push({
                        type: "PARENT_OF",
                        description: `${this.formatFamilyName(spouse)} (${spouse.relationship_label}) is also parent`,
                        person_a_pk: spouse.person_pk,
                        person_b_pk: null, // will be new person
                    });
                }

                this.addMemberInferredLinks = inferred;
            }

            // ── GRANDFATHER / GRANDMOTHER ────────────────────
            // Main link: new grandparent PARENT_OF existing parent
            // Inferred: SPOUSE_OF existing opposite grandparent
            if (relType === "GRANDFATHER" || relType === "GRANDMOTHER") {
                const fathers = findByRelLabel("Father");
                const mothers = findByRelLabel("Mother");
                const parents = [...fathers, ...mothers];
                if (parents.length > 0) {
                    this.addMemberLinkType = "PARENT_OF";
                    this.addMemberLinkTarget = parents[0].person_pk;

                    const oppositeGrandLabel = relType === "GRANDFATHER" ? "Grandmother" : "Grandfather";
                    const existingGrand = findByRelLabel(oppositeGrandLabel);
                    if (existingGrand.length > 0) {
                        inferred.push({
                            type: "SPOUSE_OF",
                            description: `Spouse of ${this.formatFamilyName(existingGrand[0])} (${oppositeGrandLabel})`,
                            person_a_pk: null,
                            person_b_pk: existingGrand[0].person_pk,
                        });
                    }
                    this.addMemberInferredLinks = inferred;
                }
            }

            // ── GRANDSON / GRANDDAUGHTER ─────────────────────
            // Inferred: viewer's child PARENT_OF new grandchild
            if (relType === "GRANDSON" || relType === "GRANDDAUGHTER") {
                const sons = findByRelLabel("Son");
                const daughters = findByRelLabel("Daughter");
                const children = [...sons, ...daughters];
                if (children.length > 0) {
                    inferred.push({
                        type: "PARENT_OF",
                        description: `${this.formatFamilyName(children[0])} (${children[0].relationship_label}) is parent of new ${relType.toLowerCase()}`,
                        person_a_pk: children[0].person_pk,
                        person_b_pk: null,
                    });
                    this.addMemberInferredLinks = inferred;
                }
            }

            // ── In-law types are now handled by onInlawSpouseChange() ──
            // (FATHER_IN_LAW, MOTHER_IN_LAW, SON_IN_LAW, DAUGHTER_IN_LAW,
            //  BROTHER_IN_LAW, SISTER_IN_LAW — all deferred to spouse selector)

            // ── STEP-FATHER / STEP-MOTHER ────────────────────
            // Parent's new spouse. Link: SPOUSE_OF existing parent
            if (relType === "STEP_FATHER" || relType === "STEP_MOTHER") {
                const targetLabel = relType === "STEP_FATHER" ? "Mother" : "Father";
                const existing = findByRelLabel(targetLabel);
                if (existing.length > 0) {
                    this.addMemberLinkType = "SPOUSE_OF";
                    this.addMemberLinkTarget = existing[0].person_pk;
                }
                this.addMemberInferredLinks = inferred;
            }

            // ── STEP-SON / STEP-DAUGHTER ─────────────────────
            // Spouse's child from another relationship. Link: spouse PARENT_OF new child
            if (relType === "STEP_SON" || relType === "STEP_DAUGHTER") {
                const spouses = findByRelLabel("Wife").concat(findByRelLabel("Husband"));
                if (spouses.length > 0) {
                    inferred.push({
                        type: "PARENT_OF",
                        description: `${this.formatFamilyName(spouses[0])} (${spouses[0].relationship_label}) is parent`,
                        person_a_pk: spouses[0].person_pk,
                        person_b_pk: null,
                    });
                }
                this.addMemberInferredLinks = inferred;
            }

            // ── UNCLE / AUNT ─────────────────────────────────
            // Parent's sibling. Link: grandparent PARENT_OF new uncle/aunt
            if (relType === "UNCLE" || relType === "AUNT") {
                const grandfathers = findByRelLabel("Grandfather");
                const grandmothers = findByRelLabel("Grandmother");
                const grandparents = [...grandfathers, ...grandmothers];
                for (const gp of grandparents) {
                    inferred.push({
                        type: "PARENT_OF",
                        description: `${this.formatFamilyName(gp)} (${gp.relationship_label}) is parent of new ${relType.toLowerCase()}`,
                        person_a_pk: gp.person_pk,
                        person_b_pk: null,
                    });
                }
                this.addMemberInferredLinks = inferred;
            }

            // ── NEPHEW / NIECE ───────────────────────────────
            // Sibling's child. Link: existing sibling PARENT_OF new nephew/niece
            if (relType === "NEPHEW" || relType === "NIECE") {
                const brothers = findByRelLabel("Brother");
                const sisters = findByRelLabel("Sister");
                const siblings = [...brothers, ...sisters];
                if (siblings.length > 0) {
                    inferred.push({
                        type: "PARENT_OF",
                        description: `${this.formatFamilyName(siblings[0])} (${siblings[0].relationship_label}) is parent of new ${relType.toLowerCase()}`,
                        person_a_pk: siblings[0].person_pk,
                        person_b_pk: null,
                    });
                }
                this.addMemberInferredLinks = inferred;
            }

            // ── COUSIN ───────────────────────────────────────
            // Parent's sibling's child. Link: existing uncle/aunt PARENT_OF new cousin
            if (relType === "COUSIN") {
                const uncles = findByRelLabel("Uncle");
                const aunts = findByRelLabel("Aunt");
                const unclesAunts = [...uncles, ...aunts];
                if (unclesAunts.length > 0) {
                    inferred.push({
                        type: "PARENT_OF",
                        description: `${this.formatFamilyName(unclesAunts[0])} (${unclesAunts[0].relationship_label}) is parent of new cousin`,
                        person_a_pk: unclesAunts[0].person_pk,
                        person_b_pk: null,
                    });
                }
                this.addMemberInferredLinks = inferred;
            }

            // ── GUARDIAN / WARD / OTHER ──────────────────────
            // No automatic graph links — these are non-standard.
            // User must manually set tree link if desired.
            if (relType === "GUARDIAN" || relType === "WARD" || relType === "OTHER") {
                // No inferred links
                this.addMemberInferredLinks = [];
            }
        },

        // Enhancement 4: Filter search results for spouse eligibility
        _filterForSpouse(results) {
            // Determine viewer's gender to find opposite
            const viewerGender = this.person.gender_code;
            if (!viewerGender) return results; // can't filter without viewer's gender

            const oppositeGender = viewerGender === "MALE" ? "FEMALE" : "MALE";

            // Exclude persons who already have spouses (check graph for existing SPOUSE_OF links)
            // We can only check within this family — external spouse data isn't available
            // Filter: opposite gender only
            return results.filter(r => {
                // gender_code may come from membership search — check if available
                if (r.gender_code && r.gender_code !== oppositeGender) return false;
                if (r.gender_name) {
                    const gn = r.gender_name.toUpperCase();
                    if (oppositeGender === "MALE" && gn !== "MALE") return false;
                    if (oppositeGender === "FEMALE" && gn !== "FEMALE") return false;
                }
                return true;
            });
        },

        async confirmAddMember() {
            if (!this.addMemberSelected || !this.addMemberRelType) return;
            if (!this.family) return;

            // In-law validation: must select a spouse connector or opt for "not in tree"
            if (this.isInlawRelType() && !this.addMemberInlawSpouse && !this.addMemberInlawSpouseNotInTree) {
                this.addMemberError = "Please select which existing member is the spouse, or choose 'Spouse not in Family Tree'.";
                return;
            }

            this.addMemberSaving = true;
            this.addMemberError = "";
            try {
                // Step 1: Add member to this family
                const payload = {
                    person_pk: this.addMemberSelected.person_pk,
                    relationship_type_code: this.addMemberRelType,
                    remarks: this.addMemberRemarks || null,
                };
                if (this.addMemberLinkType && this.addMemberLinkTarget) {
                    payload.link_type = this.addMemberLinkType;
                    payload.link_target_person_pk = this.addMemberLinkTarget;
                }

                const res = await NSSAuth.apiFetch(
                    `/api/v1/family/families/${this.family.family_group_pk}/members`,
                    {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(payload),
                    }
                );

                if (!res.ok) {
                    const err = await res.json().catch(() => ({}));
                    throw new Error(NSS.errorMessage(err, res.status));
                }

                // Step 2: Auto-create inferred links
                if (this.addMemberInferredLinks.length > 0) {
                    const newPersonPk = this.addMemberSelected.person_pk;
                    for (const link of this.addMemberInferredLinks) {
                        try {
                            const linkPayload = {
                                person_a_pk: link.person_a_pk || newPersonPk,
                                person_b_pk: link.person_b_pk || newPersonPk,
                                link_type: link.type,
                            };
                            await NSSAuth.apiFetch(
                                `/api/v1/family/families/${this.family.family_group_pk}/links`,
                                {
                                    method: "POST",
                                    headers: { "Content-Type": "application/json" },
                                    body: JSON.stringify(linkPayload),
                                }
                            );
                        } catch (linkErr) {
                            console.warn("[Dashboard] Failed to create inferred link:", link, linkErr);
                        }
                    }
                }

                // Refresh family data
                this.closeAddMemberModal();
                await this._fetchFamilyDetail();
            } catch (err) {
                this.addMemberError = err.message || "Failed to add member";
            } finally {
                this.addMemberSaving = false;
            }
        },

        // ── Remove member (head or admin) ─────────────────
        isCurrentHead() {
            if (!this.familyHeadHistory || !this.user.person_pk) return false;
            return this.familyHeadHistory.some(
                h => h.person_pk === this.user.person_pk && !h.effective_to
            );
        },

        isCurrentAdmin() {
            if (!this.familyAdmins || !this.user.person_pk) return false;
            return this.familyAdmins.some(
                a => a.person_pk === this.user.person_pk
            );
        },

        isMemberAdmin(personPk) {
            return this.familyAdmins.some(a => a.person_pk === personPk);
        },

        /**
         * Can the viewer change this family's membership (add/remove)?
         *
         * Mirrors _require_family_manage() in api/routers/family.py: the
         * family head or a current family admin. Being merely a member is
         * not enough — the API returns 403, so any affordance shown to a
         * plain member would be a button that cannot work.
         *
         * Org administrators holding FAMILY_MANAGE are not considered here
         * because they reach families through the org-level family browser,
         * not through this panel, which only ever shows the viewer's own
         * family.
         */
        canManageMembers() {
            return this.isCurrentHead() || this.isCurrentAdmin();
        },

        // ── Transfer Head (FAM-049) ─────────────────────
        async transferHead(personPk) {
            if (!this.family) return;
            const member = this.familyMembers.find(m => m.person_pk === personPk);
            const name = member ? this.formatFamilyName(member) : "this member";
            const ok = await NSSDialog.confirm(
                `Transfer Family Head role to ${name}? You will no longer be the Head.`,
                { title: "Transfer Headship", confirmText: "Transfer", confirmClass: "btn-warning" }
            );
            if (!ok) return;

            try {
                const res = await NSSAuth.apiFetch(
                    `/api/v1/family/families/${this.family.family_group_pk}/transfer-head`,
                    {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ person_pk: personPk }),
                    }
                );
                if (!res.ok) {
                    const err = await res.json().catch(() => ({}));
                    throw new Error(NSS.errorMessage(err, res.status));
                }
                await this._fetchFamilyDetail();
            } catch (err) {
                await NSSDialog.alert(err.message || "Failed to transfer headship");
            }
        },

        // ── Assign Admin (FAM-046) ──────────────────────
        async assignAdmin(personPk) {
            if (!this.family) return;
            const member = this.familyMembers.find(m => m.person_pk === personPk);
            const name = member ? this.formatFamilyName(member) : "this member";
            const ok = await NSSDialog.confirm(
                `Assign ${name} as Family Admin? Admins can edit family details, add/remove members, and view financial records.`,
                { title: "Assign Admin", confirmText: "Assign" }
            );
            if (!ok) return;

            try {
                const res = await NSSAuth.apiFetch(
                    `/api/v1/family/families/${this.family.family_group_pk}/admins`,
                    {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ person_pk: personPk }),
                    }
                );
                if (!res.ok) {
                    const err = await res.json().catch(() => ({}));
                    throw new Error(NSS.errorMessage(err, res.status));
                }
                await this._fetchFamilyDetail();
            } catch (err) {
                await NSSDialog.alert(err.message || "Failed to assign admin");
            }
        },

        // ── Revoke Admin (FAM-046) ──────────────────────
        async revokeAdmin(personPk) {
            if (!this.family) return;
            const member = this.familyMembers.find(m => m.person_pk === personPk);
            const name = member ? this.formatFamilyName(member) : "this member";
            const ok = await NSSDialog.confirm(
                `Revoke admin role from ${name}?`,
                { title: "Revoke Admin", confirmText: "Revoke", confirmClass: "btn-error" }
            );
            if (!ok) return;

            try {
                const res = await NSSAuth.apiFetch(
                    `/api/v1/family/families/${this.family.family_group_pk}/admins`,
                    {
                        method: "DELETE",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ person_pk: personPk }),
                    }
                );
                if (!res.ok) {
                    const err = await res.json().catch(() => ({}));
                    throw new Error(NSS.errorMessage(err, res.status));
                }
                await this._fetchFamilyDetail();
            } catch (err) {
                await NSSDialog.alert(err.message || "Failed to revoke admin");
            }
        },

        async removeFamilyMember(personPk) {
            if (!this.family) return;
            const member = this.familyMembers.find(m => m.person_pk === personPk);
            const name = member ? this.formatFamilyName(member) : "this member";
            const ok = await NSSDialog.confirm(
                `Remove ${name} from this family? This action can be reversed by an admin.`,
                { title: "Remove Member", confirmText: "Remove", confirmClass: "btn-error" }
            );
            if (!ok) return;

            this.removeMemberLoading = true;
            try {
                const res = await NSSAuth.apiFetch(
                    `/api/v1/family/families/${this.family.family_group_pk}/members`,
                    {
                        method: "DELETE",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            person_pk: personPk,
                            remarks: "Removed via dashboard by family head",
                        }),
                    }
                );

                if (!res.ok) {
                    const err = await res.json().catch(() => ({}));
                    throw new Error(NSS.errorMessage(err, res.status));
                }

                // Clear selected if removed
                if (this.selectedPerson?.person_pk === personPk) {
                    this.selectedPerson = null;
                    this.selectedPersonDetail = null;
                    this.selectedPersonMembership = null;
                }

                // Refresh
                await this._fetchFamilyDetail();
            } catch (err) {
                await NSSDialog.alert(err.message || "Failed to remove member");
            } finally {
                this.removeMemberLoading = false;
            }
        },

        // ── Edit Profile ─────────────────────────────────

        startEditProfile() {
            this.profileForm = {
                mobile_number: this.person.mobile_number || "",
                country_phone_code: this.person.country_phone_code || "+91",
                email: this.person.email || "",
                date_of_birth: this.person.date_of_birth ? this.person.date_of_birth.substring(0, 10) : "",
            };
            this.profileError = "";
            this.profileSuccess = "";
            this.editingProfile = true;
        },

        cancelEditProfile() {
            this.editingProfile = false;
            this.profileError = "";
            this.profileSuccess = "";
        },

        async saveProfile() {
            this.profileSaving = true;
            this.profileError = "";
            this.profileSuccess = "";
            try {
                // Build payload with only changed fields
                const payload = {};
                if (this.profileForm.mobile_number !== (this.person.mobile_number || ""))
                    payload.mobile_number = this.profileForm.mobile_number || null;
                if (this.profileForm.country_phone_code !== (this.person.country_phone_code || "+91"))
                    payload.country_phone_code = this.profileForm.country_phone_code || null;
                if (this.profileForm.email !== (this.person.email || ""))
                    payload.email = this.profileForm.email || null;
                const origDob = this.person.date_of_birth ? this.person.date_of_birth.substring(0, 10) : "";
                if (this.profileForm.date_of_birth !== origDob)
                    payload.date_of_birth = this.profileForm.date_of_birth || null;

                if (Object.keys(payload).length === 0) {
                    this.profileError = "No changes detected.";
                    return;
                }

                const res = await NSSAuth.apiFetch("/api/v1/auth/profile", {
                    method: "PATCH",
                    body: JSON.stringify(payload),
                });
                const data = await res.json().catch(() => ({}));
                if (!res.ok) {
                    this.profileError = NSS.errorMessage(data, res.status);
                    return;
                }
                this.profileSuccess = data.message || "Profile updated.";
                this.editingProfile = false;

                // Refresh person data
                const personRes = await NSSAuth.apiFetch(`/api/v1/person/persons/${this.user.person_pk}`);
                if (personRes.ok) {
                    this.person = await personRes.json();
                }
            } catch (err) {
                this.profileError = err.message || "Failed to update profile.";
            } finally {
                this.profileSaving = false;
            }
        },

        // ── Create Family ───────────────────────────────

        async _loadSakhaList() {
            if (this.createFamilySakhaList.length > 0) return;
            this.createFamilySakhaLoading = true;
            try {
                const res = await NSSAuth.apiFetch(
                    `/api/v1/organization/organizations?type_code=SAKHA_SANGHA&limit=${NSS.MAX_PAGE_SIZE}`
                );
                if (res.ok) {
                    const data = await res.json();
                    this.createFamilySakhaList = data;
                }
            } catch (e) {
                console.error("Failed to load Sakha list", e);
            } finally {
                this.createFamilySakhaLoading = false;
            }
        },

        async submitCreateFamily() {
            if (!this.createFamilyName.trim() || !this.createFamilySakhaPk) return;
            this.createFamilySubmitting = true;
            this.createFamilyError = "";

            try {
                const payload = {
                    family_name: this.createFamilyName.trim(),
                    sakha_organization_pk: this.createFamilySakhaPk,
                };
                if (this.createFamilyFormedDate) {
                    payload.formed_date = this.createFamilyFormedDate;
                }
                if (this.createFamilyRemarks?.trim()) {
                    payload.remarks = this.createFamilyRemarks.trim();
                }

                const res = await NSSAuth.apiFetch("/api/v1/family/families", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                });

                if (!res.ok) {
                    const err = await res.json().catch(() => ({}));
                    throw new Error(NSS.errorMessage(err, res.status));
                }

                const newFamily = await res.json();

                // Close modal and reset form
                this.showCreateFamilyModal = false;
                this.createFamilyName = "";
                this.createFamilySakhaPk = "";
                this.createFamilyFormedDate = "";
                this.createFamilyRemarks = "";

                // Reload family data for dashboard
                this.family = newFamily;
                this.ownFamily = newFamily;
                await this._fetchFamilyDetail();

            } catch (err) {
                this.createFamilyError = err.message || "Failed to create family";
            } finally {
                this.createFamilySubmitting = false;
            }
        },

        // ═══════════════════════════════════════════════════
        //  MEMBER SEARCH (Admin Tabs)
        // ═══════════════════════════════════════════════════

        /**
         * Header click on Member Search.
         *
         * Server-side, because this request asks for only the first 10
         * matches — the browser holds a slice, not the result set, so
         * reordering locally would reorder 10 arbitrary rows and present
         * them as "the" order.
         */
        sortMemberSearch(key) {
            const next = NSS.toggleSort(this.memberSearchSortBy, this.memberSearchSortDir, key);
            this.memberSearchSortBy = next.key;
            this.memberSearchSortDir = next.dir;
            this.searchMembers();
        },

        async searchMembers() {
            const q = this.memberSearchQuery.trim();
            if (!q || q.length < 2) {
                this.memberSearchResults = [];
                this.memberSearchError = q.length === 1 ? "Type at least 2 characters" : "";
                return;
            }
            this.memberSearchLoading = true;
            this.memberSearchError = "";
            try {
                const params = new URLSearchParams({ search: q, page: 1, page_size: 10 });
                if (this.memberSearchSortBy) {
                    params.set("sort_by", this.memberSearchSortBy);
                    params.set("sort_dir", this.memberSearchSortDir);
                }
                const res = await NSSAuth.apiFetch(`/api/v1/admin/users?${params}`);
                if (!res.ok) throw new Error(await NSS.extractError(res));
                const data = await res.json();
                this.memberSearchResults = data.users || [];
                if (this.memberSearchResults.length === 0) {
                    this.memberSearchError = "No members found.";
                }
            } catch (err) {
                this.memberSearchError = err.message || "Search failed.";
                this.memberSearchResults = [];
            } finally {
                this.memberSearchLoading = false;
            }
        },

        clearMemberSearch() {
            this.memberSearchQuery = "";
            this.memberSearchResults = [];
            this.memberSearchError = "";
        },

        //  ORG-LEVEL FAMILY BROWSER (Admin Tabs)
        // ═══════════════════════════════════════════════════

        /** Check if the current admin tab has the family browser */
        adminTabHasFamilyBrowser() {
            const at = this.adminTabs.find(t => t.key === this.tab);
            return at && FAMILY_BROWSER_ROLES.has(at.roleCode);
        },

        /** Get the start org scope for the current admin role */
        _getAdminOrgScope() {
            const at = this.adminTabs.find(t => t.key === this.tab);
            if (!at) return null;
            // Find the scope that matches this role
            const scope = this.user.scopes?.find(s => s.role_code === at.roleCode);
            return scope || null;
        },

        /** Launch the org family browser from an admin tab */
        async openOrgFamilyBrowser() {
            this.orgFamilyBrowser = true;
            this._resetOrgBrowser();

            const scope = this._getAdminOrgScope();

            if (scope && scope.organization_pk) {
                // Role is scoped to a specific org — start there
                try {
                    const res = await NSSAuth.apiFetch(`/api/v1/organization/organizations/${scope.organization_pk}/children`);
                    this.orgBreadcrumb = [{
                        organization_pk: scope.organization_pk,
                        organization_name: scope.organization_name || "Organization",
                        organization_type_name: scope.organization_type_code || scope.scope_level || "Org",
                        organization_type_code: scope.organization_type_code || scope.scope_level || "KENDRA",
                        organization_code: "",
                    }];

                    if (res.ok) {
                        const children = await res.json();
                        if (children.length > 0) {
                            this.orgChildren = children;
                            this._fetchOrgChildrenStats(scope.organization_pk);
                        } else {
                            // Leaf org (Sakha) — load families directly
                            this.orgSelectedSakhaCode = scope.organization_pk;
                            await this._fetchOrgFamilies(scope.organization_pk);
                        }
                    }
                } catch {
                    // Fallback: start from Kendra root
                    await this._fetchOrgRoot();
                }
            } else {
                // NSS-wide scope — start from Kendra root
                await this._fetchOrgRoot();
            }
        },

        closeOrgFamilyBrowser() {
            this.orgFamilyBrowser = false;
            this._resetOrgBrowser();
        },

        _resetOrgBrowser() {
            this.orgBreadcrumb = [];
            this.orgChildren = [];
            this.orgChildrenLoading = false;
            this.orgChildrenStats = {};
            this.orgFamilies = [];
            this.orgFamiliesLoading = false;
            this.orgSelectedSakhaCode = null;
            this._resetOrgFamilyDetail();
        },

        _resetOrgFamilyDetail() {
            this.orgSelectedFamily = null;
            this.orgFamilyMembers = [];
            this.orgFamilyHeadHistory = [];
            this.orgFamilyLoading = false;
            this.orgGraphMembers = [];
            this.orgGraphLoading = false;
            this.orgGraphError = false;
            this.orgViewerPersonPk = null;
            this.orgTreeHead = null;
            this.orgTreeSpouse = null;
            this.orgTreeNodes = [];
            this._orgAllTreePersons = [];
            this.orgSelectedPerson = null;
            this.orgSelectedPersonDetail = null;
            this.orgSelectedPersonLoading = false;
            this.orgSelectedPersonMembership = null;
            this.orgSelectedPersonMembershipLoading = false;
            this.orgFamilyMemberSummaries = {};
        },

        // ── Org hierarchy navigation ──────────────────────

        async _fetchOrgRoot() {
            this.orgChildrenLoading = true;
            try {
                const res = await NSSAuth.apiFetch("/api/v1/organization/organizations?type_code=KENDRA");
                if (!res.ok) throw new Error(res.statusText);
                const kendras = await res.json();
                if (kendras.length > 0) {
                    const k = kendras[0];
                    this.orgBreadcrumb = [{
                        organization_pk: k.organization_pk,
                        organization_name: k.organization_name,
                        organization_type_name: k.organization_type_name,
                        organization_type_code: k.organization_type_code || "KENDRA",
                        organization_code: k.organization_code,
                    }];
                    await this._fetchOrgChildren(k.organization_pk);
                }
            } catch {
                this.orgChildren = [];
            } finally {
                this.orgChildrenLoading = false;
            }
        },

        async _fetchOrgChildren(orgPk) {
            this.orgChildrenLoading = true;
            this.orgChildrenStats = {};
            try {
                const res = await NSSAuth.apiFetch(`/api/v1/organization/organizations/${orgPk}/children`);
                this.orgChildren = res.ok ? await res.json() : [];
            } catch {
                this.orgChildren = [];
            } finally {
                this.orgChildrenLoading = false;
            }
            this._fetchOrgChildrenStats(orgPk);
        },

        async _fetchOrgChildrenStats(orgPk) {
            try {
                const res = await NSSAuth.apiFetch(`/api/v1/organization/organizations/${orgPk}/children-stats`);
                if (res.ok) {
                    const stats = await res.json();
                    const map = {};
                    for (const s of stats) map[s.organization_pk] = s;
                    this.orgChildrenStats = map;
                }
            } catch { /* non-fatal */ }
        },

        getOrgChildStats(orgPk) {
            return this.orgChildrenStats[orgPk] || null;
        },

        /**
         * Returns icon style info per org/family category.
         * Org types: KENDRA (purple), ANCHALIKA_SANGHA (blue), ZILLA_SANGHA (teal),
         * SAKHA_SANGHA (emerald), FAMILY (orange-red).
         */
        orgCardIcon(typeCode) {
            const MAP = {
                KENDRA:            { bg: 'linear-gradient(135deg,#7c3aed,#a78bfa)', icon: 'temple', color: '#7c3aed' },
                ANCHALIKA_SANGHA:  { bg: 'linear-gradient(135deg,#2563eb,#60a5fa)', icon: 'grid', color: '#2563eb' },
                ZILLA_SANGHA:      { bg: 'linear-gradient(135deg,#0d9488,#2dd4bf)', icon: 'map', color: '#0d9488' },
                SAKHA_SANGHA:      { bg: 'linear-gradient(135deg,#059669,#34d399)', icon: 'users', color: '#059669' },
                FAMILY:            { bg: 'linear-gradient(135deg,#c2410c,#ea580c)', icon: 'family', color: '#c2410c' },
            };
            return MAP[typeCode] || MAP.KENDRA;
        },

        /** Returns inline SVG HTML for an org icon type */
        orgIconSvg(typeCode) {
            const ICONS = {
                temple: '<path stroke-linecap="round" stroke-linejoin="round" d="M12 21v-8.25M15.75 21v-8.25M8.25 21v-8.25M3 9l9-6 9 6m-1.5 12V10.332A48.36 48.36 0 0 0 12 9.75c-2.551 0-5.056.2-7.5.582V21M3 21h18M12 6.75h.008v.008H12V6.75Z"/>',
                grid:   '<path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6A2.25 2.25 0 0 1 6 3.75h2.25A2.25 2.25 0 0 1 10.5 6v2.25a2.25 2.25 0 0 1-2.25 2.25H6a2.25 2.25 0 0 1-2.25-2.25V6ZM3.75 15.75A2.25 2.25 0 0 1 6 13.5h2.25a2.25 2.25 0 0 1 2.25 2.25V18a2.25 2.25 0 0 1-2.25 2.25H6A2.25 2.25 0 0 1 3.75 18v-2.25ZM13.5 6a2.25 2.25 0 0 1 2.25-2.25H18A2.25 2.25 0 0 1 20.25 6v2.25A2.25 2.25 0 0 1 18 10.5h-2.25a2.25 2.25 0 0 1-2.25-2.25V6ZM13.5 15.75a2.25 2.25 0 0 1 2.25-2.25H18a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 18 20.25h-2.25A2.25 2.25 0 0 1 13.5 18v-2.25Z"/>',
                map:    '<path stroke-linecap="round" stroke-linejoin="round" d="M9 6.75V15m6-6v8.25m.503 3.498 4.875-2.437c.381-.19.622-.58.622-1.006V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 0L9.503 3.252a1.125 1.125 0 0 0-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c.317-.159.69-.159 1.006 0l4.994 2.497c.317.158.69.158 1.006 0Z"/>',
                users:  '<path stroke-linecap="round" stroke-linejoin="round" d="M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z"/>',
                family: '<path stroke-linecap="round" stroke-linejoin="round" d="M18 18.72a9.094 9.094 0 0 0 3.741-.479 3 3 0 0 0-4.682-2.72m.94 3.198.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0 1 12 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 0 1 6 18.719m12 0a5.971 5.971 0 0 0-.941-3.197m0 0A5.995 5.995 0 0 0 12 12.75a5.995 5.995 0 0 0-5.058 2.772m0 0a3 3 0 0 0-4.681 2.72 8.986 8.986 0 0 0 3.74.477m.94-3.197a5.971 5.971 0 0 0-.94 3.197M15 6.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm6 3a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Zm-13.5 0a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Z"/>',
            };
            const info = this.orgCardIcon(typeCode);
            const path = ICONS[info.icon] || ICONS.temple;
            return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">' + path + '</svg>';
        },

        async orgDrillInto(org) {
            this._resetOrgFamilyDetail();

            // If Sakha → load families
            if (org.organization_type_code === "SAKHA_SANGHA") {
                this.orgBreadcrumb.push({
                    organization_pk: org.organization_pk,
                    organization_name: org.organization_name,
                    organization_type_name: org.organization_type_name,
                    organization_type_code: org.organization_type_code,
                    organization_code: org.organization_code,
                });
                this.orgSelectedSakhaCode = org.organization_code || org.organization_pk;
                this.orgChildren = [];
                await this._fetchOrgFamilies(org.organization_pk);
                return;
            }

            // Otherwise drill deeper
            this.orgBreadcrumb.push({
                organization_pk: org.organization_pk,
                organization_name: org.organization_name,
                organization_type_name: org.organization_type_name,
                organization_type_code: org.organization_type_code,
                organization_code: org.organization_code,
            });
            this.orgSelectedSakhaCode = null;
            this.orgFamilies = [];
            await this._fetchOrgChildren(org.organization_pk);
        },

        async orgBreadcrumbNav(index) {
            if (index < 0) return;
            const crumb = this.orgBreadcrumb[index];
            this.orgBreadcrumb = this.orgBreadcrumb.slice(0, index + 1);
            this.orgFamilies = [];
            this._resetOrgFamilyDetail();

            // If navigating back to a Sakha, re-fetch families (not children)
            if (crumb.organization_type_code === "SAKHA_SANGHA") {
                this.orgSelectedSakhaCode = crumb.organization_code || crumb.organization_pk;
                this.orgChildren = [];
                await this._fetchOrgFamilies(crumb.organization_pk);
            } else {
                this.orgSelectedSakhaCode = null;
                await this._fetchOrgChildren(crumb.organization_pk);
            }
        },

        // ── Org-level family list ─────────────────────────

        async _fetchOrgFamilies(orgPk) {
            this.orgFamiliesLoading = true;
            try {
                let url = `/api/v1/family/families?limit=200&sakha_organization_pk=${encodeURIComponent(orgPk)}`;
                const res = await NSSAuth.apiFetch(url);
                this.orgFamilies = res.ok ? await res.json() : [];
            } catch {
                this.orgFamilies = [];
            } finally {
                this.orgFamiliesLoading = false;
            }
        },

        // ── Org-level family selection ────────────────────

        async orgSelectFamily(family) {
            this._resetOrgFamilyDetail();
            this.orgSelectedFamily = family;
            this.orgFamilyLoading = true;
            try {
                const [membersRes, headRes] = await Promise.all([
                    NSSAuth.apiFetch(`/api/v1/family/families/${family.family_group_pk}/members`)
                        .then(r => r.ok ? r.json() : []).catch(() => []),
                    NSSAuth.apiFetch(`/api/v1/family/families/${family.family_group_pk}/head-history`)
                        .then(r => r.ok ? r.json() : []).catch(() => []),
                ]);
                this.orgFamilyMembers = membersRes;
                this.orgFamilyHeadHistory = headRes;
            } catch {
                this.orgFamilyMembers = [];
                this.orgFamilyHeadHistory = [];
            } finally {
                this.orgFamilyLoading = false;
            }

            // Set viewer to the family head or first member
            const head = this.orgFamilyMembers.find(m => m.is_head);
            this.orgViewerPersonPk = head ? head.person_pk : (this.orgFamilyMembers[0]?.person_pk || null);

            // Fetch graph + summaries
            this._loadOrgGraph();
            this._fetchOrgFamilyMemberSummaries();
        },

        async _loadOrgGraph() {
            if (!this.orgSelectedFamily || !this.orgViewerPersonPk) return;
            this.orgGraphLoading = true;
            this.orgGraphError = false;
            try {
                const url = `/api/v1/family/families/${this.orgSelectedFamily.family_group_pk}/graph?viewer_person_pk=${this.orgViewerPersonPk}`;
                const res = await NSSAuth.apiFetch(url);
                if (!res.ok) throw new Error(res.statusText);
                this.orgGraphMembers = await res.json();
                this._buildOrgTree();
            } catch {
                this.orgGraphError = true;
            } finally {
                this.orgGraphLoading = false;
            }
        },

        _buildOrgTree() {
            const members = this.orgGraphMembers;
            this.orgTreeHead = null;
            this.orgTreeSpouse = null;
            this.orgTreeNodes = [];
            this._orgAllTreePersons = [];

            const viewerMember = this.orgFamilyMembers.find(
                m => m.person_pk === this.orgViewerPersonPk
            );
            const viewerSpouseGraph = members.find(
                m => SPOUSE_LABELS.has(m.relationship_label) && m.generation === 0
            );
            const viewerParentPks = members
                .filter(m => PARENT_LABELS.has(m.relationship_label))
                .map(m => m.person_pk);

            if (viewerMember) {
                this.orgTreeHead = {
                    ...viewerMember,
                    relationship_label: "Viewer",
                    generation: 0,
                    _isViewer: true,
                    _avatarClass: "av-viewer",
                    spouse_person_pk: viewerSpouseGraph ? viewerSpouseGraph.person_pk : null,
                    parent_person_pks: viewerParentPks,
                };
            }
            this.orgTreeSpouse = viewerSpouseGraph || null;

            for (const m of members) {
                const isSpouse = SPOUSE_LABELS.has(m.relationship_label);
                m._avatarClass = _avatarClass(m.generation, m.is_head, isSpouse);
            }

            const allPersons = [];
            if (this.orgTreeHead) allPersons.push(this.orgTreeHead);
            for (const m of members) allPersons.push(m);
            this._orgAllTreePersons = allPersons;

            const personMap = new Map();
            for (const p of allPersons) personMap.set(p.person_pk, p);

            const usedInCouple = new Set();
            const coupleMap = new Map();
            const allCouples = [];

            for (const p of allPersons) {
                if (usedInCouple.has(p.person_pk)) continue;
                usedInCouple.add(p.person_pk);
                let spouse = null;
                if (p.spouse_person_pk) {
                    const s = personMap.get(p.spouse_person_pk);
                    if (s && !usedInCouple.has(s.person_pk)) {
                        spouse = s;
                        usedInCouple.add(s.person_pk);
                    }
                }
                if (!spouse) {
                    for (const s of allPersons) {
                        if (s.spouse_person_pk === p.person_pk && !usedInCouple.has(s.person_pk)) {
                            spouse = s;
                            usedInCouple.add(s.person_pk);
                            break;
                        }
                    }
                }
                const couple = {
                    couple: !!spouse,
                    members: spouse ? [p, spouse] : [p],
                    children: [],
                    gen: p.generation,
                };
                for (const m of couple.members) coupleMap.set(m.person_pk, couple);
                allCouples.push(couple);
            }

            const childCouplesOf = new Map();
            const rootCouples = [];
            for (const c of allCouples) {
                let parentCouple = null;
                for (const m of c.members) {
                    for (const ppk of (m.parent_person_pks || [])) {
                        const pc = coupleMap.get(ppk);
                        if (pc && pc !== c) { parentCouple = pc; break; }
                    }
                    if (parentCouple) break;
                }
                if (parentCouple) {
                    if (!childCouplesOf.has(parentCouple)) childCouplesOf.set(parentCouple, []);
                    childCouplesOf.get(parentCouple).push(c);
                } else {
                    rootCouples.push(c);
                }
            }

            function attach(node) {
                const kids = childCouplesOf.get(node) || [];
                kids.sort((a, b) => (a.members[0].first_name || "").localeCompare(b.members[0].first_name || ""));
                node.children = kids;
                for (const kid of kids) attach(kid);
            }
            for (const root of rootCouples) attach(root);

            // Orphan rescue
            if (rootCouples.length > 1) {
                const minGen = Math.min(...rootCouples.map(c => c.gen));
                const trueRoots = [];
                const orphans = [];
                for (const c of rootCouples) {
                    if (c.gen <= minGen) trueRoots.push(c);
                    else orphans.push(c);
                }
                for (const orphan of orphans) {
                    const targetGen = orphan.gen - 1;
                    let grafted = false;
                    const bfsQueue = [...trueRoots];
                    while (bfsQueue.length > 0 && !grafted) {
                        const node = bfsQueue.shift();
                        if (node.gen === targetGen) {
                            node.children.push(orphan);
                            grafted = true;
                        }
                        for (const kid of (node.children || [])) bfsQueue.push(kid);
                    }
                    if (!grafted) trueRoots.push(orphan);
                }
                this.orgTreeNodes = trueRoots;
            } else {
                this.orgTreeNodes = rootCouples;
            }
        },

        renderOrgTree() {
            if (!this.orgTreeNodes?.length) return "";
            return this._renderOrgSubtree(this.orgTreeNodes, true);
        },

        _renderOrgSubtree(nodes, isRoot) {
            if (!nodes.length) return "";
            const gen = nodes[0].gen;
            const genLabel = GEN_LABELS[String(gen)] || (gen < 0 ? "Ancestors (" + Math.abs(gen) + ")" : "Descendants (" + gen + ")");
            let h = "";
            if (!isRoot) h += '<div class="conn-v"></div>';
            h += '<div class="gen-divider"><div class="gen-divider-line"></div><span class="gen-divider-text">' + genLabel + '</span><div class="gen-divider-line"></div></div>';
            if (nodes.length === 1) {
                h += '<div class="gen-row">' + this._renderOrgCouple(nodes[0]) + '</div>';
                if (nodes[0].children.length) h += this._renderOrgSubtree(nodes[0].children, false);
            } else {
                const w = (nodes.length - 1) * 8;
                h += '<div class="bracket-wrap"><div class="conn-h" style="width:' + w + 'rem"></div><div class="bracket-row">';
                for (const node of nodes) {
                    const hasKids = node.children.length > 0;
                    h += '<div class="bracket-item' + (hasKids ? " flex flex-col items-center" : "") + '">';
                    h += this._renderOrgCouple(node);
                    if (hasKids) h += this._renderOrgSubtree(node.children, false);
                    h += '</div>';
                }
                h += '</div></div>';
            }
            return h;
        },

        _renderOrgCouple(node) {
            if (node.couple) {
                return '<div class="couple-group">' + this._renderOrgPerson(node.members[0]) + '<div class="couple-join-line"></div>' + this._renderOrgPerson(node.members[1]) + '</div>';
            }
            return this._renderOrgPerson(node.members[0]);
        },

        _renderOrgPerson(m) {
            const av = m._avatarClass || "av-other";
            const ini = this._esc(this._getInitials(m));
            const nm = this._esc(this.formatFamilyName(m));
            const rl = m._isViewer ? "<strong>Head</strong>" : this._esc(m.relationship_label || "");
            const sel = this.orgSelectedPerson?.person_pk === m.person_pk ? " is-selected" : "";
            const vr = m._isViewer ? " is-viewer" : "";
            const dep = m.is_departed ? " is-departed" : "";
            let ind = "";
            if (m._isViewer)
                ind = '<span class="node-indicator indicator-viewer">&#128065;</span>';
            else if (m.is_head)
                ind = '<span class="node-indicator indicator-head">&#9733;</span>';
            let depInfo = "";
            if (m.is_departed) {
                const fn = this._esc(m.departed_family_name || "");
                const sn = this._esc(m.departed_sakha_name || "");
                depInfo = '<div class="departed-info" title="Click to view ' + fn + ' family">'
                    + (fn ? '<div class="departed-family">' + fn + '</div>' : '')
                    + (sn ? '<div class="departed-sakha">' + sn + '</div>' : '')
                    + '</div>';
            }
            return '<div class="tree-node' + sel + dep + '" title="' + (m.is_departed ? 'Click to visit ' + this._esc(m.departed_family_name || 'their') + ' family' : '') + '" data-org-person-pk="' + m.person_pk + '">'
                 + '<div class="node-avatar ' + av + '">' + ini + ind + '</div>'
                 + '<div class="node-name">' + nm + '</div>'
                 + '<div class="node-role' + vr + '">' + rl + '</div>'
                 + depInfo
                 + '</div>';
        },

        orgHandleTreeClick(event) {
            const el = event.target.closest("[data-org-person-pk]");
            if (!el) return;
            const pk = el.dataset.orgPersonPk;
            const member = this._orgAllTreePersons?.find(m => m.person_pk === pk);
            if (!member) return;

            // Ghost nodes are not clickable
            if (member.is_departed) return;

            this.orgSelectTreePerson(member);
        },

        async _orgNavigateToDepartedFamily(familyGroupPk) {
            try {
                const res = await NSSAuth.apiFetch(`/api/v1/family/families/${familyGroupPk}`);
                if (!res.ok) throw new Error("Family not found");
                const familyData = await res.json();
                // Reset current selection and load the new family
                this.orgSelectedPerson = null;
                this.orgSelectedPersonDetail = null;
                this.orgSelectedPersonMembership = null;
                await this.orgSelectFamily(familyData);
            } catch (err) {
                console.error("[OrgBrowser] Navigate to departed family failed:", err);
            }
        },

        async orgSelectTreePerson(member) {
            if (this.orgSelectedPerson?.person_pk === member.person_pk) {
                this.orgSelectedPerson = null;
                this.orgSelectedPersonDetail = null;
                this.orgSelectedPersonMembership = null;
                return;
            }
            this.orgSelectedPerson = member;
            this.orgSelectedPersonDetail = null;
            this.orgSelectedPersonLoading = true;
            this.orgSelectedPersonMembership = null;
            this.orgSelectedPersonMembershipLoading = true;

            const [personData, membershipData] = await Promise.all([
                NSSAuth.apiFetch(`/api/v1/person/persons/${member.person_pk}`)
                    .then(r => r.ok ? r.json() : null).catch(() => null),
                NSSAuth.apiFetch(`/api/v1/family/person/${member.person_pk}/membership-summary`)
                    .then(r => r.ok ? r.json() : null).catch(() => null),
            ]);

            this.orgSelectedPersonDetail = personData;
            this.orgSelectedPersonLoading = false;
            this.orgSelectedPersonMembership = membershipData;
            this.orgSelectedPersonMembershipLoading = false;
        },

        orgDisplayRelationship(m) {
            if (m._isViewer) return "Viewer";
            if (m.person_pk === this.orgViewerPersonPk) return "Viewer";
            if (m.relationship_label) return m.relationship_label;
            const gm = this.orgGraphMembers.find(g => g.person_pk === m.person_pk);
            if (gm?.relationship_label) return gm.relationship_label;
            if (m.is_head) return "Head of Family";
            return m.relationship_type_name || m.relationship_type_code || "—";
        },

        orgGetSpouseName(personPk) {
            const gm = this.orgGraphMembers.find(g => g.person_pk === personPk);
            if (gm && gm.spouse_person_pk) {
                const spouse = this.orgGraphMembers.find(g => g.person_pk === gm.spouse_person_pk)
                    || this.orgFamilyMembers.find(m => m.person_pk === gm.spouse_person_pk);
                if (spouse) return this.formatFamilyName(spouse);
            }
            if (personPk === this.orgViewerPersonPk && this.orgTreeSpouse) {
                return this.formatFamilyName(this.orgTreeSpouse);
            }
            return null;
        },

        orgGetSpouseInitials(personPk) {
            const gm = this.orgGraphMembers.find(g => g.person_pk === personPk);
            if (gm && gm.spouse_person_pk) {
                const spouse = this.orgGraphMembers.find(g => g.person_pk === gm.spouse_person_pk)
                    || this.orgFamilyMembers.find(m => m.person_pk === gm.spouse_person_pk);
                if (spouse) return this._getInitials(spouse);
            }
            if (personPk === this.orgViewerPersonPk && this.orgTreeSpouse) return this._getInitials(this.orgTreeSpouse);
            return "?";
        },

        orgSelectSpouse(personPk) {
            const gm = this.orgGraphMembers.find(g => g.person_pk === personPk);
            const spousePk = gm?.spouse_person_pk || (personPk === this.orgViewerPersonPk && this.orgTreeSpouse ? this.orgTreeSpouse.person_pk : null);
            if (!spousePk) return;
            const spouseMember = this.orgGraphMembers.find(g => g.person_pk === spousePk) || this.orgFamilyMembers.find(m => m.person_pk === spousePk);
            if (spouseMember) this.orgSelectTreePerson(spouseMember);
        },

        async _fetchOrgFamilyMemberSummaries() {
            if (!this.orgFamilyMembers.length) return;
            const summaries = {};
            await Promise.all(
                this.orgFamilyMembers.map(m =>
                    NSSAuth.apiFetch(`/api/v1/family/person/${m.person_pk}/membership-summary`)
                        .then(r => r.ok ? r.json() : null)
                        .then(data => { if (data) summaries[m.person_pk] = data; })
                        .catch(() => {})
                )
            );
            this.orgFamilyMemberSummaries = summaries;
        },

        getOrgMemberSummary(personPk) {
            return this.orgFamilyMemberSummaries[personPk] || null;
        },

        orgGetAvatarClass(m) {
            if (!m) return "av-other";
            if (m._avatarClass) return m._avatarClass;
            if (m._isViewer || m.person_pk === this.orgViewerPersonPk) return "av-viewer";
            const gm = this.orgGraphMembers.find(g => g.person_pk === m.person_pk);
            if (gm?._avatarClass) return gm._avatarClass;
            return "av-other";
        },

        // ── Tab switching ─────────────────────────────────
        switchTab(newTab) {
            // Reset org browser when switching tabs
            if (this.orgFamilyBrowser && newTab !== this.tab) {
                this.orgFamilyBrowser = false;
                this._resetOrgBrowser();
            }
            this.tab = newTab;
            this.sidebarOpen = false;
            sessionStorage.setItem('nss_dashboard_tab', newTab);
        },

        get currentTabLabel() {
            if (TAB_LABELS[this.tab]) return TAB_LABELS[this.tab];
            const at = this.adminTabs.find(t => t.key === this.tab);
            return at ? at.label : "Dashboard";
        },

        // ── Formatting helpers ────────────────────────────
        formatDate(dateStr) {
            return NSS.formatDate(dateStr);
        },

        formatDateTime(dtStr) {
            return NSS.formatDateTime(dtStr);
        },

        formatPhone(code, number) {
            return NSS.formatPhone(code, number);
        },

        formatAddress(addr) {
            const lines = [];
            if (addr.address_line_1) lines.push(addr.address_line_1);
            if (addr.address_line_2) lines.push(addr.address_line_2);
            return lines.join("<br>") || "—";
        },

        formatFamilyName(m) {
            return NSS.formatName(m);
        },

        formatEventType(type) {
            if (!type) return "—";
            return type.replace(/_/g, " ");
        },

        // ── Internal helpers ──────────────────────────────
        _computeInitials(name) {
            if (!name) return "?";
            const parts = name.trim().split(/\s+/);
            if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
            return parts[0].substring(0, 2).toUpperCase();
        },

        _buildDisplayName(person) {
            return [person.first_name, person.middle_name, person.last_name].filter(Boolean).join(" ") || null;
        },

        _buildAdminTabs() {
            if (!this.user.scopes || this.user.scopes.length === 0) { this.adminTabs = []; return; }
            const seen = new Set();
            const tabs = [];
            for (const scope of this.user.scopes) {
                const def = ADMIN_TAB_MAP[scope.role_code];
                if (!def || seen.has(scope.role_code)) continue;
                seen.add(scope.role_code);
                let scopeLabel = scope.scope_level || "NSS-WIDE";
                if (scope.scope_level !== "NSS-WIDE" && scope.organization_pk) scopeLabel += " (Organization-scoped)";
                tabs.push({ key: "admin_" + scope.role_code.toLowerCase(), label: def.label, description: def.description, adminUrl: def.adminUrl, roleCode: scope.role_code, scopeLabel });
            }
            tabs.sort((a, b) => { if (a.roleCode === "NSS_ERP_ADMIN") return -1; if (b.roleCode === "NSS_ERP_ADMIN") return 1; return a.label.localeCompare(b.label); });
            this.adminTabs = tabs;
        },

        _buildAdminStats() {
            this.adminStats = {
                NSS_ERP_ADMIN:              { members: "—", families: "—", orgs: "—", orgsLabel: "Sakha Sanghas", extra: "—", extraLabel: "Total Organizations" },
                NSS_ERP_KENDRA_ADMIN:       { members: "—", families: "—", orgs: "—", orgsLabel: "Sakha Sanghas", extra: "—", extraLabel: "Mahila Sanghas" },
                NSS_ERP_ANCHALIKA_ADMIN:    { members: "—", families: "—", orgs: "—", orgsLabel: "Sakha Sanghas", extra: "—", extraLabel: "Mahila Sanghas" },
                NSS_ERP_ZILLA_ADMIN:        { members: "—", families: "—", orgs: "—", orgsLabel: "Sakha Sanghas", extra: "—", extraLabel: "Renewals Due" },
                NSS_ERP_SAKHA_ADMIN:        { members: "—", families: "—", orgs: "—", orgsLabel: "Renewals Due",  extra: "—", extraLabel: "Attendance %" },
                NSS_ERP_PATHA_CHAKRA_ADMIN: { members: "—", families: "—", orgs: "—", orgsLabel: "Sessions",      extra: "—", extraLabel: "Curriculum Items" },
                NSS_ERP_AUDITOR:            { members: "—", families: "—", orgs: "—", orgsLabel: "Audit Trails",   extra: "—", extraLabel: "Compliance Items" },
                NSS_ERP_REPORT_VIEWER:      { members: "—", families: "—", orgs: "—", orgsLabel: "Reports Available", extra: "—", extraLabel: "Exports" },
            };
        },

        async _loadAdminStats() {
            try {
                const res = await NSSAuth.apiFetch("/api/v1/admin/dashboard-stats");
                if (!res.ok) return;   // silently keep placeholders on auth/permission failure
                const data = await res.json();

                // Apply fetched numbers to every role tab that the user has
                for (const tab of this.adminTabs) {
                    const rc = tab.roleCode;
                    if (!this.adminStats[rc]) continue;

                    this.adminStats[rc] = {
                        ...this.adminStats[rc],
                        members:  data.members  ?? "—",
                        families: data.families ?? "—",
                        orgs:     data.renewals_due ?? "—",
                        extra:    data.attendance_pct != null ? `${data.attendance_pct}%` : "—",
                    };
                }
            } catch (e) {
                console.warn("[dashboard] Failed to load admin stats:", e);
            }
        },
    };
}
