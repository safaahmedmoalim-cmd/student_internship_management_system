-- =============================================================================
-- Demo data - the same accounts and records the frontend ships with.
-- Run AFTER schema.sql:   psql -d langata -v ON_ERROR_STOP=1 -f seed.sql
--
-- All demo accounts use the password  demo1234  (stored as a bcrypt hash).
-- DO NOT load this file into a production database.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;      -- provides crypt() / gen_salt() for bcrypt hashing
SET search_path TO langata, public;

BEGIN;

-- Users ------------------------------------------------------------------------
INSERT INTO users (role, full_name, email, phone, password_hash) VALUES
    ('coordinator', 'Mary Wanjiku',     'coordinator@langata.ac.ke', '0711 000 001', crypt('demo1234', gen_salt('bf', 10))),
    ('academic',    'Dr. Peter Otieno', 'academic@langata.ac.ke',    '0711 000 002', crypt('demo1234', gen_salt('bf', 10))),
    ('industrial',  'James Mwangi',     'industrial@langata.ac.ke',  '0711 000 003', crypt('demo1234', gen_salt('bf', 10))),
    ('student',     'Amina Hassan',     'student@langata.ac.ke',     '0711 000 004', crypt('demo1234', gen_salt('bf', 10))),
    ('student',     'Brian Kiptoo',     'brian@langata.ac.ke',       '0711 000 005', crypt('demo1234', gen_salt('bf', 10))),
    ('student',     'Grace Achieng',    'grace@langata.ac.ke',       '0711 000 006', crypt('demo1234', gen_salt('bf', 10)));

-- Host organisation -------------------------------------------------------------
INSERT INTO organizations (name, location) VALUES ('Savannah Tech Ltd', 'Westlands, Nairobi');

-- Role profiles -------------------------------------------------------------------
INSERT INTO coordinator_profiles (user_id, staff_no)
SELECT id, 'LC-C-001' FROM users WHERE email = 'coordinator@langata.ac.ke';

INSERT INTO academic_profiles (user_id, staff_no, department)
SELECT id, 'LC-A-014', 'Information & Communication Technology' FROM users WHERE email = 'academic@langata.ac.ke';

INSERT INTO industrial_profiles (user_id, organization_id, position)
SELECT u.id, o.id, 'IT Operations Manager'
FROM users u, organizations o
WHERE u.email = 'industrial@langata.ac.ke' AND o.name = 'Savannah Tech Ltd';

-- Students (Amina has both supervisors, Brian only an academic one, Grace none yet)
INSERT INTO student_profiles (user_id, adm_no, course_id, year_of_study, academic_supervisor_id, industrial_supervisor_id)
SELECT s.id, v.adm_no, c.id, 2,
       CASE WHEN v.has_acad THEN (SELECT id FROM users WHERE email = 'academic@langata.ac.ke') END,
       CASE WHEN v.has_ind  THEN (SELECT id FROM users WHERE email = 'industrial@langata.ac.ke') END
FROM (VALUES
        ('student@langata.ac.ke', 'LC/2024/0101', 'Diploma in ICT',                true,  true),
        ('brian@langata.ac.ke',   'LC/2024/0102', 'Diploma in Business Management', true,  false),
        ('grace@langata.ac.ke',   'LC/2024/0103', 'Diploma in Accounting',         false, false)
     ) AS v(email, adm_no, course, has_acad, has_ind)
JOIN users   s ON s.email = v.email
JOIN courses c ON c.name  = v.course;

-- Placements -----------------------------------------------------------------------
INSERT INTO placements (student_id, organization_id, department, start_date, end_date, industrial_supervisor_id, status)
SELECT s.id, o.id, v.dept, v.start_date::date, v.end_date::date,
       (SELECT id FROM users WHERE email = 'industrial@langata.ac.ke'), v.status::approval_status
FROM (VALUES
        ('student@langata.ac.ke', 'IT Support', '2026-09-01', '2026-11-06', 'approved'),
        ('brian@langata.ac.ke',   'Accounts',   '2026-09-07', '2026-11-13', 'pending')
     ) AS v(email, dept, start_date, end_date, status)
JOIN users s         ON s.email = v.email
JOIN organizations o ON o.name = 'Savannah Tech Ltd';

-- Logbook: Amina's first four weeks (weeks 1-3 approved, week 4 waiting) -----------
INSERT INTO logbook_entries (student_id, week_no, week_start, hours_worked, activities, skills_learned, status, industrial_comment, academic_comment)
SELECT (SELECT id FROM users WHERE email = 'student@langata.ac.ke'),
       v.week_no, DATE '2026-09-01' + (v.week_no - 1) * 7, 40, v.activities, v.skills,
       v.status::approval_status, v.ind_comment, v.acad_comment
FROM (VALUES
        (1, 'Orientation, office tour and introduction to the IT support team. Set up workstation and company email.',
            'Ticketing system, basic helpdesk etiquette',            'approved', 'Good start.',                      NULL),
        (2, 'Handled first-line support tickets: password resets, printer faults and software installs under supervision.',
            'Troubleshooting, documentation of fixes',               'approved', 'Keep documenting each fix.',       'Well written. Add more detail on tools used.'),
        (3, 'Assisted in configuring five new laptops and joining them to the company network.',
            'Network setup, imaging, asset tagging',                 'approved', 'Excellent initiative this week.',  NULL),
        (4, 'Helped back up the file server and tested restore of selected folders. Started inventory of network cabling.',
            'Backup and recovery basics',                            'pending',  NULL,                               NULL)
     ) AS v(week_no, activities, skills, status, ind_comment, acad_comment);

-- Industrial evaluation of Amina: ratings 5,4,4,4,4  ->  21 / 25  = 84 % ------------
WITH ev AS (
    INSERT INTO assessments (student_id, assessor_id, assessor_role, assessment_type, marks, comment)
    SELECT s.id, i.id, 'industrial', 'Industrial evaluation', 84, 'Reliable and eager to learn.'
    FROM users s, users i
    WHERE s.email = 'student@langata.ac.ke' AND i.email = 'industrial@langata.ac.ke'
    RETURNING id
)
INSERT INTO assessment_ratings (assessment_id, criterion_id, rating)
SELECT ev.id, c.id, r.rating
FROM ev
JOIN (VALUES ('Punctuality & attendance', 5), ('Technical skills', 4), ('Teamwork', 4),
             ('Initiative', 4), ('Communication', 4)) AS r(criterion, rating) ON true
JOIN assessment_criteria c ON c.name = r.criterion;

-- A visit coming up ---------------------------------------------------------------
INSERT INTO visits (student_id, academic_id, visit_date, mode, notes)
SELECT s.id, a.id, CURRENT_DATE + 12, 'Physical', 'Mid-attachment visit and logbook check.'
FROM users s, users a
WHERE s.email = 'student@langata.ac.ke' AND a.email = 'academic@langata.ac.ke';

-- Announcements ---------------------------------------------------------------------
INSERT INTO announcements (title, body, author_id)
SELECT v.title, v.body, (SELECT id FROM users WHERE email = 'coordinator@langata.ac.ke')
FROM (VALUES
        ('Final reports deadline', 'Final attachment reports must be submitted through the portal by the end of the attachment period.'),
        ('Weekly logbooks',        'Remember to submit your logbook every week so your industrial supervisor can approve it on time.')
     ) AS v(title, body);

COMMIT;
