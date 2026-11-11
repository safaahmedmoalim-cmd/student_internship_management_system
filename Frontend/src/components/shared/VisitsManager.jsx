import { useState } from 'react';

import Modal from '../common/Modal';
import { EmptyState, ErrorAlert, Loading, StatusBadge } from '../common/ui';
import Field, { FormError, SubmitButton } from '../forms/Field';
import PromptModal from '../forms/PromptModal';
import { useToast } from '../../context/ToastContext';
import useFetch from '../../hooks/useFetch';
import useForm from '../../hooks/useForm';
import api from '../../services/api';
import { formatDateTime, fromLocalInput, toLocalInput } from '../../services/format';

function ScheduleForm({ onDone, onCancel }) {
  const students = useFetch('/students/');
  const toast = useToast();
  const form = useForm({ student: '', visit_date: '', visit_type: 'physical', meeting_link: '', objectives: '' });
  const { values: v, onChange, errors } = form;
  const onSubmit = form.submit(async (vals) => {
    await api.post('/visits/', { ...vals, visit_date: fromLocalInput(vals.visit_date) });
    toast('Visit scheduled. The student and supervisors have been notified.');
    onDone();
  });
  const eligible = (students.data || []).filter((s) => s.academic_supervisor_name);
  return (
    <form onSubmit={onSubmit} noValidate>
      <FormError error={form.error} />
      <Field label="Student" name="student" value={v.student} onChange={onChange} error={errors.student} required
        options={eligible.map((s) => ({ value: s.id, label: `${s.full_name} (${s.registration_number}) — ${s.organization_name || ''}` }))} />
      <div className="row">
        <div className="col-md-7"><Field label="Date and time" name="visit_date" type="datetime-local" value={v.visit_date} onChange={onChange} error={errors.visit_date} required /></div>
        <div className="col-md-5"><Field label="Visit type" name="visit_type" value={v.visit_type} onChange={onChange} placeholder={false}
          options={[{ value: 'physical', label: 'Physical' }, { value: 'virtual', label: 'Virtual' }]} /></div>
      </div>
      {v.visit_type === 'virtual' && <Field label="Meeting link" name="meeting_link" type="url" value={v.meeting_link} onChange={onChange} error={errors.meeting_link} />}
      <Field label="Visit objectives" name="objectives" as="textarea" value={v.objectives} onChange={onChange} error={errors.objectives} required />
      <div className="d-flex justify-content-end gap-2">
        <button type="button" className="btn btn-outline-secondary" onClick={onCancel}>Cancel</button>
        <SubmitButton submitting={form.submitting}>Schedule visit</SubmitButton>
      </div>
    </form>
  );
}

/** Schedule, reschedule, cancel and record supervision visits (academic supervisors and administrator). */
export default function VisitsManager() {
  const toast = useToast();
  const [status, setStatus] = useState('');
  const { data, loading, error, reload } = useFetch('/visits/', status ? { status } : undefined);
  const [scheduling, setScheduling] = useState(false);
  const [action, setAction] = useState(null); // {type, visit}

  const run = async (path, body, message) => { await api.post(path, body); toast(message); reload(); };

  return (
    <>
      <div className="d-flex flex-wrap justify-content-between gap-2 mb-3">
        <select className="form-select w-auto" value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Filter visits">
          <option value="">All visits</option>
          <option value="scheduled">Scheduled</option><option value="rescheduled">Rescheduled</option>
          <option value="completed">Completed</option><option value="cancelled">Cancelled</option>
        </select>
        <button type="button" className="btn btn-primary" onClick={() => setScheduling(true)}><i className="bi bi-calendar-plus me-1" />Schedule visit</button>
      </div>
      <ErrorAlert error={error} onRetry={reload} />
      {loading ? <Loading /> : (data || []).length === 0 ? <EmptyState icon="calendar-event" text="No visits." /> : (
        <div className="card table-responsive">
          <table className="table mb-0 align-middle">
            <thead><tr><th>Date</th><th>Student</th><th>Organization</th><th>Type</th><th>Status</th><th>Report</th><th /></tr></thead>
            <tbody>
              {data.map((v) => {
                const upcoming = ['scheduled', 'rescheduled'].includes(v.visit_status);
                const past = new Date(v.visit_date) <= new Date();
                return (
                  <tr key={v.id}>
                    <td className="small">{formatDateTime(v.visit_date)}</td>
                    <td>{v.student_detail.full_name}<div className="small text-muted">{v.academic_supervisor_name}</div></td>
                    <td className="small">{v.organization_name || '—'}</td>
                    <td className="small">{v.visit_type_label}{v.meeting_link && <div><a href={v.meeting_link} target="_blank" rel="noreferrer">Link</a></div>}</td>
                    <td><StatusBadge status={v.visit_status} label={v.visit_status_label} /></td>
                    <td className="small" style={{ maxWidth: 260 }}>
                      <div><strong>Objectives:</strong> {v.objectives}</div>
                      {v.observations && <div><strong>Observations:</strong> {v.observations}</div>}
                      {v.recommendations && <div><strong>Recommendations:</strong> {v.recommendations}</div>}
                    </td>
                    <td className="text-end text-nowrap">
                      {upcoming && (
                        <div className="btn-group btn-group-sm">
                          <button type="button" className="btn btn-success" disabled={!past} title={past ? '' : 'Available after the visit date'}
                            onClick={() => setAction({ type: 'complete', visit: v })}>Record</button>
                          <button type="button" className="btn btn-outline-primary" onClick={() => setAction({ type: 'reschedule', visit: v })}>Reschedule</button>
                          <button type="button" className="btn btn-outline-danger" onClick={() => setAction({ type: 'cancel', visit: v })}>Cancel</button>
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      <Modal show={scheduling} title="Schedule supervision visit" onClose={() => setScheduling(false)}>
        {scheduling && <ScheduleForm onCancel={() => setScheduling(false)} onDone={() => { setScheduling(false); reload(); }} />}
      </Modal>
      <PromptModal show={action?.type === 'complete'} title="Record visit report" confirmText="Save report" variant="success"
        fields={[{ name: 'observations', label: 'Observations', required: true }, { name: 'recommendations', label: 'Recommendations' }]}
        onClose={() => setAction(null)}
        onSubmit={(vals) => run(`/visits/${action.visit.id}/complete/`, vals, 'Visit report recorded.')} />
      <PromptModal show={action?.type === 'reschedule'} title="Reschedule visit" confirmText="Reschedule"
        fields={[{ name: 'visit_date', label: 'New date and time', type: 'datetime-local', required: true, initial: action?.visit ? toLocalInput(action.visit.visit_date) : '' },
          { name: 'reason', label: 'Reason (optional)' }]}
        onClose={() => setAction(null)}
        onSubmit={(vals) => run(`/visits/${action.visit.id}/reschedule/`, { ...vals, visit_date: fromLocalInput(vals.visit_date) }, 'Visit rescheduled.')} />
      <PromptModal show={action?.type === 'cancel'} title="Cancel visit" label="Reason (optional)" confirmText="Cancel visit" variant="danger"
        onClose={() => setAction(null)}
        onSubmit={(reason) => run(`/visits/${action.visit.id}/cancel/`, { reason }, 'Visit cancelled.')} />
    </>
  );
}
