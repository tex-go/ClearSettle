-- ============================================================
-- ClearSettle: Truncate all user data + seed one user per RBAC role
-- Password for all users: Admin@12345
-- ============================================================

BEGIN;

-- 1. Truncate (safe: skip tables that might not exist yet)
DO $trunc$
DECLARE
    tbl TEXT;
    tbls TEXT[] := ARRAY[
        'audit_logs','user_permissions','user_roles','branch_users','branches',
        'refresh_tokens','marketplace_connections','flipkart_reports','report_rows',
        'reconciliation_runs','reconciliation_results','settlements','disputes',
        'gst_entries','email_verifications','password_resets','companies','users'
    ];
BEGIN
    FOREACH tbl IN ARRAY tbls LOOP
        BEGIN
            EXECUTE format('TRUNCATE TABLE %I RESTART IDENTITY CASCADE', tbl);
            RAISE NOTICE 'Truncated %', tbl;
        EXCEPTION WHEN undefined_table THEN
            RAISE NOTICE 'Skipped (not found): %', tbl;
        END;
    END LOOP;
END $trunc$;

-- 2. Seed users (bcrypt hash of "Admin@12345")
DO $seed$
DECLARE
    pwd  TEXT := '$2b$12$S46fzrpnwI1csgogd8Z08O6mGtilFpfwj0gMwlftNkorINWlhfeS.';
    uid  UUID;
