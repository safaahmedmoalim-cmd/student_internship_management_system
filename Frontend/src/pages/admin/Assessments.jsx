import { useState } from 'react';

import Modal from '../../components/common/Modal';
import { DownloadButton, EmptyState, ErrorAlert, Loading, PageHeader, StatusBadge } from '../../components/common/ui';
import ScoreRubric from '../../components/forms/ScoreRubric';
import { useToast } from '../../context/ToastContext';
import useFetch from '../../hooks/useFetch';
import api, { errorMessage } from '../../services/api';
import { formatDate } from '../../services/format';

export default function AdminAssessments() {
  const toast = useToast();
  const [status, setStatus] = useState('completed');
  const [type, setType] = useState('');
  const params = { ...(status ? { status } : {}), ...(type ? { type } : {}) };
  const { data, loading, error, reload } = useFetch('/assessments/', params);
  const [viewing, setViewing] = useState(null);
  const [busy, setBusy] = useState(false);

  const act = async (a, action) => {
    try {
      await api.post(`/assessments/${a.id}/${action}/`);
      toast(action === 'release' ? 'Results released to the student.' : 'Assessment re-opened for the supervisor.');
      setViewing(null);
      reload();
    } catch (e) { toast(errorMessage(e), 'danger'); }
  };

  const releaseAll = async () => {
    const ready = (data || []).filter((a) => a.assessment_status === 'completed');
    setBusy(true);
    let done = 0;
    for (const a of ready) {
      try { await api.post(`/assessments/${a.id}/release/`); done += 1; } catch { /* continue with the rest */ }
    }
    setBusy(false);
    toast(`${done} of ${ready.length} assessment(s) released.`);
    reload();
  };

  const completedCount = (data || []).filter((a) => a.assessment_status === 'completed').length;

  return (
    <>
      <PageHeader title="Assessments" subtitle="Monitor assessment completion and release marks to students"
        actions={completedCount > 0 && (
          <button type="button" className="btn btn-success" onClick={releaseAll} disabled={busy}>
            {busy && <span className="spinner-border spinner-border-sm me-2" />}Release all completed ({completedCount})
          </button>
        )} />
      <div className="filter-bar">
        <select className="form-select" value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Filter by status">
          <option value="">All statuses</option><option value="in_progress">In progress</option><option value="completed">Completed (not released)</option><option value="released">Released</option>
        </select>
        <select className="form-select" value={type} onChange={(e) => setType(e.target.value)} aria-label="Filter by type">
          <option value="">Academic and workplace</option><option value="academic">Academic</option><option value="workplace">Workplace</option>
        </select>
      </div>
      <ErrorAlert error={error} onRetry={reload} />
      {loading ? <Loading /> : (data || []).length === 0 ? <EmptyState icon="award" text="No assessments." /> : (
        <div className="card table-responsive">
          <table className="table table-hover mb-0 align-middle">
            <thead><tr><th>Student</th><th>Type</th><th>Supervisor</th><th>Marks</th><th>Date</th><th>Status</th><th /></tr></thead>
            <tbody>
              {data.map((a) => (
                <tr key={a.id}>
                  <td>{a.student.full_name}<div className="small text-muted">{a.student.registration_number}</div></td>
                  <td>{a.assessment_type_label}</td>
                  <td className="small">{a.supervisor_name}</td>
                  <td className="fw-semibold">{Number(a.marks)}%</td>
                  <td className="small">{formatDate(a.assessment_date)}</td>
                  <td><StatusBadge status={a.assessment_status} label={a.assessment_status_label} /></td>
                  <td className="text-end text-nowrap">
                    <button type="button" className="btn btn-sm btn-outline-primary me-1" onClick={() => setViewing(a)}>View</button>
                    {a.assessment_status === 'completed' && <button type="button" className="btn btn-sm btn-success" onClick={() => act(a, 'release')}>Release</button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Modal show={Boolean(viewing)} size="lg" title={viewing ? `${viewing.assessment_type_label} — ${viewing.student.full_name}` : ''} onClose={() => setViewing(null)}
        footer={viewing?.assessment_status === 'completed' && (
          <>
            <button type="button" className="btn btn-outline-warning" onClick={() => act(viewing, 'reopen')}>Re-open for changes</button>
            <button type="button" className="btn btn-success" onClick={() => act(viewing, 'release')}>Release to student</button>
          </>
        )}>
        {viewing && (
          <>
            <ScoreRubric criteria={Object.keys(viewing.assessment_criteria)} scores={viewing.assessment_criteria} readOnly />
            {viewing.comments && <p className="pre-wrap"><strong>Comments:</strong> {viewing.comments}</p>}
            {viewing.recommendations && <p className="pre-wrap"><strong>Recommendations:</strong> {viewing.recommendations}</p>}
            {viewing.evaluation_form_url && <DownloadButton url={viewing.evaluation_form_url} label="Evaluation form" />}
          </>
        )}
      </Modal>
    </>
  );
}
