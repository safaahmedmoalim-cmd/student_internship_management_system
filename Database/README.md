# Database

PostgreSQL database **`student_internship_management`**, managed by Django migrations.

| File | Purpose |
|---|---|
| [`database_design.md`](database_design.md) | Tables, fields, relationships, ER diagram, status values |
| [`schema.sql`](schema.sql) | Generated reference DDL of every table (regenerate with `generate_schema.py`) |
| [`sample_data.sql`](sample_data.sql) | Departments, organizations, an attachment period and an administrator account |
| [`generate_schema.py`](generate_schema.py) | Rebuilds the DDL from the Django models without a database server |
| [`backup/`](backup/) | Backup and restore instructions; backup files are stored here (git-ignored) |

Create the tables with `cd Backend && python manage.py migrate`; see
[`../Documentation/installation_guide.md`](../Documentation/installation_guide.md).
