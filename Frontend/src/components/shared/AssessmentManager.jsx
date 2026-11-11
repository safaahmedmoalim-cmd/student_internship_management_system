import { useState } from 'react';

import Modal from '../common/Modal';
import { DownloadButton, EmptyState, ErrorAlert, Loading, StatusBadge } from '../common/ui';
import Field, { FormError, SubmitButton } from '../forms/Field';
import ScoreRubric from '../forms/ScoreRubric';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import useFetch from '../../hooks/useFetch';
import useForm from '../../hooks/useForm';
import useMeta from '../../hooks/useMeta';
import api, { toFormData } from '../../services/api';

function AssessmentForm({ student, existing, criteria, allowForm, onDone, onCancel }) {
  const toast = useToast();
  const form = useForm({
    assessment_criteria: existing?.assessment_criteria || {}, comments: existing?.comments || '',
    recommendations: existing?.recommendations || '', evaluation_form: null,
  });
  const { values: v, setValues, onChange, errors } = form;
  const complete = criteria.every((c) => v.assessment_criteria[c]);

  const save = (submit) => form.submit(async (vals) => {
    const payload = { ...vals, submit: submit ? 'true' : 'false', student: student.id };
    const body = vals.evaluation_form ? toFormData(payload) : { ...payload, submit };
    if (existing) await api.put(`/assessments/${existing.id}/`, body);
    else await api.post('/assessments/', body);
    toast(submit ? 'Assessment submitted.' : 'Draft saved.');
    onDone();
  });

  return (
    <form onSubmit={save(true)} noValidate>
      <FormError error={form.error} />
      <ScoreRubric criteria={criteria} scores={v.assessment_criteria}
        onChange={(s) => setValues((x) => ({ ...x, assessment_criteria: s }))} />
      {errors.assessment_criteria && <div className="text-danger small mb-2">{errors.assessment_criteria}</div>}
      <Field label="Comments" name="comments" as="textarea" value={v.comments} onChange={onChange} />
      <Field label="Recommendations" name="recommendations" as="textarea" value={v.recommendations} onChange={onChange} />
      {allowForm && <Field label="Signed evaluation form (optional)" name="evaluation_form" type="file" accept=".pdf,.doc,.docx"
        onChange={onChange} error={errors.evaluation_form} />}
      <div className="alert alert-info small py-2">Saving keeps a draft you can change. Submitting locks the assessment and sends it to the administrator, who releases results to the student.</div>
      <div className="d-flex justify-content-end gap-2">
        <button type="button" className="btn btn-outline-secondary" onClick={onCancel}>Cancel</button>
        <button type="button" className="btn btn-outline-primary" disabled={!complete || form.submitting} onClick={save(false)}>Save draft</button>
        <SubmitButton submitting={form.submitting} disabled={!complete}>Submit assessment</SubmitButton>
      </div>
    </form>
  );
}

/** Academic assessment (academic supervisors) or workplace evaluation (industrial supervisors). */
export default function AssessmentManager() {
  const { user } = useAuth();
  const meta = useMeta();
  const students = useFetch('/students/');
  const mine = useFetch('/assessments/');
  const [editing, setEditing] = useState(null);
  const type = user.role === 'academic' ? 'academic' : 'workplace';
  const criteria = meta?.criteria?.[type] || [];

  if (students.loading || mine.loading || !meta) return <Loading />;
  const byStudent = Object.fromEntries((mine.data || []).filter((a) => a.assessment_type === type).map((a) => [a.student.id, a]));

  return (
    <>
      <ErrorAlert error={students.error || mine.error} onRetry={() => { students.reload(); mine.reload(); }} />
      {(students.data || []).length === 0 ? <EmptyState icon="people" text="No students assigned to you." /> : (
        <div className="card table-responsive">
          <table className="table mb-0 align-middle">
            <thead><tr><th>Student</th><th>Organization</th><th>Status</th><th>Marks</th><th /></tr></thead>
            <tbody>
              {students.data.map((s) => {
                const a = byStudent[s.id];
                return (
                  <tr key={s.id}>
                    <td><div className="fw-semibold">{s.full_name}</div><div className="small text-muted">{s.registration_number}</div></td>
                    <td className="small">{s.organization_name || '—'}</td>
                    <td><StatusBadge status={a?.assessment_status || 'pending'} label={a?.assessment_status_label || 'Pending'} /></td>
                    <td>{a ? `${Number(a.marks)}%` : '—'}</td>
                    <td className="text-end">
                      {a?.evaluation_form_url && <DownloadButton url={a.evaluation_form_url} label="Form" className="btn btn-sm btn-link" />}
                      {(!a || a.assessment_status === 'in_progress') ? (
                        <button type="button" className="btn btn-sm btn-primary" onClick={() => setEditing({ student: s, existing: a })}>
                          {a ? 'Continue' : 'Assess'}
                        </button>
                      ) : (
                        <button type="button" className="btn btn-sm btn-outline-secondary" onClick={() => setEditing({ student: s, existing: a, view: true })}>View</button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      <Modal show={Boolean(editing)} size="lg" onClose={() => setEditing(null)}
        title={editing ? `${type === 'academic' ? 'Academic assessment' : 'Workplace evaluation'} — ${editing.student.full_name}` : ''}>
        {editing && (editing.view ? (
          <>
            <ScoreRubric criteria={criteria} scores={editing.existing.assessment_criteria} readOnly />
            {editing.existing.comments && <p className="pre-wrap"><strong>Comments:</strong> {editing.existing.comments}</p>}
            {editing.existing.recommendations && <p className="pre-wrap"><strong>Recommendations:</strong> {editing.existing.recommendations}</p>}
            <p className="small text-muted mb-0">Submitted assessments are locked. Ask the administrator to re-open it if a change is needed.</p>
          </>
        ) : (
          <AssessmentForm student={editing.student} existing={editing.existing} criteria={criteria}
            allowForm={type === 'workplace'} onCancel={() => setEditing(null)}
            onDone={() => { setEditing(null); mine.reload(); }} />
        ))}
      </Modal>
    </>
  );
}
