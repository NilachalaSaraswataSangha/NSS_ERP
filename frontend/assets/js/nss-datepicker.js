/**
 * NSS ERP — Shared Date Picker (DD/MM/YYYY)
 *
 * Generic Alpine.js component for Indian-format date input
 * with a calendar popup. Works with any parent data model.
 *
 * Usage (model path resolves relative to the nearest x-data scope):
 *
 *   <!-- With a "form" object in parent x-data -->
 *   <div x-data="nssDatePicker('form.date_of_birth')"> ... </div>
 *
 *   <!-- Direct property in parent x-data -->
 *   <div x-data="nssDatePicker('createFamilyFormedDate')"> ... </div>
 *
 * Stores ISO (YYYY-MM-DD) into the model; displays DD/MM/YYYY.
 *
 * Calendar popup HTML is provided by nssCalendarHTML() for easy
 * inline embedding, or use the full template (see register.html).
 */

function nssDatePicker(modelPath, opts) {
    opts = opts || {};
    return {
        _modelPath: modelPath,
        // Validation options (all optional, backward-compatible):
        //   maxToday : true  → reject any date after today (e.g. DOB)
        //   minYear / maxYear → override the default 1900–2100 window
        _opts: {
            maxToday: opts.maxToday === true,
            minYear: opts.minYear || 1900,
            maxYear: opts.maxYear || 2100,
        },
        open: false,
        display: "",
        // Validation feedback surfaced to the template. `invalid` is true only
        // when the field holds a COMPLETE but unacceptable date, so a
        // half-typed value never flashes an error.
        invalid: false,
        errorMsg: "",

        viewYear: new Date().getFullYear(),
        viewMonth: new Date().getMonth(),
        calDays: [],
        calBlanks: [],

        monthNames: [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ],

        // ── Model access helpers ─────────────────────────
        // Resolve "form.date_of_birth" or "myDate" from parent scope

        _getModel() {
            var parts = this._modelPath.split(".");
            var obj = this;
            for (var i = 0; i < parts.length - 1; i++) {
                obj = obj[parts[i]];
                if (obj == null) return { obj: null, key: null };
            }
            return { obj: obj, key: parts[parts.length - 1] };
        },

        _readModel() {
            var m = this._getModel();
            return m.obj && m.key ? (m.obj[m.key] || "") : "";
        },

        _writeModel(isoDate) {
            var m = this._getModel();
            if (m.obj && m.key) m.obj[m.key] = isoDate;
        },

        // ── Lifecycle ────────────────────────────────────

        init() {
            this.rebuildCal();

            // Restore display from existing model value
            var iso = this._readModel();
            if (iso) {
                var p = iso.split("-");
                if (p.length === 3) {
                    this.display = p[2] + "/" + p[1] + "/" + p[0];
                    this.viewYear = parseInt(p[0], 10);
                    this.viewMonth = parseInt(p[1], 10) - 1;
                    this.rebuildCal();
                }
            }

            this.$watch("viewMonth", () => this.rebuildCal());
            this.$watch("viewYear", () => this.rebuildCal());
        },

        rebuildCal() {
            var count = new Date(this.viewYear, this.viewMonth + 1, 0).getDate();
            this.calDays = [];
            for (var i = 1; i <= count; i++) this.calDays.push(i);

            var offset = new Date(this.viewYear, this.viewMonth, 1).getDay();
            this.calBlanks = [];
            for (var j = 0; j < offset; j++) this.calBlanks.push(j);
        },

        // ── Manual text input with auto-slash ────────────

        onInput(event) {
            var val = event.target.value.replace(/[^0-9/]/g, "");
            var digits = val.replace(/\//g, "");
            if (digits.length >= 4) {
                val = digits.slice(0, 2) + "/" + digits.slice(2, 4) + "/" + digits.slice(4, 8);
            } else if (digits.length >= 2) {
                val = digits.slice(0, 2) + "/" + digits.slice(2);
            }
            this.display = val;

            if (/^\d{2}\/\d{2}\/\d{4}$/.test(val)) {
                var parts = val.split("/");
                var day = parseInt(parts[0], 10);
                var month = parseInt(parts[1], 10);
                var year = parseInt(parts[2], 10);
                var check = this.validate(day, month, year);
                if (check.ok) {
                    this.invalid = false;
                    this.errorMsg = "";
                    this._writeModel(year + "-" + String(month).padStart(2, "0") + "-" + String(day).padStart(2, "0"));
                    this.viewYear = year;
                    this.viewMonth = month - 1;
                } else {
                    // Complete but unacceptable date — flag it and clear the
                    // model so downstream "date required" guards stay closed.
                    this.invalid = true;
                    this.errorMsg = check.msg;
                    this._writeModel("");
                }
            } else {
                // Partial / incomplete entry. Validate each completed segment
                // as it is typed so obvious mistakes (day 45, month 19) warn
                // immediately, rather than waiting for a full DD/MM/YYYY.
                this._writeModel("");
                var partialMsg = "";
                if (digits.length >= 2) {
                    var pDay = parseInt(digits.slice(0, 2), 10);
                    if (pDay < 1 || pDay > 31) {
                        partialMsg = "Invalid date — day must be between 01 and 31.";
                    }
                }
                if (!partialMsg && digits.length >= 4) {
                    var pMonth = parseInt(digits.slice(2, 4), 10);
                    if (pMonth < 1 || pMonth > 12) {
                        partialMsg = "Invalid date — month must be between 01 and 12.";
                    }
                }
                this.invalid = !!partialMsg;
                this.errorMsg = partialMsg;
            }
        },

        // Full validation with a human-readable reason. Returns
        // { ok: bool, msg: string }. `isValidDate` is kept as a thin
        // boolean wrapper for any existing callers.
        validate(day, month, year) {
            if (month < 1 || month > 12) {
                return { ok: false, msg: "Invalid date — month must be between 01 and 12." };
            }
            if (day < 1 || day > 31) {
                return { ok: false, msg: "Invalid date — day must be between 01 and 31." };
            }
            if (year < this._opts.minYear || year > this._opts.maxYear) {
                return { ok: false, msg: "Invalid date — year must be between " + this._opts.minYear + " and " + this._opts.maxYear + "." };
            }
            var d = new Date(year, month - 1, day);
            if (d.getFullYear() !== year || d.getMonth() !== month - 1 || d.getDate() !== day) {
                return { ok: false, msg: "That date does not exist on the calendar." };
            }
            if (this._opts.maxToday) {
                var today = new Date();
                today.setHours(0, 0, 0, 0);
                if (d > today) {
                    return { ok: false, msg: "Date of birth cannot be in the future." };
                }
            }
            return { ok: true, msg: "" };
        },

        isValidDate(day, month, year) {
            return this.validate(day, month, year).ok;
        },

        // ── Calendar navigation ──────────────────────────

        prevMonth() {
            if (this.viewMonth === 0) { this.viewMonth = 11; this.viewYear--; }
            else { this.viewMonth--; }
        },

        nextMonth() {
            if (this.viewMonth === 11) { this.viewMonth = 0; this.viewYear++; }
            else { this.viewMonth++; }
        },

        onMonthChange(e) {
            this.viewMonth = parseInt(e.target.value, 10);
        },

        onYearInput(e) {
            var v = parseInt(e.target.value, 10);
            if (v >= 1930 && v <= 2100) this.viewYear = v;
        },

        // ── Day helpers ──────────────────────────────────

        isToday(day) {
            var n = new Date();
            return day === n.getDate() && this.viewMonth === n.getMonth() && this.viewYear === n.getFullYear();
        },

        isSelected(day) {
            var iso = this._readModel();
            if (!iso) return false;
            var p = iso.split("-");
            return parseInt(p[0], 10) === this.viewYear &&
                   parseInt(p[1], 10) === this.viewMonth + 1 &&
                   parseInt(p[2], 10) === day;
        },

        selectDay(day) {
            var m = this.viewMonth + 1;
            var check = this.validate(day, m, this.viewYear);
            if (!check.ok) {
                this.invalid = true;
                this.errorMsg = check.msg;
                return;
            }
            var iso = this.viewYear + "-" + String(m).padStart(2, "0") + "-" + String(day).padStart(2, "0");
            this.display = String(day).padStart(2, "0") + "/" + String(m).padStart(2, "0") + "/" + this.viewYear;
            this.invalid = false;
            this.errorMsg = "";
            this._writeModel(iso);
            this.open = false;
        },

        clearDate() {
            this.display = "";
            this.invalid = false;
            this.errorMsg = "";
            this._writeModel("");
            this.open = false;
        },

        goToday() {
            var n = new Date();
            this.viewYear = n.getFullYear();
            this.viewMonth = n.getMonth();
            this.selectDay(n.getDate());
        },
    };
}

var NSS_CAL_ICON_SVG = '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" style="width:1rem;height:1rem;"><path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5" /></svg>';

/* ═══════════════════════════════════════════════════════════
 * SHARED CALENDAR MARKUP — single source of truth
 *
 * Previously every date field hand-copied ~30 lines of popup
 * markup. Ten copies had drifted: only the Create Person DOB
 * field rendered the validation error, register.html used a
 * different input class, and some were missing Today/Clear.
 *
 * Now the markup lives here once and is injected into every
 * `x-data="nssDatePicker(...)"` element on DOMContentLoaded —
 * which runs BEFORE Alpine starts (Alpine is loaded `defer`,
 * this file is a blocking head script, so our listener is
 * registered first). Alpine then compiles the injected
 * directives normally.
 *
 * Callsites only declare intent:
 *   <div x-data="nssDatePicker('form.date_of_birth', { maxToday: true })">
 *       <label class="form-label">Date of Birth *</label>
 *   </div>
 *
 * Optional per-callsite overrides (data attributes on the root):
 *   data-dp-input-class : input CSS class   (default nss-dp-input)
 *   data-dp-disabled    : Alpine expr for :disabled (e.g. "loading")
 *   data-dp-placeholder : default DD/MM/YYYY
 * ═══════════════════════════════════════════════════════════ */

var NSS_DP_MONTH_OPTIONS =
    '<option value="0">Jan</option><option value="1">Feb</option>' +
    '<option value="2">Mar</option><option value="3">Apr</option>' +
    '<option value="4">May</option><option value="5">Jun</option>' +
    '<option value="6">Jul</option><option value="7">Aug</option>' +
    '<option value="8">Sep</option><option value="9">Oct</option>' +
    '<option value="10">Nov</option><option value="11">Dec</option>';

/**
 * Build the canonical input + calendar-popup markup.
 * @param {Object} cfg - { inputClass, disabledExpr, placeholder }
 * @returns {string} HTML to append inside the nssDatePicker root.
 */
function nssDatePickerMarkup(cfg) {
    cfg = cfg || {};
    var inputClass = cfg.inputClass || "nss-dp-input";
    var placeholder = cfg.placeholder || "DD/MM/YYYY";
    var disabled = cfg.disabledExpr
        ? ' :disabled="' + cfg.disabledExpr + '"'
        : "";

    return '' +
        '<div class="nss-dp-wrap">' +
            '<input type="text" class="' + inputClass + '" x-model="display"' +
                   ' @click="open = true" @input="onInput($event)"' +
                   ' placeholder="' + placeholder + '" maxlength="10"' +
                   ' autocomplete="off"' + disabled + '>' +
            '<button type="button" class="nss-dp-icon" @click="open = !open" tabindex="-1">' +
                NSS_CAL_ICON_SVG +
            '</button>' +
        '</div>' +
        '<div x-show="open" x-cloak class="nss-cal-popup" @click.outside="open = false" x-transition>' +
            '<div class="nss-cal-header">' +
                '<button type="button" @click="prevMonth()" class="nss-cal-nav">&lsaquo;</button>' +
                '<div class="nss-cal-selectors">' +
                    '<select class="nss-cal-select" :value="viewMonth" @change="onMonthChange($event)">' +
                        NSS_DP_MONTH_OPTIONS +
                    '</select>' +
                    '<input type="number" class="nss-cal-year" min="1930" max="2100"' +
                           ' :value="viewYear" @input="onYearInput($event)">' +
                '</div>' +
                '<button type="button" @click="nextMonth()" class="nss-cal-nav">&rsaquo;</button>' +
            '</div>' +
            '<div class="nss-cal-weekdays">' +
                '<template x-for="d in [\'Su\',\'Mo\',\'Tu\',\'We\',\'Th\',\'Fr\',\'Sa\']">' +
                    '<span x-text="d"></span>' +
                '</template>' +
            '</div>' +
            '<div class="nss-cal-days">' +
                '<template x-for="b in calBlanks" :key="\'b\'+b"><span></span></template>' +
                '<template x-for="day in calDays" :key="\'d\'+day">' +
                    '<button type="button" class="nss-cal-day"' +
                            ' :class="{ \'nss-cal-today\': isToday(day), \'nss-cal-selected\': isSelected(day) }"' +
                            ' @click="selectDay(day)" x-text="day"></button>' +
                '</template>' +
            '</div>' +
            '<div class="nss-cal-footer">' +
                '<button type="button" class="nss-cal-today-btn" @click="goToday()">Today</button>' +
                '<button type="button" class="nss-cal-clear" @click="clearDate()">Clear</button>' +
            '</div>' +
        '</div>' +
        '<div class="nss-dp-error" x-show="invalid" x-cloak x-text="errorMsg"></div>';
}

/**
 * Expand every nssDatePicker root in `scope` with the shared markup.
 * Idempotent — a root already carrying data-nss-dp-built is skipped,
 * so this is safe to re-run after injecting dynamic HTML.
 *
 * Also stamps data-nss-dp="<modelPath>" on the root, giving tests and
 * other code a stable hook that does not depend on the exact x-data
 * argument spelling.
 */
function nssDatePickerExpand(scope) {
    scope = scope || document;

    var nodes = scope.querySelectorAll('[x-data^="nssDatePicker("]');
    for (var i = 0; i < nodes.length; i++) {
        var node = nodes[i];
        if (node.hasAttribute("data-nss-dp-built")) continue;

        // Stable hook: the model path this picker writes to.
        var match = /nssDatePicker\(\s*['"]([^'"]+)['"]/.exec(
            node.getAttribute("x-data") || ""
        );
        if (match) node.setAttribute("data-nss-dp", match[1]);

        // The popup is absolutely positioned against this root.
        if (!node.style.position) node.style.position = "relative";

        node.insertAdjacentHTML("beforeend", nssDatePickerMarkup({
            inputClass: node.getAttribute("data-dp-input-class"),
            disabledExpr: node.getAttribute("data-dp-disabled"),
            placeholder: node.getAttribute("data-dp-placeholder"),
        }));

        node.setAttribute("data-nss-dp-built", "");
    }

    // Nine of ten date fields live inside Alpine <template x-if/x-for>
    // blocks. querySelectorAll does NOT descend into template content,
    // so recurse explicitly. Expanding the template's content fragment
    // before Alpine starts means every clone Alpine stamps out already
    // carries the calendar markup.
    var tpls = scope.querySelectorAll("template");
    for (var t = 0; t < tpls.length; t++) {
        if (tpls[t].content) nssDatePickerExpand(tpls[t].content);
    }
}

// Runs before Alpine.start() — see the block comment above.
document.addEventListener("DOMContentLoaded", function () {
    nssDatePickerExpand(document);
});
