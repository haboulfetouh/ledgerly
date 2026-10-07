"""Operator CLI for actions that don't yet have a self-service UI.

Usage (inside the backend container):
    python -m app.cli bootstrap-tenant --name "Al Marsa Retail Group" --slug al-marsa \\
        --admin-email admin@almarsa.example --admin-password "ChangeMe123!"

    python -m app.cli bootstrap-platform-admin \\
        --email platform@ledgerly.internal --password "ChangeMe123!"
"""

from __future__ import annotations

import argparse
import sys

from app.db.session import SessionLocal
from app.services.auth.keycloak_admin import KeycloakAdminClient
from app.services.tenants.onboarding import onboard_tenant, slugify


def bootstrap_tenant(name: str, slug: str | None, admin_email: str, admin_password: str) -> None:
    db = SessionLocal()
    try:
        tenant = onboard_tenant(
            db,
            name=name,
            slug=slug or slugify(name),
            admin_email=admin_email,
            admin_password=admin_password,
        )
        print(f"Tenant created: id={tenant.id} name={tenant.name!r} slug={tenant.slug!r}")
        print(f"Admin user provisioned in Keycloak: {admin_email}")
        print(f"Workspace: /t/{tenant.slug}/login")
    finally:
        db.close()


def bootstrap_platform_admin(email: str, password: str) -> None:
    KeycloakAdminClient().create_platform_admin(email=email, password=password)
    print(f"Platform admin provisioned in Keycloak: {email}")
    print("Log in at /platform/login with these credentials.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="ledgerly-cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    bootstrap = subparsers.add_parser(
        "bootstrap-tenant", help="Create a new tenant and its first admin user"
    )
    bootstrap.add_argument("--name", required=True, help="Tenant/organization display name")
    bootstrap.add_argument("--slug", required=False, help="URL slug (defaults to a slugified name)")
    bootstrap.add_argument("--admin-email", required=True)
    bootstrap.add_argument("--admin-password", required=True)

    platform_admin = subparsers.add_parser(
        "bootstrap-platform-admin", help="Create the first platform_admin user (not tied to any tenant)"
    )
    platform_admin.add_argument("--email", required=True)
    platform_admin.add_argument("--password", required=True)

    args = parser.parse_args()

    if args.command == "bootstrap-tenant":
        bootstrap_tenant(args.name, args.slug, args.admin_email, args.admin_password)
    elif args.command == "bootstrap-platform-admin":
        bootstrap_platform_admin(args.email, args.password)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
