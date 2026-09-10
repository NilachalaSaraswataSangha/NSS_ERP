/**
 * NSS ERP — Tier 1 Foundation Verification UI
 *
 * Alpine.js data component. Fetches from /api/v1/foundation/* endpoints.
 * No authentication. Read-only verification.
 *
 * Sections:
 *   1. Master Data (categories + values with category filter)
 *   2. System Settings
 *   3. ID Sequences (infrastructure — current_value excluded)
 *   4. Geographic (country → state → district → city/village + postal codes)
 *   5. Documents (runtime, empty at launch)
 *
 * field_change_log is not exposed in Tier 1 — audit data requires
 * authentication (deferred to Tier 5).
 */

const FND_API = "/api/v1/foundation";

function foundationApp() {
    return {
        // Active tab
        activeTab: "master",

        // Health (reuse bootstrap endpoint)
        health: { loading: true, connected: false },

        // ── Master Data ──────────────────────────────────────────────
        categories: [],
        categoriesLoading: true,
        categoriesError: false,

        masterData: [],
        masterDataLoading: false,
        masterDataError: false,
        selectedCategoryCode: "",  // filter dropdown

        // ── System Settings ──────────────────────────────────────────
        settings: [],
        settingsLoading: true,
        settingsError: false,

        // ── ID Sequences ─────────────────────────────────────────────
        sequences: [],
        sequencesLoading: true,
        sequencesError: false,

        // ── Geographic ───────────────────────────────────────────────
        countries: [],
        countriesLoading: true,
        countriesError: false,

        states: [],
        statesLoading: false,
        statesError: false,
        selectedCountry: null,

        districts: [],
        districtsLoading: false,
        districtsError: false,
        selectedState: null,

        cities: [],
        citiesLoading: false,
        citiesError: false,
        selectedDistrict: null,

        postalCodes: [],
        postalCodesLoading: false,
        postalCodesError: false,

        // ── Runtime Tables ───────────────────────────────────────────
        documents: [],
        documentsLoading: true,
        documentsError: false,

        // ── Init ─────────────────────────────────────────────────────

        async init() {
            await this.fetchHealth();
            // Load data for the default tab
            await this.loadMasterTab();
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

        // ── Tab switching ────────────────────────────────────────────

        async switchTab(tab) {
            this.activeTab = tab;
            if (tab === "master") await this.loadMasterTab();
            else if (tab === "config") await this.loadConfigTab();
            else if (tab === "geo") await this.loadGeoTab();
            else if (tab === "runtime") await this.loadRuntimeTab();
        },

        async loadMasterTab() {
            if (this.categories.length === 0) await this.fetchCategories();
            if (this.masterData.length === 0) await this.fetchMasterData();
        },

        async loadConfigTab() {
            if (this.settings.length === 0) await this.fetchSettings();
            if (this.sequences.length === 0) await this.fetchSequences();
        },

        async loadGeoTab() {
            if (this.countries.length === 0) await this.fetchCountries();
        },

        async loadRuntimeTab() {
            if (!this._runtimeLoaded) {
                await this.fetchDocuments();
                this._runtimeLoaded = true;
            }
        },

        // ── Master Data fetchers ─────────────────────────────────────

        async fetchCategories() {
            this.categoriesLoading = true;
            this.categoriesError = false;
            try {
                const res = await fetch(`${FND_API}/categories`);
                if (!res.ok) throw new Error(res.statusText);
                this.categories = await res.json();
            } catch {
                this.categoriesError = true;
            } finally {
                this.categoriesLoading = false;
            }
        },

        async fetchMasterData(categoryCode) {
            this.masterDataLoading = true;
            this.masterDataError = false;
            try {
                let url = `${FND_API}/master-data`;
                if (categoryCode) url += `?category_code=${encodeURIComponent(categoryCode)}`;
                const res = await fetch(url);
                if (!res.ok) throw new Error(res.statusText);
                this.masterData = await res.json();
            } catch {
                this.masterDataError = true;
            } finally {
                this.masterDataLoading = false;
            }
        },

        async filterByCategory() {
            await this.fetchMasterData(this.selectedCategoryCode || null);
        },

        // ── System Config fetchers ───────────────────────────────────

        async fetchSettings() {
            this.settingsLoading = true;
            this.settingsError = false;
            try {
                const res = await fetch(`${FND_API}/settings`);
                if (!res.ok) throw new Error(res.statusText);
                this.settings = await res.json();
            } catch {
                this.settingsError = true;
            } finally {
                this.settingsLoading = false;
            }
        },

        async fetchSequences() {
            this.sequencesLoading = true;
            this.sequencesError = false;
            try {
                const res = await fetch(`${FND_API}/sequences`);
                if (!res.ok) throw new Error(res.statusText);
                this.sequences = await res.json();
            } catch {
                this.sequencesError = true;
            } finally {
                this.sequencesLoading = false;
            }
        },

        // ── Geographic fetchers ──────────────────────────────────────

        async fetchCountries() {
            this.countriesLoading = true;
            this.countriesError = false;
            try {
                const res = await fetch(`${FND_API}/countries`);
                if (!res.ok) throw new Error(res.statusText);
                this.countries = await res.json();
            } catch {
                this.countriesError = true;
            } finally {
                this.countriesLoading = false;
            }
        },

        async selectCountry(country) {
            if (this.selectedCountry?.country_pk === country.country_pk) {
                this.selectedCountry = null;
                this.states = [];
                this.selectedState = null;
                this.districts = [];
                this.selectedDistrict = null;
                this.cities = [];
                this.postalCodes = [];
                return;
            }
            this.selectedCountry = country;
            this.selectedState = null;
            this.districts = [];
            this.selectedDistrict = null;
            this.cities = [];

            this.statesLoading = true;
            this.statesError = false;
            try {
                const res = await fetch(`${FND_API}/states?country_pk=${country.country_pk}`);
                if (!res.ok) throw new Error(res.statusText);
                this.states = await res.json();
            } catch {
                this.statesError = true;
            } finally {
                this.statesLoading = false;
            }

            // Also load postal codes for this country
            this.postalCodesLoading = true;
            this.postalCodesError = false;
            try {
                const res = await fetch(`${FND_API}/postal-codes?country_pk=${country.country_pk}`);
                if (!res.ok) throw new Error(res.statusText);
                this.postalCodes = await res.json();
            } catch {
                this.postalCodesError = true;
            } finally {
                this.postalCodesLoading = false;
            }
        },

        async selectState(state) {
            if (this.selectedState?.state_pk === state.state_pk) {
                this.selectedState = null;
                this.districts = [];
                this.selectedDistrict = null;
                this.cities = [];
                return;
            }
            this.selectedState = state;
            this.selectedDistrict = null;
            this.cities = [];

            this.districtsLoading = true;
            this.districtsError = false;
            try {
                const res = await fetch(`${FND_API}/districts?state_pk=${state.state_pk}`);
                if (!res.ok) throw new Error(res.statusText);
                this.districts = await res.json();
            } catch {
                this.districtsError = true;
            } finally {
                this.districtsLoading = false;
            }
        },

        async selectDistrict(district) {
            if (this.selectedDistrict?.district_pk === district.district_pk) {
                this.selectedDistrict = null;
                this.cities = [];
                return;
            }
            this.selectedDistrict = district;

            this.citiesLoading = true;
            this.citiesError = false;
            try {
                const res = await fetch(`${FND_API}/cities?district_pk=${district.district_pk}`);
                if (!res.ok) throw new Error(res.statusText);
                this.cities = await res.json();
            } catch {
                this.citiesError = true;
            } finally {
                this.citiesLoading = false;
            }
        },

        // ── Runtime fetchers ─────────────────────────────────────────

        async fetchDocuments() {
            this.documentsLoading = true;
            this.documentsError = false;
            try {
                const res = await fetch(`${FND_API}/documents`);
                if (!res.ok) throw new Error(res.statusText);
                this.documents = await res.json();
            } catch {
                this.documentsError = true;
            } finally {
                this.documentsLoading = false;
            }
        },

        // ── Helpers ──────────────────────────────────────────────────

        get filteredMasterData() {
            if (!this.selectedCategoryCode) return this.masterData;
            return this.masterData.filter(
                d => d.category_code === this.selectedCategoryCode
            );
        },

        formatSample(seq) {
            const padded = "1".padStart(seq.padding_length, "0");
            return `${seq.prefix}${padded}`;
        },
    };
}
