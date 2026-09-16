/**
 * NSS ERP — Tier 4 Family Verification UI
 *
 * Alpine.js data component. Fetches from /api/v1/family/* endpoints.
 * No authentication. Read-only verification.
 *
 * Layout:
 *   - Left sidebar:  Family list (clickable items)
 *   - Center panel:  Family tree (always visible, generation-based)
 *   - Right panel:   Family info + selected person detail + members + head history
 *
 * DYNAMIC RELATIONSHIP MODEL (v2):
 *   The tree uses the /graph endpoint which computes relationship
 *   labels dynamically relative to a viewer via BFS traversal.
 *   Only direct edges (PARENT_OF, SPOUSE_OF) are stored in the DB.
 *   All kinship labels (grandfather, uncle, cousin, etc.) are derived.
 *
 *   A "View As" selector lets users pick any family member as the
 *   viewer — the tree labels update instantly. No data re-entry needed.
 *
 * RECURSIVE TREE (v16):
 *   The tree is built as a recursive data structure from graphMembers.
 *   Each couple/person node has a children array of child couples.
 *   Parent-child links are resolved dynamically via parent_person_pks
 *   from the graph API. Rendered via x-html for arbitrary depth.
 */

const FAMILY_API = "/api/v1/family";
const ORG_API    = "/api/v1/organization";

/* ── Avatar color class by generation ─────────────────────────── */

