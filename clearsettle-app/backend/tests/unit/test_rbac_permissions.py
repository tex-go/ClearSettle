"""
Unit tests for app.core.rbac — permission matrix and get_role_permissions().

PERMISSIONS structure: {permission_name: frozenset[role_names]}
get_role_permissions(role) → set[str] of permission names this role can use
"""
import pytest

from app.core.rbac import PERMISSIONS, get_role_permissions


# ── Fixtures ──────────────────────────────────────────────────────────────────

# All roles that must appear somewhere in the permission matrix
ALL_EXPECTED_ROLES = [
    "admin", "superadmin",
    "company_admin", "business_owner", "finance_manager", "accountant",
    "reconciliation_analyst", "gst_consultant", "auditor",
    "ca_admin", "ca_reviewer", "ca_staff", "ca_viewer",
    "branch_manager", "branch_accountant", "branch_viewer",
]

VIEW_ONLY_ROLES = ["auditor", "ca_viewer", "branch_viewer"]

MUST_HAVE_DASHBOARD_VIEW = [
    "company_admin", "business_owner", "finance_manager", "accountant",
    "reconciliation_analyst", "gst_consultant", "auditor",
    "ca_admin", "ca_reviewer", "ca_staff", "ca_viewer",
    "branch_manager", "branch_accountant", "branch_viewer",
]

MUST_HAVE_UPLOAD = [
    "company_admin", "finance_manager", "accountant",
    "branch_manager", "branch_accountant",
]

MUST_NOT_HAVE_USER_MANAGEMENT = [
    "ca_viewer", "branch_viewer", "auditor", "gst_consultant",
    "reconciliation_analyst", "ca_staff",
]

WRITE_ACTIONS = (".upload", ".create", ".delete", ".manage", ".run", ".connect", ".file", ".generate")


# ── PERMISSIONS dict structure ────────────────────────────────────────────────

class TestPermissionsDict:
    def test_permissions_is_non_empty(self):
        assert len(PERMISSIONS) > 0

    def test_all_values_are_frozensets(self):
        for perm, roles in PERMISSIONS.items():
            assert isinstance(roles, frozenset), f"Expected frozenset for {perm!r}, got {type(roles)}"

    def test_all_permission_keys_are_strings(self):
        for perm in PERMISSIONS:
            assert isinstance(perm, str), f"Permission key must be str, got {type(perm)}"

    def test_permission_keys_use_dot_or_colon_format(self):
        for perm in PERMISSIONS:
            assert "." in perm or ":" in perm, (
                f"Permission {perm!r} must use module.action or module:action format"
            )

    def test_no_permission_has_empty_role_set(self):
        for perm, roles in PERMISSIONS.items():
            assert len(roles) > 0, f"Permission {perm!r} has no roles assigned"

    @pytest.mark.parametrize("role", ALL_EXPECTED_ROLES)
    def test_role_appears_in_matrix(self, role: str):
        all_roles = {r for roles in PERMISSIONS.values() for r in roles}
        assert role in all_roles, f"Role '{role}' not found in any permission entry"


# ── get_role_permissions() ────────────────────────────────────────────────────

