import { useState } from 'react';

import Modal from '../../components/common/Modal';
import { DownloadButton, EmptyState, ErrorAlert, InfoRow, Loading, PageHeader, StatusBadge } from '../../components/common/ui';
import PromptModal from '../../components/forms/PromptModal';
import AssignForm from '../../components/shared/AssignForm';
import { useToast } from '../../context/ToastContext';
import useFetch from '../../hooks/useFetch';
import api, { errorMessage } from '../../services/api';
import { formatDate, formatDateTime } from '../../services/format';

const TABS = [['pending', 'Pending'], ['returned', 'Returned'], ['approved', 'Approved'], ['rejected', 'Rejected'], ['withdrawn', 'Withdrawn'], ['', 'All']];
const NEXT = { not_started: ['active', 'terminated'], active: ['completed', 'terminated'], completed: ['active'], terminated: ['active'] };
const NEXT_LABEL = { active: 'Mark active', completed: 'Confirm completion', terminated: 'Terminate' };

export default function AdminPlacements() {
  const toast = useToast();
  const [status, setStatus] = useState('pending');
  const [search, setSearch] = useState('');
  const params = { ...(status ? { status } : {}), ...(search ? { search } : {}) };
  const { data, loading, error, reload } = useFetch('/placements/', params);
  const [viewing, setViewing] = useState(null);
  const [decision, setDecision] = useState(null); // {type, p}
  const [assigning, setAssigning] = useState(null);

  const setAttachment = async (p, value) => {
    try {
      const { data: updated } = await api.post(`/placements/${p.id}/attachment-status/`, { attachment_status: value });
      toast(`Attachment marked ${updated.attachment_status_label.toLowerCase()}.`);
      setViewing(updated);
      reload();
    } catch (e) { toast(errorMessage(e), 'danger'); }
  };

  return (
    <>
      <PageHeader title="Placement Applications" subtitle="Review, approve, reject or return placement applications" />
      <ul className="nav nav-tabs mb-3">
        {TABS.map(([k, label]) => (
          <li className="nav-item" key={k}><button type="button" className={`nav-link ${status === k ? 'active' : ''}`} onClick={() => setStatus(k)}>{label}</button></li>
        ))}
      </ul>
      <input className="form-control mb-3" style={{ maxWidth: 360 }} placeholder="Search student or organization" value={search}
        onChange={(e) => setSearch(e.target.value)} aria-label="Search placements" />
      <ErrorAlert error={error} onRetry={reload} />
      {loading ? <Loading /> : (data || []).length === 0 ? <EmptyState icon="building" text="No applications here." /> : (
        <div className="card table-responsive">
          <table className="table table-hover mb-0 align-middle">
            <thead><tr><th>Student</th><th>Organization</th><th>Dates</th><th>Applied</th><th>Status</th><th>Supervisors</th><th /></tr></thead>
            <tbody>
              {data.map((p) => (
                <tr key={p.id}>
                  <td>{p.student.full_name}<div className="small text-muted">{p.student.registration_number}</div></td>
                  <td>{p.organization.organization_name}<div className="small text-muted">{p.organization.county}{p.organization.status === 'pending' && ' · new organization'}</div></td>
                  <td className="small">{formatDate(p.start_date)} – {formatDate(p.end_date)}</td>
                  <td className="small">{formatDate(p.application_date)}</td>
                  <td><StatusBadge status={p.application_status} label={p.application_status_label} />
                    {p.application_status === 'approved' && <div className="small text-muted">{p.attachment_status_label}</div>}</td>
                  <td className="small">{p.assignment ? <>{p.assignment.academic_supervisor.full_name}<br />{p.assignment.industrial_supervisor.full_name}</> : '—'}</td>
                  <td className="text-end text-nowrap">
                    <button type="button" className="btn btn-sm btn-outline-primary me-1" onClick={() => setViewing(p)}>Details</button>
                    {p.application_status === 'pending' && (
                      <>
                        <button type="button" className="btn btn-sm btn-success me-1" onClick={() => setDecision({ type: 'approve', p })}>Approve</button>
                        <button type="button" className="btn btn-sm btn-outline-warning me-1" onClick={() => setDecision({ type: 'return', p })}>Return</button>
                        <button type="button" className="btn btn-sm btn-outline-danger" onClick={() => setDecision({ type: 'reject', p })}>Reject</button>
                      </>
                    )}
                    {p.application_status === 'approved' && ['not_started', 'active'].includes(p.attachment_status) && (
                      <button type="button" className="btn btn-sm btn-primary" onClick={() => setAssigning(p)}>{p.assignment ? 'Reassign' : 'Assign supervisors'}</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Modal show={Boolean(viewing)} title="Placement details" size="lg" onClose={() => setViewing(null)}>
        {viewing && (
          <>
            <InfoRow label="Student">{viewing.student.full_name} ({viewing.student.registration_number}) · {viewing.student.department_name}</InfoRow>
            <InfoRow label="Student contact">{viewing.student.email} · {viewing.student.phone_number}</InfoRow>
            <InfoRow label="Organization">{viewing.organization.organization_name} <StatusBadge status={viewing.organization.status} /></InfoRow>
            <InfoRow label="Address">{viewing.organization.address}, {viewing.organization.county}</InfoRow>
            <InfoRow label="Contact person">{viewing.organization.contact_person} · {viewing.organization.phone_number} · {viewing.organization.email}</InfoRow>
            <InfoRow label="Attachment period">{viewing.attachment_period_name}</InfoRow>
            <InfoRow label="Dates">{formatDate(viewing.start_date)} – {formatDate(viewing.end_date)}</InfoRow>
            <InfoRow label="Applied">{formatDateTime(viewing.application_date)}</InfoRow>
            <InfoRow label="Status"><StatusBadge status={viewing.application_status} label={viewing.application_status_label} /></InfoRow>
            {viewing.approval_comments && <InfoRow label="Comments">{viewing.approval_comments}</InfoRow>}
            {viewing.withdrawal_reason && <InfoRow label="Withdrawal reason">{viewing.withdrawal_reason}</InfoRow>}
            {viewing.reviewed_by_name && <InfoRow label="Decided by">{viewing.reviewed_by_name} · {formatDateTime(viewing.reviewed_at)}</InfoRow>}
            <InfoRow label="Supporting document">{viewing.supporting_document_url ? <DownloadButton url={viewing.supporting_document_url} /> : 'None'}</InfoRow>
            {viewing.application_status === 'approved' && (
              <InfoRow label="Attachment status">
                <StatusBadge status={viewing.attachment_status} label={viewing.attachment_status_label} />
                <div className="mt-2 d-flex flex-wrap gap-2">
                  {(NEXT[viewing.attachment_status] || []).map((s) => (
                    <button key={s} type="button" className={`btn btn-sm ${s === 'terminated' ? 'btn-outline-danger' : 'btn-outline-success'}`}
                      onClick={() => setAttachment(viewing, s)}>{NEXT_LABEL[s]}</button>
                  ))}
                </div>
              </InfoRow>
            )}
          </>
        )}
      </Modal>

      <PromptModal show={Boolean(decision)}
        title={{ approve: 'Approve placement', reject: 'Reject placement', return: 'Return for correction' }[decision?.type]}
        message={decision && `${decision.p.student.full_name} — ${decision.p.organization.organization_name}`}
        label={decision?.type === 'approve' ? 'Comments (optional)' : decision?.type === 'reject' ? 'Reason for rejection' : 'What must the student correct?'}
        required={decision?.type !== 'approve'} variant={decision?.type === 'approve' ? 'success' : decision?.type === 'reject' ? 'danger' : 'warning'}
        confirmText={{ approve: 'Approve', reject: 'Reject', return: 'Return' }[decision?.type]} onClose={() => setDecision(null)}
        onSubmit={async (comments) => {
          await api.post(`/placements/${decision.p.id}/${decision.type}/`, { comments });
          toast('Decision saved and the student has been notified.');
          reload();
        }} />

      <Modal show={Boolean(assigning)} title="Assign supervisors" onClose={() => setAssigning(null)}>
        {assigning && <AssignForm placement={assigning} onCancel={() => setAssigning(null)} onDone={() => { setAssigning(null); reload(); }} />}
      </Modal>
    </>
  );
}
