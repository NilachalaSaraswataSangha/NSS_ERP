/**
 * NSS ERP — Org Dashboard tab (Tier 5)
 *
 * One component, six layouts — the rendered layout depends on the
 * viewed organization's type, each matching its own mockup exactly
 * (colors + structure): docs/03_Solution/ui/mockups/03_sakha_dashboard.html,
 * 05_anchalika_dashboard.html, 06_zilla_dashboard.html, 02_kendra_dashboard.html.
 * Patha Chakra and Mahila Sangha have no mockups of their own (added after
 * the four above) — they reuse the same card idiom as the other tiers rather
 * than introducing a new visual language.
 *
 * The six tiers are exactly the six ORGANIZATIONAL roles in role_master
 * (SOL-ADMIN-004 §8.7): every scoped-admin role has one dashboard, and no
 * dashboard exists without a role that can hold it.
 *
 * Embedded as a tab inside admin.html/dashboard.html's own sidebar+topbar
 * shell (not a standalone page) — both host pages instantiate this same
 * factory in a nested x-data scope and pass in the org PK to view via
 * init(orgPk); each host wires its own openOrgDashboard(orgPk)/
 * myOrgDashboardPk/myOrgDashboardLabel to switch tabs and re-init this
 * component when the viewed org changes.
 *
 * Every number shown is real (member/family counts, Darshak counts,
 * hierarchy) — attendance % and renewal tracking don't exist in this
 * system yet (no DB tables for either), so those mockup widgets are shown
 * as honest "not tracked yet" placeholders rather than fabricated figures.
 * The two Zilla "insights" mockup widgets that depended on attendance/
 * renewal data were swapped for ones backed by real data (largest/smallest
 * Sakha by member count) — same card layout, different, truthful content.
 */

