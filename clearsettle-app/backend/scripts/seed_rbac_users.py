"""
Truncate all user/company data and seed one user per RBAC role.
Run inside the backend container:
    python scripts/seed_rbac_users.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.security import hash_password

PASSWORD = "Admin@12345"

# role → (display name, company name)
USERS = [
    ("admin",                  "Admin User",                "ClearSettle Admin"),
    ("superadmin",             "Super Admin",               "ClearSettle Platform"),
    ("company_admin",          "Company Admin",             "Demo Company Pvt Ltd"),
    ("business_owner",         "Business Owner",            "Demo Business Co"),
    ("finance_manager",        "Finance Manager",           "Demo Finance Ltd"),
    ("accountant",             "Staff Accountant",          "Demo Accounting Firm"),
    ("reconciliation_analyst", "Recon Analyst",             "Demo Analytics Co"),
    ("gst_consultant",         "GST Consultant",            "Demo GST Services"),
    ("auditor",                "Internal Auditor",          "Demo Audit Firm"),
    ("ca_admin",               "CA Admin",                  "Demo CA Firm"),
    ("ca_reviewer",            "CA Reviewer",               "Demo CA Firm"),
    ("ca_staff",               "CA Staff",                  "Demo CA Firm"),
    ("ca_viewer",              "CA Viewer",                 "Demo CA Firm"),
    ("branch_manager",         "Branch Manager",            "Demo Retail Chain"),
    ("branch_accountant",      "Branch Accountant",         "Demo Retail Chain"),
    ("branch_viewer",          "Branch Viewer",             "Demo Retail Chain"),
]

TRUNCATE_SQL = """
TRUNCATE TABLE
    audit_logs,
    user_permissions,
    user_roles,
    branch_users,
    branches,
    refresh_tokens,
    email_verifications,
    password_resets,
    marketplace_connections,
    flipkart_reports,
    report_rows,
    reconciliation_runs,
    reconciliation_results,
    settlements,
    disputes,
    gst_entries,
    companies,
    users
RESTART IDENTITY CASCADE;
"""

async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        print("Truncating all tables...")
        # Run truncate — some tables may not exist yet, so do them individually
        tables_to_clear = [
            "audit_logs", "user_permissions", "user_roles", "branch_users", "branches",
            "refresh_tokens", "email_verifications", "password_resets",
            "marketplace_connections", "flipkart_reports", "report_rows",
            "reconciliation_runs", "reconciliation_results", "settlements",
            "disputes", "gst_entries", "companies", "users",
        ]
        for table in tables_to_clear:
            try:
                await db.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
                print(f"  ✓ {table}")
            except Exception as e:
                print(f"  ⚠ {table}: {e} (skipping)")
                await db.rollback()

        await db.commit()
        print("\nSeeding RBAC users...")

        hashed = hash_password(PASSWORD)

        for role, name, company_name in USERS:
            email = f"{role.replace('_', '.')}@clearsettle.com"
            # Special case for admin
            if role == "admin":
                email = "admin@clearsettle.com"
            elif role == "superadmin":
                email = "superadmin@clearsettle.com"

            try:
                # Insert user
                result = await db.execute(text("""
                    INSERT INTO users (email, hashed_password, name, role, is_active, email_verified, is_superadmin)
                    VALUES (:email, :pwd, :name, :role, true, true, :is_super)
                    RETURNING id
                """), {
                    "email": email,
                    "pwd": hashed,
                    "name": name,
                    "role": role,
                    "is_super": role == "superadmin",
                })
                user_id = result.scalar_one()

                # Insert company
                await db.execute(text("""
                    INSERT INTO companies (user_id, name, gstin, state, city, registration_completed)
                    VALUES (:uid, :cname, NULL, 'Tamil Nadu', 'Chennai', true)
                """), {"uid": user_id, "cname": company_name})

                print(f"  ✓ {email} [{role}]")
            except Exception as e:
                print(f"  ✗ {email}: {e}")
                await db.rollback()
                continue

        await db.commit()
        print(f"\nDone! Password for all users: {PASSWORD}")
        print("\nUser list:")
        print(f"  {'EMAIL':<42} ROLE")
        print(f"  {'-'*42} {'-'*25}")
        for role, name, _ in USERS:
            email = "admin@clearsettle.com" if role == "admin" else \
                    "superadmin@clearsettle.com" if role == "superadmin" else \
                    f"{role.replace('_', '.')}@clearsettle.com"
            print(f"  {email:<42} {role}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
