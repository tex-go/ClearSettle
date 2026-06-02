"""Enterprise Multi-Tenant RBAC v2.

Extends the existing roles/permissions tables with:
- scope column on roles (system | tenant | branch | custom)
- module + action columns on permissions (module.action format)
- branches table (linked to companies/tenants)
- user_roles junction table (replaces single role string column)
- user_permissions table (direct per-user permission overrides)
- branch_users junction table
- Seed all enterprise roles and permissions

Revision ID: 034
Revises: 033
Create Date: 2026-06-02
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

revision = "034"
down_revision = "033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Extend roles table ────────────────────────────────────────────────────
    op.add_column("roles", sa.Column("scope", sa.String(20), nullable=False, server_default="tenant"))
    op.add_column("roles", sa.Column("is_custom", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("roles", sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=True))
    op.create_index("ix_roles_company_id", "roles", ["company_id"])

    # ── Extend permissions table ───────────────────────────────────────────────
    op.add_column("permissions", sa.Column("module", sa.String(50), nullable=True))
    op.add_column("permissions", sa.Column("action", sa.String(50), nullable=True))
    op.add_column("permissions", sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"))

    # ── branches table ────────────────────────────────────────────────────────
    op.create_table(
        "branches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("city", sa.String(100)),
        sa.Column("state", sa.String(100)),
        sa.Column("address", sa.Text()),
        sa.Column("gstin", sa.String(20)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_branches_company_id", "branches", ["company_id"])

    # ── user_roles junction table ─────────────────────────────────────────────
    op.create_table(
        "user_roles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role_id", sa.Integer(),
                  sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=True),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("branches.id", ondelete="CASCADE"), nullable=True),
        sa.Column("granted_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("granted_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("user_id", "role_id", "company_id"),
    )
    op.create_index("ix_user_roles_user_id", "user_roles", ["user_id"])
    op.create_index("ix_user_roles_role_id", "user_roles", ["role_id"])
    op.create_index("ix_user_roles_company_id", "user_roles", ["company_id"])

    # ── user_permissions table (direct overrides) ─────────────────────────────
    op.create_table(
        "user_permissions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("permission_id", sa.Integer(),
                  sa.ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=True),
        sa.Column("branch_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("branches.id", ondelete="CASCADE"), nullable=True),
        sa.Column("granted", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("granted_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("granted_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "permission_id", "company_id", name="uq_user_permissions"),
    )
    op.create_index("ix_user_permissions_user_id", "user_permissions", ["user_id"])

    # ── branch_users junction table ───────────────────────────────────────────
    op.create_table(
        "branch_users",
        sa.Column("branch_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("branches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("branch_id", "user_id"),
    )

    # ── Update existing roles with scope ──────────────────────────────────────
    op.execute(text("""
        UPDATE roles SET scope = 'system' WHERE name IN ('superadmin', 'admin')
    """))

    # ── Seed new enterprise roles ─────────────────────────────────────────────
    op.execute(text("""
        INSERT INTO roles (name, scope, description) VALUES
        ('company_admin',           'tenant',  'Company Administrator — full tenant access'),
        ('business_owner',          'tenant',  'Business Owner — view all, connect marketplaces'),
        ('finance_manager',         'tenant',  'Finance Manager — upload reports, run recon, manage disputes'),
        ('accountant',              'tenant',  'Accountant — upload reports, view recon, view GST'),
        ('reconciliation_analyst',  'tenant',  'Reconciliation Analyst — view reports, run reconciliation'),
        ('gst_consultant',          'tenant',  'GST Consultant — GST modules only'),
        ('auditor',                 'tenant',  'Auditor — read-only across all modules'),
        ('ca_admin',                'tenant',  'CA Admin — access all assigned client tenants'),
        ('ca_reviewer',             'tenant',  'CA Reviewer — review and comment on client data'),
        ('ca_staff',                'tenant',  'CA Staff — view assigned clients only'),
        ('ca_viewer',               'tenant',  'CA Viewer — read-only CA access'),
        ('branch_manager',          'branch',  'Branch Manager — manage assigned branch'),
        ('branch_accountant',       'branch',  'Branch Accountant — accounting for assigned branch'),
        ('branch_viewer',           'branch',  'Branch Viewer — read-only branch access')
        ON CONFLICT (name) DO NOTHING
    """))

    # ── Seed enterprise permissions (module.action format) ────────────────────
    op.execute(text("""
        INSERT INTO permissions (name, module, action, description) VALUES
        -- Dashboard
        ('dashboard.view',              'dashboard',        'view',       'View dashboard'),
        -- Reports
        ('reports.view',                'reports',          'view',       'View reports'),
        ('reports.upload',              'reports',          'upload',     'Upload reports'),
        ('reports.delete',              'reports',          'delete',     'Delete reports'),
        ('reports.download',            'reports',          'download',   'Download reports'),
        -- Reconciliation
        ('reconciliation.view',         'reconciliation',   'view',       'View reconciliation'),
        ('reconciliation.run',          'reconciliation',   'run',        'Run reconciliation engine'),
        ('reconciliation.export',       'reconciliation',   'export',     'Export reconciliation results'),
        -- Bank Reconciliation
        ('bank_reconciliation.view',    'bank_reconciliation', 'view',    'View bank reconciliation'),
        ('bank_reconciliation.run',     'bank_reconciliation', 'run',     'Run bank reconciliation'),
        -- Marketplace
        ('marketplace.view',            'marketplace',      'view',       'View marketplace connections'),
        ('marketplace.connect',         'marketplace',      'connect',    'Connect marketplace'),
        ('marketplace.disconnect',      'marketplace',      'disconnect', 'Disconnect marketplace'),
        ('marketplace.sync',            'marketplace',      'sync',       'Trigger marketplace sync'),
        -- Settlements
        ('settlements.view',            'settlements',      'view',       'View settlements'),
        ('settlements.export',          'settlements',      'export',     'Export settlements'),
        -- Disputes
        ('disputes.view',               'disputes',         'view',       'View disputes'),
        ('disputes.create',             'disputes',         'create',     'Create disputes'),
        ('disputes.update',             'disputes',         'update',     'Update disputes'),
        ('disputes.close',              'disputes',         'close',      'Close disputes'),
        -- GST
        ('gst.view',                    'gst',              'view',       'View GST module'),
        ('gst.file',                    'gst',              'file',       'File GST returns'),
        ('gst.export',                  'gst',              'export',     'Export GST data'),
        ('gstr1.view',                  'gst',              'gstr1_view', 'View GSTR-1'),
        ('gstr1.file',                  'gst',              'gstr1_file', 'File GSTR-1'),
        ('gstr3b.view',                 'gst',              'gstr3b_view','View GSTR-3B'),
        ('gstr3b.file',                 'gst',              'gstr3b_file','File GSTR-3B'),
        -- AI Insights
        ('ai.view',                     'ai',               'view',       'View AI insights'),
        ('ai.generate',                 'ai',               'generate',   'Generate AI analysis'),
        -- User Management
        ('users.view',                  'users',            'view',       'View users'),
        ('users.create',                'users',            'create',     'Create users'),
        ('users.update',                'users',            'update',     'Update users'),
        ('users.delete',                'users',            'delete',     'Delete users'),
        ('roles.assign',                'users',            'roles_assign','Assign roles to users'),
        -- Audit
        ('audit.view',                  'audit',            'view',       'View audit logs'),
        -- Subscription
        ('subscription.view',           'subscription',     'view',       'View subscription'),
        ('subscription.manage',         'subscription',     'manage',     'Manage subscription'),
        -- Settings
        ('settings.update',             'settings',         'update',     'Update company settings'),
        -- Notifications
        ('notifications.manage',        'notifications',    'manage',     'Manage notifications')
        ON CONFLICT (name) DO NOTHING
    """))

    # ── Assign permissions to new enterprise roles ────────────────────────────

    # company_admin — full tenant access
    op.execute(text("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r, permissions p
        WHERE r.name = 'company_admin'
        AND p.name IN (
            'dashboard.view',
            'reports.view','reports.upload','reports.delete','reports.download',
            'reconciliation.view','reconciliation.run','reconciliation.export',
            'bank_reconciliation.view','bank_reconciliation.run',
            'marketplace.view','marketplace.connect','marketplace.disconnect','marketplace.sync',
            'settlements.view','settlements.export',
            'disputes.view','disputes.create','disputes.update','disputes.close',
            'gst.view','gst.file','gst.export','gstr1.view','gstr1.file','gstr3b.view','gstr3b.file',
            'ai.view','ai.generate',
            'users.view','users.create','users.update','users.delete','roles.assign',
            'audit.view','subscription.view','subscription.manage','settings.update','notifications.manage'
        )
        ON CONFLICT DO NOTHING
    """))

    # business_owner — view everything + connect marketplaces
    op.execute(text("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r, permissions p
        WHERE r.name = 'business_owner'
        AND p.name IN (
            'dashboard.view',
            'reports.view','reports.download',
            'reconciliation.view','bank_reconciliation.view',
            'marketplace.view','marketplace.connect','marketplace.disconnect','marketplace.sync',
            'settlements.view','settlements.export',
            'disputes.view',
            'gst.view','gstr1.view','gstr3b.view',
            'ai.view','ai.generate',
            'users.view','audit.view','subscription.view','subscription.manage','settings.update'
        )
        ON CONFLICT DO NOTHING
    """))

    # finance_manager
    op.execute(text("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r, permissions p
        WHERE r.name = 'finance_manager'
        AND p.name IN (
            'dashboard.view',
            'reports.view','reports.upload','reports.download',
            'reconciliation.view','reconciliation.run','reconciliation.export',
            'bank_reconciliation.view','bank_reconciliation.run',
            'marketplace.view',
            'settlements.view','settlements.export',
            'disputes.view','disputes.create','disputes.update','disputes.close',
            'gst.view','gst.file','gst.export','gstr1.view','gstr1.file','gstr3b.view','gstr3b.file',
            'ai.view','users.view'
        )
        ON CONFLICT DO NOTHING
    """))

    # accountant
    op.execute(text("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r, permissions p
        WHERE r.name = 'accountant'
        AND p.name IN (
            'dashboard.view',
            'reports.view','reports.upload','reports.download',
            'reconciliation.view',
            'bank_reconciliation.view',
            'settlements.view',
            'disputes.view',
            'gst.view','gstr1.view','gstr3b.view',
            'ai.view'
        )
        ON CONFLICT DO NOTHING
    """))

    # reconciliation_analyst
    op.execute(text("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r, permissions p
        WHERE r.name = 'reconciliation_analyst'
        AND p.name IN (
            'dashboard.view',
            'reports.view','reports.download',
            'reconciliation.view','reconciliation.run','reconciliation.export',
            'bank_reconciliation.view','bank_reconciliation.run',
            'settlements.view',
            'disputes.view',
            'ai.view'
        )
        ON CONFLICT DO NOTHING
    """))

    # gst_consultant — GST only
    op.execute(text("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r, permissions p
        WHERE r.name = 'gst_consultant'
        AND p.name IN (
            'dashboard.view',
            'gst.view','gst.file','gst.export','gstr1.view','gstr1.file','gstr3b.view','gstr3b.file'
        )
        ON CONFLICT DO NOTHING
    """))

    # auditor — read-only
    op.execute(text("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r, permissions p
        WHERE r.name = 'auditor'
        AND p.name IN (
            'dashboard.view',
            'reports.view','reports.download',
            'reconciliation.view',
            'bank_reconciliation.view',
            'settlements.view',
            'disputes.view',
            'gst.view','gstr1.view','gstr3b.view',
            'ai.view','users.view','audit.view'
        )
        ON CONFLICT DO NOTHING
    """))

    # ca_admin — all tenant data access
    op.execute(text("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r, permissions p
        WHERE r.name = 'ca_admin'
        AND p.name IN (
            'dashboard.view',
            'reports.view','reports.download',
            'reconciliation.view','reconciliation.run','reconciliation.export',
            'bank_reconciliation.view','bank_reconciliation.run',
            'settlements.view','settlements.export',
            'disputes.view',
            'gst.view','gst.export','gstr1.view','gstr3b.view',
            'ai.view','users.view','audit.view'
        )
        ON CONFLICT DO NOTHING
    """))

    # ca_reviewer
    op.execute(text("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r, permissions p
        WHERE r.name = 'ca_reviewer'
        AND p.name IN (
            'dashboard.view',
            'reports.view','reports.download',
            'reconciliation.view',
            'settlements.view',
            'gst.view','gstr1.view','gstr3b.view'
        )
        ON CONFLICT DO NOTHING
    """))

    # ca_staff + ca_viewer + branch_* — minimal read
    for role_name, perms in [
        ("ca_staff",        ["dashboard.view","reports.view","reconciliation.view","settlements.view"]),
        ("ca_viewer",       ["dashboard.view","reports.view","settlements.view"]),
        ("branch_manager",  ["dashboard.view","reports.view","reports.upload","reports.download",
                             "reconciliation.view","reconciliation.run","settlements.view",
                             "disputes.view","disputes.create","disputes.update","users.view"]),
        ("branch_accountant",["dashboard.view","reports.view","reports.upload","reports.download",
                              "reconciliation.view","settlements.view","disputes.view","gst.view"]),
        ("branch_viewer",   ["dashboard.view","reports.view","settlements.view","disputes.view"]),
    ]:
        perm_list = "','".join(perms)
        op.execute(text(f"""
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id FROM roles r, permissions p
            WHERE r.name = '{role_name}'
            AND p.name IN ('{perm_list}')
            ON CONFLICT DO NOTHING
        """))


def downgrade() -> None:
    op.drop_table("branch_users")
    op.drop_table("user_permissions")
    op.drop_index("ix_user_roles_company_id", "user_roles")
    op.drop_index("ix_user_roles_role_id", "user_roles")
    op.drop_index("ix_user_roles_user_id", "user_roles")
    op.drop_table("user_roles")
    op.drop_index("ix_branches_company_id", "branches")
    op.drop_table("branches")
    op.drop_column("permissions", "is_active")
    op.drop_column("permissions", "action")
    op.drop_column("permissions", "module")
    op.drop_index("ix_roles_company_id", "roles")
    op.drop_column("roles", "company_id")
    op.drop_column("roles", "is_custom")
    op.drop_column("roles", "scope")