class TestGetRolePermissions:
    @pytest.mark.parametrize("role", ALL_EXPECTED_ROLES)
    def test_returns_non_empty_set(self, role: str):
        perms = get_role_permissions(role)
        assert len(perms) > 0, f"Role '{role}' has no permissions"

    def test_unknown_role_returns_empty_set(self):
        perms = get_role_permissions("totally_unknown_role_xyz")
        assert len(perms) == 0

    def test_admin_has_more_perms_than_viewer(self):
        admin = get_role_permissions("admin")
        viewer = get_role_permissions("ca_viewer")
        assert len(admin) > len(viewer)

    def test_superadmin_has_admin_level_permissions(self):
        superadmin = get_role_permissions("superadmin")
        assert "users.create" in superadmin, "superadmin must have users.create"
        assert "users.delete" in superadmin, "superadmin must have users.delete"
        assert "roles.assign" in superadmin, "superadmin must have roles.assign"

    # ── Dashboard view ─────────────────────────────────────────────────────────

    @pytest.mark.parametrize("role", MUST_HAVE_DASHBOARD_VIEW)
    def test_has_dashboard_view(self, role: str):
        perms = get_role_permissions(role)
        assert any("dashboard" in p and "view" in p for p in perms), (
            f"role={role} should have dashboard.view, got: {perms}"
        )

    # ── Upload permission ──────────────────────────────────────────────────────

    @pytest.mark.parametrize("role", MUST_HAVE_UPLOAD)
    def test_has_reports_upload(self, role: str):
        perms = get_role_permissions(role)
        assert any("upload" in p for p in perms), (
            f"role={role} should have reports.upload"
        )

    # ── View-only constraint ───────────────────────────────────────────────────

    @pytest.mark.parametrize("role", VIEW_ONLY_ROLES)
    def test_view_only_has_no_write_actions(self, role: str):
        perms = get_role_permissions(role)
        write_perms = [p for p in perms if any(p.endswith(a) for a in WRITE_ACTIONS)]
        assert not write_perms, (
            f"View-only role '{role}' must not have write permissions, found: {write_perms}"
        )

    # ── User management ────────────────────────────────────────────────────────

    @pytest.mark.parametrize("role", MUST_NOT_HAVE_USER_MANAGEMENT)
    def test_cannot_create_users(self, role: str):
        perms = get_role_permissions(role)
        assert "users.create" not in perms, f"role={role} must not have users.create"
        assert "users.delete" not in perms, f"role={role} must not have users.delete"

    def test_company_admin_can_manage_users(self):
        perms = get_role_permissions("company_admin")
        assert "users.create" in perms
        assert "users.view" in perms

    # ── GST consultant ────────────────────────────────────────────────────────

    def test_gst_consultant_has_gst_permissions(self):
        perms = get_role_permissions("gst_consultant")
        assert any("gst" in p for p in perms), "gst_consultant must have at least one gst permission"

    def test_gst_consultant_cannot_manage_users(self):
        perms = get_role_permissions("gst_consultant")
        assert "users.create" not in perms

    # ── Reconciliation analyst ────────────────────────────────────────────────

    def test_reconciliation_analyst_can_run_recon(self):
        perms = get_role_permissions("reconciliation_analyst")
        assert "reconciliation.run" in perms

    def test_reconciliation_analyst_cannot_delete_reports(self):
        perms = get_role_permissions("reconciliation_analyst")
        assert "reports.delete" not in perms

    # ── CA hierarchy ──────────────────────────────────────────────────────────

    def test_ca_admin_has_more_perms_than_ca_reviewer(self):
        ca_admin = get_role_permissions("ca_admin")
        ca_reviewer = get_role_permissions("ca_reviewer")
        assert len(ca_admin) >= len(ca_reviewer)

    def test_ca_reviewer_has_more_perms_than_ca_staff(self):
        ca_reviewer = get_role_permissions("ca_reviewer")
        ca_staff = get_role_permissions("ca_staff")
        assert len(ca_reviewer) >= len(ca_staff)

    def test_ca_staff_has_more_perms_than_ca_viewer(self):
        ca_staff = get_role_permissions("ca_staff")
        ca_viewer = get_role_permissions("ca_viewer")
        assert len(ca_staff) >= len(ca_viewer)

    # ── Branch hierarchy ──────────────────────────────────────────────────────

    def test_branch_manager_has_more_perms_than_branch_accountant(self):
        manager = get_role_permissions("branch_manager")
        accountant = get_role_permissions("branch_accountant")
        assert len(manager) >= len(accountant)

    def test_branch_accountant_has_more_perms_than_branch_viewer(self):
        accountant = get_role_permissions("branch_accountant")
        viewer = get_role_permissions("branch_viewer")
        assert len(accountant) >= len(viewer)

    # ── Auditor is read-only ──────────────────────────────────────────────────

    def test_auditor_has_audit_view(self):
        perms = get_role_permissions("auditor")
        assert any("audit" in p for p in perms) or any("view" in p for p in perms), (
            "auditor should have at least some view permissions"
        )

    def test_auditor_cannot_run_reconciliation(self):
        perms = get_role_permissions("auditor")
        assert "reconciliation.run" not in perms

    def test_auditor_cannot_upload_reports(self):
        perms = get_role_permissions("auditor")
        assert "reports.upload" not in perms