BEGIN
    -- admin
    INSERT INTO users (email, hashed_password, name, role, is_active, email_verified, is_superadmin)
    VALUES ('admin@clearsettle.com', pwd, 'Admin User', 'admin', true, true, true) RETURNING id INTO uid;
    INSERT INTO companies (user_id, name, state, city, registration_completed) VALUES (uid, 'ClearSettle Admin', 'Tamil Nadu', 'Chennai', true);
    RAISE NOTICE 'Created admin@clearsettle.com [admin]';

    -- superadmin
    INSERT INTO users (email, hashed_password, name, role, is_active, email_verified, is_superadmin)
    VALUES ('superadmin@clearsettle.com', pwd, 'Super Admin', 'superadmin', true, true, true) RETURNING id INTO uid;
    INSERT INTO companies (user_id, name, state, city, registration_completed) VALUES (uid, 'ClearSettle Platform', 'Tamil Nadu', 'Chennai', true);
    RAISE NOTICE 'Created superadmin@clearsettle.com [superadmin]';

    -- company_admin
    INSERT INTO users (email, hashed_password, name, role, is_active, email_verified, is_superadmin)
    VALUES ('company.admin@clearsettle.com', pwd, 'Company Admin', 'company_admin', true, true, false) RETURNING id INTO uid;
    INSERT INTO companies (user_id, name, state, city, registration_completed) VALUES (uid, 'Demo Company Pvt Ltd', 'Tamil Nadu', 'Chennai', true);
    RAISE NOTICE 'Created company.admin@clearsettle.com [company_admin]';

    -- business_owner
    INSERT INTO users (email, hashed_password, name, role, is_active, email_verified, is_superadmin)
    VALUES ('business.owner@clearsettle.com', pwd, 'Business Owner', 'business_owner', true, true, false) RETURNING id INTO uid;
    INSERT INTO companies (user_id, name, state, city, registration_completed) VALUES (uid, 'Demo Business Co', 'Tamil Nadu', 'Chennai', true);
    RAISE NOTICE 'Created business.owner@clearsettle.com [business_owner]';

    -- finance_manager
    INSERT INTO users (email, hashed_password, name, role, is_active, email_verified, is_superadmin)
    VALUES ('finance.manager@clearsettle.com', pwd, 'Finance Manager', 'finance_manager', true, true, false) RETURNING id INTO uid;
    INSERT INTO companies (user_id, name, state, city, registration_completed) VALUES (uid, 'Demo Finance Ltd', 'Tamil Nadu', 'Chennai', true);
    RAISE NOTICE 'Created finance.manager@clearsettle.com [finance_manager]';

    -- accountant
    INSERT INTO users (email, hashed_password, name, role, is_active, email_verified, is_superadmin)
    VALUES ('accountant@clearsettle.com', pwd, 'Staff Accountant', 'accountant', true, true, false) RETURNING id INTO uid;
    INSERT INTO companies (user_id, name, state, city, registration_completed) VALUES (uid, 'Demo Accounting Firm', 'Tamil Nadu', 'Chennai', true);
    RAISE NOTICE 'Created accountant@clearsettle.com [accountant]';

    -- reconciliation_analyst
    INSERT INTO users (email, hashed_password, name, role, is_active, email_verified, is_superadmin)
    VALUES ('recon.analyst@clearsettle.com', pwd, 'Recon Analyst', 'reconciliation_analyst', true, true, false) RETURNING id INTO uid;
    INSERT INTO companies (user_id, name, state, city, registration_completed) VALUES (uid, 'Demo Analytics Co', 'Tamil Nadu', 'Chennai', true);
    RAISE NOTICE 'Created recon.analyst@clearsettle.com [reconciliation_analyst]';

    -- gst_consultant
    INSERT INTO users (email, hashed_password, name, role, is_active, email_verified, is_superadmin)
    VALUES ('gst.consultant@clearsettle.com', pwd, 'GST Consultant', 'gst_consultant', true, true, false) RETURNING id INTO uid;
    INSERT INTO companies (user_id, name, state, city, registration_completed) VALUES (uid, 'Demo GST Services', 'Tamil Nadu', 'Chennai', true);
    RAISE NOTICE 'Created gst.consultant@clearsettle.com [gst_consultant]';

    -- auditor
    INSERT INTO users (email, hashed_password, name, role, is_active, email_verified, is_superadmin)
    VALUES ('auditor@clearsettle.com', pwd, 'Internal Auditor', 'auditor', true, true, false) RETURNING id INTO uid;
    INSERT INTO companies (user_id, name, state, city, registration_completed) VALUES (uid, 'Demo Audit Firm', 'Tamil Nadu', 'Chennai', true);
    RAISE NOTICE 'Created auditor@clearsettle.com [auditor]';

    -- ca_admin
    INSERT INTO users (email, hashed_password, name, role, is_active, email_verified, is_superadmin)
    VALUES ('ca.admin@clearsettle.com', pwd, 'CA Admin', 'ca_admin', true, true, false) RETURNING id INTO uid;
    INSERT INTO companies (user_id, name, state, city, registration_completed) VALUES (uid, 'Demo CA Firm', 'Tamil Nadu', 'Chennai', true);
    RAISE NOTICE 'Created ca.admin@clearsettle.com [ca_admin]';

    -- ca_reviewer
    INSERT INTO users (email, hashed_password, name, role, is_active, email_verified, is_superadmin)
    VALUES ('ca.reviewer@clearsettle.com', pwd, 'CA Reviewer', 'ca_reviewer', true, true, false) RETURNING id INTO uid;
    INSERT INTO companies (user_id, name, state, city, registration_completed) VALUES (uid, 'Demo CA Firm', 'Tamil Nadu', 'Chennai', true);
    RAISE NOTICE 'Created ca.reviewer@clearsettle.com [ca_reviewer]';

    -- ca_staff
    INSERT INTO users (email, hashed_password, name, role, is_active, email_verified, is_superadmin)
    VALUES ('ca.staff@clearsettle.com', pwd, 'CA Staff', 'ca_staff', true, true, false) RETURNING id INTO uid;
    INSERT INTO companies (user_id, name, state, city, registration_completed) VALUES (uid, 'Demo CA Firm', 'Tamil Nadu', 'Chennai', true);
    RAISE NOTICE 'Created ca.staff@clearsettle.com [ca_staff]';

    -- ca_viewer
    INSERT INTO users (email, hashed_password, name, role, is_active, email_verified, is_superadmin)
    VALUES ('ca.viewer@clearsettle.com', pwd, 'CA Viewer', 'ca_viewer', true, true, false) RETURNING id INTO uid;
    INSERT INTO companies (user_id, name, state, city, registration_completed) VALUES (uid, 'Demo CA Firm', 'Tamil Nadu', 'Chennai', true);
    RAISE NOTICE 'Created ca.viewer@clearsettle.com [ca_viewer]';

    -- branch_manager
    INSERT INTO users (email, hashed_password, name, role, is_active, email_verified, is_superadmin)
    VALUES ('branch.manager@clearsettle.com', pwd, 'Branch Manager', 'branch_manager', true, true, false) RETURNING id INTO uid;
    INSERT INTO companies (user_id, name, state, city, registration_completed) VALUES (uid, 'Demo Retail Chain', 'Tamil Nadu', 'Chennai', true);
    RAISE NOTICE 'Created branch.manager@clearsettle.com [branch_manager]';

    -- branch_accountant
    INSERT INTO users (email, hashed_password, name, role, is_active, email_verified, is_superadmin)
    VALUES ('branch.accountant@clearsettle.com', pwd, 'Branch Accountant', 'branch_accountant', true, true, false) RETURNING id INTO uid;
    INSERT INTO companies (user_id, name, state, city, registration_completed) VALUES (uid, 'Demo Retail Chain', 'Tamil Nadu', 'Chennai', true);
    RAISE NOTICE 'Created branch.accountant@clearsettle.com [branch_accountant]';

    -- branch_viewer
    INSERT INTO users (email, hashed_password, name, role, is_active, email_verified, is_superadmin)
    VALUES ('branch.viewer@clearsettle.com', pwd, 'Branch Viewer', 'branch_viewer', true, true, false) RETURNING id INTO uid;
    INSERT INTO companies (user_id, name, state, city, registration_completed) VALUES (uid, 'Demo Retail Chain', 'Tamil Nadu', 'Chennai', true);
    RAISE NOTICE 'Created branch.viewer@clearsettle.com [branch_viewer]';

END $seed$;

COMMIT;

-- Show result
SELECT
    email,
    role,
    is_superadmin AS super,
    is_active     AS active,
    email_verified AS verified
FROM users
ORDER BY created_at;
