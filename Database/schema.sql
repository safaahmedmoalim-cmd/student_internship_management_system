-- =============================================================================
-- Langata College - Internship & Attachment Management System
-- PostgreSQL schema (PostgreSQL 13 or newer)
--
-- Run:   psql -d langata -v ON_ERROR_STOP=1 -f schema.sql
-- Reset: DROP SCHEMA langata CASCADE;   (then run this file again)
--
-- Design notes
--  * One `users` table for all four roles; role-specific details live in
--    one profile table per role (student / academic / industrial / coordinator).
--  * Profile tables carry a fixed `role` column and a composite foreign key
--    (user_id, role) -> users(id, role), so the database itself guarantees that
--    e.g. a student profile can only belong to a user whose role is 'student',
--    and that a "supervisor" column can only point at a real supervisor.
--  * Business rules from the frontend are enforced here too (see section 6).
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS langata;
SET search_path TO langata, public;

-- -----------------------------------------------------------------------------
-- 1. Enumerated types
-- -----------------------------------------------------------------------------
CREATE TYPE user_role       AS ENUM ('student', 'academic', 'industrial', 'coordinator');
CREATE TYPE approval_status AS ENUM ('pending', 'approved', 'rejected');   -- placements & logbook entries
CREATE TYPE report_status   AS ENUM ('submitted', 'reviewed');
CREATE TYPE visit_mode      AS ENUM ('Physical', 'Virtual');
CREATE TYPE visit_status    AS ENUM ('scheduled', 'completed', 'cancelled');

-- -----------------------------------------------------------------------------
-- 2. Shared helper: keep updated_at current
-- -----------------------------------------------------------------------------
CREATE FUNCTION set_updated_at() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END $$;

-- -----------------------------------------------------------------------------
-- 3. Accounts
-- -----------------------------------------------------------------------------
CREATE TABLE users (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    role           user_role    NOT NULL,
    full_name      varchar(150) NOT NULL,
    email          varchar(254) NOT NULL,
    phone          varchar(30),
    password_hash  text         NOT NULL,            -- never store plain passwords (bcrypt / argon2 / Django hash)
    is_active      boolean      NOT NULL DEFAULT true,
    last_login_at  timestamptz,
    created_at     timestamptz  NOT NULL DEFAULT now(),
    updated_at     timestamptz  NOT NULL DEFAULT now(),
    CONSTRAINT users_email_key        UNIQUE (email),
    CONSTRAINT users_email_lowercase  CHECK (email = lower(email)),
    CONSTRAINT users_email_format     CHECK (email ~ '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$'),
    CONSTRAINT users_name_length      CHECK (char_length(btrim(full_name)) >= 3),
    CONSTRAINT users_id_role_key      UNIQUE (id, role)   -- target of the composite FKs below
);
CREATE INDEX users_role_idx ON users (role);
CREATE TRIGGER users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- API login tokens (store only a hash of the token, never the token itself)
CREATE TABLE auth_tokens (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id      bigint      NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    token_hash   text        NOT NULL UNIQUE,
    created_at   timestamptz NOT NULL DEFAULT now(),
    expires_at   timestamptz NOT NULL,
    last_used_at timestamptz,
    CONSTRAINT auth_tokens_expiry CHECK (expires_at > created_at)
);
CREATE INDEX auth_tokens_user_idx ON auth_tokens (user_id);

-- -----------------------------------------------------------------------------
-- 4. Reference data
-- -----------------------------------------------------------------------------
CREATE TABLE courses (
    id        smallint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name      varchar(120) NOT NULL UNIQUE,
    is_active boolean      NOT NULL DEFAULT true
);

CREATE TABLE organizations (                       -- host companies
    id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name       varchar(150) NOT NULL,
    location   varchar(150) NOT NULL DEFAULT '',
    created_at timestamptz  NOT NULL DEFAULT now(),
    CONSTRAINT organizations_name_length CHECK (char_length(btrim(name)) >= 2)
);
CREATE UNIQUE INDEX organizations_name_location_key ON organizations (lower(name), lower(location));

CREATE TABLE assessment_criteria (                 -- the 5 skills an industrial supervisor rates
    id         smallint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name       varchar(80) NOT NULL UNIQUE,
    sort_order smallint    NOT NULL DEFAULT 0
);

CREATE TABLE app_settings (
    key         varchar(60) PRIMARY KEY,
    value       text NOT NULL,
    description text
);

