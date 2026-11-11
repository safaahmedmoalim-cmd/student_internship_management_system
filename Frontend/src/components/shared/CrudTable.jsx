import { useState } from 'react';

import Modal from '../common/Modal';
import { EmptyState, ErrorAlert, Loading } from '../common/ui';
import Field, { FormError, SubmitButton } from '../forms/Field';
import PromptModal from '../forms/PromptModal';
import { useToast } from '../../context/ToastContext';
import useFetch from '../../hooks/useFetch';
import useForm from '../../hooks/useForm';
import api from '../../services/api';

function RecordForm({ endpoint, fields, record, onDone, onCancel, noun }) {
  const toast = useToast();
  const initial = Object.fromEntries(fields.map((f) => [f.name, record?.[f.name] ?? f.default ?? (f.type === 'checkbox' ? false : '')]));
  const form = useForm(initial);
  const onSubmit = form.submit(async (values) => {
    // Empty optional dates / numbers must be sent as null, not "".
    const v = Object.fromEntries(Object.entries(values).map(([k, val]) => {
      const type = fields.find((f) => f.name === k)?.type;
      return [k, val === '' && ['date', 'number'].includes(type) ? null : val];
    }));
    if (record) await api.patch(`${endpoint}${record.id}/`, v);
    else await api.post(endpoint, v);
    toast(`${noun} ${record ? 'updated' : 'created'}.`);
    onDone();
  });
  return (
    <form onSubmit={onSubmit} noValidate>
      <FormError error={form.error} />
      <div className="row">
        {fields.map((f) => (
          <div key={f.name} className={f.col || 'col-12'}>
            <Field {...f} value={form.values[f.name]} onChange={form.onChange} error={form.errors[f.name]} />
          </div>
        ))}
      </div>
      <div className="d-flex justify-content-end gap-2">
        <button type="button" className="btn btn-outline-secondary" onClick={onCancel}>Cancel</button>
        <SubmitButton submitting={form.submitting}>Save</SubmitButton>
      </div>
    </form>
  );
}

/** List + create/edit/delete for simple administrator-managed records. */
export default function CrudTable({ endpoint, params, columns, fields, noun, canDelete = true, toolbar, rowActions }) {
  const toast = useToast();
  const { data, loading, error, reload } = useFetch(endpoint, params);
  const [editing, setEditing] = useState(null); // null | 'new' | record
  const [deleting, setDeleting] = useState(null);

  return (
    <>
      <div className="d-flex flex-wrap justify-content-between gap-2 mb-3">
        <div className="d-flex flex-wrap gap-2">{toolbar}</div>
        <button type="button" className="btn btn-primary" onClick={() => setEditing('new')}><i className="bi bi-plus-lg me-1" />Add {noun.toLowerCase()}</button>
      </div>
      <ErrorAlert error={error} onRetry={reload} />
      {loading ? <Loading /> : (data || []).length === 0 ? <EmptyState text={`No ${noun.toLowerCase()} records.`} /> : (
        <div className="card table-responsive">
          <table className="table table-hover mb-0 align-middle">
            <thead><tr>{columns.map((c) => <th key={c.key}>{c.label}</th>)}<th /></tr></thead>
            <tbody>
              {data.map((row) => (
                <tr key={row.id}>
                  {columns.map((c) => <td key={c.key} className={c.className}>{c.render ? c.render(row) : (row[c.key] ?? '—')}</td>)}
                  <td className="text-end text-nowrap">
                    {rowActions?.(row, reload)}
                    <button type="button" className="btn btn-sm btn-outline-primary ms-1" onClick={() => setEditing(row)} aria-label="Edit"><i className="bi bi-pencil" /></button>
                    {canDelete && <button type="button" className="btn btn-sm btn-outline-danger ms-1" onClick={() => setDeleting(row)} aria-label="Delete"><i className="bi bi-trash" /></button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Modal show={Boolean(editing)} title={editing === 'new' ? `Add ${noun.toLowerCase()}` : `Edit ${noun.toLowerCase()}`} size="lg" onClose={() => setEditing(null)}>
        {editing && <RecordForm endpoint={endpoint} fields={fields} noun={noun} record={editing === 'new' ? null : editing}
          onCancel={() => setEditing(null)} onDone={() => { setEditing(null); reload(); }} />}
      </Modal>
      <PromptModal show={Boolean(deleting)} title={`Delete ${noun.toLowerCase()}`} inputType={null} variant="danger" confirmText="Delete"
        message="This cannot be undone. Records that are in use cannot be deleted." onClose={() => setDeleting(null)}
        onSubmit={async () => { await api.delete(`${endpoint}${deleting.id}/`); toast(`${noun} deleted.`); reload(); }} />
    </>
  );
}
