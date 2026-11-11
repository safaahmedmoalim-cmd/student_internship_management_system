import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { Card, DownloadButton, EmptyState, ErrorAlert, InfoRow, Loading, PageHeader, ProgressBar, StatusBadge } from '../common/ui';
import LogbookEntry from './LogbookEntry';
import useFetch from '../../hooks/useFetch';
import { formatDate, formatDateTime } from '../../services/format';

const TABS = [
  ['overview', 'Overview'], ['logbooks', 'Logbooks'], ['visits', 'Visits'], ['attendance', 'Attendance'],
  ['reports', 'Final reports'], ['assessments', 'Assessments'],
];

function TabData({ url, render, empty }) {
  const { data, loading, error, reload } = useFetch(url);
  if (loading) return <Loading />;
  if (error) return <ErrorAlert error={error} onRetry={reload} />;
  if (!data?.length) return <EmptyState text={empty} />;
  return render(data);
}

/** Full record of one student for supervisors (assigned only) and the administrator. */
export default function StudentDetailView({ backTo }) {
  const { id } = useParams();
  const [tab, setTab] = useState('overview');
  const { data: s, loading, error, reload } = useFetch(`/students/${id}/`);
  if (loading) return <Loading />;
  if (error) return <ErrorAlert error={error} onRetry={reload} />;
  const p = s.progress;

  return (
    <>
      <PageHeader title={s.full_name} subtitle={`${s.registration_number} · ${s.department_name} · ${s.academic_year}`}
        actions={<Link to={backTo} className="btn btn-outline-secondary btn-sm"><i className="bi bi-arrow-left me-1" />Back</Link>} />
      <ul className="nav nav-tabs mb-3">
        {TABS.map(([k, label]) => (
          <li className="nav-item" key={k}>
            <button type="button" className={`nav-link ${tab === k ? 'active' : ''}`} onClick={() => setTab(k)}>{label}</button>
          </li>
        ))}
      </ul>

      {tab === 'overview' && (
        <div className="row">
          <div className="col-lg-6">
            <Card title="Contact">
              <InfoRow label="Email">{s.email}</InfoRow>
              <InfoRow label="Phone">{s.phone_number}</InfoRow>
            </Card>
            <Card title="Placement">
              {p.placement ? (
                <>
                  <InfoRow label="Organization">{p.placement.organization_name} ({p.placement.county})</InfoRow>
                  <InfoRow label="Dates">{formatDate(p.placement.start_date)} – {formatDate(p.placement.end_date)}</InfoRow>
                  <InfoRow label="Application"><StatusBadge status={p.placement.application_status} label={p.placement.application_status_label} /></InfoRow>
                  <InfoRow label="Attachment"><StatusBadge status={p.placement.attachment_status} label={p.placement.attachment_status_label} /></InfoRow>
                </>
              ) : <p className="text-muted mb-0">No placement.</p>}
            </Card>
            <Card title="Supervisors">
              {p.supervisors ? (
                <>
                  <InfoRow label="Academic">{p.supervisors.academic.name} · {p.supervisors.academic.email}</InfoRow>
                  <InfoRow label="Industrial">{p.supervisors.industrial.name} · {p.supervisors.industrial.email}</InfoRow>
                  <InfoRow label="Assigned">{formatDate(p.supervisors.assigned_date)}</InfoRow>
                </>
              ) : <p className="text-muted mb-0">Not assigned.</p>}
            </Card>
          </div>
          <div className="col-lg-6">
            <Card title="Progress">
              <ProgressBar value={p.logbooks.percent} label={`Logbooks approved (${p.logbooks.approved} of ${p.logbooks.required})`} />
              <div className="mt-3">
                <InfoRow label="Logbook entries">{p.logbooks.total} submitted · {p.logbooks.pending} awaiting review · {p.logbooks.rejected} rejected</InfoRow>
                <InfoRow label="Attendance">{p.attendance.rate === null ? 'Not recorded' : `${p.attendance.rate}% (${p.attendance.present} present, ${p.attendance.late} late, ${p.attendance.absent} absent)`}</InfoRow>
                <InfoRow label="Visits">{p.visits.completed} completed · {p.visits.scheduled} upcoming</InfoRow>
                <InfoRow label="Final report">{p.final_report ? <StatusBadge status={p.final_report.status} label={`v${p.final_report.version} · ${p.final_report.status_label}`} /> : 'Not submitted'}</InfoRow>
                <InfoRow label="Academic assessment"><StatusBadge status={p.assessments.academic.status} label={p.assessments.academic.status_label} />{p.assessments.academic.marks !== null && <strong className="ms-2">{p.assessments.academic.marks}%</strong>}</InfoRow>
                <InfoRow label="Workplace assessment"><StatusBadge status={p.assessments.workplace.status} label={p.assessments.workplace.status_label} />{p.assessments.workplace.marks !== null && <strong className="ms-2">{p.assessments.workplace.marks}%</strong>}</InfoRow>
              </div>
            </Card>
          </div>
        </div>
      )}

      {tab === 'logbooks' && <TabData url={`/logbooks/?student=${id}`} empty="No logbook entries."
        render={(rows) => rows.map((e) => <LogbookEntry key={e.id} entry={e} />)} />}

      {tab === 'visits' && <TabData url={`/visits/?student=${id}`} empty="No supervision visits."
        render={(rows) => rows.map((v) => (
          <div key={v.id} className={`timeline-item ${v.visit_status === 'completed' ? 'success' : v.visit_status === 'cancelled' ? 'danger' : ''}`}>
            <div className="d-flex gap-2 align-items-center"><strong>{formatDateTime(v.visit_date)}</strong> <StatusBadge status={v.visit_status} label={v.visit_status_label} /> <span className="small text-muted">{v.visit_type_label} · {v.academic_supervisor_name}</span></div>
            <div className="small"><strong>Objectives:</strong> {v.objectives}</div>
            {v.observations && <div className="small"><strong>Observations:</strong> {v.observations}</div>}
            {v.recommendations && <div className="small"><strong>Recommendations:</strong> {v.recommendations}</div>}
          </div>
        ))} />}

      {tab === 'attendance' && <TabData url={`/attendance/?student=${id}`} empty="No attendance recorded."
        render={(rows) => (
          <div className="table-responsive card"><table className="table mb-0">
            <thead><tr><th>Date</th><th>Status</th><th>Remarks</th><th>Recorded by</th></tr></thead>
            <tbody>{rows.map((r) => <tr key={r.id}><td>{formatDate(r.attendance_date)}</td><td><StatusBadge status={r.attendance_status} label={r.attendance_status_label} /></td><td>{r.remarks || '—'}</td><td className="small">{r.recorded_by_name}</td></tr>)}</tbody>
          </table></div>
        )} />}

      {tab === 'reports' && <TabData url={`/final-reports/?student=${id}`} empty="No final report submitted."
        render={(rows) => (
          <div className="table-responsive card"><table className="table mb-0 align-middle">
            <thead><tr><th>Version</th><th>Title</th><th>Submitted</th><th>Status</th><th>Feedback</th><th /></tr></thead>
            <tbody>{rows.map((r) => <tr key={r.id}><td>v{r.version}</td><td>{r.title}</td><td className="small">{formatDateTime(r.submission_date)}</td><td><StatusBadge status={r.review_status} label={r.review_status_label} /></td><td className="small">{r.feedback || '—'}</td><td><DownloadButton url={r.download_url} label="File" name={r.original_filename} /></td></tr>)}</tbody>
          </table></div>
        )} />}

      {tab === 'assessments' && <TabData url={`/assessments/?student=${id}`} empty="No assessments you can view yet."
        render={(rows) => (
          <div className="table-responsive card"><table className="table mb-0">
            <thead><tr><th>Type</th><th>Supervisor</th><th>Marks</th><th>Status</th><th>Comments</th></tr></thead>
            <tbody>{rows.map((a) => <tr key={a.id}><td>{a.assessment_type_label}</td><td>{a.supervisor_name}</td><td>{Number(a.marks)}%</td><td><StatusBadge status={a.assessment_status} label={a.assessment_status_label} /></td><td className="small">{a.comments || '—'}</td></tr>)}</tbody>
          </table></div>
        )} />}
    </>
  );
}
