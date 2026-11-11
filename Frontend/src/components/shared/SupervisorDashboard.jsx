import { Link } from 'react-router-dom';

import { Card, ErrorAlert, Loading, PageHeader, StatCard, StatusBadge } from '../common/ui';
import useFetch from '../../hooks/useFetch';
import { formatDate, formatDateTime } from '../../services/format';

/** Dashboard overview for academic and industrial supervisors. */
export default function SupervisorDashboard({ role }) {
  const { data: d, loading, error, reload } = useFetch('/dashboard/');
  if (loading) return <Loading />;
  if (error) return <ErrorAlert error={error} onRetry={reload} />;
  const academic = role === 'academic';
  const base = academic ? '/academic' : '/industrial';
  const studentsPath = academic ? '/academic/students' : '/industrial/interns';

  return (
    <>
      <PageHeader title={`Welcome, ${d.full_name}`}
        subtitle={academic ? 'Academic supervisor dashboard' : `Industrial supervisor · ${d.organization_name}`} />
      <div className="row g-3 mb-4">
        <div className="col-sm-6 col-xl-3"><StatCard label={academic ? 'Assigned students' : 'Assigned interns'} value={d.assigned_students} icon="people" to={studentsPath} /></div>
        <div className="col-sm-6 col-xl-3"><StatCard label="Logbooks awaiting my review" value={d.pending_logbook_reviews} icon="journal-text" variant="warning" to={`${base}/logbooks`} /></div>
        {academic ? (
          <div className="col-sm-6 col-xl-3"><StatCard label="Final reports to review" value={d.pending_report_reviews} icon="file-earmark-text" variant="info" to="/academic/final-reports" /></div>
        ) : (
          <div className="col-sm-6 col-xl-3"><StatCard label="Attendance recorded today" value={`${d.attendance_recorded_today} / ${d.assigned_students}`} icon="calendar-check" variant="info" to="/industrial/attendance" /></div>
        )}
        <div className="col-sm-6 col-xl-3"><StatCard label={academic ? 'Assessments pending' : 'Evaluations pending'} value={d.assessments_pending} icon="clipboard-check" variant="danger"
          to={academic ? '/academic/assessments' : '/industrial/evaluations'} hint={`${d.assessments_completed} completed`} /></div>
      </div>
      <div className="row">
        <div className="col-lg-8">
          <Card title={academic ? 'My students' : 'My interns'} actions={<Link to={studentsPath} className="small">View all</Link>} bodyClass="p-0">
            {d.students.length === 0 ? <p className="text-muted p-3 mb-0">Nobody is assigned to you yet.</p> : (
              <div className="table-responsive">
                <table className="table mb-0 align-middle">
                  <thead><tr><th>Student</th><th>Organization</th><th>Attachment</th><th>Logbooks</th></tr></thead>
                  <tbody>
                    {d.students.map((s) => (
                      <tr key={s.id}>
                        <td><Link to={`${studentsPath}/${s.id}`}>{s.full_name}</Link><div className="small text-muted">{s.registration_number}</div></td>
                        <td className="small">{s.organization_name}</td>
                        <td><StatusBadge status={s.attachment_status} /></td>
                        <td className="small">{s.logbooks_approved}/{s.logbooks_total}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>
        <div className="col-lg-4">
          {academic && (
            <Card title="Upcoming visits" actions={<Link to="/academic/visits" className="small">Manage</Link>}>
              {d.upcoming_visits.length === 0 ? <p className="text-muted mb-0">No visits scheduled.</p> : d.upcoming_visits.map((v) => (
                <div key={v.id} className="mb-2">
                  <div className="fw-semibold">{v.student_name}</div>
                  <div className="small text-muted">{formatDateTime(v.visit_date)} · {v.visit_type} · {v.organization_name}</div>
                </div>
              ))}
            </Card>
          )}
          <Card title="Announcements" actions={<Link to="/announcements" className="small">View all</Link>}>
            {d.announcements.length === 0 ? <p className="text-muted mb-0">No announcements.</p> : d.announcements.map((a) => (
              <div key={a.id} className="mb-3"><div className="fw-semibold">{a.title}</div><div className="small text-muted">{formatDate(a.publication_date)}</div><div className="small pre-wrap">{a.message}</div></div>
            ))}
          </Card>
        </div>
      </div>
    </>
  );
}
