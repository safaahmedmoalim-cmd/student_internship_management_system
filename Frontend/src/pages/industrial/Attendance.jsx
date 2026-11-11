import { useEffect, useState } from 'react';

import { Card, EmptyState, ErrorAlert, Loading, PageHeader, StatusBadge } from '../../components/common/ui';
import { useToast } from '../../context/ToastContext';
import useFetch from '../../hooks/useFetch';
import api, { errorMessage } from '../../services/api';
import { formatDate, todayISO } from '../../services/format';

const STATUSES = [['present', 'Present'], ['late', 'Late'], ['absent', 'Absent'], ['excused', 'Excused']];

export default function IndustrialAttendance() {
  const toast = useToast();
  const [day, setDay] = useState(todayISO());
  const interns = useFetch('/students/');
  const recorded = useFetch('/attendance/', { date: day });
  const history = useFetch('/attendance/');
  const [rows, setRows] = useState({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const existing = Object.fromEntries((recorded.data || []).map((a) => [a.student, { attendance_status: a.attendance_status, remarks: a.remarks }]));
    setRows(Object.fromEntries((interns.data || []).map((s) => [s.id, existing[s.id] || { attendance_status: 'present', remarks: '' }])));
  }, [interns.data, recorded.data]);

  const set = (id, key, value) => setRows((r) => ({ ...r, [id]: { ...r[id], [key]: value } }));

  const save = async () => {
    setSaving(true);
    try {
      await api.post('/attendance/bulk/', {
        attendance_date: day,
        records: Object.entries(rows).map(([student, r]) => ({ student: Number(student), ...r })),
      });
      toast(`Attendance saved for ${formatDate(day)}.`);
      recorded.reload();
      history.reload();
    } catch (e) {
      toast(errorMessage(e), 'danger');
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <PageHeader title="Attendance" subtitle="Record daily attendance and punctuality of your interns" />
      <Card title="Daily register" actions={(
        <input type="date" className="form-control form-control-sm" value={day} max={todayISO()} onChange={(e) => setDay(e.target.value)} aria-label="Attendance date" />
      )}>
        <ErrorAlert error={interns.error} onRetry={interns.reload} />
        {interns.loading ? <Loading /> : (interns.data || []).length === 0 ? <EmptyState icon="people" text="No interns assigned to you." /> : (
          <>
            <div className="table-responsive">
              <table className="table align-middle">
                <thead><tr><th>Intern</th><th>Status</th><th>Remarks</th></tr></thead>
                <tbody>
                  {interns.data.map((s) => (
                    <tr key={s.id}>
                      <td>{s.full_name}<div className="small text-muted">{s.registration_number}</div></td>
                      <td>
                        <div className="btn-group btn-group-sm flex-wrap" role="group" aria-label={`Attendance for ${s.full_name}`}>
                          {STATUSES.map(([v, label]) => (
                            <button key={v} type="button" onClick={() => set(s.id, 'attendance_status', v)}
                              className={`btn ${rows[s.id]?.attendance_status === v ? 'btn-primary' : 'btn-outline-primary'}`}>{label}</button>
                          ))}
                        </div>
                      </td>
                      <td><input className="form-control form-control-sm" value={rows[s.id]?.remarks || ''} maxLength={255}
                        onChange={(e) => set(s.id, 'remarks', e.target.value)} aria-label={`Remarks for ${s.full_name}`} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <button type="button" className="btn btn-primary" onClick={save} disabled={saving}>
              {saving && <span className="spinner-border spinner-border-sm me-2" />}Save attendance
            </button>
            {(recorded.data || []).length > 0 && <span className="small text-muted ms-3">Already recorded for this day — saving updates it.</span>}
          </>
        )}
      </Card>
      <Card title="Recent attendance records" bodyClass="p-0">
        {history.loading ? <div className="p-3"><Loading /></div> : (history.data || []).length === 0 ? <EmptyState text="Nothing recorded yet." /> : (
          <div className="table-responsive">
            <table className="table mb-0">
              <thead><tr><th>Date</th><th>Intern</th><th>Status</th><th>Remarks</th></tr></thead>
              <tbody>
                {history.data.slice(0, 50).map((a) => (
                  <tr key={a.id}><td>{formatDate(a.attendance_date)}</td><td>{a.student_name}</td>
                    <td><StatusBadge status={a.attendance_status} label={a.attendance_status_label} /></td><td className="small">{a.remarks || '—'}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  );
}
