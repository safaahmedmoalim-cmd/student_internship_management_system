# Installation Guide

## Requirements

| Software | Version |
|---|---|
| Python | 3.12 or newer |
| Node.js | 20 or newer (with npm) |
| PostgreSQL | 14 or newer (pgAdmin optional) |
| Git | any recent version |

## 1. Get the code

```bash
git clone <repository-url> Student-Internship-Attachment-Management-System
cd Student-Internship-Attachment-Management-System
```

## 2. Create the PostgreSQL database

```bash
psql -U postgres -c "CREATE DATABASE student_internship_management;"
```

(or in pgAdmin: *Databases → Create → Database*, name `student_internship_management`).

## 3. Backend (Django)

```bash
cd Backend
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS / Linux
pip install -r requirements.txt
copy .env.example .env            # Windows   (cp .env.example .env on macOS / Linux)
```

Edit `.env`: set `DB_PASSWORD` (your postgres password) and a `DJANGO_SECRET_KEY`. Then:

```bash
python manage.py migrate          # creates all tables
python manage.py seed_demo        # optional: demonstration data for every role
# or: python manage.py createsuperuser   (creates an administrator account)
python manage.py test apps        # optional: run the test suite
python manage.py runserver        # http://127.0.0.1:8000/api/
```

Instead of `seed_demo` you can load reference data with SQL after `migrate`:
`psql -U postgres -d student_internship_management -f ../Database/sample_data.sql`
(administrator `admin` / `Langata@2026`).

### Demo accounts (`seed_demo`)

Password for all: `Langata@2026`

| Role | Usernames |
|---|---|
| Administrator | `admin` |
| Academic supervisors | `akamau`, `mnjeri` |
| Industrial supervisors | `jmwangi`, `lochieng`, `skiprop` |
| Students | `bwekesa` (active attachment with logbooks, visits, assessments), `cakinyi` (just started), `dmutiso` (approved, no supervisors), `eatieno` (pending application), `fnyambura` (no placement) |

## 4. Frontend (React + Vite)

```bash
cd Frontend
npm install
npm run dev                       # http://localhost:5173
```

`Frontend/.env` sets `VITE_API_URL=http://127.0.0.1:8000/api`. If you change the frontend address, add it
to `CORS_ALLOWED_ORIGINS` in `Backend/.env`.

## 5. Deadline reminders (optional)

Schedule this daily (cron or Windows Task Scheduler):

```bash
python manage.py send_deadline_reminders --days 3
```

## 6. Production deployment

1. `Backend/.env`: `DJANGO_DEBUG=False`, a long random `DJANGO_SECRET_KEY`, real `DJANGO_ALLOWED_HOSTS`,
   `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `FRONTEND_URL`, SMTP email settings, hosted PostgreSQL credentials.
2. `python manage.py migrate` and `python manage.py collectstatic`.
3. Run Django with gunicorn behind a reverse proxy (nginx) with HTTPS:
   `gunicorn config.wsgi --bind 127.0.0.1:8000 --workers 3`.
4. Build the frontend with `VITE_API_URL=https://your-domain/api npm run build` and serve `Frontend/dist/`
   as static files, sending unknown paths to `index.html` (single-page app).
5. Keep `Backend/media/` private (do **not** serve it publicly): files are downloaded through
   authenticated API endpoints.
6. Configure daily database backups – see `Database/backup/README.md`.

## Troubleshooting

| Problem | Fix |
|---|---|
| `connection to server ... failed: fe_sendauth: no password supplied` | Set `DB_PASSWORD` in `Backend/.env`. |
| Frontend shows "Cannot reach the server" | Start the backend; check `VITE_API_URL`. |
| Browser console shows a CORS error | Add the frontend origin to `CORS_ALLOWED_ORIGINS` and restart Django. |
| Password reset email not received | In development emails are printed in the Django terminal (console backend). |
