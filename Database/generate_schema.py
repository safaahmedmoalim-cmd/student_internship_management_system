"""Regenerate Database/schema.sql from the Django models without a database server.

Usage (from the project root):
    Backend/.venv/Scripts/python Database/generate_schema.py Backend > Database/schema_body.sql
"""
import os
import sys

sys.path.insert(0, sys.argv[1])
os.environ['DB_ENGINE'] = 'postgres'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django  # noqa: E402

django.setup()
from django.db import connection  # noqa: E402

connection.__dict__['pg_version'] = 180000  # skip the version query


def _q(v):
    if v is None:
        return 'NULL'
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


connection.ops.compose_sql = lambda sql, params: sql % tuple(_q(x) for x in params) if params else sql
from django.apps import apps  # noqa: E402

LOCAL = ['accounts', 'students', 'supervisors', 'organizations', 'placements', 'logbooks', 'visits',
         'assessments', 'reports', 'announcements', 'notifications']
order = LOCAL + ['auth', 'contenttypes', 'admin', 'sessions', 'token_blacklist']
models = [m for label in order for m in apps.get_app_config(label).get_models()]
with connection.schema_editor(collect_sql=True, atomic=False) as editor:
    for m in models:
        editor.create_model(m)
print(chr(10).join(editor.collected_sql))
