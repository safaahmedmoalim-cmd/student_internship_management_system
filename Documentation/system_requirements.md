# STUDENT INTERNSHIP AND ATTACHMENT MANAGEMENT SYSTEM
## SYSTEM REQUIREMENTS AND DESIGN DOCUMENT

**Proposed Institution:** Langata Technical and Vocational College
**Project Type:** Web-Based Management Information System
**Frontend:** ReactJS
**Backend:** Python Django
**API Framework:** Django REST Framework
**Database:** PostgreSQL

> Implementation notes for each chapter are in [`implementation_notes`](#implementation-notes) at the end
> of this document.

---

# CHAPTER ONE: INTRODUCTION

## 1.1 Background

The Student Internship and Attachment Management System is a web-based application designed to simplify and automate the management of student internship and industrial attachment activities within an educational institution.

The system will provide a centralized platform through which students can submit placement applications, maintain weekly logbooks, communicate with supervisors, submit final attachment reports and monitor their academic progress.

It will also enable academic supervisors to monitor assigned students, review logbooks, schedule supervision visits and conduct academic evaluations.

Industrial supervisors will use the platform to monitor interns within their organizations, approve weekly logbook submissions and evaluate workplace performance.

The system administrator will coordinate the entire attachment process by managing users, approving student placements, assigning supervisors, publishing announcements and generating administrative reports.

The system will consist of four main user entities:

1. Student
2. Academic Supervisor
3. Industrial Supervisor
4. System Administrator

Each entity will have a unique dashboard with functionalities and permissions appropriate to its responsibilities.

## 1.2 Problem Statement

Traditional internship and industrial attachment management processes may involve manual submission of placement documents, physical logbooks, printed evaluation forms and communication through separate channels.

These processes can create difficulties in tracking student progress, monitoring submissions, coordinating supervisors and maintaining accurate assessment records.

The proposed system will address these challenges by introducing a centralized digital platform that facilitates communication, document management, placement approval, supervision and assessment.

## 1.3 Main Objective

To design and develop a web-based Student Internship and Attachment Management System that automates student placement, supervision, logbook management, assessment and reporting.

## 1.4 Specific Objectives

1. To develop a centralized student registration and account management system.
2. To automate student placement application and approval.
3. To facilitate assignment of academic and industrial supervisors.
4. To provide an electronic weekly logbook submission and review platform.
5. To enable academic supervisors to schedule and record supervision visits.
6. To facilitate industrial and academic student evaluations.
7. To provide electronic final report submission and review.
8. To facilitate communication through announcements and notifications.
9. To generate reports showing student attachment progress and assessment results.
10. To implement secure role-based access control.

---

# CHAPTER TWO: SYSTEM OVERVIEW

## 2.1 System Description

The proposed application will operate as a web-based system accessible through a browser on computers, tablets and smartphones.

It will use a three-tier architecture:

- Presentation layer: ReactJS frontend.
- Application layer: Django backend.
- Data layer: PostgreSQL database.

The frontend will communicate with the backend through REST API endpoints. The backend will process requests, enforce permissions and interact with the PostgreSQL database.

## 2.2 System Entities

| Entity | Main responsibility |
|---|---|
| Student | Apply for placement, submit logbooks and final reports, and monitor progress. |
| Academic Supervisor | Monitor assigned students, review submissions, schedule visits and assess students. |
| Industrial Supervisor | Monitor workplace activities, approve logbooks and evaluate workplace performance. |
| Administrator | Manage users, placements, supervisors, announcements and system reports. |

## 2.3 System Architecture

- **Frontend: ReactJS** – the user interface and separate dashboards for the four entities.
- **Backend: Django** – business logic, authentication, authorization, data processing, file management and API requests. Django REST Framework exposes the REST APIs.
- **Database: PostgreSQL** – user information, placement applications, organization details, supervisor assignments, logbooks, assessments, reports and notifications.

```
FRONTEND – REACTJS
  Student Dashboard · Academic Supervisor Dashboard · Industrial Supervisor Dashboard · Administrator Dashboard
        ↓  REST API – AXIOS / HTTP
BACKEND – DJANGO REST FRAMEWORK
  Authentication and authorization · Placement · User · Logbook · Assessment · Report · Notification management
        ↓
DATABASE – POSTGRESQL
  Users · Students · Supervisors · Organizations · Placements · Logbooks · Assessments · Reports · Announcements
```

---

# CHAPTER THREE: SYSTEM USERS AND FUNCTIONAL REQUIREMENTS

## 3.1 Student Entity

The student entity represents individuals undertaking internship or industrial attachment through the institution.

### Student responsibilities

1. Register an account using their student registration details.
2. Log in and log out securely.
3. Update personal information.
4. View their academic and departmental information.
5. Submit placement details to the administrator for approval.
6. Withdraw a placement application with a reason.
7. Resubmit corrected placement details.
8. View placement approval status.
9. View assigned academic and industrial supervisors.
10. View attachment commencement and completion dates.
11. Submit weekly logbook entries to both supervisors.
12. View logbook approval and rejection status.
13. Read supervisor comments and feedback.
14. Resubmit rejected logbook entries.
15. Submit the final attachment report to the academic supervisor.
16. View assessment results and feedback after release.
17. Receive announcements from the administrator.
18. Receive notifications about placement, logbook and assessment updates.

### Student dashboard components

Profile overview · Placement status · Assigned supervisors · Weekly logbook · Logbook submission history · Final report submission · Assessment results · Announcements · Notifications

## 3.2 Academic Supervisor Entity

The academic supervisor represents a lecturer or authorized institutional staff member responsible for monitoring students during attachment.

### Academic supervisor responsibilities

1. Log in and log out securely.
2. Update personal information.
3. View assigned students.
4. View student placement details.
5. View assigned students' host organizations.
6. Review weekly logbook entries.
7. Approve or return logbook entries with comments.
8. Schedule physical or virtual supervision visits.
9. Record supervision visit reports.
10. Evaluate students using an approved assessment rubric.
11. Record assessment marks.
12. Provide comments and recommendations to students.
13. Review final attachment reports.
14. Return final reports for corrections or approve them.
15. View assessment history.
16. Receive announcements from the administrator.
17. Receive notifications about new student submissions.

### Academic supervisor dashboard components

Dashboard overview · Assigned students · Student placement details · Logbook review · Visit scheduling · Visit reports · Final report review · Student evaluation · Assessment records · Announcements · Notifications

## 3.3 Industrial Supervisor Entity

The industrial supervisor represents an authorized employee at the host organization responsible for guiding and evaluating interns.

### Industrial supervisor responsibilities

1. Log in and log out securely.
2. Update personal information.
3. View assigned interns.
4. View relevant student and placement information.
5. Review weekly logbook entries.
6. Approve satisfactory weekly logbook entries.
7. Reject unsatisfactory entries with explanations.
8. Provide feedback and recommendations.
9. Evaluate interns on workplace skills.
10. Record workplace assessment marks.
11. Monitor student attendance.
12. Submit final workplace evaluation forms.
13. View previous evaluations.
14. Receive announcements from the administrator.
15. Receive notifications about intern submissions.

### Workplace evaluation areas

Technical competence · Communication skills · Teamwork · Time management · Problem-solving · Professional conduct · Adaptability · Initiative · Responsibility · Attendance and punctuality

### Industrial supervisor dashboard components

Dashboard overview · Assigned interns · Intern profiles · Weekly logbook review · Logbook approval · Workplace evaluation · Attendance records · Evaluation history · Announcements · Notifications

## 3.4 System Administrator Entity

The administrator will coordinate and manage the entire system.

### Administrator responsibilities

1. Log in and log out securely.
2. Update personal information.
3. Register and manage student accounts.
4. Register and manage academic supervisors.
5. Register and manage industrial supervisors.
6. Approve, deactivate or manage user accounts.
7. Create and manage departments.
8. Register and manage host organizations.
9. Review student placement applications.
10. Approve or reject placement applications.
11. Return placement applications for correction.
12. Assign academic supervisors to students.
13. Assign industrial supervisors to students.
14. Manage attachment periods and deadlines.
15. Publish announcements to all users.
16. Publish announcements to selected user groups.
17. Monitor student logbook submissions.
18. Monitor supervision progress.
19. View student assessment results.
20. Generate student and attachment reports.
21. Monitor overall system activities.
22. View audit logs.
23. Manage system settings.
24. Reset user passwords and manage account access.

### Administrator dashboard components

Total registered students · Total academic supervisors · Total industrial supervisors · Total host organizations · Pending placement applications · Approved placements · Rejected placements · Active attachment students · Pending logbook reviews · Completed assessments · Announcements · Reports and analytics · User management · System settings

---

# CHAPTER FOUR: SYSTEM MODULES

## 4.1 Authentication and User Management Module
User registration · User login · User logout · Password reset · Profile management · Role assignment · Account activation and deactivation · Access permissions

## 4.2 Student Placement Management Module
Students submit placement applications containing: student registration number, organization name, organization address, organization location, organization contact person, contact telephone number, contact email, attachment start date, attachment completion date, placement application date, supporting documents and application status. The administrator reviews and processes each application.

## 4.3 Organization Management Module
A directory of organizations offering internship and industrial attachment opportunities: organization ID, name, physical address, county, contact person, telephone number, email address, industry or business category, organization status.

## 4.4 Supervisor Assignment Module
The administrator assigns two supervisors (academic and industrial) to each approved placement. The assignment links the student, placement and supervisors.

## 4.5 Logbook Management Module
Weekly entries contain: student ID, week number, week starting date, week ending date, activities performed, skills acquired, challenges experienced, solutions applied, supporting attachments and submission date. Both supervisors independently review the entry and record their decisions and comments.

## 4.6 Supervision Visit Management Module
Visit information: student ID, academic supervisor ID, organization, visit date, visit type, visit objectives, observations, recommendations, visit status.

## 4.7 Assessment Management Module
Academic supervisors record academic assessments and industrial supervisors record workplace assessments: student ID, supervisor ID, assessment category, assessment criteria, marks, comments, assessment date, assessment status. The administrator views assessment summaries.

## 4.8 Final Report Management Module
Students upload final attachment reports; academic supervisors approve, return for correction or provide feedback. Report submission history is maintained.

## 4.9 Announcement Management Module
The administrator publishes notices to all users, students, academic supervisors or industrial supervisors, with a title, message, publication date and optional expiry date.

## 4.10 Notification Management Module
Notifications for: placement approval or rejection, supervisor assignment, new logbook submissions, logbook approval or rejection, supervision visit scheduling, assessment updates, final report feedback, new announcements and important deadlines.

## 4.11 Reporting and Analytics Module
Reports on registered students, students placed in organizations, placement approval statistics, student attachment progress, supervisor allocation, logbook submission statistics, assessment results and completed attachment periods, with PDF and Excel export.

---

# CHAPTER FIVE: SYSTEM WORKFLOW

**5.1 Student Registration** – open the system → select registration → provide information → system validates → account created → student logs in and completes the profile.

**5.2 Placement Application** – student enters organization information and submits → recorded as pending → administrator notified → administrator approves, rejects or returns → student receives the decision.

**5.3 Supervisor Assignment** – administrator opens approved placements → selects student, academic supervisor and industrial supervisor → assignment saved → both supervisors notified → student views assigned supervisors.

**5.4 Weekly Logbook Submission** – student records and submits weekly activities → both supervisors notified → each reviews and records an independent decision → student views feedback → corrections are resubmitted.

**5.5 Supervision Visits** – academic supervisor selects a student and schedules a visit → student notified → visit conducted → observations recorded → visit report stored.

**5.6 Student Assessment** – industrial and academic supervisors evaluate and submit → records stored → administrator monitors completion → authorized marks and feedback released to the student.

**5.7 Final Report Submission** – student uploads the report → academic supervisor reviews, approves or returns it → student receives feedback → approval recorded.

**5.8 Attachment Completion** – attachment period completed → logbooks reviewed → visits recorded → final report reviewed → assessments completed → administrator confirms administrative completion.

---

# CHAPTER SIX: PROJECT FOLDER STRUCTURE

```
Student-Internship-Attachment-Management-System/
├── Frontend/      public/, src/{assets/{images,icons}, components/{common,forms}, pages/{auth,student,academic,industrial,admin},
│                  services, context, hooks, layouts, styles, App.jsx, main.jsx}, package.json, vite.config.js, .env
├── Backend/       config/{settings,urls,asgi,wsgi}.py, apps/{accounts,students,supervisors,organizations,placements,logbooks,
│                  visits,assessments,reports,announcements,notifications}, media/{logbooks,final_reports,evaluation_forms},
│                  manage.py, requirements.txt, .env
├── Database/      schema.sql, sample_data.sql, database_design.md, erd.png, backup/
├── Documentation/ system_requirements.md, user_manual.md, api_documentation.md, installation_guide.md
├── README.md
└── .gitignore
```

Frontend responsibilities: user interface, navigation, forms, dashboards, data presentation, client-side validation, API communication, role-based page access.
Backend responsibilities: authentication, authorization, database operations, API endpoints, business logic, document uploads, assessment processing, notifications, reports.
Database responsibilities: user, student, supervisor, organization, placement, logbook, assessment and report records, notifications and system activity records.

---

# CHAPTER SEVEN: DATABASE DESIGN

Database: **student_internship_management** (PostgreSQL, managed through the Django ORM).

17 main tables: users, students, academic_supervisors, industrial_supervisors, departments, organizations, placements, supervisor_assignments, logbooks, logbook_reviews, supervision_visits, final_reports, assessments, announcements, notifications, attendance, audit_logs.

Fields and relationships: see [`../Database/database_design.md`](../Database/database_design.md).

Relationships:
1. One user has one associated student, academic supervisor or industrial supervisor profile.
2. One department can have many students.
3. One department can have many academic supervisors.
4. One student can submit multiple placement applications over time.
5. One organization can host multiple students.
6. One placement can have one active supervisor assignment.
7. One academic supervisor can supervise multiple students.
8. One industrial supervisor can supervise multiple interns.
9. One student can submit many weekly logbook entries.
10. One logbook can receive reviews from two supervisors.
11. One academic supervisor can conduct multiple supervision visits.
12. One student can submit multiple final report versions.
13. One student can receive multiple assessments.
14. One user can receive multiple notifications.
15. One user can generate multiple audit records.

---

# CHAPTER EIGHT: USER ACCESS CONTROL

| Function | Student | Academic | Industrial | Admin |
|---|---|---|---|---|
| View own profile | Yes | Yes | Yes | Yes |
| Edit own profile | Yes | Yes | Yes | Yes |
| Manage student accounts | No | No | No | Yes |
| Manage supervisor accounts | No | No | No | Yes |
| Submit placement | Yes | No | No | No |
| Approve placement | No | No | No | Yes |
| Assign supervisors | No | No | No | Yes |
| View assigned students | No | Yes | Yes | Yes |
| Submit logbook | Yes | No | No | No |
| Review logbook | No | Yes | Yes | Yes |
| Schedule visits | No | Yes | No | Yes |
| Submit final report | Yes | No | No | No |
| Assess students | No | Yes | Yes | No |
| View released assessments | Yes | Yes | Yes | Yes |
| Publish announcements | No | No | No | Yes |
| Generate system reports | No | Limited | Limited | Yes |
| Manage system settings | No | No | No | Yes |

Access to student records by supervisors is restricted to assigned students.

---

# CHAPTER NINE: SYSTEM STATUS MANAGEMENT

- **Placement:** Pending, Approved, Rejected, Returned for Correction, Withdrawn
- **Logbook:** Submitted, Under Review, Approved, Rejected (each supervisor has an independent review status)
- **Final report:** Submitted, Under Review, Returned for Correction, Approved
- **Supervision visit:** Scheduled, Completed, Rescheduled, Cancelled
- **Attachment:** Not Started, Active, Completed, Terminated
- **Assessment:** Pending, In Progress, Completed, Released

---

# CHAPTER TEN: SECURITY REQUIREMENTS

1. Secure password hashing using Django.
2. JWT-based authentication.
3. Role-based access control.
4. API-level permission checking.
5. Validation of submitted information.
6. Secure document upload handling.
7. Restricted access to private documents.
8. HTTPS communication during deployment.
9. Regular PostgreSQL database backups.
10. Audit logging for important actions.
11. Protection against unauthorized access.
12. Secure management of environment variables.
13. Protection against SQL injection through Django ORM.
14. Restricted access to assessment records.
15. Session and token expiration management.

---

# CHAPTER ELEVEN: NON-FUNCTIONAL REQUIREMENTS

Performance · Usability · Reliability · Availability · Scalability · Maintainability · Compatibility (modern browsers; desktop, tablet and mobile screen sizes).

---

# CHAPTER TWELVE: DEVELOPMENT TOOLS AND TECHNOLOGIES

ReactJS · JavaScript · HTML5 · CSS3 · Bootstrap · Python · Django · Django REST Framework · PostgreSQL · pgAdmin · Axios · JWT · Git · GitHub · Visual Studio Code · Postman · Vite

---

# CHAPTER THIRTEEN: SYSTEM IMPLEMENTATION PLAN

1. Project setup · 2. Database implementation · 3. Authentication and authorization · 4. Administrator dashboard · 5. Student dashboard · 6. Academic supervisor dashboard · 7. Industrial supervisor dashboard · 8. System integration · 9. Testing · 10. Deployment

---

# CHAPTER FOURTEEN: EXPECTED SYSTEM BENEFITS

Reduced paperwork; faster placement processing; improved communication; easier progress monitoring; centralized document storage; improved supervisor accountability; faster logbook review; better visit management; accurate assessment records; easier report generation; transparent placement approval; reduced loss of records; improved accessibility.

---

# CHAPTER FIFTEEN: CONCLUSION

The system provides a centralized digital solution for managing internship and industrial attachment activities at Langata Technical and Vocational College, integrating students, academic supervisors, industrial supervisors and administrators, each with a dedicated dashboard, on a modular, secure and scalable ReactJS + Django + PostgreSQL platform.

---

# Implementation notes

How the requirements were realised, where the design document left a choice open:

| Requirement | Implementation |
|---|---|
| Registration (3.1.1, 5.1) | Students self-register; supervisor and administrator accounts are created by the administrator. Self-registration can be closed in System Settings. |
| Login | With username **or** email. JWT access token (30 min) + refresh token (1 day, rotated; blacklisted on logout, password change and deactivation). |
| Password reset (4.1) | Email link (expires in 2 hours) or administrator reset with a one-time temporary password. |
| Placement organization (4.2) | Student chooses a registered organization or types new details; a new organization is added as *Pending Verification* and becomes *Active* when the placement is approved or the administrator verifies it. |
| One open application | A student can have only one pending/returned application and one running approved placement at a time; history is kept. |
| Supervisor assignment (4.4) | The industrial supervisor must work at the placement's organization. Re-assigning replaces (deactivates) the previous assignment. |
| Logbook status | Each supervisor's review is stored separately (`logbook_reviews`). Overall: *Rejected* if either rejects, *Approved* when both approve, *Under Review* when one has approved. Correcting an entry resets both reviews. |
| Assessment rubric (3.2.10) | Academic: 6 criteria; workplace: the 10 areas of 3.3; each scored 1–5, marks = total ÷ maximum × 100. Draft (*In Progress*) → *Completed* (locked) → *Released* by the administrator, who can also re-open a completed assessment. Students see only released results. |
| Logbook review by administrator | The administrator monitors all logbooks (read-only); decisions are made by the two assigned supervisors. |
| Limited reports for supervisors | Supervisors can generate the progress, logbook and assessment reports for their own students. |
| Attachment periods and deadlines (3.4.14) | `attachment_periods` table; deadline reminders: `python manage.py send_deadline_reminders` (schedule daily). |
| Attachment completion (5.8) | The administrator moves an approved placement Not Started → Active → Completed (or Terminated). |
