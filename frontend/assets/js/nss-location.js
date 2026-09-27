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
 *       arrays: {                         // where to store fetched lists
 *           countries: 'regCountries',
 *           states:    'regStates',
 *           districts: 'regDistricts',
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
 */

const NSSLocation = {
    /**
     * Create a location cascade instance.
     * @param {Object} opts
     * @param {Function} opts.fetchFn - fetch or NSSAuth.apiFetch
     * @param {Object} opts.arrays - map of { countries, states, districts, postalCodes } → Alpine property names
     * @param {string} opts.form - name of the form object property on the Alpine component
     * @returns {Object} cascade methods
     */
    create(opts) {
        const { fetchFn, arrays, form } = opts;

        return {
            async loadCountries(ctx) {
                try {
                    const res = await fetchFn("/api/v1/foundation/countries");
                    if (res.ok) ctx[arrays.countries] = await res.json();
                } catch (_) {}
            },

            async loadStates(ctx, countryPk) {
                ctx[arrays.states] = [];
                ctx[arrays.districts] = [];
                ctx[arrays.postalCodes] = [];
                if (!countryPk) return;
                try {
                    const res = await fetchFn(`/api/v1/foundation/states?country_pk=${countryPk}`);
                    if (res.ok) ctx[arrays.states] = await res.json();
                } catch (_) {}
            },

            async loadDistricts(ctx, statePk) {
                ctx[arrays.districts] = [];
                if (!statePk) return;
                try {
                    const res = await fetchFn(`/api/v1/foundation/districts?state_pk=${statePk}`);
                    if (res.ok) ctx[arrays.districts] = await res.json();
                } catch (_) {}
            },

            async loadPostalCodes(ctx, statePk) {
                ctx[arrays.postalCodes] = [];
                if (!statePk) return;
                try {
                    const res = await fetchFn(`/api/v1/foundation/postal-codes?state_pk=${statePk}`);
                    if (res.ok) ctx[arrays.postalCodes] = await res.json();
                } catch (_) {}
            },

            onCountryChange(ctx) {
                const f = ctx[form];
                f.state_pk = "";
                f.district_pk = "";
                f.city_village_name = "";
                f.postal_code_pk = "";
                ctx[arrays.states] = [];
                ctx[arrays.districts] = [];
                ctx[arrays.postalCodes] = [];
                if (f.country_pk) this.loadStates(ctx, f.country_pk);
            },

            onStateChange(ctx) {
                const f = ctx[form];
                f.district_pk = "";
                f.city_village_name = "";
                f.postal_code_pk = "";
                ctx[arrays.districts] = [];
                ctx[arrays.postalCodes] = [];
                if (f.state_pk) {
                    this.loadDistricts(ctx, f.state_pk);
                    this.loadPostalCodes(ctx, f.state_pk);
                }
            },

            onDistrictChange(ctx) {
                ctx[form].city_village_name = "";
            },
        };
    },
};