function avatarClass(gen, isHead, isSpouse) {
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

/* ── Spouse detection from relationship_label ─────────────────── */
const SPOUSE_LABELS = new Set(["Husband", "Wife"]);

/* ── Generation labels ────────────────────────────────────────── */
const GEN_LABELS = {
    "-3": "Great-Grandparents",
    "-2": "Grandparents",
    "-1": "Parents",
    "0":  "Self & Siblings",
    "1":  "Children",
    "2":  "Grandchildren",
    "3":  "Great-Grandchildren",
};

/* ── Alpine component ───────────────────────────────────────────── */

function familyApp() {
    return {
        // Health
        health: { loading: true, connected: false },

        // ── View mode ────────────────────────────────────────
        // "member" = direct family view (current default)
        // "admin"  = org hierarchy drill-down view
        viewMode: "admin",

        // ── Org navigation (admin view) ──────────────────────
        orgBreadcrumb: [],      // [{organization_pk, organization_name, organization_type_name}]
        orgChildren: [],        // children of current org node
        orgChildrenLoading: false,
        orgChildrenStats: {},   // {organization_pk: {family_count, member_count, person_count}}
        selectedSakhaCode: null, // when a Sakha is selected, filter families by this

        // ── Families ──────────────────────────────────────────
        families: [],
        familiesLoading: true,
        familiesError: false,

        // Detail state
        selectedFamily: null,
        detailLoading: false,

        // Members (from static endpoint — for member list & viewer selector)
        familyMembers: [],
        membersLoading: false,

        // Head history
        headHistory: [],
        headLoading: false,

        // ── Graph (dynamic relationships) ─────────────────────
        viewerPersonPk: null,   // person_pk of the current viewer
        graphMembers: [],       // computed from /graph endpoint
        graphLoading: false,
        graphError: false,

        // ── Selected person (clicked in tree or member table) ─
        selectedPerson: null,
        selectedPersonDetail: null,   // full person data from /person API
        selectedPersonLoading: false,
        selectedPersonMembership: null,  // membership summary
        selectedPersonMembershipLoading: false,

        // ── Sakha alignment (FAM-036 majority rule) ──────────
        sakhaAlignment: null,           // FamilySakhaAlignmentResponse
        sakhaAlignmentLoading: false,

        // ── Tree (rebuilt from graphMembers) ──────────────────
        treeHead: null,         // viewer node (synthesized)
        treeSpouse: null,       // viewer's spouse (for detail helpers)
        treeNodes: [],          // recursive tree: [{couple, members, children}]
        _allTreePersons: [],    // flat lookup for click handler

        /**
         * Build a recursive tree from graphMembers.
         *
         * Algorithm:
         *   1. Synthesize the viewer node (not in graph response)
         *   2. Infer viewer's parent PKs from graph labels
         *   3. Combine viewer + graph members
         *   4. Group into couples via spouse_person_pk
         *   5. Build parent→child-couple map via parent_person_pks
         *   6. Find root couples (no parent in graph)
         *   7. Recursively attach children to each couple
         *
         * Each tree node: { couple, members, children, gen }
         * Rendered via renderTree() → x-html (supports any depth).
         */
        buildTree() {
            const members = this.graphMembers;

            // Reset
            this.treeHead = null;
            this.treeSpouse = null;
            this.treeNodes = [];
            this._allTreePersons = [];

            // ── Viewer node (synthesized — not in graphMembers) ──
            const viewerMember = this.familyMembers.find(
                m => m.person_pk === this.viewerPersonPk
            );
            const viewerSpouseGraph = members.find(
                m => SPOUSE_LABELS.has(m.relationship_label) && m.generation === 0
            );

            // Infer viewer's parents from graph (Father/Mother labels)
            const PARENT_LABELS = new Set([
                "Father", "Mother", "Step-Father", "Step-Mother"
            ]);
            const viewerParentPks = members
                .filter(m => PARENT_LABELS.has(m.relationship_label))
                .map(m => m.person_pk);

            if (viewerMember) {
                this.treeHead = {
                    ...viewerMember,
                    relationship_label: "You (Viewer)",
                    generation: 0,
                    _isViewer: true,
                    _avatarClass: "av-viewer",
                    spouse_person_pk: viewerSpouseGraph
                        ? viewerSpouseGraph.person_pk : null,
                    parent_person_pks: viewerParentPks,
                };
            }
            this.treeSpouse = viewerSpouseGraph || null;

            // ── Assign avatar classes ──
            for (const m of members) {
                const isSpouse = SPOUSE_LABELS.has(m.relationship_label);
                m._avatarClass = avatarClass(m.generation, m.is_head, isSpouse);
            }

            // ── All persons ──
            const allPersons = [];
            if (this.treeHead) allPersons.push(this.treeHead);
            for (const m of members) allPersons.push(m);
            this._allTreePersons = allPersons;

            const personMap = new Map();
            for (const p of allPersons) personMap.set(p.person_pk, p);

            // ── Group into couples ──
            const usedInCouple = new Set();
            const coupleMap = new Map();   // person_pk → couple
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
                        if (s.spouse_person_pk === p.person_pk
                            && !usedInCouple.has(s.person_pk)) {
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

            // ── Build parent→child-couple map ──
            // For each couple, find its parent couple via any member's
            // parent_person_pks. This correctly handles spouses who
            // married in (no parents in graph) — their couple is placed
            // under the other member's parents.
            const childCouplesOf = new Map();  // couple → [child couples]
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
                    if (!childCouplesOf.has(parentCouple)) {
                        childCouplesOf.set(parentCouple, []);
                    }
                    childCouplesOf.get(parentCouple).push(c);
                } else {
                    rootCouples.push(c);
                }
            }

            // ── Recursively attach children ──
            function attach(node) {
                const kids = childCouplesOf.get(node) || [];
                kids.sort((a, b) =>
                    (a.members[0].first_name || "")
                        .localeCompare(b.members[0].first_name || ""));
                node.children = kids;
                for (const kid of kids) attach(kid);
            }

            for (const root of rootCouples) attach(root);
            this.treeNodes = rootCouples;
        },

        // ── Render tree as HTML (recursive, any depth) ───────

        /** Top-level renderer — called by x-html. */
        renderTree() {
            if (!this.treeNodes?.length) return "";
            return this._renderSubtree(this.treeNodes, true);
        },

        /**
         * Render an array of sibling tree nodes.
         * @param {Array} nodes — sibling couples at the same generation
         * @param {boolean} isRoot — suppress connector above root
         */
        _renderSubtree(nodes, isRoot) {
            if (!nodes.length) return "";

            const gen = nodes[0].gen;
            const genLabel = GEN_LABELS[String(gen)]
                || (gen < 0 ? "Ancestors (" + Math.abs(gen) + ")"
                            : "Descendants (" + gen + ")");

            let h = "";

            // Connector from parent above
            if (!isRoot) h += '<div class="conn-v"></div>';

            // Generation divider
            h += '<div class="gen-divider">'
               + '<div class="gen-divider-line"></div>'
               + '<span class="gen-divider-text">' + genLabel + '</span>'
               + '<div class="gen-divider-line"></div></div>';

            if (nodes.length === 1) {
                // Single node — no bracket
                h += '<div class="gen-row">'
                   + this._renderCouple(nodes[0])
                   + '</div>';
                if (nodes[0].children.length) {
                    h += this._renderSubtree(nodes[0].children, false);
                }
            } else {
                // Multiple nodes — bracket with horizontal bar
                const w = (nodes.length - 1) * 8;
                h += '<div class="bracket-wrap">'
                   + '<div class="conn-h" style="width:' + w + 'rem"></div>'
                   + '<div class="bracket-row">';

                for (const node of nodes) {
                    const hasKids = node.children.length > 0;
                    h += '<div class="bracket-item'
                       + (hasKids ? " flex flex-col items-center" : "")
                       + '">';
                    h += this._renderCouple(node);
                    if (hasKids) {
                        h += this._renderSubtree(node.children, false);
                    }
                    h += '</div>';
                }

                h += '</div></div>';
            }

            return h;
        },

        /** Render a couple group (or single person). */
        _renderCouple(node) {
            if (node.couple) {
                return '<div class="couple-group">'
                     + this._renderPerson(node.members[0])
                     + '<div class="couple-join-line"></div>'
                     + this._renderPerson(node.members[1])
                     + '</div>';
            }
            return this._renderPerson(node.members[0]);
        },

        /** Render a single person card. */
        _renderPerson(m) {
            const av  = m._avatarClass || "av-other";
            const ini = this._esc(this.getInitials(m));
            const nm  = this._esc(this.formatName(m));
            const rl  = this._esc(m._isViewer ? "Viewer" : (m.relationship_label || ""));
            const sel = this.selectedPerson?.person_pk === m.person_pk ? " is-selected" : "";
            const vr  = m._isViewer ? " is-viewer" : "";

            let ind = "";
            if (m._isViewer)
                ind = '<span class="node-indicator indicator-viewer">&#128065;</span>';
            else if (m.is_head)
                ind = '<span class="node-indicator indicator-head">&#9733;</span>';

            return '<div class="tree-node' + sel + '" data-person-pk="' + m.person_pk + '">'
                 + '<div class="node-avatar ' + av + '">' + ini + ind + '</div>'
                 + '<div class="node-name">' + nm + '</div>'
                 + '<div class="node-role' + vr + '">' + rl + '</div>'
                 + '</div>';
        },

        /** Minimal HTML escaping for user-visible text. */
        _esc(s) {
            if (!s) return "";
            return s.replace(/&/g,"&amp;").replace(/</g,"&lt;")
                    .replace(/>/g,"&gt;").replace(/"/g,"&quot;");
        },

        /** Event-delegation click handler for tree nodes. */
        handleTreeClick(event) {
            const el = event.target.closest("[data-person-pk]");
            if (!el) return;
            const pk = el.dataset.personPk;
            const member = this._allTreePersons?.find(m => m.person_pk === pk);
            if (member) this.selectPerson(member);
        },

        // ── Init ──────────────────────────────────────────────

        async init() {
            // Fire health check in parallel — don't block data loading
            this.fetchHealth();
            if (this.viewMode === "admin") {
                await this.fetchOrgRoot();
            } else {
                await this.fetchFamilies();
            }
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

        // ── Org hierarchy navigation (admin view) ────────────

        /** Load the root org (Kendra) and its children */
        async fetchOrgRoot() {
            this.orgChildrenLoading = true;
            this.orgBreadcrumb = [];
            this.orgChildren = [];
            this.orgChildrenStats = {};
            this.selectedSakhaCode = null;
            this.families = [];
            try {
                const res = await fetch(`${ORG_API}/organizations?type_code=KENDRA`);
                if (!res.ok) throw new Error(res.statusText);
                const kendras = await res.json();
                if (kendras.length > 0) {
                    const kendra = kendras[0];
                    this.orgBreadcrumb = [{
                        organization_pk: kendra.organization_pk,
                        organization_name: kendra.organization_name,
                        organization_type_name: kendra.organization_type_name,
                        organization_code: kendra.organization_code,
                    }];
                    await this.fetchOrgChildren(kendra.organization_pk);
                }
            } catch {
                this.orgChildren = [];
            } finally {
                this.orgChildrenLoading = false;
            }
        },

        /** Fetch children of a given org node */
        async fetchOrgChildren(orgPk) {
            this.orgChildrenLoading = true;
            this.orgChildrenStats = {};
            try {
                // Children list is fast — show cards immediately
                const childRes = await fetch(`${ORG_API}/organizations/${orgPk}/children`);
                if (childRes.ok) {
                    this.orgChildren = await childRes.json();
                } else {
                    this.orgChildren = [];
                }
            } catch {
                this.orgChildren = [];
            } finally {
                this.orgChildrenLoading = false;
            }
            // Stats load in background (heavy recursive CTE — non-blocking)
            this._fetchOrgChildrenStats(orgPk);
        },

        /** Background fetch for org children stats (non-blocking) */
        async _fetchOrgChildrenStats(orgPk) {
            try {
                const statsRes = await fetch(`${ORG_API}/organizations/${orgPk}/children-stats`);
                if (statsRes.ok) {
                    const stats = await statsRes.json();
                    const map = {};
                    for (const s of stats) map[s.organization_pk] = s;
                    this.orgChildrenStats = map;
                }
            } catch {
                // Non-fatal — stats are supplementary
            }
        },

        /** Get stats for an org child card */
        getOrgStats(orgPk) {
            return this.orgChildrenStats[orgPk] || null;
        },

        /** Drill into an org node (Anchalika → Sakha → families) */
        async drillIntoOrg(org) {
            // If this is a Sakha, load families filtered by sakha_code
            if (org.organization_type_code === "SAKHA_SANGHA") {
                this.orgBreadcrumb.push({
                    organization_pk: org.organization_pk,
                    organization_name: org.organization_name,
                    organization_type_name: org.organization_type_name,
                    organization_code: org.organization_code,
                });
                this.selectedSakhaCode = org.organization_code;
                this.orgChildren = [];
                await this.fetchFamilies(org.organization_code);
                return;
            }

            // Otherwise drill deeper
            this.orgBreadcrumb.push({
                organization_pk: org.organization_pk,
                organization_name: org.organization_name,
                organization_type_name: org.organization_type_name,
                organization_code: org.organization_code,
            });
            this.selectedSakhaCode = null;
            this.families = [];
            this.selectedFamily = null;
            this._resetDetail();
            await this.fetchOrgChildren(org.organization_pk);
        },

        /** Navigate back to a breadcrumb level */
        async breadcrumbNav(index) {
            if (index < 0) return;
            const crumb = this.orgBreadcrumb[index];
            this.orgBreadcrumb = this.orgBreadcrumb.slice(0, index + 1);
            this.selectedSakhaCode = null;
            this.families = [];
            this.selectedFamily = null;
            this._resetDetail();

            // If navigating back to a Sakha, reload families
            if (crumb.organization_code) {
                // Check if it was a Sakha — reload children of parent
                await this.fetchOrgChildren(crumb.organization_pk);
            }
        },

        /** Switch between member and admin views */
        async switchViewMode(mode) {
            this.viewMode = mode;
            this.selectedFamily = null;
            this._resetDetail();
            this.families = [];
            if (mode === "admin") {
                await this.fetchOrgRoot();
            } else {
                this.orgBreadcrumb = [];
                this.orgChildren = [];
                this.orgChildrenStats = {};
                this.selectedSakhaCode = null;
                await this.fetchFamilies();
            }
        },

        // ── Family list ───────────────────────────────────────

        async fetchFamilies(sakhaCode) {
            this.familiesLoading = true;
            this.familiesError = false;
            try {
                let url = `${FAMILY_API}/families`;
                if (sakhaCode) url += `?sakha_code=${encodeURIComponent(sakhaCode)}`;
                const res = await fetch(url);
                if (!res.ok) throw new Error(res.statusText);
                this.families = await res.json();
            } catch {
                this.familiesError = true;
            } finally {
                this.familiesLoading = false;
            }
        },

        // ── Family selection ──────────────────────────────────

        async selectFamily(family) {
            if (this.selectedFamily?.family_group_pk === family.family_group_pk) {
                this.selectedFamily = null;
                this._resetDetail();
                return;
            }

            this.detailLoading = true;
            this.selectedFamily = family;
            this._resetDetail();

            try {
                const [membersRes, headRes] = await Promise.all([
                    fetch(`${FAMILY_API}/families/${family.family_group_pk}/members`),
                    fetch(`${FAMILY_API}/families/${family.family_group_pk}/head-history`),
                ]);

                // Sakha alignment — fire-and-forget (non-blocking)
                this.fetchSakhaAlignment(family.family_group_pk);

                if (membersRes.ok) {
                    this.familyMembers = await membersRes.json();
                }
                if (headRes.ok) {
                    this.headHistory = await headRes.json();
                }

                // Auto-select the HEAD as default viewer
                const head = this.familyMembers.find(m => m.is_head);
                if (head) {
                    this.viewerPersonPk = head.person_pk;
                    await this.fetchGraph();
                } else if (this.familyMembers.length > 0) {
                    this.viewerPersonPk = this.familyMembers[0].person_pk;
                    await this.fetchGraph();
                }
            } catch {
                // Non-fatal
            } finally {
                this.detailLoading = false;
            }
        },

        // ── Graph fetch (dynamic relationships) ───────────────

        async fetchGraph() {
            if (!this.selectedFamily || !this.viewerPersonPk) return;

            this.graphLoading = true;
            this.graphError = false;
            try {
                const url = `${FAMILY_API}/families/${this.selectedFamily.family_group_pk}/graph?viewer_person_pk=${this.viewerPersonPk}`;
                const res = await fetch(url);
                if (!res.ok) throw new Error(res.statusText);
                this.graphMembers = await res.json();
                this.buildTree();
            } catch {
                this.graphError = true;
            } finally {
                this.graphLoading = false;
            }
        },

        // ── Viewer change (from dropdown) ─────────────────────

        async changeViewer(personPk) {
            this.viewerPersonPk = personPk;
            this.selectedPerson = null;
            this.selectedPersonDetail = null;
            this.selectedPersonMembership = null;
            await this.fetchGraph();
        },

        // ── Sakha alignment (FAM-036 majority rule) ──────────

        async fetchSakhaAlignment(familyGroupPk) {
            this.sakhaAlignmentLoading = true;
            try {
                const res = await fetch(
                    `${FAMILY_API}/families/${familyGroupPk}/sakha-alignment`
                );
                if (res.ok) {
                    this.sakhaAlignment = await res.json();
                }
            } catch {
                // Non-fatal — alignment is informational
            } finally {
                this.sakhaAlignmentLoading = false;
            }
        },

        /** Check if a person's Sakha differs from the family's effective (majority) Sakha */
        isMemberSakhaMismatch(personPk) {
            if (!this.sakhaAlignment?.members) return false;
            const m = this.sakhaAlignment.members.find(
                x => x.person_pk === personPk
            );
            return m?.has_membership && m?.is_home_sakha === false;
        },

        /** Get a person's affiliated Sakha name from the alignment data */
        getMemberSakhaName(personPk) {
            if (!this.sakhaAlignment?.members) return null;
            const m = this.sakhaAlignment.members.find(
                x => x.person_pk === personPk
            );
            return m?.affiliated_sakha_name || null;
        },

        _resetDetail() {
            this.familyMembers = [];
            this.headHistory = [];
            this.graphMembers = [];
            this.viewerPersonPk = null;
            this.selectedPerson = null;
            this.selectedPersonDetail = null;
            this.selectedPersonLoading = false;
            this.selectedPersonMembership = null;
            this.selectedPersonMembershipLoading = false;
            this.sakhaAlignment = null;
            this.sakhaAlignmentLoading = false;
            this.graphError = false;
            this.treeHead = null;
            this.treeSpouse = null;
            this.treeNodes = [];
            this._allTreePersons = [];
        },

        // ── Person selection (click on tree card or table row) ─

        async selectPerson(member) {
            if (this.selectedPerson?.person_pk === member.person_pk) {
                this.selectedPerson = null; // toggle off
                this.selectedPersonDetail = null;
                this.selectedPersonMembership = null;
                return;
            }
            this.selectedPerson = member;
            this.selectedPersonDetail = null;
            this.selectedPersonLoading = true;
            this.selectedPersonMembership = null;
            this.selectedPersonMembershipLoading = true;

            // Fetch full person details + membership summary in parallel
            const personFetch = fetch(`/api/v1/person/persons/${member.person_pk}`)
                .then(r => r.ok ? r.json() : null)
                .catch(() => null);

            const membershipFetch = fetch(`${FAMILY_API}/person/${member.person_pk}/membership-summary`)
                .then(r => r.ok ? r.json() : null)
                .catch(() => null);

            const [personData, membershipData] = await Promise.all([personFetch, membershipFetch]);

            this.selectedPersonDetail = personData;
            this.selectedPersonLoading = false;
            this.selectedPersonMembership = membershipData;
            this.selectedPersonMembershipLoading = false;
        },

        // ── Helpers ───────────────────────────────────────────

        /** Full name from member object */
        formatName(m) {
            return [m.first_name, m.middle_name, m.last_name]
                .filter(Boolean)
                .join(" ");
        },

        /**
         * Display-friendly relationship label.
         * Checks in order:
         *   1. Viewer flag (_isViewer)
         *   2. Direct relationship_label (from graph endpoint)
         *   3. Lookup in graphMembers (when clicked from member table)
         *   4. Viewer PK match (clicked from member table as viewer)
         *   5. Static relationship_type_name fallback
         */
        displayRelationship(m) {
            if (m._isViewer) return "You (Viewer)";
            if (m.relationship_label) return m.relationship_label;
            // Look up dynamic label from graph (handles member-table clicks)
            if (m.person_pk === this.viewerPersonPk) return "You (Viewer)";
            const graphMember = this.graphMembers.find(g => g.person_pk === m.person_pk);
            if (graphMember?.relationship_label) return graphMember.relationship_label;
            if (m.is_head) return "Head of Family";
            return m.relationship_type_name || m.relationship_type_code || "—";
        },

        /** Two-letter initials for avatar circle */
        getInitials(m) {
            const first = (m.first_name || "")[0] || "";
            const last = (m.last_name || "")[0] || "";
            return (first + last).toUpperCase() || "?";
        },

        /** CSS class for the person-avatar */
        getAvatarClass(m) {
            if (!m) return "av-other";
            if (m._avatarClass) return m._avatarClass;
            if (m._isViewer) return "av-viewer";
            // Look up from graph (handles member-table clicks that lack _avatarClass)
            if (m.person_pk === this.viewerPersonPk) return "av-viewer";
            const graphMember = this.graphMembers.find(g => g.person_pk === m.person_pk);
            if (graphMember?._avatarClass) return graphMember._avatarClass;
            return "av-other";
        },

        /** Get the viewer's name for display */
        getViewerName() {
            const viewer = this.familyMembers.find(m => m.person_pk === this.viewerPersonPk);
            return viewer ? this.formatName(viewer) : "";
        },

        /** Find spouse name from graph for the selected person */
        getSpouseName(personPk) {
            const graphMember = this.graphMembers.find(g => g.person_pk === personPk);
            if (graphMember && graphMember.spouse_person_pk) {
                const spouse = this.graphMembers.find(g => g.person_pk === graphMember.spouse_person_pk)
                    || this.familyMembers.find(m => m.person_pk === graphMember.spouse_person_pk);
                if (spouse) return this.formatName(spouse);
            }
            if (personPk === this.viewerPersonPk && this.treeSpouse) {
                return this.formatName(this.treeSpouse);
            }
            return null;
        },

        /** Get spouse person_pk for click-navigation */
        getSpousePersonPk(personPk) {
            const graphMember = this.graphMembers.find(g => g.person_pk === personPk);
            if (graphMember && graphMember.spouse_person_pk) return graphMember.spouse_person_pk;
            if (personPk === this.viewerPersonPk && this.treeSpouse) return this.treeSpouse.person_pk;
            return null;
        },

        /** Get spouse initials for the mini-card avatar */
        getSpouseInitials(personPk) {
            const graphMember = this.graphMembers.find(g => g.person_pk === personPk);
            if (graphMember && graphMember.spouse_person_pk) {
                const spouse = this.graphMembers.find(g => g.person_pk === graphMember.spouse_person_pk)
                    || this.familyMembers.find(m => m.person_pk === graphMember.spouse_person_pk);
                if (spouse) return this.getInitials(spouse);
            }
            if (personPk === this.viewerPersonPk && this.treeSpouse) {
                return this.getInitials(this.treeSpouse);
            }
            return "?";
        },

        /** Navigate to spouse when clicking spouse card */
        selectSpouse(personPk) {
            const spousePk = this.getSpousePersonPk(personPk);
            if (!spousePk) return;
            const spouseMember = this.graphMembers.find(g => g.person_pk === spousePk)
                || this.familyMembers.find(m => m.person_pk === spousePk);
            if (spouseMember) this.selectPerson(spouseMember);
        },
    };
}
