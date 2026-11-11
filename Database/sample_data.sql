-- =============================================================================
-- SAMPLE DATA - Student Internship and Attachment Management System (PostgreSQL)
--
-- Reference data needed to start using the system: departments, host organizations,
-- an attachment period, the system settings row and ONE administrator account.
--
--   psql -U postgres -d student_internship_management -f sample_data.sql
--
-- Run it AFTER `python manage.py migrate`. Administrator login:
--   username: admin     password: Langata@2026     (change it after the first login)
--
-- For a full demonstration data set (supervisors, students, placements, logbooks,
-- visits, assessments) use instead:   python manage.py seed_demo
-- =============================================================================

BEGIN;

INSERT INTO departments (department_code, department_name, description) VALUES
  ('ICT', 'Information and Communication Technology', 'Diploma and certificate courses in ICT'),
  ('BUS', 'Business Studies', 'Business management, sales and marketing'),
  ('ELE', 'Electrical and Electronic Engineering', 'Electrical installation and power engineering'),
  ('HOS', 'Hospitality and Institutional Management', 'Food production, front office and housekeeping'),
  ('ACC', 'Accounting and Finance', 'Accounting, banking and finance')
ON CONFLICT (department_code) DO NOTHING;

INSERT INTO organizations (organization_name, address, county, contact_person, phone_number, email,
                           industry_category, status, created_at) VALUES
  ('Nairobi Tech Solutions Ltd', 'Ngong Road, Nairobi', 'Nairobi', 'Grace Wanjiru', '0712000001',
   'hr@nairobitech.example', 'Information Technology', 'active', NOW()),
  ('Lakeview Hospitality Group', 'Lake Road, Naivasha', 'Nakuru', 'Peter Otieno', '0712000002',
   'careers@lakeview.example', 'Hospitality', 'active', NOW()),
  ('Kilimani Power Engineering', 'Industrial Area, Nairobi', 'Nairobi', 'Ann Mutua', '0712000003',
   'info@kilimanipower.example', 'Engineering', 'active', NOW()),
  ('Greenfield Accounting Partners', 'Moi Avenue, Mombasa', 'Mombasa', 'Hassan Ali', '0712000004',
   'office@greenfield.example', 'Finance', 'active', NOW())
ON CONFLICT DO NOTHING;

INSERT INTO attachment_periods (name, start_date, end_date, application_deadline, report_deadline, is_active)
VALUES ('May - August Attachment', DATE '2027-05-03', DATE '2027-08-27', DATE '2027-04-16', DATE '2027-09-10', TRUE)
ON CONFLICT (name) DO NOTHING;

INSERT INTO system_settings (id, institution_name, allow_student_registration, required_logbook_weeks, updated_at)
VALUES (1, 'Langata Technical and Vocational College', TRUE, 12, NOW())
ON CONFLICT (id) DO NOTHING;

-- Administrator (password "Langata@2026", hashed with Django's PBKDF2-SHA256).
INSERT INTO users (username, email, password, role, is_active, is_staff, is_superuser, date_joined, last_login)
VALUES ('admin', 'admin@langata.example',
        'pbkdf2_sha256$1000000$2yZrsgLqDGU8K3dl9jpqst$BFOETy+I0PUzGbbaCaJOClhDxZLrcg9vX3GvbAu8UiM=',
        'admin', TRUE, TRUE, TRUE, NOW(), NULL)
ON CONFLICT (username) DO NOTHING;

INSERT INTO announcements (administrator_id, title, message, target_audience, publication_date, expiry_date)
SELECT id, 'Welcome to the attachment portal',
       'Register, complete your profile and submit your placement details before the application deadline.',
       'all', NOW(), NULL
FROM users WHERE username = 'admin';

COMMIT;
