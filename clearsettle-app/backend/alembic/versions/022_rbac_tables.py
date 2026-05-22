"""Create DB-backed RBAC tables (roles, permissions, role_permissions) with seed data.

Revision ID: 022
Revises: 021
Create Date: 2026-05-22

Moves all role/permission definitions out of Python code and into the database.
Existing user.role string column stays — it maps to the roles.name column here.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── roles ─────────────────────────────────────────────────────────────────
    op.create_table(
        "roles",
        sa.Column("id",          sa.Integer,     primary_key=True, autoincrement=True),
        sa.Column("name",        sa.String(50),  nullable=False),
        sa.Column("description", sa.Text,        nullable=True),
        sa.Column("is_active",   sa.Boolean,     nullable=False, server_default="true"),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_roles_name", "roles", ["name"], unique=True)

    # ── permissions ───────────────────────────────────────────────────────────
    op.create_table(
        "permissions",
        sa.Column("id",          sa.Integer,      primary_key=True, autoincrement=True),
        sa.Column("name",        sa.String(100),  nullable=False),
        sa.Column("description", sa.Text,         nullable=True),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_permissions_name", "permissions", ["name"], unique=True)

    # ── role_permissions ──────────────────────────────────────────────────────
    op.create_table(
        "role_permissions",
        sa.Column("role_id",       sa.Integer, sa.ForeignKey("roles.id",       ondelete="CASCADE"), nullable=False),
        sa.Column("permission_id", sa.Integer, sa.ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
    )
    op.create_index("ix_role_permissions_role_id", "role_permissions", ["role_id"])

    # ── seed roles ────────────────────────────────────────────────────────────
    op.execute(text("""
        INSERT INTO roles (name, description) VALUES
        ('admin',      'Internal admin with full platform access'),
        ('superadmin', 'ClearSettle super administrator'),
        ('member',     'Team member with operational access'),
        ('finance',    'Finance team — read-only financial views'),
        ('ca',         'Chartered accountant — read-only access'),
        ('viewer',     'Read-only viewer'),
        ('seller',     'Public seller — sees only own data')
    """))

    # ── seed permissions ──────────────────────────────────────────────────────
    op.execute(text("""
        INSERT INTO permissions (name, description) VALUES
        ('dashboard:read',             'View dashboard'),
        ('analytics:read',             'View analytics and reports'),
        ('settlements:read',           'View settlements'),
        ('settlements:dispute',        'Raise settlement disputes'),
        ('reconciliation:read',        'View reconciliation reports'),
        ('reconciliation:run',         'Run reconciliation engine'),
        ('reconciliation:resolve',     'Resolve reconciliation issues'),
        ('reconciliation:rules:read',  'View reconciliation rules'),
        ('reconciliation:rules:write', 'Edit reconciliation rules'),
        ('reconciliation:seed',        'Seed reconciliation test data'),
        ('platforms:read',             'View platform connections'),
        ('platforms:write',            'Manage platform connections'),
        ('sync:read',                  'View sync jobs'),
        ('sync:trigger',               'Trigger platform sync'),
        ('reports:read',               'Download reports'),
        ('disputes:read',              'View disputes'),
        ('disputes:write',             'Create and manage disputes'),
        ('admin:users',                'Manage user accounts'),
        ('admin:roles',                'Manage roles and permissions'),
        ('rules:read',                 'View rule engine'),
        ('rules:write',                'Edit rules'),
        ('rules:test',                 'Test rules against data'),
        ('onboarding:read',            'View onboarding flow'),
        ('onboarding:write',           'Complete onboarding steps')
    """))

    # ── seed role_permissions via JOIN (avoids hardcoded IDs) ─────────────────
    op.execute(text("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        JOIN permissions p ON (
            (r.name = 'admin' AND p.name IN (
                'dashboard:read','analytics:read','settlements:read','settlements:dispute',
                'reconciliation:read','reconciliation:run','reconciliation:resolve',
                'reconciliation:rules:read','reconciliation:rules:write','reconciliation:seed',
                'platforms:read','platforms:write','sync:read','sync:trigger',
                'reports:read','disputes:read','disputes:write',
                'admin:users','admin:roles',
                'rules:read','rules:write','rules:test',
                'onboarding:read','onboarding:write'
            ))
            OR (r.name = 'superadmin' AND p.name IN (
                'admin:users','admin:roles',
                'dashboard:read','analytics:read'
            ))
            OR (r.name = 'member' AND p.name IN (
                'dashboard:read','analytics:read','settlements:read','settlements:dispute',
                'reconciliation:read','reconciliation:run','reconciliation:resolve',
                'reconciliation:rules:read',
                'platforms:read','sync:read','sync:trigger',
                'reports:read','disputes:read','disputes:write',
                'rules:read','rules:test',
                'onboarding:read','onboarding:write'
            ))
            OR (r.name = 'finance' AND p.name IN (
                'dashboard:read','analytics:read','settlements:read',
                'reconciliation:read','reconciliation:rules:read',
                'reports:read','disputes:read',
                'rules:read','onboarding:read'
            ))
            OR (r.name = 'ca' AND p.name IN (
                'dashboard:read','analytics:read','settlements:read',
                'reconciliation:read','reconciliation:rules:read',
                'reports:read','disputes:read',
                'rules:read'
            ))
            OR (r.name = 'viewer' AND p.name IN (
                'settlements:read'
            ))
            OR (r.name = 'seller' AND p.name IN (
                'dashboard:read','analytics:read','settlements:read','settlements:dispute',
                'reconciliation:read','reconciliation:run','reconciliation:resolve',
                'reconciliation:rules:read','reconciliation:rules:write',
                'platforms:read','platforms:write','sync:read','sync:trigger',
                'reports:read','disputes:read','disputes:write',
                'rules:read','rules:test',
                'onboarding:read','onboarding:write'
            ))
        )
    """))


def downgrade() -> None:
    op.drop_index("ix_role_permissions_role_id", "role_permissions")
    op.drop_table("role_permissions")
    op.drop_index("ix_permissions_name", "permissions")
    op.drop_table("permissions")
    op.drop_index("ix_roles_name", "roles")
    op.drop_table("roles")
