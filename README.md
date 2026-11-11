# Student Internship and Attachment Management System

Web-based system for managing student internship and industrial attachment at
**Langata Technical and Vocational College**: placement applications and approval, supervisor
assignment, weekly logbooks reviewed by two supervisors, supervision visits, attendance, academic and
workplace assessments, final reports, announcements, notifications and reports.

| Layer | Technology |
|---|---|
| Frontend | ReactJS (Vite), Bootstrap 5, Axios, React Router |
| Backend | Python Django, Django REST Framework, JWT (SimpleJWT) |
| Database | PostgreSQL (`student_internship_management`) |

## Users

| Role | Main tasks |
|---|---|
| Student | Register, submit/withdraw/resubmit placement, weekly logbooks, final report, view results |
| Academic supervisor | Assigned students, logbook review, supervision visits, final report review, academic assessment |
| Industrial supervisor | Assigned interns, logbook approval, attendance, workplace evaluation |
| Administrator | Users, departments, organizations, periods, placement approval, supervisor assignment, announcements, assessment release, reports, audit logs, settings |

## Project structure

```
├── Frontend/        React app (src/pages/{auth,student,academic,industrial,admin}, components, services, ...)
├── Backend/         Django project (config/, apps/<11 modules>/, media/)
├── Database/        schema.sql, sample_data.sql, database_design.md, backup/
└── Documentation/   system_requirements.md, user_manual.md, api_documentation.md, installation_guide.md
```

## Run it

```bash
# Backend
cd Backend
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env          # set DB_PASSWORD (PostgreSQL) and DJANGO_SECRET_KEY
python manage.py migrate
python manage.py seed_demo      # demo data; every account's password is Langata@2026
python manage.py runserver

# Frontend (second terminal)
cd Frontend
npm install
npm run dev                     # http://localhost:5173
```

Sign in as `admin`, `akamau` (academic), `jmwangi` (industrial) or `bwekesa` (student).

See [Documentation/installation_guide.md](Documentation/installation_guide.md) for details and deployment,
[Documentation/user_manual.md](Documentation/user_manual.md) for how to use each dashboard and
[Documentation/api_documentation.md](Documentation/api_documentation.md) for the REST API.
