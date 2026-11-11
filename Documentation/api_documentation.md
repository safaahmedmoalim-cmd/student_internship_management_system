# API Documentation

Base URL (development): `http://127.0.0.1:8000/api/`

All requests and responses are JSON, except file uploads (`multipart/form-data`) and downloads/exports.

## Authentication

JWT (djangorestframework-simplejwt). Send the access token on every request:

```
Authorization: Bearer <access token>
```

The access token lasts 30 minutes; get a new one with the refresh token (`POST auth/refresh/`).
Refresh tokens rotate (each refresh returns a new one) and are blacklisted on logout, on password change/reset
and when an account is deactivated.

```bash
curl -X POST http://127.0.0.1:8000/api/auth/login/ -H "Content-Type: application/json" \
     -d '{"username": "bwekesa", "password": "Langata@2026"}'
# -> {"access": "...", "refresh": "...", "user": {...}}
curl http://127.0.0.1:8000/api/dashboard/ -H "Authorization: Bearer <access>"
```

Errors use normal HTTP codes: `400` validation (`{"field": ["message"]}` or `{"detail": "..."}`),
`401` not signed in / token expired, `403` role not allowed, `404` not found **or not visible to you**
(supervisors get 404 for students who are not assigned to them).

Roles: `student`, `academic`, `industrial`, `admin`.

---

## Accounts (`apps.accounts`)

| Method & path | Who | Description |
|---|---|---|
| `POST auth/register/` | public | Student self-registration: `username, email, password, confirm_password, registration_number, first_name, last_name, phone_number, department, academic_year` → tokens + user |
| `POST auth/login/` | public | `{username (or email), password}` → `{access, refresh, user}` |
| `POST auth/refresh/` | public | `{refresh}` → `{access, refresh}` |
| `POST auth/logout/` | any | `{refresh}` – blacklists the refresh token |
| `GET / PATCH auth/me/` | any | Own account. PATCH: `email`, `first_name`, `last_name`, `phone_number`, `job_title` (industrial) |
| `POST auth/change-password/` | any | `{current_password, new_password, confirm_password}` → new tokens |
| `POST auth/password-reset/` | public | `{email}` – emails a reset link (always 200) |
| `POST auth/password-reset/confirm/` | public | `{uid, token, new_password, confirm_password}` |
| `GET users/` | admin | `?role= &is_active=true\|false &search=` |
| `POST users/` | admin | `{username, email, role, password?, profile: {...}}` – omit password to get `temporary_password` back |
| `GET / PATCH users/<id>/` | admin | Role cannot be changed |
| `POST users/<id>/activate/`, `deactivate/` | admin | |
| `POST users/<id>/reset-password/` | admin | `{new_password?}` → `{temporary_password}` |
| `GET departments/` | public | List (used by registration) |
| `POST / PATCH / DELETE departments/<id>/` | admin | `department_name, department_code, description` |
| `GET audit-logs/` | admin | `?action= &user= &search= &date_from= &date_to=` (latest 500) |
| `GET / PATCH settings/` | admin | `institution_name, allow_student_registration, required_logbook_weeks` |
| `GET settings/public/` | public | `institution_name, allow_student_registration` |

`profile` for `POST users/`:

| Role | Fields |
|---|---|
| student | `registration_number, first_name, last_name, phone_number, department, academic_year` |
| academic | `staff_number, first_name, last_name, phone_number, department` |
| industrial | `organization, employee_number, first_name, last_name, phone_number, job_title` |
| admin | – |

## Organizations (`apps.organizations`)

| Method & path | Who | Description |
|---|---|---|
| `GET organizations/` | any (non-admins see active only) | `?status= &county= &search=` |
| `POST / PATCH / DELETE organizations/<id>/` | admin | `organization_name, address, county, contact_person, phone_number, email, industry_category, status (active\|pending\|inactive)` |

## Placements (`apps.placements`)

| Method & path | Who | Description |
|---|---|---|
| `GET placements/` | student (own), supervisors (assigned), admin (all) | `?status= &attachment_status= &organization= &search= &unassigned=true` |
| `POST placements/` | student | multipart: `organization` **or** `organization_name, address, county, contact_person, phone_number, email, industry_category`; `attachment_period?, start_date, end_date, supporting_document?` |
| `PUT placements/<id>/` | student | Correct and resubmit a *pending* or *returned* application (same fields) |
| `POST placements/<id>/withdraw/` | student | `{reason}` |
| `POST placements/<id>/approve/` | admin | `{comments?}` |
| `POST placements/<id>/reject/` | admin | `{comments}` (required) |
| `POST placements/<id>/return/` | admin | `{comments}` (required) |
| `POST placements/<id>/attachment-status/` | admin | `{attachment_status: active\|completed\|terminated}` |
| `GET placements/<id>/document/` | authorised viewers | Supporting document download |
| `GET attachment-periods/` | any (`?active=true`) | |
| `POST / PATCH attachment-periods/<id>/` | admin | `name, start_date, end_date, application_deadline, report_deadline, is_active` |

## Supervisors and assignment (`apps.supervisors`)

