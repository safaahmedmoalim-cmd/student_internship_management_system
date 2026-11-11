import { DownloadButton, StatusBadge } from '../common/ui';
import { formatDate, formatDateTime } from '../../services/format';

function Section({ title, text }) {
  if (!text) return null;
  return (
    <div className="mb-2">
      <div className="small fw-semibold text-muted">{title}</div>
      <div className="pre-wrap">{text}</div>
    </div>
  );
}

/** One weekly logbook entry with both supervisors' independent reviews. */
export default function LogbookEntry({ entry, showStudent = false, actions }) {
  return (
    <div className="card mb-3">
      <div className="card-header bg-white d-flex flex-wrap justify-content-between align-items-center gap-2">
        <div>
          <strong>Week {entry.week_number}</strong>
          <span className="text-muted small ms-2">{formatDate(entry.start_date)} – {formatDate(entry.end_date)}</span>
          {showStudent && <span className="ms-2">· {entry.student.full_name} <span className="text-muted small">({entry.student.registration_number})</span></span>}
        </div>
        <div className="d-flex align-items-center gap-2">
          <StatusBadge status={entry.status} label={entry.status_label} />
          {actions}
        </div>
      </div>
      <div className="card-body">
        <Section title="Activities performed" text={entry.activities} />
        <Section title="Skills acquired" text={entry.skills_acquired} />
        <Section title="Challenges experienced" text={entry.challenges} />
        <Section title="Solutions applied" text={entry.solutions} />
        {entry.attachment_url && <DownloadButton url={entry.attachment_url} label={entry.attachment_name || 'Attachment'} />}
        <div className="small text-muted mt-2">Submitted {formatDateTime(entry.submission_date)}</div>
        <div className="row g-2 mt-2">
          {entry.reviews.map((r) => (
            <div className="col-md-6" key={r.id}>
              <div className={`border rounded p-2 h-100 ${r.review_status === 'rejected' ? 'border-danger' : r.review_status === 'approved' ? 'border-success' : ''}`}>
                <div className="d-flex justify-content-between">
                  <span className="small fw-semibold">{r.supervisor_role_label}</span>
                  <StatusBadge status={r.review_status} label={r.review_status_label} />
                </div>
                <div className="small text-muted">{r.supervisor_name}{r.review_date && ` · ${formatDateTime(r.review_date)}`}</div>
                {r.comments && <div className="small mt-1 pre-wrap">“{r.comments}”</div>}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
