import { Link } from 'react-router-dom';

import { Card, ErrorAlert, Loading, PageHeader, StatCard, StatusBadge } from '../../components/common/ui';
import useFetch from '../../hooks/useFetch';
import { formatDate } from '../../services/format';

export default function AdminDashboard() {
  const { data: d, loading, error, reload } = useFetch('/dashboard/');
  if (loading) return <Loading />;
  if (error) return <ErrorAlert error={error} onRetry={reload} />;
  const max = Math.max(1, ...d.placement_status_chart.map((x) => x.count));

  const stats = [
    ['Registered students', d.total_students, 'mortarboard', 'primary', '/admin/students'],
    ['Academic supervisors', d.total_academic_supervisors, 'person-video3', 'primary', '/admin/users'],
    ['Industrial supervisors', d.total_industrial_supervisors, 'briefcase', 'primary', '/admin/users'],
    ['Host organizations', d.total_organizations, 'buildings', 'primary', '/admin/organizations'],
    ['Pending placements', d.pending_placements, 'hourglass-split', 'warning', '/admin/placements'],
    ['Approved placements', d.approved_placements, 'check-circle', 'success', '/admin/placements'],
    ['Rejected placements', d.rejected_placements, 'x-circle', 'danger', '/admin/placements'],
    ['Active attachment students', d.active_attachment_students, 'activity', 'success', '/admin/students'],
    ['Pending logbook reviews', d.pending_logbook_reviews, 'journal-text', 'warning', '/admin/logbooks'],
    ['Completed assessments (to release)', d.completed_assessments, 'award', 'info', '/admin/assessments'],
    ['Placements without supervisors', d.unassigned_placements, 'person-exclamation', 'danger', '/admin/assignments'],
    ['Completed attachments', d.completed_attachments, 'flag', 'success', '/admin/reports'],
  ];

  return (
    <>
      <PageHeader title="Administrator Dashboard" subtitle="Overview of the internship and attachment process" />
      {d.organizations_pending_verification > 0 && (
        <div className="alert alert-info">
          {d.organizations_pending_verification} organization(s) added by students are waiting for verification. <Link to="/admin/organizations">Review</Link>
        </div>
      )}
      <div className="row g-3 mb-4">
        {stats.map(([label, value, icon, variant, to]) => (
          <div className="col-sm-6 col-lg-4 col-xl-3" key={label}><StatCard label={label} value={value} icon={icon} variant={variant} to={to} /></div>
        ))}
      </div>
      <div className="row">
        <div className="col-lg-5">
          <Card title="Placement applications by status">
            {d.placement_status_chart.map((x) => (
              <div key={x.status} className="mb-2">
                <div className="d-flex justify-content-between small"><span>{x.status}</span><strong>{x.count}</strong></div>
                <div className="bg-light rounded"><div className="chart-bar" style={{ width: `${(x.count / max) * 100}%`, minWidth: x.count ? 6 : 0 }} /></div>
              </div>
            ))}
          </Card>
          <Card title="Announcements" actions={<Link to="/admin/announcements" className="small">Manage</Link>}>
            {d.announcements.length === 0 ? <p className="text-muted mb-0">None published.</p> : d.announcements.map((a) => (
              <div key={a.id} className="mb-2"><div className="fw-semibold">{a.title}</div><div className="small text-muted">{formatDate(a.publication_date)}</div></div>
            ))}
          </Card>
        </div>
        <div className="col-lg-7">
          <Card title="Recent placement applications" actions={<Link to="/admin/placements" className="small">View all</Link>} bodyClass="p-0">
            <div className="table-responsive">
              <table className="table mb-0 align-middle">
                <thead><tr><th>Student</th><th>Organization</th><th>Applied</th><th>Status</th></tr></thead>
                <tbody>
                  {d.recent_placements.map((p) => (
                    <tr key={p.id}><td>{p.student_name}</td><td className="small">{p.organization_name}</td><td className="small">{formatDate(p.application_date)}</td>
                      <td><StatusBadge status={p.status} label={p.status_label} /></td></tr>
                  ))}
                  {d.recent_placements.length === 0 && <tr><td colSpan={4} className="text-muted">No applications yet.</td></tr>}
                </tbody>
              </table>
            </div>
          </Card>
          <div className="row g-3">
            <div className="col-sm-6"><StatCard label="Final reports awaiting review" value={d.pending_final_reports} icon="file-earmark-text" variant="info" /></div>
            <div className="col-sm-6"><StatCard label="Released assessments" value={d.released_assessments} icon="send-check" variant="success" to="/admin/assessments" /></div>
          </div>
        </div>
      </div>
    </>
  );
}