-- -----------------------------------------------------------------------------
-- 5. Role profiles
-- -----------------------------------------------------------------------------
CREATE TABLE coordinator_profiles (
    user_id  bigint PRIMARY KEY,
    role     user_role NOT NULL DEFAULT 'coordinator' CHECK (role = 'coordinator'),
    staff_no varchar(40) NOT NULL UNIQUE,
    FOREIGN KEY (user_id, role) REFERENCES users (id, role) ON DELETE CASCADE
);

CREATE TABLE academic_profiles (
    user_id    bigint PRIMARY KEY,
    role       user_role NOT NULL DEFAULT 'academic' CHECK (role = 'academic'),
    staff_no   varchar(40)  NOT NULL UNIQUE,
    department varchar(120) NOT NULL,
    FOREIGN KEY (user_id, role) REFERENCES users (id, role) ON DELETE CASCADE
);

CREATE TABLE industrial_profiles (
    user_id         bigint PRIMARY KEY,
    role            user_role NOT NULL DEFAULT 'industrial' CHECK (role = 'industrial'),
    organization_id bigint       NOT NULL REFERENCES organizations (id) ON DELETE RESTRICT,
    position        varchar(120) NOT NULL,
    FOREIGN KEY (user_id, role) REFERENCES users (id, role) ON DELETE CASCADE
);
CREATE INDEX industrial_profiles_org_idx ON industrial_profiles (organization_id);

CREATE TABLE student_profiles (
    user_id                  bigint PRIMARY KEY,
    role                     user_role NOT NULL DEFAULT 'student' CHECK (role = 'student'),
    adm_no                   varchar(40) NOT NULL UNIQUE,
    course_id                smallint    NOT NULL REFERENCES courses (id) ON DELETE RESTRICT,
    year_of_study            smallint    NOT NULL CHECK (year_of_study BETWEEN 1 AND 6),
    academic_supervisor_id   bigint REFERENCES academic_profiles   (user_id) ON DELETE SET NULL,
    industrial_supervisor_id bigint REFERENCES industrial_profiles (user_id) ON DELETE SET NULL,
    FOREIGN KEY (user_id, role) REFERENCES users (id, role) ON DELETE CASCADE
);
CREATE INDEX student_profiles_course_idx   ON student_profiles (course_id);
CREATE INDEX student_profiles_academic_idx ON student_profiles (academic_supervisor_id);
CREATE INDEX student_profiles_industry_idx ON student_profiles (industrial_supervisor_id);

-- -----------------------------------------------------------------------------
-- 6. Attachment workflow
-- -----------------------------------------------------------------------------

-- 6.1 Placement: one per student; the student deletes a rejected/pending one to resubmit
CREATE TABLE placements (
    id                       bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    student_id               bigint NOT NULL UNIQUE REFERENCES student_profiles (user_id) ON DELETE CASCADE,
    organization_id          bigint NOT NULL REFERENCES organizations (id) ON DELETE RESTRICT,
    department              varchar(120) NOT NULL,
    start_date               date   NOT NULL,
    end_date                 date   NOT NULL,
    industrial_supervisor_id bigint REFERENCES industrial_profiles (user_id) ON DELETE SET NULL,
    status                   approval_status NOT NULL DEFAULT 'pending',
    coordinator_comment      text,
    decided_by               bigint REFERENCES coordinator_profiles (user_id) ON DELETE SET NULL,
    decided_at               timestamptz,
    created_at               timestamptz NOT NULL DEFAULT now(),
    updated_at               timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT placements_dates_valid CHECK (end_date > start_date),
    CONSTRAINT placements_reject_needs_reason
        CHECK (status <> 'rejected' OR char_length(btrim(coalesce(coordinator_comment, ''))) > 0)
);
CREATE INDEX placements_status_idx   ON placements (status);
CREATE INDEX placements_org_idx      ON placements (organization_id);
CREATE INDEX placements_industry_idx ON placements (industrial_supervisor_id);
CREATE TRIGGER placements_updated_at BEFORE UPDATE ON placements FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Stamp the decision time automatically.
CREATE FUNCTION placements_stamp_decision() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.status <> 'pending' AND NEW.decided_at IS NULL THEN
        NEW.decided_at := now();
    ELSIF NEW.status = 'pending' THEN
        NEW.decided_at := NULL;
        NEW.decided_by := NULL;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER placements_decision BEFORE INSERT OR UPDATE OF status ON placements
    FOR EACH ROW EXECUTE FUNCTION placements_stamp_decision();