| Method & path | Who | Description |
|---|---|---|
| `GET supervisors/academic/` | admin | `?department=` (includes `active_students`) |
| `GET supervisors/industrial/` | admin | `?organization=` |
| `GET assignments/` | scoped | `?status=active\|inactive &placement=` |
| `POST assignments/` | admin | `{placement, academic_supervisor, industrial_supervisor}` – ids of supervisor **profiles**; replaces an existing active assignment |
| `POST assignments/<id>/deactivate/` | admin | |

## Students (`apps.students`)

| Method & path | Who | Description |
|---|---|---|
| `GET students/` | academic, industrial (assigned), admin (all) | Summary rows. `?search= &department= &placement_status=` |
| `GET students/<id>/` | same | Summary + `progress` (placement, supervisors, logbooks, attendance, visits, final report, assessments) |

## Logbooks and attendance (`apps.logbooks`)

| Method & path | Who | Description |
|---|---|---|
| `GET logbooks/` | scoped | `?student= &status= &week= &pending_my_review=true` |
| `POST logbooks/` | student | multipart: `week_number, start_date, end_date, activities, skills_acquired?, challenges?, solutions?, attachment?` – needs an approved placement with supervisors |
| `PATCH logbooks/<id>/` | student | Correct a *submitted* or *rejected* entry; both reviews reset to pending |
| `POST logbooks/<id>/review/` | academic, industrial | `{decision: approved\|rejected, comments}` – comments required to reject |
| `GET logbooks/<id>/attachment/` | authorised viewers | |
| `GET attendance/` | scoped | `?student= &date= &date_from= &date_to=` |
| `POST attendance/` | industrial | `{student, attendance_date, attendance_status: present\|absent\|late\|excused, remarks}` (updates if the day exists) |
| `POST attendance/bulk/` | industrial | `{attendance_date, records: [{student, attendance_status, remarks}]}` |
| `PATCH / DELETE attendance/<id>/` | industrial | |

## Supervision visits (`apps.visits`)

| Method & path | Who | Description |
|---|---|---|
| `GET visits/` | scoped | `?student= &status= &upcoming=true` |
| `POST visits/` | academic, admin | `{student, visit_date (ISO datetime), visit_type: physical\|virtual, meeting_link?, objectives, academic_supervisor? (admin)}` |
| `POST visits/<id>/reschedule/` | academic, admin | `{visit_date, reason?}` |
| `POST visits/<id>/cancel/` | academic, admin | `{reason?}` |
| `POST visits/<id>/complete/` | academic, admin | `{observations, recommendations?}` – after the visit date |

## Assessments (`apps.assessments`)

| Method & path | Who | Description |
|---|---|---|
| `GET assessments/` | student: released only; supervisors: own + released; admin: all | `?student= &status= &type=academic\|workplace` |
| `GET assessments/criteria/` | any | Rubric criteria |
| `POST assessments/` | academic, industrial | `{student, assessment_criteria: {criterion: 1-5}, comments?, recommendations?, evaluation_form? (multipart), submit: bool}` |
| `PUT assessments/<id>/` | owner, while *in_progress* | Same fields (without `student`) |
| `POST assessments/<id>/release/` | admin | Completed → released (student notified) |
| `POST assessments/<id>/reopen/` | admin | Completed → in progress |
| `GET assessments/<id>/evaluation-form/` | authorised viewers | |

Marks = sum of scores ÷ (number of criteria × 5) × 100.

## Final reports, dashboards and reports (`apps.reports`)

| Method & path | Who | Description |
|---|---|---|
| `GET final-reports/` | scoped | `?student= &status=` – all versions |
| `POST final-reports/` | student | multipart `{title, report_file (pdf/doc/docx ≤ 10 MB)}` – new version; blocked while the latest is submitted/under review/approved |
| `POST final-reports/<id>/start-review/` | academic | |
| `POST final-reports/<id>/approve/` | academic | `{feedback?}` |
| `POST final-reports/<id>/return/` | academic | `{feedback}` (required) |
| `GET final-reports/<id>/download/` | authorised viewers | |
| `GET dashboard/` | any | Role-specific dashboard data |
| `GET meta/` | public | Status choices, rubric criteria, upload limits |
| `GET reports/` | staff roles | Reports available to the caller |
| `GET reports/<slug>/` | admin; supervisors for some | `?department= &status= &export=pdf\|xlsx` |

Report slugs: `students`, `placements`, `supervisor-allocation` (admin only), `logbooks`, `assessments`,
`attachment-progress`, `completed-attachments` (supervisors: own students only).

## Announcements and notifications

| Method & path | Who | Description |
|---|---|---|
| `GET announcements/` | any | Published, unexpired, for the caller's role (admin: all, `?audience=`) |
| `POST / PATCH / DELETE announcements/<id>/` | admin | `{title, message, target_audience: all\|student\|academic\|industrial, publication_date?, expiry_date?}` – recipients are notified |
| `GET notifications/` | any | Own, latest 100, `?unread=true` |
| `GET notifications/unread-count/` | any | `{unread}` |
| `POST notifications/<id>/read/`, `POST notifications/read-all/` | any | |
| `DELETE notifications/<id>/` | any | |

## Postman

Import the endpoints above, set a collection variable `base_url = http://127.0.0.1:8000/api` and an
`Authorization: Bearer {{access}}` header; save `access` from the login response with a test script:
`pm.collectionVariables.set("access", pm.response.json().access)`.
