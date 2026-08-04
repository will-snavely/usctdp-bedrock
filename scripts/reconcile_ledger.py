#!/usr/bin/env python3
"""
Read-only reconciliation report: finds usctdp_purchase rows with no matching
usctdp_ledger rows. Same query as `wp usctdp reconcile_ledger` (see
web/app/plugins/usctdp-mgmt/includes/cli/class-usctdp-reconcile-ledger.php),
but runnable from outside the container over a DB connection - e.g. an SSH
tunnel to production - so you can see the scope of the issue without
shelling into the box.

Deliberately does NOT write anything, and does NOT attempt to backfill.
Once you've reviewed the list here, run the backfill with:

    wp usctdp reconcile_ledger --fix

inside the container - that reuses the actual plugin/WooCommerce code (order
objects, pricing helpers) to compute the missing entries, rather than this
script reimplementing that logic in raw SQL from outside.

SETUP
-----
1. pip install pymysql
2. Open a tunnel to the DB (adjust host/user/ports for your setup):
       ssh -L 3307:127.0.0.1:3306 you@your-bastion-or-app-host
3. Run this script pointed at the tunnel's local port:
       python3 reconcile_ledger.py --host 127.0.0.1 --port 3307 \\
           --user wordpress --database wordpress

Connection args can also come from environment variables (useful if you
don't want the password on your shell history / in a script arg):
    DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, DB_PREFIX
CLI args always take precedence over env vars.
"""

import argparse
import getpass
import os
import sys

try:
    import pymysql
except ImportError:
    print("Missing dependency. Install it with: pip install pymysql", file=sys.stderr)
    sys.exit(1)


ORPHANED_PURCHASES_QUERY = """
    SELECT
        reg.id AS registration_id,
        reg.status AS registration_status,
        reg.activity_id AS activity_id,
        pur.id AS purchase_id,
        pur.type AS purchase_type,
        pur.tracking_id AS tracking_id,
        pur.created_at AS purchase_created_at,
        pur.family_id AS family_id,
        stud.id AS student_id,
        stud.first AS student_first,
        stud.last AS student_last,
        act.title AS activity_title,
        act.product_id AS product_id
    FROM {prefix}usctdp_registration AS reg
    JOIN {prefix}usctdp_purchase AS pur ON pur.id = reg.purchase_id
    JOIN {prefix}usctdp_student AS stud ON stud.id = reg.student_id
    JOIN {prefix}usctdp_activity AS act ON act.id = reg.activity_id
    WHERE reg.purchase_id > 0
    AND NOT EXISTS (
        SELECT 1 FROM {prefix}usctdp_ledger AS led
        WHERE led.purchase_id = reg.purchase_id
    )
    ORDER BY reg.id ASC
"""


def parse_args():
    parser = argparse.ArgumentParser(
        description="Report purchases with no matching ledger entries (read-only).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--host", default=os.environ.get("DB_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("DB_PORT", "3306")))
    parser.add_argument("--user", default=os.environ.get("DB_USER"))
    parser.add_argument("--password", default=os.environ.get("DB_PASSWORD"))
    parser.add_argument("--database", default=os.environ.get("DB_NAME"))
    parser.add_argument(
        "--prefix",
        default=os.environ.get("DB_PREFIX", "wp_"),
        help="WordPress table prefix (default: wp_, or $DB_PREFIX).",
    )
    parser.add_argument(
        "--ssl-disabled",
        action="store_true",
        help="Disable TLS for the connection (e.g. for a plain SSH-tunneled localhost connection).",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if not args.user:
        args.user = input("DB user: ")
    if not args.database:
        args.database = input("DB name: ")
    if args.password is None:
        args.password = getpass.getpass(f"DB password for {args.user}@{args.host}:{args.port}: ")

    connect_kwargs = dict(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database,
        cursorclass=pymysql.cursors.DictCursor,
        # Read-only intent: this connection should never write anything.
        autocommit=True,
    )
    if args.ssl_disabled:
        connect_kwargs["ssl"] = None

    try:
        conn = pymysql.connect(**connect_kwargs)
    except pymysql.err.OperationalError as e:
        print(f"Could not connect to the database: {e}", file=sys.stderr)
        print(
            "If you're going through an SSH tunnel, make sure it's still open "
            "and --host/--port point at the tunnel's local end.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        with conn.cursor() as cursor:
            cursor.execute(ORPHANED_PURCHASES_QUERY.format(prefix=args.prefix))
            rows = cursor.fetchall()
    finally:
        conn.close()

    if not rows:
        print("No orphaned purchases found - every purchase has matching ledger entries.")
        return

    print(f"Found {len(rows)} purchase(s) with no ledger entries:\n")
    for row in rows:
        student_name = f"{row['student_first']} {row['student_last']}".strip()
        tracking_id = row["tracking_id"] or "(none)"
        print(
            f"registration #{row['registration_id']} | "
            f"purchase #{row['purchase_id']} ({row['purchase_type']}) | "
            f"{student_name} | {row['activity_title']} | "
            f"tracking_id={tracking_id} | created {row['purchase_created_at']}"
        )

    print(f"\n{len(rows)} orphaned purchase(s) found.")
    print("Review this list, then backfill with `wp usctdp reconcile_ledger --fix` inside the container.")


if __name__ == "__main__":
    main()
