import { useState } from 'react';

import Modal from '../../components/common/Modal';
import { EmptyState, ErrorAlert, Loading, PageHeader } from '../../components/common/ui';
import Field, { FormError, SubmitButton } from '../../components/forms/Field';
import LogbookEntry from '../../components/shared/LogbookEntry';
import { useToast } from '../../context/ToastContext';
import useFetch from '../../hooks/useFetch';
import useForm from '../../hooks/useForm';
import api, { toFormData } from '../../services/api';

function EntryForm({ entry, nextWeek, onDone, onCancel }) {
  const toast = useToast();
  const form = useForm(entry ? {
    week_number: entry.week_number, start_date: entry.start_date, end_date: entry.end_date, activities: entry.activities,
    skills_acquired: entry.skills_acquired, challenges: entry.challenges, solutions: entry.solutions, attachment: null,
  } : { week_number: nextWeek, start_date: '', end_date: '', activities: '', skills_acquired: '', challenges: '', solutions: '', attachment: null });
  const { values: v, onChange, errors } = form;
  const f = (name, label, props = {}) => <Field name={name} label={label} value={v[name]} onChange={onChange} error={errors[name]} {...props} />;

  const onSubmit = form.submit(async (vals) => {
    const fd = toFormData(vals);
    // allow clearing optional text on edit
    ['skills_acquired', 'challenges', 'solutions'].forEach((k) => { if (!vals[k]) fd.append(k, ''); });
    if (entry) await api.patch(`/logbooks/${entry.id}/`, fd);
    else await api.post('/logbooks/', fd);
    toast(entry ? 'Entry resubmitted to both supervisors.' : 'Entry submitted to both supervisors.');
    onDone();
  });

  return (
    <form onSubmit={onSubmit} noValidate>
      <FormError error={form.error} />
      <div className="row">
        <div className="col-md-4">{f('week_number', 'Week number', { type: 'number', min: 1, max: 52, required: true })}</div>
        <div className="col-md-4">{f('start_date', 'Week starting date', { type: 'date', required: true })}</div>
        <div className="col-md-4">{f('end_date', 'Week ending date', { type: 'date', required: true })}</div>
      </div>
      {f('activities', 'Activities performed', { as: 'textarea', rows: 5, required: true })}
      {f('skills_acquired', 'Skills acquired', { as: 'textarea' })}
      <div className="row">
        <div className="col-md-6">{f('challenges', 'Challenges experienced', { as: 'textarea' })}</div>
        <div className="col-md-6">{f('solutions', 'Solutions applied', { as: 'textarea' })}</div>
      </div>
      {f('attachment', 'Supporting attachment (optional)', { type: 'file', help: 'PDF, Word, Excel, PowerPoint or image, up to 10 MB.' })}
      <div className="d-flex gap-2 justify-content-end">
        <button type="button" className="btn btn-outline-secondary" onClick={onCancel}>Cancel</button>
        <SubmitButton submitting={form.submitting}>{entry ? 'Resubmit' : 'Submit'}</SubmitButton>
      </div>
    </form>
  );
}

export default function StudentLogbook() {
  const { data, loading, error, reload } = useFetch('/logbooks/');
  const [editor, setEditor] = useState(null); // null | 'new' | entry
  const entries = data || [];
  const nextWeek = entries.reduce((m, e) => Math.max(m, e.week_number), 0) + 1;

  return (
    <>
      <PageHeader title="Weekly Logbook" subtitle="Each entry is reviewed independently by your academic and industrial supervisors"
        actions={<button type="button" className="btn btn-primary" onClick={() => setEditor('new')}><i className="bi bi-plus-lg me-1" />New entry</button>} />
      <ErrorAlert error={error} onRetry={reload} />
      {loading ? <Loading /> : entries.length === 0 ? (
        <EmptyState icon="journal-plus" text="No logbook entries yet. Entries can be submitted once your placement is approved and supervisors are assigned." />
      ) : entries.map((e) => (
        <LogbookEntry key={e.id} entry={e} actions={['submitted', 'rejected'].includes(e.status) && (
          <button type="button" className="btn btn-sm btn-outline-primary" onClick={() => setEditor(e)}>
            <i className="bi bi-pencil me-1" />{e.status === 'rejected' ? 'Correct & resubmit' : 'Edit'}
          </button>
        )} />
      ))}
      <Modal show={Boolean(editor)} size="lg" onClose={() => setEditor(null)}
        title={editor === 'new' ? 'New logbook entry' : `Week ${editor?.week_number}`}>
        {editor && (
          <EntryForm entry={editor === 'new' ? null : editor} nextWeek={nextWeek}
            onCancel={() => setEditor(null)} onDone={() => { setEditor(null); reload(); }} />
        )}
      </Modal>
    </>
  );
}
