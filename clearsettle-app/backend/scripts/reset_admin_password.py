"""
Reset super-admin password via direct DB update.

Run inside the backend container on GCP:
  docker exec clearsettle-backend-prod python scripts/reset_admin_password.py

Or with a custom password:
  docker exec clearsettle-backend-prod python scripts/reset_admin_password.py --password "NewPassword@123"
"""
import argparse
import asyncio
import os
import sys

import bcrypt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def reset(email: str, new_password: str, database_url: str):
    engine = create_async_engine(database_url, echo=False)
    hashed = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")

    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT id, email, role FROM users WHERE email = :email AND deleted_at IS NULL"),
            {"email": email},
        )
        row = result.fetchone()
        if not row:
            print(f"[ERROR] No user found with email: {email}")
            sys.exit(1)

        await conn.execute(
            text("UPDATE users SET password_hash = :hash WHERE email = :email"),
            {"hash": hashed, "email": email},
        )

    print(f"[OK] Password reset for {email} (role={row.role})")
    print(f"     Bcrypt hash: {hashed[:30]}...")
    print(f"     New password: {new_password}")
    await engine.dispose()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email",    default=os.getenv("SUPER_ADMIN_EMAIL", "Admin@clearsettle.com"))
    parser.add_argument("--password", default=os.getenv("SUPER_ADMIN_PASSWORD", "Admin@12345"))
    args = parser.parse_args()

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("[ERROR] DATABASE_URL env var not set")
        sys.exit(1)

    asyncio.run(reset(args.email, args.password, db_url))


if __name__ == "__main__":
    main()