function orgDashboardTab() {
    return {
        loading: true,
        error: "",
        org: null,

        // Sakha tier
        // null means "could not be determined" (request failed, no permission,
        // or no org_code to scope by) and renders as "—". 0 means a real zero.
        sakhaMemberTotal: null,
        sakhaFamilyTotal: null,
        // /family/families has no total, so the count above is a page length.
        // True when it saturated the page limit and is therefore a lower bound.
        sakhaFamilyTruncated: false,
        recentMembers: [],
        darshak: { home_probationary_count: 0, attending_from_other_sakha_count: 0 },

        // Anchalika / Zilla / Kendra tier
        childStats: [],
        sakhaCount: null,
        mahilaCount: null,
        renewalsDue: null,

        // Kendra tier — whole-subtree totals from /organizations/{pk}/stats.
        // Members split into its two constituent parts (these sum exactly to
        // the subtree member total, since every membership_type except
        // PROBATIONARY carries a Parichay Patra), plus one count per
        // constituent ORGANIZATION_TYPE beneath the Kendra.
        //
        // NOTE the Darshak figure here is HOME probationary members only. It
        // deliberately omits card-holders visiting from another Sakha — those
        // are already counted at their home Sakha, so including them would
        // count one person many times over a 175-Sakha rollup. The visiting
        // figure belongs to a single Sakha's own dashboard, and lives there.
        parichayPatraTotal: null,
        darshakTotal: null,
        anchalikaCount: null,
        zillaCount: null,
        pathaChakraCount: null,
        paribarikCount: null,
        kumariCount: null,
        sevakCount: null,

        /**
         * Render a count that may be unknown. Keeps a real 0 visible while
         * showing "—" for null, so a failed/unscoped fetch is never displayed
         * as a confident zero.
         */
        statNum(v, truncated = false) {
            if (v === null || v === undefined) return "—";
            return truncated ? `${v}+` : String(v);
        },

        async init(orgPk) {
            if (!orgPk) {
                this.error = "No organization specified.";
                this.loading = false;
                return;
            }

            this.loading = true;
            this.error = "";
            try {
                const res = await NSSAuth.apiFetch(`/api/v1/organization/organizations/${orgPk}`);
                if (!res.ok) throw new Error(await NSS.extractError(res));
                this.org = await res.json();
                await this._loadTierData();
            } catch (err) {
                this.error = err.message || "Failed to load organization.";
            } finally {
                this.loading = false;
            }
        },

        // ── Tier helpers ───────────────────────────────────

        get orgTypeCode() {
            return this.org?.organization_type_code || "";
        },
        get isSakha() { return this.orgTypeCode === "SAKHA_SANGHA"; },
        get isAnchalika() { return this.orgTypeCode === "ANCHALIKA_SANGHA"; },
        get isZilla() { return this.orgTypeCode === "ZILLA_SANGHA"; },
        get isKendra() { return this.orgTypeCode === "KENDRA"; },
        get isPathaChakra() { return this.orgTypeCode === "PATHA_CHAKRA"; },
        get isMahila() { return this.orgTypeCode === "MAHILA_SANGHA"; },
        get isChildOverviewTier() { return this.isAnchalika || this.isZilla; },

        // Sakha "Members" split (Sakha tier ONLY — deliberately not exposed
        // on Anchalika/Zilla/Kendra, which roll up member counts across many
        // Sakhas via childStats; mixing in cross-Sakha Darshak attendance
        // there would double-count the same person under two different
        // Sakhas and inflate the broader dashboards' totals).
        //
        // sakhaMemberTotal (from /membership/members?org_code=…) is every
        // active sangha_sevi whose HOME org is this Sakha, with no
        // membership_type filter — so it already includes this Sakha's own
        // PROBATIONARY ("Darshaka") home members alongside its REGULAR/
        // ASSOCIATE/HONORARY ones. A Parichay Patra is issued to every
        // membership_type EXCEPT PROBATIONARY (value_name "Darshaka" — see
        // MEMBERSHIP_TYPE seed), so subtracting darshak.home_probationary_count
        // yields the true card-holder count with no extra query.
        get parichayPatraHolderCount() {
            if (this.sakhaMemberTotal === null) return null;
            return this.sakhaMemberTotal - (this.darshak.home_probationary_count || 0);
        },

        // Visiting Darshaks: members whose Parichay Patra home Sakha is a
        // DIFFERENT organization, currently attending this Sakha — the
        // darshak-summary endpoint's attending_from_other_sakha_count.
        // Explicitly NOT the same as home_probationary_count (this Sakha's
        // own not-yet-confirmed members), which stays in the existing
        // Darshak card unchanged.
        get visitingDarshakCount() {
            return this.darshak.attending_from_other_sakha_count ?? null;
        },

        // Sakha "Darshaks" tile (Sakha tier ONLY): BOTH Darshak flavours —
        // this Sakha's own not-yet-confirmed PROBATIONARY entrants
        // (home_probationary_count) PLUS Parichay Patra holders whose home is
        // a DIFFERENT Sakha but who attend here (attending_from_other_sakha_count).
        get sakhaDarshakTotal() {
            return (this.darshak.home_probationary_count || 0)
                 + (this.darshak.attending_from_other_sakha_count || 0);
        },

        // Sakha "Total Members" (Sakha tier ONLY): everyone who counts as
        // attending THIS Sakha — its home card-holders + its home Darshaks
        // (both already inside sakhaMemberTotal, which is home-scoped by
        // org_code) PLUS visiting Darshaks whose Parichay Patra home is
        // another Sakha. So: parichay holders + home probationary + visiting.
        //
        // Deliberately DIFFERENT from the broad Kendra/Anchalika/Zilla tiers,
        // whose member totals are home-based (childStats.member_count) and
        // exclude visitors — adding cross-Sakha attendance there would count
        // the same person under two Sakhas and inflate the rollup. On a single
        // Sakha's own dashboard the visitor headcount is the point ("how many
        // are attending this Sangha"), so it belongs here and only here.
        get sakhaTotalMembers() {
            if (this.sakhaMemberTotal === null) return null;
            return this.sakhaMemberTotal
                 + (this.darshak.attending_from_other_sakha_count || 0);
        },

        // A Mahila Sangha hangs off either a Kendra (the central Mahila
        // Sangha) or a Sakha Sangha (a local one) — see
        // _ALLOWED_PARENT_TYPES in api/routers/organization.py. The tier
        // shows which, because the Parichalana Mandali's remit differs.
        get isCentralMahila() {
            return this.isMahila && this.org?.parent_organization_type_code === "KENDRA";
        },

        async _loadTierData() {
            if (this.isSakha) return this._loadSakhaData();
            if (this.isChildOverviewTier) return this._loadChildOrgData();
            if (this.isKendra) return this._loadKendraData();
            if (this.isPathaChakra) return this._loadPathaChakraData();
            // Mahila Sangha: there is no mahila module and no governance
            // tables in the DDL yet (00_bootstrap..07_administration), so its
            // Mandali membership/office-bearer widgets are honest placeholders
            // over the org identity init() already loaded.
        },

        // ── Sakha tier data ────────────────────────────────

        async _loadSakhaData() {
            const orgPk = this.org.organization_pk;
            const code = this.org.organization_code;

            // /membership/members can only be filtered by org_code. There is
            // deliberately NO fallback to org_type_code=SAKHA_SANGHA here: that
            // returns every Sakha member in the system, which was then
            // displayed as this one Sakha's member count. With no code there is
            // no way to scope the query, so the count stays null and the card
            // renders "—".
            const memberQs = code ? `org_code=${encodeURIComponent(code)}` : null;

            const FAMILY_LIMIT = 500;
            const [memberRes, familyRes, recentRes, darshakRes] = await Promise.all([
                memberQs
                    ? NSSAuth.apiFetch(`/api/v1/membership/members?${memberQs}&limit=1`)
                        .then(r => r.ok ? r.json() : null).catch(() => null)
                    : Promise.resolve(null),
                NSSAuth.apiFetch(`/api/v1/family/families?sakha_organization_pk=${orgPk}&limit=${FAMILY_LIMIT}`)
                    .then(r => r.ok ? r.json() : null).catch(() => null),
                memberQs
                    ? NSSAuth.apiFetch(`/api/v1/membership/members?${memberQs}&limit=5&sort_by=joining_date&sort_dir=desc`)
                        .then(r => r.ok ? r.json() : { members: [] }).catch(() => ({ members: [] }))
                    : Promise.resolve({ members: [] }),
                NSSAuth.apiFetch(`/api/v1/membership/organizations/${orgPk}/darshak-summary`)
                    .then(r => r.ok ? r.json() : null).catch(() => null),
            ]);

            // null (request failed / not permitted) is kept distinct from 0 so
            // a permission failure shows "—" rather than a confident zero.
            this.sakhaMemberTotal = memberRes ? (memberRes.total || 0) : null;

            // /family/families returns a bare list with no total, so this is a
            // page length, not a COUNT. Flag when it saturates the limit so the
            // card can show "500+" instead of a wrong exact figure.
            if (Array.isArray(familyRes)) {
                this.sakhaFamilyTotal = familyRes.length;
                this.sakhaFamilyTruncated = familyRes.length >= FAMILY_LIMIT;
            } else {
                this.sakhaFamilyTotal = null;
                this.sakhaFamilyTruncated = false;
            }

            this.recentMembers = recentRes.members || [];
            if (darshakRes) this.darshak = darshakRes;
        },

        // ── Anchalika / Zilla tier data ────────────────────

        async _loadChildOrgData() {
            const orgPk = this.org.organization_pk;
            const [childRes, statsRes] = await Promise.all([
                NSSAuth.apiFetch(`/api/v1/organization/organizations/${orgPk}/children-stats`)
                    .then(r => r.ok ? r.json() : []).catch(() => []),
                // Org-scoped totals (renewals due for Zilla, Mahila Sangha
                // count for Anchalika) for THIS org's subtree specifically —
                // not the viewer's own admin scope, which is what
                // /admin/dashboard-stats answers and would be wrong for a
                // drill-down into someone else's org. See OrgStatsResponse's
                // docstring (api/schemas/organization.py).
                NSSAuth.apiFetch(`/api/v1/organization/organizations/${orgPk}/stats`)
                    .then(r => r.ok ? r.json() : null).catch(() => null),
            ]);
            this.childStats = childRes;
            this.renewalsDue = statsRes ? (statsRes.renewals_due ?? null) : null;
            this.mahilaCount = statsRes ? (statsRes.mahila_sanghas ?? null) : null;

            // Membership split for this Anchalika/Zilla's subtree — same
            // single /stats call, no extra round trip. Home-based like
            // member_count, so it excludes Parichay Patra holders whose home
            // Sakha is elsewhere and who only attend here as Darshaks
            // (the Sakha tier is the only tier that adds those in).
            this.parichayPatraTotal = statsRes ? (statsRes.parichay_patra_holders ?? null) : null;
            this.darshakTotal = statsRes ? (statsRes.darshaks ?? null) : null;
        },

        // ── Kendra tier data ───────────────────────────────

        async _loadKendraData() {
            const orgPk = this.org.organization_pk;
            const [childRes, statsRes] = await Promise.all([
                NSSAuth.apiFetch(`/api/v1/organization/organizations/${orgPk}/children-stats`)
                    .then(r => r.ok ? r.json() : []).catch(() => []),
                // Org-scoped COUNT(*)s for THIS Kendra's subtree — replaces
                // /admin/dashboard-stats (viewer-scoped, wrong for a Kendra
                // admin drilling into a peer Kendra) and the earlier
                // `/organizations?type_code=…&limit=500` calls, which were
                // both globally unscoped AND silently capped at MAX_LIMIT.
                NSSAuth.apiFetch(`/api/v1/organization/organizations/${orgPk}/stats`)
                    .then(r => r.ok ? r.json() : null).catch(() => null),
            ]);
            this.childStats = childRes;
            this.sakhaCount = statsRes ? (statsRes.sakha_sanghas ?? null) : null;
            this.mahilaCount = statsRes ? (statsRes.mahila_sanghas ?? null) : null;

            // Per-type constituent-body counts + the members split. All come
            // from the same single /stats call already being made above — no
            // extra round trip. null (request failed / not permitted) stays
            // distinct from a real 0 so statNum() renders "—".
            this.parichayPatraTotal = statsRes ? (statsRes.parichay_patra_holders ?? null) : null;
            this.darshakTotal   = statsRes ? (statsRes.darshaks ?? null) : null;
            this.anchalikaCount = statsRes ? (statsRes.anchalika_sanghas ?? null) : null;
            this.zillaCount     = statsRes ? (statsRes.zilla_sanghas ?? null) : null;
            this.pathaChakraCount = statsRes ? (statsRes.patha_chakras ?? null) : null;
            this.paribarikCount = statsRes ? (statsRes.paribarik_sanghas ?? null) : null;
            this.kumariCount    = statsRes ? (statsRes.kumari_sanghas ?? null) : null;
            this.sevakCount     = statsRes ? (statsRes.sevak_sanghas ?? null) : null;
        },

        // ── Patha Chakra tier data ─────────────────────────

        async _loadPathaChakraData() {
            const orgPk = this.org.organization_pk;
            // A Patha Chakra sits directly under a Kendra and is a LEAF type:
            // _ALLOWED_PARENT_TYPES (api/routers/admin.py) never names
            // PATHA_CHAKRA as an allowed parent, so it can hold no child orgs,
            // and members may only attach to a Sakha Sangha
            // (require_sakha_organization in api/helpers.py). Its /stats
            // subtree is therefore always itself alone and the membership
            // figures are a structural zero, not "nobody registered yet" —
            // which is exactly what the note beside the tiles says. The call
            // is still made rather than hard-coding 0, so the tiles report
            // whatever the server actually computes (and show "—" if the
            // request is not permitted).
            const statsRes = await NSSAuth.apiFetch(`/api/v1/organization/organizations/${orgPk}/stats`)
                .then(r => r.ok ? r.json() : null).catch(() => null);
            this.parichayPatraTotal = statsRes ? (statsRes.parichay_patra_holders ?? null) : null;
            this.darshakTotal = statsRes ? (statsRes.darshaks ?? null) : null;
        },

        // ── Derived totals (Anchalika/Zilla/Kendra child table) ──

        get childMemberTotal() {
            return this.childStats.reduce((sum, c) => sum + (c.member_count || 0), 0);
        },
        get childFamilyTotal() {
            return this.childStats.reduce((sum, c) => sum + (c.family_count || 0), 0);
        },
        get largestChild() {
            if (this.childStats.length === 0) return null;
            return this.childStats.reduce((a, b) => (b.member_count > a.member_count ? b : a));
        },
        get smallestChild() {
            if (this.childStats.length === 0) return null;
            return this.childStats.reduce((a, b) => (b.member_count < a.member_count ? b : a));
        },

        // "Total Members" for every non-Sakha tier (Kendra, Anchalika, Zilla):
        // the two parts from /stats when available, so the headline figure and
        // the Parichay Patra / Darshak tiles beside it always agree. Falls back
        // to summing childStats (same home-based definition, different
        // endpoint) if /stats was not permitted. Kept separate from the Sakha
        // tier's sakhaTotalMembers, which deliberately ALSO adds visiting
        // Parichay Patra holders from other Sakhas.
        get orgMemberTotal() {
            if (this.parichayPatraTotal !== null && this.darshakTotal !== null) {
                return this.parichayPatraTotal + this.darshakTotal;
            }
            return this.childMemberTotal;
        },

        formatDate(d) {
            return NSS.formatDate(d);
        },
    };
}
