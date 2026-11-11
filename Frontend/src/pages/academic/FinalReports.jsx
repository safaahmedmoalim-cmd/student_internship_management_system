import { useState } from 'react';

import { DownloadButton, EmptyState, ErrorAlert, Loading, PageHeader, StatusBadge } from '../../components/common/ui';
import PromptModal from '../../components/forms/PromptModal';
import { useToast } from '../../context/ToastContext';
import useFetch from '../../hooks/useFetch';
import api from '../../services/api';
import { formatDateTime } from '../../services/format';

export default function AcademicFinalReports() {
  const toast = useToast();
  const [status, setStatus] = useState('');
  const { data, loading, error, reload } = useFetch('/final-reports/', status ? { status } : undefined);
  const [action, setAction] = useState(null);

  const startReview = async (r) => {
    await api.post(`/final-reports/${r.id}/start-review/`);
    toast('Marked as under review.');
    reload();
  };

  return (
    <>
      <PageHeader title="Final Report Review" subtitle="Approve final attachment reports or return them for correction" />
      <select className="form-select w-auto mb-3" value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Filter reports">
        <option value="">All reports</option><option value="submitted">Submitted</option><option value="under_review">Under review</option>
        <option value="returned">Returned</option><option value="approved">Approved</option>
      </select>
      <ErrorAlert error={error} onRetry={reload} />
      {loading ? <Loading /> : (data || []).length === 0 ? <EmptyState icon="file-earmark-text" text="No reports." /> : (
        <div className="card table-responsive">
          <table className="table mb-0 align-middle">
            <thead><tr><th>Student</th><th>Title</th><th>Version</th><th>Submitted</th><th>Status</th><th>Feedback</th><th /></tr></thead>
            <tbody>
              {data.map((r) => {
                const open = ['submitted', 'under_review'].includes(r.review_status);
                return (
                  <tr key={r.id}>
                    <td>{r.student.full_name}<div className="small text-muted">{r.student.registration_number}</div></td>
                    <td>{r.title}</td>
                    <td>v{r.version}</td>
                    <td className="small">{formatDateTime(r.submission_date)}</td>
                    <td><StatusBadge status={r.review_status} label={r.review_status_label} /></td>
                    <td className="small pre-wrap" style={{ maxWidth: 240 }}>{r.feedback || '—'}</td>
                    <td className="text-end text-nowrap">
                      <DownloadButton url={r.download_url} label="Open" name={r.original_filename} className="btn btn-sm btn-outline-primary me-1" />
                      {r.review_status === 'submitted' && <button type="button" className="btn btn-sm btn-outline-secondary me-1" onClick={() => startReview(r)}>Start review</button>}
                      {open && (
                        <>
                          <button type="button" className="btn btn-sm btn-success me-1" onClick={() => setAction({ type: 'approve', r })}>Approve</button>
                          <button type="button" className="btn btn-sm btn-outline-danger" onClick={() => setAction({ type: 'return', r })}>Return</button>
                        </>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      <PromptModal show={Boolean(action)} title={action?.type === 'approve' ? 'Approve final report' : 'Return report for correction'}
        label={action?.type === 'approve' ? 'Feedback (optional)' : 'Corrections required'} required={action?.type === 'return'}
        variant={action?.type === 'approve' ? 'success' : 'danger'} confirmText={action?.type === 'approve' ? 'Approve' : 'Return'}
        onClose={() => setAction(null)}
        onSubmit={async (feedback) => {
          await api.post(`/final-reports/${action.r.id}/${action.type}/`, { feedback });
          toast(action.type === 'approve' ? 'Report approved.' : 'Report returned to the student.');
          reload();
        }} />
    </>
  );
}