-- When a placement is approved and names an industrial supervisor, the student
-- is attached to that supervisor (unless one is already assigned).
CREATE FUNCTION placements_assign_supervisor() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.industrial_supervisor_id IS NOT NULL THEN
        UPDATE student_profiles
           SET industrial_supervisor_id = NEW.industrial_supervisor_id
         WHERE user_id = NEW.student_id AND industrial_supervisor_id IS NULL;
    END IF;
    RETURN NULL;
END $$;
CREATE TRIGGER placements_approved AFTER INSERT OR UPDATE OF status ON placements
    FOR EACH ROW WHEN (NEW.status = 'approved') EXECUTE FUNCTION placements_assign_supervisor();

-- 6.2 Weekly logbook
CREATE TABLE logbook_entries (
    id                 bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    student_id         bigint NOT NULL REFERENCES student_profiles (user_id) ON DELETE CASCADE,
    week_no            smallint NOT NULL CHECK (week_no BETWEEN 1 AND 30),
    week_start         date     NOT NULL,
    hours_worked       smallint NOT NULL CHECK (hours_worked BETWEEN 1 AND 60),
    activities         text     NOT NULL CHECK (char_length(btrim(activities)) > 0),
    skills_learned     text,
    status             approval_status NOT NULL DEFAULT 'pending',   -- decided by the industrial supervisor
    industrial_comment text,
    academic_comment   text,
    reviewed_at        timestamptz,
    created_at         timestamptz NOT NULL DEFAULT now(),
    updated_at         timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT logbook_one_entry_per_week UNIQUE (student_id, week_no),
    CONSTRAINT logbook_reject_needs_reason
        CHECK (status <> 'rejected' OR char_length(btrim(coalesce(industrial_comment, ''))) > 0)
);
CREATE INDEX logbook_status_idx ON logbook_entries (status);
CREATE TRIGGER logbook_updated_at BEFORE UPDATE ON logbook_entries FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Rule: a student can only log weeks once their placement has been approved.
CREATE FUNCTION logbook_require_approved_placement() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM placements p WHERE p.student_id = NEW.student_id AND p.status = 'approved') THEN
        RAISE EXCEPTION 'Student % has no approved placement; logbook entries are not allowed yet.', NEW.student_id
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER logbook_requires_placement BEFORE INSERT ON logbook_entries
    FOR EACH ROW EXECUTE FUNCTION logbook_require_approved_placement();

-- Stamp review time when the status leaves 'pending'.
CREATE FUNCTION logbook_stamp_review() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.status <> 'pending' AND NEW.reviewed_at IS NULL THEN
        NEW.reviewed_at := now();
    ELSIF NEW.status = 'pending' THEN
        NEW.reviewed_at := NULL;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER logbook_review_time BEFORE INSERT OR UPDATE OF status ON logbook_entries
    FOR EACH ROW EXECUTE FUNCTION logbook_stamp_review();

-- 6.3 Final report (one per student; resubmitting replaces the row)
CREATE TABLE final_reports (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    student_id      bigint NOT NULL UNIQUE REFERENCES student_profiles (user_id) ON DELETE CASCADE,
    title           varchar(200) NOT NULL,
    summary         text         NOT NULL,
    file_name       varchar(255) NOT NULL,
    file_path       text         NOT NULL,                  -- where the file lives (disk / object storage key)
    file_size_bytes bigint       NOT NULL,
    status          report_status NOT NULL DEFAULT 'submitted',
    reviewed_by     bigint REFERENCES academic_profiles (user_id) ON DELETE SET NULL,
    reviewed_at     timestamptz,
    submitted_at    timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT report_file_type CHECK (file_name ~* '\.(pdf|docx?)$'),
    CONSTRAINT report_file_size CHECK (file_size_bytes > 0 AND file_size_bytes <= 10 * 1024 * 1024),
    CONSTRAINT report_review_consistent CHECK ((status = 'reviewed') = (reviewed_at IS NOT NULL))
);
CREATE INDEX final_reports_status_idx ON final_reports (status);

