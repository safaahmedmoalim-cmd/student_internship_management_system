import Field, { FormError, SubmitButton } from '../forms/Field';
import { useToast } from '../../context/ToastContext';
import useFetch from '../../hooks/useFetch';
import useForm from '../../hooks/useForm';
import api from '../../services/api';

/** Workflow 5.3 - link an approved placement with an academic and an industrial supervisor. */
export default function AssignForm({ placement, onDone, onCancel }) {
  const toast = useToast();
  const academics = useFetch('/supervisors/academic/');
  const industrials = useFetch('/supervisors/industrial/', { organization: placement.organization.id });
  const form = useForm({
    academic_supervisor: placement.assignment?.academic_supervisor.id || '',
    industrial_supervisor: placement.assignment?.industrial_supervisor.id || '',
  });
  const { values: v, onChange, errors } = form;

  const onSubmit = form.submit(async (vals) => {
    await api.post('/assignments/', { placement: placement.id, ...vals });
    toast('Supervisors assigned. The student and both supervisors have been notified.');
    onDone();
  });

  return (
    <form onSubmit={onSubmit} noValidate>
      <p className="mb-3">
        <strong>{placement.student.full_name}</strong> ({placement.student.registration_number})<br />
        <span className="text-muted">{placement.organization.organization_name}</span>
      </p>
      <FormError error={form.error} />
      <Field label="Academic supervisor" name="academic_supervisor" value={v.academic_supervisor} onChange={onChange}
        error={errors.academic_supervisor} required
        options={(academics.data || []).map((a) => ({ value: a.id, label: `${a.full_name} — ${a.department_name} (${a.active_students} students)` }))} />
      <Field label="Industrial supervisor" name="industrial_supervisor" value={v.industrial_supervisor} onChange={onChange}
        error={errors.industrial_supervisor} required
        options={(industrials.data || []).map((s) => ({ value: s.id, label: `${s.full_name} — ${s.job_title}` }))}
        help={!industrials.loading && (industrials.data || []).length === 0
          ? 'No industrial supervisor is registered for this organization yet. Create one in User Management first.'
          : 'Only supervisors employed by the host organization are listed.'} />
      {placement.assignment && <div className="alert alert-warning small">The current assignment will be replaced.</div>}
      <div className="d-flex justify-content-end gap-2">
        <button type="button" className="btn btn-outline-secondary" onClick={onCancel}>Cancel</button>
        <SubmitButton submitting={form.submitting}>Save assignment</SubmitButton>
      </div>
    </form>
  );
}
