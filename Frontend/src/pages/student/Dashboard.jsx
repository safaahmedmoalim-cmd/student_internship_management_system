import { Link } from 'react-router-dom';

import { Card, EmptyState, ErrorAlert, InfoRow, Loading, PageHeader, ProgressBar, StatCard, StatusBadge } from '../../components/common/ui';
import { useAuth } from '../../context/AuthContext';
import useFetch from '../../hooks/useFetch';
import { formatDate, formatDateTime } from '../../services/format';

function Supervisor({ title, s }) {
  return (
    <div className="mb-3">
      <div className="small text-muted">{title}</div>
      <div className="fw-semibold">{s.name}</div>
      {s.job_title && <div className="small">{s.job_title}</div>}
      <div className="small"><i className="bi bi-envelope me-1" />{s.email}</div>
      {s.phone_number && <div className="small"><i className="bi bi-telephone me-1" />{s.phone_number}</div>}
    </div>
  );
}

export default function StudentDashboard() {
  const { user } = useAuth();
  const { data: d, loading, error, reload } = useFetch('/dashboard/');
  if (loading) return <Loading />;
  if (error) return <ErrorAlert error={error} onRetry={reload} />;
  const p = user.profile || {};
  const app = d.latest_application;

  return (
    <>
      <PageHeader title={`Welcome, ${p.first_name || user.username}`}
        subtitle={`${p.registration_number || ''} · ${p.department_name || ''} · ${p.academic_year || ''}`} />

      {app && ['returned', 'rejected'].includes(app.status) && (
        <div className={`alert alert-${app.status === 'returned' ? 'warning' : 'danger'}`}>
          Your placement application at <strong>{app.organization_name}</strong> was {app.status_label.toLowerCase()}.
          {app.approval_comments && <> Comments: <em>{app.approval_comments}</em></>}{' '}
          <Link to="/student/placement">Open placement</Link>
        </div>
      )}

      <div className="row g-3 mb-4">
        <div className="col-sm-6 col-xl-3">
          <StatCard label="Placement" icon="building" to="/student/placement"
            value={<StatusBadge status={d.placement?.application_status || app?.status || 'none'}
              label={d.placement?.application_status_label || app?.status_label || 'Not submitted'} />}
            hint={d.placement?.organization_name || app?.organization_name} />
        </div>
        <div className="col-sm-6 col-xl-3">
          <StatCard label="Logbooks approved" icon="journal-check" variant="success" to="/student/logbook"
            value={`${d.logbooks.approved} / ${d.logbooks.required}`} hint={`${d.logbooks.pending} awaiting review · ${d.logbooks.rejected} to correct`} />
        </div>
        <div className="col-sm-6 col-xl-3">
          <StatCard label="Attendance rate" icon="calendar-check" variant="info"
            value={d.attendance.rate === null ? '—' : `${d.attendance.rate}%`} hint={`${d.attendance.total} day(s) recorded`} />
        </div>
        <div className="col-sm-6 col-xl-3">
          <StatCard label="Final report" icon="file-earmark-text" variant="warning" to="/student/final-report"
            value={<StatusBadge status={d.final_report?.status || 'none'} label={d.final_report?.status_label || 'Not submitted'} />} />
        </div>
      </div>

      <div className="row">
        <div className="col-lg-7">
          <Card title="My attachment">
            {d.placement ? (
              <>
                <InfoRow label="Organization">{d.placement.organization_name} ({d.placement.county})</InfoRow>
                <InfoRow label="Commencement">{formatDate(d.placement.start_date)}</InfoRow>
                <InfoRow label="Completion">{formatDate(d.placement.end_date)}</InfoRow>
                <InfoRow label="Attachment status"><StatusBadge status={d.placement.attachment_status} label={d.placement.attachment_status_label} /></InfoRow>
                <div className="mt-3"><ProgressBar value={d.logbooks.percent} label="Logbook progress" /></div>
              </>
            ) : (
              <EmptyState icon="building-add" text="You do not have an approved placement yet.">
                <Link to="/student/placement" className="btn btn-primary btn-sm">Submit placement details</Link>
              </EmptyState>
            )}
          </Card>
          <Card title="Upcoming supervision visits">
            {d.upcoming_visits.length === 0 ? <p className="text-muted mb-0">No visits scheduled.</p> : (
              <ul className="list-unstyled mb-0">
                {d.upcoming_visits.map((v) => (
                  <li key={v.id} className="mb-2"><i className="bi bi-calendar-event me-2" />
                    {formatDateTime(v.visit_date)} · <span className="text-capitalize">{v.visit_type}</span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
          <Card title="Assessments">
            <InfoRow label="Academic assessment">
              <StatusBadge status={d.assessments.academic.status} label={d.assessments.academic.status_label} />
              {d.assessments.academic.marks !== null && <strong className="ms-2">{d.assessments.academic.marks}%</strong>}
            </InfoRow>
            <InfoRow label="Workplace assessment">
              <StatusBadge status={d.assessments.workplace.status} label={d.assessments.workplace.status_label} />
              {d.assessments.workplace.marks !== null && <strong className="ms-2">{d.assessments.workplace.marks}%</strong>}
            </InfoRow>
            <p className="small text-muted mt-2 mb-0">Marks become visible once the administrator releases them.</p>
          </Card>
        </div>
        <div className="col-lg-5">
          <Card title="Assigned supervisors">
            {d.supervisors ? (
              <>
                <Supervisor title="Academic supervisor" s={d.supervisors.academic} />
                <Supervisor title="Industrial supervisor" s={d.supervisors.industrial} />
              </>
            ) : <p className="text-muted mb-0">Supervisors are assigned after your placement is approved.</p>}
          </Card>
          <Card title="Announcements" actions={<Link to="/announcements" className="small">View all</Link>}>
            {d.announcements.length === 0 ? <p className="text-muted mb-0">No announcements.</p> : d.announcements.map((a) => (
              <div key={a.id} className="mb-3">
                <div className="fw-semibold">{a.title}</div>
                <div className="small text-muted">{formatDate(a.publication_date)}</div>
                <div className="small pre-wrap">{a.message}</div>
              </div>
            ))}
          </Card>
        </div>
      </div>
    </>
  );
}
