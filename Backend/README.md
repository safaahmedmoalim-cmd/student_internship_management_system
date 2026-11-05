# Langata College Internship & Attachment Management – Backend

Django 5.1 + Django REST Framework API for the four roles in the portal: **student, academic supervisor,
industrial supervisor, coordinator**. Token authentication, role-based access, no database foreign keys
(tables are related only through id columns and joined by the ORM).

> **Status:** the code was written and statically checked (compiles, imports and URL names resolve,
> serializer fields match the models) but it has **not been run**, and the test suite has **not been
> executed**, because Django could not be installed where it was written. Run the steps below, then
> `python manage.py test`, and report anything that fails.

## 1. Setup

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                 # edit SECRET_KEY, COORDINATOR_ACCESS_CODE, etc.

python manage.py makemigrations accounts attachments    # migrations are not shipped - generate them first
python manage.py migrate
python manage.py seed_demo                              # optional, development only
python manage.py createsuperuser                        # optional, for /admin/
python manage.py test                                   # run the test suite
python manage.py runserver                              # http://127.0.0.1:8000/api/
```

`seed_demo` creates `coordinator@`, `academic@`, `industrial@`, `student@`, `brian@` and `grace@`
`langata.ac.ke`, all with password `demo1234` (`--password` to change, `--force` to recreate).

## 2. Database

SQLite is the default. For MySQL:

1. Create an empty database: `CREATE DATABASE langata_django CHARACTER SET utf8mb4;`
2. `pip install mysqlclient`
3. In `.env` set `DB_ENGINE=mysql` and the `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` values.
4. Run `migrate`.

`DB_ENGINE=postgres` works the same way (`pip install psycopg[binary]`).
This Django-managed database is separate from the hand-written `langata_attachment` MySQL script.

## 3. Using the API

Sign in, then send the token on every request: `Authorization: Token <key>`.

```bash
curl -X POST localhost:8000/api/auth/login/ -H 'Content-Type: application/json' \
     -d '{"email":"student@langata.ac.ke","password":"demo1234"}'
curl localhost:8000/api/dashboard/ -H 'Authorization: Token <key>'
```

| Endpoint | Who | Purpose |
|---|---|---|
| `POST auth/register/` | public | Sign up (any role; coordinator needs `access_code`) |
| `POST auth/login/` | public | `{email, password, role?}` → `{token, user}` |
| `POST auth/logout/` | any | Invalidate token |
| `GET/PATCH auth/me/` | any | View / edit own profile |
| `POST auth/change-password/` | any | Returns a new token |
| `GET supervisors/?role=` | any | Industrial list (coordinator: also academic) |
| `GET meta/` | public | Courses, years, rating criteria, limits |
| `GET dashboard/` | any | Role-specific numbers and lists |
| `GET/POST placements/` | student creates; all read (scoped) | Placement details |
| `POST placements/<id>/approve\|reject/` | coordinator | Decide (reject needs `comment`) |
| `DELETE placements/<id>/` | student | Withdraw a pending/rejected placement |
| `GET/POST logbook/` | student creates; all read (scoped) | Weekly entries (placement must be approved) |
| `POST logbook/<id>/approve\|reject/` | industrial supervisor | Review |
| `POST logbook/<id>/comment/` | academic supervisor | Feedback |
| `GET/POST final-reports/` | student uploads (multipart: title, summary, file) | pdf/doc/docx, ≤ 10 MB |
| `GET final-reports/<id>/download/` | authorised viewers | Authenticated file download |
| `POST final-reports/<id>/review/` | academic supervisor | Mark reviewed |
| `GET/POST visits/`, `POST visits/<id>/complete\|cancel/` | academic supervisor | Supervision visits |
| `GET/POST assessments/` | academic (marks) / industrial (5 ratings 1–5) | Industrial marks = sum × 100 / 25 |
| `GET/POST/DELETE announcements/` | all read; coordinator writes | Notices |
| `GET students/`, `GET students/<id>/` | staff roles | Progress per student (`search`, `course`, `placement_status`) |
| `PATCH students/<id>/assign/` | coordinator | Set academic / industrial supervisor |
| `GET reports/summary/`, `reports/summary.csv` | coordinator | Results for every student |

Visibility: a student sees only their own records, an academic supervisor their assigned students,
an industrial supervisor their assigned interns, the coordinator everyone.

## 4. Configuration (`.env`)

`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DB_*`, `CORS_ALLOWED_ORIGINS`, `COORDINATOR_ACCESS_CODE`
(empty disables coordinator self-sign-up), `TARGET_HOURS`, `MAX_REPORT_SIZE_MB`. See `.env.example`.

For production: `DEBUG=False`, a long random `SECRET_KEY`, real `ALLOWED_HOSTS`, run behind HTTPS with
`gunicorn config.wsgi`, and serve `MEDIA_ROOT` (uploaded reports) from private storage.
