import { useState } from 'react';

import Modal from '../../components/common/Modal';
import { Card, EmptyState, ErrorAlert, Loading, PageHeader, StatusBadge } from '../../components/common/ui';
import PromptModal from '../../components/forms/PromptModal';
import AssignForm from '../../components/shared/AssignForm';
import { useToast } from '../../context/ToastContext';
import useFetch from '../../hooks/useFetch';
import api from '../../services/api';
import { formatDate } from '../../services/format';

export default function AdminAssignments() {
  const toast = useToast();
  const unassigned = useFetch('/placements/', { unassigned: 'true' });
  const [status, setStatus] = useState('active');
  const assignments = useFetch('/assignments/', status ? { status } : undefined);
  const [assigning, setAssigning] = useState(null);
  const [ending, setEnding] = useState(null);
  const pending = (unassigned.data || []).filter((p) => ['not_started', 'active'].includes(p.attachment_status));

  return (
    <>
      <PageHeader title="Supervisor Assignment" subtitle="Assign an academic and an industrial supervisor to every approved placement" />
      <Card title={`Approved placements without supervisors (${pending.length})`} bodyClass="p-0">
        <ErrorAlert error={unassigned.error} onRetry={unassigned.reload} />
        {unassigned.loading ? <div className="p-3"><Loading /></div> : pending.length === 0 ? <EmptyState icon="check2-all" text="Every approved placement has supervisors." /> : (
          <div className="table-responsive">
            <table className="table mb-0 align-middle">
              <thead><tr><th>Student</th><th>Organization</th><th>Start</th><th /></tr></thead>
              <tbody>
                {pending.map((p) => (
                  <tr key={p.id}>
                    <td>{p.student.full_name}<div className="small text-muted">{p.student.registration_number} · {p.student.department_name}</div></td>
                    <td>{p.organization.organization_name}</td>
                    <td className="small">{formatDate(p.start_date)}</td>
                    <td className="text-end"><button type="button" className="btn btn-sm btn-primary" onClick={() => setAssigning(p)}>Assign</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card title="Assignments" bodyClass="p-0" actions={(
        <select className="form-select form-select-sm" value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Filter assignments">
          <option value="active">Active</option><option value="inactive">Inactive</option><option value="">All</option>
        </select>
      )}>
        {assignments.loading ? <div className="p-3"><Loading /></div> : (assignments.data || []).length === 0 ? <EmptyState text="No assignments." /> : (
          <div className="table-responsive">
            <table className="table mb-0 align-middle">
              <thead><tr><th>Student</th><th>Organization</th><th>Academic supervisor</th><th>Industrial supervisor</th><th>Assigned</th><th>Status</th><th /></tr></thead>
              <tbody>
                {assignments.data.map((a) => (
                  <tr key={a.id}>
                    <td>{a.student_detail.full_name}<div className="small text-muted">{a.student_detail.registration_number}</div></td>
                    <td className="small">{a.organization_name}</td>
                    <td className="small">{a.academic_detail.full_name}<div className="text-muted">{a.academic_detail.email}</div></td>
                    <td className="small">{a.industrial_detail.full_name}<div className="text-muted">{a.industrial_detail.email}</div></td>
                    <td className="small">{formatDate(a.assigned_date)}</td>
                    <td><StatusBadge status={a.assignment_status} /></td>
                    <td className="text-end">{a.assignment_status === 'active' && (
                      <button type="button" className="btn btn-sm btn-outline-danger" onClick={() => setEnding(a)}>Deactivate</button>
                    )}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Modal show={Boolean(assigning)} title="Assign supervisors" onClose={() => setAssigning(null)}>
        {assigning && <AssignForm placement={assigning} onCancel={() => setAssigning(null)}
          onDone={() => { setAssigning(null); unassigned.reload(); assignments.reload(); }} />}
      </Modal>
      <PromptModal show={Boolean(ending)} title="Deactivate assignment" inputType={null} variant="danger" confirmText="Deactivate"
        message="The supervisors will no longer see this student. Use Assign on the placement to set new supervisors."
        onClose={() => setEnding(null)}
        onSubmit={async () => {
          await api.post(`/assignments/${ending.id}/deactivate/`);
          toast('Assignment deactivated.');
          assignments.reload();
          unassigned.reload();
        }} />
    </>
  );
}
