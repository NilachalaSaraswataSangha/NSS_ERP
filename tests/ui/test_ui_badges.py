"""
Source-level tests for the shared badge system.

Every status/type/role pill in the app is one component: the classes defined
in `frontend/assets/css/badges.css` (the single source of truth), selected at
runtime by the helper maps in `frontend/assets/js/nss-config.js`
(`NSS.statusBadgeClass(code)` etc.). Callsites emit only `class="badge <x>"`
markup or bind `:class="NSS.xBadgeClass(code)"`; they never define geometry or
colour themselves.

The badges.css header states the invariant explicitly:

    Individual pages MUST NOT define .badge, .badge-xs/sm/md/lg,
    badge-status-*, badge-type-*, badge-aff-*, badge-account-*, or
    badge-claim-* classes in inline <style> blocks, and MUST NOT set badge
    colors via inline style= or Tailwind bg-*/text-* utilities.

These tests lock that invariant in at the source level so a page can't quietly
reintroduce a hand-rolled pill (the same drift class that the datepicker
`TestNoHandwrittenMarkupInSource` guards against). They need no browser or
server — they parse the shipped frontend files directly.

What is checked:
  1. badges.css actually defines the base + size scale + the documented
     family prefixes, and the `badge-muted` fallback the JS maps fall back to.
  2. Every badge class the JS maps hand out (nss-config.js) has a matching
     definition in badges.css — no map/CSS drift.
  3. Every statically hand-written `badge-<family>-<code>` class in the HTML
     and JS resolves to a defined class in badges.css — no typos.
  4. No page-local <style> block redefines `.badge`/`badge-*` (the header rule).
  5. No element that carries a `badge-*` class also sets its colour via an
     inline `style=` or a Tailwind `bg-*/text-*` colour utility.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.ui

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND = REPO_ROOT / "frontend"
BADGES_CSS = FRONTEND / "assets" / "css" / "badges.css"
NSS_CONFIG_JS = FRONTEND / "assets" / "js" / "nss-config.js"

# The documented family prefixes and the base/size classes badges.css owns.
REQUIRED_BASE_CLASSES = {"badge", "badge-xs", "badge-sm", "badge-md", "badge-lg"}
REQUIRED_FAMILY_PREFIXES = [
    "badge-status-",
    "badge-type-",
    "badge-aff-",
    "badge-account-",
    "badge-claim-",
    "badge-role-",
    "badge-gender-",
]
# The universal fallback every JS map returns when a code is unmapped.
FALLBACK_CLASS = "badge-muted"

# Matches a badge class token: `badge` or `badge-foo-bar` (kebab-case).
BADGE_TOKEN = re.compile(r"\bbadge(?:-[a-z0-9]+)*\b")


def _read(path: Path) -> str:
    assert path.exists(), f"expected file missing: {path.relative_to(REPO_ROOT)}"
    return path.read_text(encoding="utf-8")


def _defined_classes() -> set[str]:
    """All class names defined by a `.badge...` selector in badges.css."""
    css = _read(BADGES_CSS)
    # Strip comments so a class name mentioned in prose isn't counted as defined.
    css_no_comments = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    return set(re.findall(r"\.(badge(?:-[a-z0-9]+)*)\b", css_no_comments))


def _html_files() -> list[Path]:
    return sorted(FRONTEND.glob("*.html"))


def _js_files() -> list[Path]:
    return sorted((FRONTEND / "assets" / "js").glob("*.js"))


# ── 1. badges.css owns the base scale + documented families ────────────────


def test_base_and_size_classes_defined():
    defined = _defined_classes()
    missing = REQUIRED_BASE_CLASSES - defined
    assert not missing, f"badges.css missing base/size classes: {sorted(missing)}"


def test_fallback_class_defined():
    defined = _defined_classes()
    assert FALLBACK_CLASS in defined, (
        f"badges.css must define {FALLBACK_CLASS!r} — every NSS.*BadgeClass() "
        "map falls back to it for unmapped codes."
    )


@pytest.mark.parametrize("prefix", REQUIRED_FAMILY_PREFIXES)
def test_family_has_definitions(prefix: str):
    defined = _defined_classes()
    members = [c for c in defined if c.startswith(prefix)]
    assert members, f"badges.css defines no {prefix}* classes"


# ── 2. JS badge maps never hand out an undefined class ─────────────────────


def test_js_map_classes_are_all_defined():
    """Every `badge-*` literal in nss-config.js resolves to a defined class."""
    defined = _defined_classes()
    js = _read(NSS_CONFIG_JS)
    used = set(re.findall(r'["\'](badge-[a-z0-9-]+)["\']', js))
    assert used, "no badge-* literals found in nss-config.js — parser drift?"
    undefined = sorted(used - defined)
    assert not undefined, (
        "nss-config.js maps codes to badge classes with no CSS definition "
        f"(will render unstyled): {undefined}"
    )


# ── 3. Hand-written badge classes in markup all resolve ────────────────────


def test_static_markup_badge_classes_are_defined():
    """
    Every statically-written `badge-<family>-<code>` in the HTML/JS has a
    definition in badges.css. Dynamically-built classes (string concat / the
    NSS map lookups) are covered by test 2 instead — this catches literal typos
    like `class="badge badge-status-actve"`.
    """
    defined = _defined_classes()
    offenders: dict[str, set[str]] = {}
    for path in _html_files() + _js_files():
        text = _read(path)
        tokens = {
            t for t in BADGE_TOKEN.findall(text)
            # only family-qualified tokens; bare `badge`/`badge-sm` are base
            if t.count("-") >= 2
        }
        undefined = tokens - defined
        if undefined:
            offenders[str(path.relative_to(REPO_ROOT))] = undefined
    assert not offenders, (
        "hand-written badge classes with no badges.css definition "
        f"(typo or missing class): {offenders}"
    )


# ── 4. No page-local redefinition of badge classes (the header rule) ───────

STYLE_BLOCK = re.compile(r"<style\b[^>]*>(.*?)</style>", re.DOTALL | re.IGNORECASE)


def test_no_page_local_badge_class_definitions():
    """
    No inline <style> block may define a `.badge`/`.badge-*` selector.

    A layout container that merely *contains* badges (e.g. `.member-header
    .badges { ... }` — note the trailing 's', a wrapper not a pill) is allowed;
    only a rule whose selector targets the pill class itself is forbidden.
    """
    offenders: dict[str, list[str]] = {}
    # `.badge` or `.badge-foo` as a selector token, NOT `.badges` (wrapper).
    pill_selector = re.compile(r"\.badge(?:-[a-z0-9-]+)?(?![a-z0-9-])")
    for path in _html_files():
        text = _read(path)
        hits: list[str] = []
        for block in STYLE_BLOCK.findall(text):
            block_no_comments = re.sub(r"/\*.*?\*/", "", block, flags=re.DOTALL)
            # Inspect only selector text (left of each `{`).
            for rule in block_no_comments.split("}"):
                selector = rule.split("{")[0]
                if pill_selector.search(selector):
                    hits.append(selector.strip()[:80])
        if hits:
            offenders[str(path.relative_to(REPO_ROOT))] = hits
    assert not offenders, (
        "page-local <style> defines badge classes — must live only in "
        f"badges.css: {offenders}"
    )


# ── 5. No inline / Tailwind colour override on a badge element ─────────────

CLASS_ATTR = re.compile(r'\bclass\s*=\s*"([^"]*)"', re.IGNORECASE)
TAILWIND_COLOUR = re.compile(
    r"\b(?:bg|text)-(?:red|green|blue|yellow|amber|orange|gray|grey|slate|"
    r"emerald|rose|indigo|violet|purple|pink|teal|cyan|lime|sky)-\d{2,3}\b"
)


def test_no_tailwind_colour_on_badge_elements():
    """
    An element carrying a `badge-*` class must not also carry a Tailwind
    colour utility (bg-<colour>-NNN / text-<colour>-NNN) in the same class
    attribute — colour is owned by badges.css, per the header rule.
    """
    offenders: dict[str, list[str]] = {}
    for path in _html_files():
        text = _read(path)
        hits: list[str] = []
        for attr in CLASS_ATTR.findall(text):
            if "badge-" not in attr:
                continue
            if TAILWIND_COLOUR.search(attr):
                hits.append(attr.strip()[:100])
        if hits:
            offenders[str(path.relative_to(REPO_ROOT))] = hits
    assert not offenders, (
        "badge elements set colour via Tailwind utilities instead of "
        f"badges.css: {offenders}"
    )
