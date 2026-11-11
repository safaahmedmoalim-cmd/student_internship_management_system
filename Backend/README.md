# Backend – Django REST API

Django 5 + Django REST Framework + SimpleJWT + PostgreSQL.

```
Backend/
├── config/            settings.py, urls.py, asgi.py, wsgi.py
├── apps/
│   ├── accounts/      users & roles, departments, audit logs, system settings, JWT auth, password reset
│   ├── students/      student profiles, student records & progress endpoint
│   ├── supervisors/   academic & industrial supervisor profiles, supervisor assignment, access scoping
│   ├── organizations/ host organization directory
│   ├── placements/    placement applications, attachment periods & status
│   ├── logbooks/      weekly logbooks, independent supervisor reviews, attendance
│   ├── visits/        supervision visits
│   ├── assessments/   academic & workplace assessments
│   ├── reports/       final reports, dashboards, analytics, PDF/Excel export
│   ├── announcements/ announcements
│   ├── notifications/ in-app notifications, deadline reminders
│   └── common/        shared helpers (upload validation, file download, test factories)
├── media/             private uploads: logbooks/, final_reports/, evaluation_forms/, placement_documents/
├── manage.py
└── requirements.txt
```

## Quick start

```bash
python -m venv .venv && .venv\Scripts\activate     # source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
copy .env.example .env                              # set DB_PASSWORD and DJANGO_SECRET_KEY
python manage.py migrate
python manage.py seed_demo                          # demo accounts, password Langata@2026
python manage.py runserver
```

Tests: `python manage.py test apps` (run them on SQLite with `DB_ENGINE=sqlite` if PostgreSQL is not available).

Management commands: `seed_demo [--force] [--password X]`, `send_deadline_reminders [--days N]`.

Who can see what is decided in one place, `apps/supervisors/access.py` (`visible_students`): students see
themselves, supervisors their actively assigned students, the administrator everyone.

Full endpoint list: [`../Documentation/api_documentation.md`](../Documentation/api_documentation.md).
