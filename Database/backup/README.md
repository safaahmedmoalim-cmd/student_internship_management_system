# Database backups

Backup files (`*.dump`, `*.sql`) are written here and are ignored by git.

## Create a backup

```bash
pg_dump -U postgres -h localhost -F c -f backup/sims_$(date +%Y%m%d_%H%M).dump student_internship_management
```

Windows (PowerShell):

```powershell
pg_dump -U postgres -h localhost -F c -f "backup\sims_$(Get-Date -Format yyyyMMdd_HHmm).dump" student_internship_management
```

Also back up `Backend/media/` (uploaded logbook attachments, final reports and evaluation forms).
The database only stores the file paths.

## Restore

```bash
createdb -U postgres student_internship_management
pg_restore -U postgres -h localhost -d student_internship_management --clean --if-exists backup/<file>.dump
```

## Schedule

In production, run the backup daily (cron or Windows Task Scheduler), keep at least 14 daily copies,
and store one copy off the server.
