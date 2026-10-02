/**
 * NSS ERP — Shared Location Cascade Utility
 *
 * Reusable helper for the country → state → district → postal code
 * cascading dropdown pattern. Used by register.js, admin.js (org edit
 * and org create) to eliminate three near-identical implementations.
 *
 * Usage:
 *   // In Alpine.js init():
 *   this._loc = NSSLocation.create({
 *       fetchFn: fetch,                   // or NSSAuth.apiFetch
 *       basePath: '/api/v1/foundation',   // optional — see below
 *       arrays: {                         // where to store fetched lists
 *           countries: 'regCountries',
 *           states:    'regStates',
 *           districts: 'regDistricts',
 *           cities:    'regCities',       // optional — omit to skip the
 *                                         // city/village dropdown entirely
 *           postalCodes: 'regPostalCodes',
 *       },
 *       form: 'form',                     // property name of the form object on `this`
 *   });
 *
 *   // Call from Alpine methods:
 *   this._loc.loadCountries(this);
 *   this._loc.onCountryChange(this);
 *
 * All methods take `ctx` (the Alpine component `this`) as the first
 * argument so the utility stays stateless and framework-agnostic.
 *
 * Design:
 *   - No global state; each instance is a config object
 *   - Works with both plain fetch() and NSSAuth.apiFetch()
 *   - Form field names are fixed: country_pk, state_pk, district_pk,
 *     city_village_name, postal_code_pk (matches DB column names)
 *   - basePath defaults to '/api/v1/foundation' (the authenticated
 *     Foundation endpoints admin.js uses). register.js instead passes
 *     '/api/v1/register', a set of unauthenticated endpoints that call the
 *     exact same shared query functions as Foundation's — see
 *     api/routers/registration.py — since the person filling out that page
 *     has no JWT yet.
 */

const NSSLocation = {
    /**
     * Create a location cascade instance.
     * @param {Object} opts
     * @param {Function} opts.fetchFn - fetch or NSSAuth.apiFetch
     * @param {string} [opts.basePath] - API prefix, default '/api/v1/foundation'
     * @param {Object} opts.arrays - map of { countries, states, districts, cities, postalCodes } → Alpine property names (cities optional)
     * @param {string} opts.form - name of the form object property on the Alpine component
     * @returns {Object} cascade methods
     */
    create(opts) {
        const { fetchFn, arrays, form } = opts;
        const basePath = opts.basePath || "/api/v1/foundation";

        return {
            async loadCountries(ctx) {
                try {
                    const res = await fetchFn(`${basePath}/countries`);
                    if (res.ok) ctx[arrays.countries] = await res.json();
                } catch (_) {}
            },

            async loadStates(ctx, countryPk) {
                ctx[arrays.states] = [];
                ctx[arrays.districts] = [];
                ctx[arrays.postalCodes] = [];
                if (!countryPk) return;
                try {
                    const res = await fetchFn(`${basePath}/states?country_pk=${countryPk}`);
                    if (res.ok) ctx[arrays.states] = await res.json();
                } catch (_) {}
            },

            async loadDistricts(ctx, statePk) {
                ctx[arrays.districts] = [];
                if (!statePk) return;
                try {
                    const res = await fetchFn(`${basePath}/districts?state_pk=${statePk}`);
                    if (res.ok) ctx[arrays.districts] = await res.json();
                } catch (_) {}
            },

            async loadCities(ctx, districtPk) {
                if (!arrays.cities) return; // consumer opted out of city/village dropdown
                ctx[arrays.cities] = [];
                if (!districtPk) return;
                try {
                    const res = await fetchFn(`${basePath}/cities?district_pk=${districtPk}`);
                    if (res.ok) ctx[arrays.cities] = await res.json();
                } catch (_) {}
            },

            async loadPostalCodes(ctx, statePk) {
                ctx[arrays.postalCodes] = [];
                if (!statePk) return;
                try {
                    const res = await fetchFn(`${basePath}/postal-codes?state_pk=${statePk}`);
                    if (res.ok) ctx[arrays.postalCodes] = await res.json();
                } catch (_) {}
            },

            onCountryChange(ctx) {
                const f = ctx[form];
                f.state_pk = "";
                f.district_pk = "";
                f.city_village_name = "";
                this._clearPostalCode(f);
                ctx[arrays.states] = [];
                ctx[arrays.districts] = [];
                ctx[arrays.postalCodes] = [];
                if (arrays.cities) ctx[arrays.cities] = [];
                if (f.country_pk) this.loadStates(ctx, f.country_pk);
            },

            onStateChange(ctx) {
                const f = ctx[form];
                f.district_pk = "";
                f.city_village_name = "";
                this._clearPostalCode(f);
                ctx[arrays.districts] = [];
                ctx[arrays.postalCodes] = [];
                if (arrays.cities) ctx[arrays.cities] = [];
                if (f.state_pk) {
                    this.loadDistricts(ctx, f.state_pk);
                    this.loadPostalCodes(ctx, f.state_pk);
                }
            },

            // A postal code is only valid within one state, so it must be
            // cleared whenever country/state changes. Both key names are
            // handled because the two consumers disagree: register.js and
            // admin.js both hold free text in `postal_code_value`, while
            // this module was originally written against a `postal_code_pk`
            // select that no form ever adopted. Clearing only
            // `postal_code_pk` was a silent no-op, so a PIN typed for one
            // state survived a switch to another and was submitted against
            // the wrong state.
            _clearPostalCode(f) {
                if ("postal_code_value" in f) f.postal_code_value = "";
                if ("postal_code_pk" in f) f.postal_code_pk = "";
            },

            onDistrictChange(ctx) {
                const f = ctx[form];
                f.city_village_name = "";
                if (arrays.cities) this.loadCities(ctx, f.district_pk);
            },
        };
    },
};