-- 6.4 Supervisor visits
CREATE TABLE visits (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    student_id  bigint NOT NULL REFERENCES student_profiles  (user_id) ON DELETE CASCADE,
    academic_id bigint NOT NULL REFERENCES academic_profiles (user_id) ON DELETE CASCADE,
    visit_date  date   NOT NULL,
    mode        visit_mode   NOT NULL DEFAULT 'Physical',
    notes       text,
    status      visit_status NOT NULL DEFAULT 'scheduled',
    created_at  timestamptz  NOT NULL DEFAULT now(),
    updated_at  timestamptz  NOT NULL DEFAULT now()
);
CREATE INDEX visits_student_idx  ON visits (student_id);
CREATE INDEX visits_academic_idx ON visits (academic_id, visit_date);
CREATE TRIGGER visits_updated_at BEFORE UPDATE ON visits FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 6.5 Assessments (academic marks and industrial evaluations)
CREATE TABLE assessments (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    student_id      bigint NOT NULL REFERENCES student_profiles (user_id) ON DELETE CASCADE,
    assessor_id     bigint NOT NULL,
    assessor_role   user_role NOT NULL CHECK (assessor_role IN ('academic', 'industrial')),
    assessment_type varchar(60) NOT NULL,        -- 'Mid-attachment visit' | 'Final assessment' | 'Industrial evaluation'
    marks           smallint NOT NULL CHECK (marks BETWEEN 0 AND 100),
    comment         text,
    created_at      timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (assessor_id, assessor_role) REFERENCES users (id, role) ON DELETE CASCADE
);
CREATE INDEX assessments_student_idx  ON assessments (student_id);
CREATE INDEX assessments_assessor_idx ON assessments (assessor_id);

CREATE TABLE assessment_ratings (               -- the per-skill 1-5 ratings behind an industrial evaluation
    assessment_id bigint   NOT NULL REFERENCES assessments (id) ON DELETE CASCADE,
    criterion_id  smallint NOT NULL REFERENCES assessment_criteria (id) ON DELETE RESTRICT,
    rating        smallint NOT NULL CHECK (rating BETWEEN 1 AND 5),
    PRIMARY KEY (assessment_id, criterion_id)
);

-- 6.6 Announcements (posted by the coordinator)
CREATE TABLE announcements (
    id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title      varchar(200) NOT NULL,
    body       text         NOT NULL,
    author_id  bigint REFERENCES coordinator_profiles (user_id) ON DELETE SET NULL,
    created_at timestamptz  NOT NULL DEFAULT now()
);
CREATE INDEX announcements_created_idx ON announcements (created_at DESC);

-- -----------------------------------------------------------------------------
-- 7. Rules that span tables
-- -----------------------------------------------------------------------------

-- Visits and assessments must come from the student's own supervisor.
CREATE FUNCTION require_assigned_academic_supervisor() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM student_profiles s
                    WHERE s.user_id = NEW.student_id AND s.academic_supervisor_id = NEW.academic_id) THEN
        RAISE EXCEPTION 'Academic supervisor % is not assigned to student %.', NEW.academic_id, NEW.student_id
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER visits_require_supervisor BEFORE INSERT ON visits
    FOR EACH ROW EXECUTE FUNCTION require_assigned_academic_supervisor();

CREATE FUNCTION assessments_require_supervisor() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.assessor_role = 'academic' AND NOT EXISTS (
           SELECT 1 FROM student_profiles s WHERE s.user_id = NEW.student_id AND s.academic_supervisor_id = NEW.assessor_id) THEN
        RAISE EXCEPTION 'Academic supervisor % is not assigned to student %.', NEW.assessor_id, NEW.student_id
            USING ERRCODE = 'check_violation';
    ELSIF NEW.assessor_role = 'industrial' AND NOT EXISTS (
           SELECT 1 FROM student_profiles s WHERE s.user_id = NEW.student_id AND s.industrial_supervisor_id = NEW.assessor_id) THEN
        RAISE EXCEPTION 'Industrial supervisor % is not assigned to student %.', NEW.assessor_id, NEW.student_id
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER assessments_require_supervisor BEFORE INSERT ON assessments
    FOR EACH ROW EXECUTE FUNCTION assessments_require_supervisor();

-- Only the student's academic supervisor may mark their report as reviewed.
CREATE FUNCTION reports_require_supervisor() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.status = 'reviewed' AND NOT EXISTS (
           SELECT 1 FROM student_profiles s WHERE s.user_id = NEW.student_id AND s.academic_supervisor_id = NEW.reviewed_by) THEN
        RAISE EXCEPTION 'Only the student''s academic supervisor can review this report.'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER reports_require_supervisor BEFORE INSERT OR UPDATE OF status, reviewed_by ON final_reports
    FOR EACH ROW EXECUTE FUNCTION reports_require_supervisor();

-- -----------------------------------------------------------------------------
-- 8. Views used by the dashboards
-- -----------------------------------------------------------------------------

