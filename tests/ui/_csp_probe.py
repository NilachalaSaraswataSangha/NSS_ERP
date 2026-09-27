"""
Throwaway CSP probe — loads each public page in Chromium and reports any
Content-Security-Policy violation or console error. Not part of the suite.

Run against a live server:  python3 tests/ui/_csp_probe.py
"""

import sys

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8001"
PAGES = [
    "/", "/login", "/register", "/dashboard", "/admin", "/family",
]


def main() -> int:
    problems = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for path in PAGES:
            page = browser.new_page()
            msgs = []
            page.on("console", lambda m: msgs.append((m.type, m.text)))
            page.on("pageerror", lambda e: msgs.append(("pageerror", str(e))))
            try:
                page.goto(f"{BASE}{path}", wait_until="networkidle", timeout=20000)
                page.wait_for_timeout(1500)
                # Alpine must have booted for anything on these pages to work.
                alpine = page.evaluate("() => typeof window.Alpine !== 'undefined'")
                if not alpine:
                    problems.append(f"{path}: Alpine did not load")
            except Exception as exc:  # noqa: BLE001
                problems.append(f"{path}: navigation failed: {exc}")

            for kind, text in msgs:
                low = text.lower()
                if "content security policy" in low or "refused to" in low:
                    problems.append(f"{path}: CSP VIOLATION: {text}")
                elif kind in ("error", "pageerror"):
                    problems.append(f"{path}: {kind}: {text}")
            page.close()
        browser.close()

    if problems:
        print("PROBLEMS:")
        for item in problems:
            print(f"  - {item}")
        return 1
    print(f"OK — {len(PAGES)} pages loaded, Alpine booted, no CSP violations.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
