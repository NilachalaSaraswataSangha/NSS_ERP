/**
 * NSS ERP — Shared Configuration & Display Mappings
 *
 * Single source of truth for display name overrides,
 * badge class lookups, and shared constants.
 *
 * Every page includes this before its own module JS.
 * Module JS can call NSS.typeBadgeClass(code) etc.
 * without duplicating the mapping logic.
 *
 * Design rule: value_code is the stable DB key.
 * Display names come from master_data.value_name (API)
 * unless overridden here per NSS Bye-Law terminology.
 */

const NSS = {
    /* ── Membership type display name overrides ──────────────
     * DB stores value_name from master_data.
     * These overrides map value_code → portal display label
     * when the Bye-Law term differs from the DB name.
     *
     * If a code is NOT in this map, use API's value_name as-is.
     * Authority: NSS Bye-Law §B, MBR-007
     */
    TYPE_DISPLAY_NAMES: {
        PROBATIONARY: "Darshaka",
        // REGULAR, ASSOCIATE, HONORARY — use DB value_name as-is
    },

    /**
     * Get display name for a membership type.
     * @param {string} code   - value_code (e.g. "PROBATIONARY")
     * @param {string} dbName - value_name from API (e.g. "Darshaka")
     * @returns {string} display label
     */
    typeDisplayName(code, dbName) {
        return this.TYPE_DISPLAY_NAMES[code] || dbName || code;
    },

    /* ── Badge class lookups ─────────────────────────────────
     * Maps value_code → CSS class from badges.css.
     * Keeps HTML templates clean: :class="NSS.statusBadgeClass(code)"
     */

    STATUS_BADGE_MAP: {
        ACTIVE:              "badge-status-active",
        INACTIVE:            "badge-status-inactive",
        PROPOSED:            "badge-status-proposed",
        APPROVED:            "badge-status-approved",
        SUSPENDED:           "badge-status-suspended",
        LAPSED:              "badge-status-lapsed",
        TRANSFERRED:         "badge-status-transferred",
        RESIGNED:            "badge-status-resigned",
        EXPELLED:            "badge-status-expelled",
        DECEASED:            "badge-status-deceased",
        DISSOLVED:           "badge-status-dissolved",
        ARCHIVED:            "badge-status-archived",
        EXPIRED:             "badge-status-expired",
        CANCELLED:           "badge-status-cancelled",
        REPLACED:            "badge-status-replaced",
        RENEWAL_PENDING:     "badge-status-renewal-pending",
        ON_HOLD:             "badge-status-on-hold",
        DISCIPLINARY_REVIEW: "badge-status-disciplinary-review",
    },

    TYPE_BADGE_MAP: {
        PROBATIONARY: "badge-type-probationary",
        REGULAR:      "badge-type-regular",
        ASSOCIATE:    "badge-type-associate",
        HONORARY:     "badge-type-honorary",
    },

    AFF_BADGE_MAP: {
        ACTIVE:      "badge-aff-active",
        ARCHIVED:    "badge-aff-archived",
        REACTIVATED: "badge-aff-reactivated",
    },

    GENDER_BADGE_MAP: {
        MALE:   "badge-gender-male",
        FEMALE: "badge-gender-female",
        OTHER:  "badge-gender-other",
    },

    /**
     * Lifecycle status → badge CSS class.
     * @param {string} code - status value_code
     * @returns {string} CSS class
     */
    statusBadgeClass(code) {
        return this.STATUS_BADGE_MAP[code] || "badge-ghost";
    },

    /**
     * Membership type → badge CSS class.
     * @param {string} code - membership_type value_code
     * @returns {string} CSS class
     */
    typeBadgeClass(code) {
        return this.TYPE_BADGE_MAP[code] || "badge-ghost";
    },

    /**
     * Affiliation status → badge CSS class.
     * @param {string} status - affiliation_status string
     * @returns {string} CSS class
     */
    affBadgeClass(status) {
        return this.AFF_BADGE_MAP[status] || "badge-ghost";
    },

    /**
     * Gender code → badge CSS class.
     * @param {string} code - gender value_code
     * @returns {string} CSS class
     */
    genderBadgeClass(code) {
        return this.GENDER_BADGE_MAP[code] || "badge-ghost";
    },

    /* ── Document visibility rules ──────────────────────────────
     * Authority: NSS Bye-Law §B, MBR-019A/B
     *
     * Parichaya Patra:  All membership types (REGULAR, ASSOCIATE, HONORARY, PROBATIONARY)
     * Anumati Patra:    Darshaka (PROBATIONARY) and Regular only — NOT Associate (MBR-019A/B)
     *
     * Use these helpers in x-show / x-if to keep visibility
     * rules consistent across all pages.
     */

    /**
     * Whether Parichaya Patra section should be shown.
     * @param {string} typeCode - membership_type_code
     * @returns {boolean}
     */
    showParichayaPatra(typeCode) {
        return true; // All membership types receive Parichaya Patra
    },

    /**
     * Whether Anumati Patra section should be shown.
     * Darshaka (PROBATIONARY) receives Anumati Patra.
     * Associate does NOT (MBR-019A/B).
     * @param {string} typeCode - membership_type_code
     * @returns {boolean}
     */
    showAnumatiPatra(typeCode) {
        return typeCode !== "ASSOCIATE";
    },
};