-- One row per student: everything the coordinator's Reports page and the
-- supervisors' student lists show. "overall" = average of the academic and
-- industrial scores that exist (same rule as the frontend).
CREATE VIEW v_student_summary AS
SELECT  u.id                       AS student_id,
        u.full_name,
        u.email,
        u.phone,
        sp.adm_no,
        c.name                     AS course,
        sp.year_of_study,
        sp.academic_supervisor_id,
        sp.industrial_supervisor_id,
        pl.status                  AS placement_status,
        o.name                     AS organization,
        COALESCE(h.approved_hours, 0)                                       AS approved_hours,
        COALESCE(h.logged_hours, 0)                                         AS logged_hours,
        COALESCE((SELECT value::int FROM app_settings WHERE key = 'target_hours'), 400) AS target_hours,
        fr.status                  AS report_status,
        m.academic_marks,
        m.industrial_marks,
        CASE WHEN m.academic_marks IS NULL AND m.industrial_marks IS NULL THEN NULL
             ELSE round((COALESCE(m.academic_marks, 0) + COALESCE(m.industrial_marks, 0))::numeric
                        / ((m.academic_marks IS NOT NULL)::int + (m.industrial_marks IS NOT NULL)::int))
        END                        AS overall_marks
FROM users u
JOIN student_profiles sp ON sp.user_id = u.id
JOIN courses c           ON c.id = sp.course_id
LEFT JOIN placements pl     ON pl.student_id = u.id
LEFT JOIN organizations o   ON o.id = pl.organization_id
LEFT JOIN final_reports fr  ON fr.student_id = u.id
LEFT JOIN LATERAL (
        SELECT SUM(le.hours_worked) FILTER (WHERE le.status = 'approved') AS approved_hours,
               SUM(le.hours_worked)                                       AS logged_hours
          FROM logbook_entries le WHERE le.student_id = u.id) h ON true
LEFT JOIN LATERAL (
        SELECT round(avg(a.marks) FILTER (WHERE a.assessor_role = 'academic'))   AS academic_marks,
               round(avg(a.marks) FILTER (WHERE a.assessor_role = 'industrial')) AS industrial_marks
          FROM assessments a WHERE a.student_id = u.id) m ON true;

-- Logbook entries with the student and both supervisors attached (filter by
-- industrial_supervisor_id / academic_supervisor_id for each supervisor's page).
CREATE VIEW v_logbook_details AS
SELECT  le.id, le.student_id, u.full_name AS student_name, sp.adm_no,
        sp.academic_supervisor_id, sp.industrial_supervisor_id,
        le.week_no, le.week_start, le.hours_worked, le.activities, le.skills_learned,
        le.status, le.industrial_comment, le.academic_comment, le.reviewed_at, le.created_at
FROM logbook_entries le
JOIN student_profiles sp ON sp.user_id = le.student_id
JOIN users u             ON u.id = le.student_id;

-- Supervisors with how many students each one looks after (Coordinator > Supervisors).
CREATE VIEW v_supervisors AS
SELECT  u.id, u.role, u.full_name, u.email, u.phone,
        ap.department, NULL::varchar AS organization, NULL::varchar AS position,
        (SELECT count(*) FROM student_profiles s WHERE s.academic_supervisor_id = u.id) AS student_count
FROM users u JOIN academic_profiles ap ON ap.user_id = u.id
UNION ALL
SELECT  u.id, u.role, u.full_name, u.email, u.phone,
        NULL, o.name, ip.position,
        (SELECT count(*) FROM student_profiles s WHERE s.industrial_supervisor_id = u.id)
FROM users u JOIN industrial_profiles ip ON ip.user_id = u.id
JOIN organizations o ON o.id = ip.organization_id;

-- Coordinator overview: students per placement state, including "none".
CREATE VIEW v_placement_overview AS
SELECT  COALESCE(pl.status::text, 'none') AS placement_state, count(*) AS students
FROM student_profiles sp
LEFT JOIN placements pl ON pl.student_id = sp.user_id
GROUP BY 1;

-- -----------------------------------------------------------------------------
-- 9. Defaults every installation needs
-- -----------------------------------------------------------------------------
INSERT INTO app_settings (key, value, description) VALUES
    ('target_hours', '400', 'Attachment hours a student must complete');

INSERT INTO assessment_criteria (name, sort_order) VALUES
    ('Punctuality & attendance', 1),
    ('Technical skills',         2),
    ('Teamwork',                 3),
    ('Initiative',               4),
    ('Communication',            5);

INSERT INTO courses (name) VALUES
    ('Diploma in ICT'),
    ('Diploma in Business Management'),
    ('Diploma in Accounting'),
    ('Diploma in Hospitality Management'),
    ('Diploma in Electrical Engineering'),
    ('Certificate in Community Development');
