"""
NSS ERP — Bootstrap the NSS Admin superuser account.

Executes the SQL seed (database/seed/04_admin/01_admin_bootstrap.sql)
with the password hash generated at runtime using the app's own
Argon2 hasher. No hardcoded hashes.

The seed file is the single source of truth for what the admin account
looks like (person P1, sangha_sevi SS1, user_account, password_history,
NSS_ERP_ADMIN role, NSS-WIDE scope). This script only supplies the one
value SQL cannot produce on its own — the Argon2 password_hash, bound to
the file's `%(password_hash)s` placeholder — and runs the file in a single
transaction. Keep all schema/seed logic in the .sql file, not here.

Usage:
    python3 scripts/bootstrap_admin.py
    python3 scripts/bootstrap_admin.py --password MyCustomPass1

Default password: Admin@123  (force_password_change = FALSE)

Prerequisites:
    - Tier 0-4 DDL + seed data already applied
    - Authentication + Administration DDL applied; nss_db_writer granted
    - api/.env configured with DB credentials

Authority: SOL-AUTH-006, Tier 5 decisions
"""

import argparse
import sys
from pathlib import Path

# Ensure the project root is on sys.path so `api.*` imports resolve
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.services.auth_service import hash_password
from api.database import get_write_pool

DEFAULT_PASSWORD = "Admin@123"

# Single source of truth: the SQL seed file. It carries the full account
# definition and one bind parameter, %(password_hash)s, which we supply
# at runtime. Do not duplicate the SQL here.
SEED_FILE = PROJECT_ROOT / "database" / "seed" / "04_admin" / "01_admin_bootstrap.sql"


def main():
    parser = argparse.ArgumentParser(
        description="Bootstrap the NSS Admin superuser account."
    )
    parser.add_argument(
        "--password",
        default=DEFAULT_PASSWORD,
        help=f"Admin password (default: {DEFAULT_PASSWORD})",
    )
    args = parser.parse_args()

    password = args.password
    pw_hash = hash_password(password)

    if not SEED_FILE.is_file():
        print(f"\nError: seed file not found: {SEED_FILE}", file=sys.stderr)
        sys.exit(1)
    seed_sql = SEED_FILE.read_text()

    print("Bootstrapping NSS Admin account...")
    print(f"  Seed file: {SEED_FILE.relative_to(PROJECT_ROOT)}")
    print("  Login ID : SS1 (or P1)")
    print(f"  Password : {'(custom)' if password != DEFAULT_PASSWORD else DEFAULT_PASSWORD}")
    print("  Hash algo: argon2id (runtime-generated)")
    print()

    pool = get_write_pool()
    conn = pool.getconn()
    try:
        conn.autocommit = False
        with conn.cursor() as cur:
            # The seed is a multi-statement script with a single
            # %(password_hash)s placeholder; psycopg2 runs the whole
            # script in one transaction and binds the one parameter.
            print("  Executing seed (person, sangha_sevi, user_account, "
                  "password_history, role, scope)...")
            cur.execute(seed_sql, {"password_hash": pw_hash})

        conn.commit()
        print()
        print("Done. NSS Admin account is ready.")
        print("*** Change this password before using beyond local dev. ***")

    except Exception as e:
        conn.rollback()
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        pool.putconn(conn)


if __name__ == "__main__":
    main()
