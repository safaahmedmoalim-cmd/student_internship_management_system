import { useEffect, useState } from 'react';

import Modal from '../common/Modal';
import { errorMessage } from '../../services/api';

/**
 * Ask for a reason / comment / confirmation, then call onSubmit(text). Keeps itself open and shows
 * the API error if onSubmit throws. `fields` lets a caller ask for more than one value.
 */
export default function PromptModal({
  show, title, message, label = 'Comments', required = false, confirmText = 'Confirm', variant = 'primary',
  onSubmit, onClose, inputType = 'textarea', initial = '', fields,
}) {
  const [value, setValue] = useState(initial);
  const [values, setValues] = useState({});
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (show) {
      setValue(initial);
      setValues(Object.fromEntries((fields || []).map((f) => [f.name, f.initial || ''])));
      setError('');
    }
    // Reset only when the dialog opens (callers often pass `fields` inline).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [show]);

  const submit = async (e) => {
    e.preventDefault();
    if (!fields && required && !String(value).trim()) { setError(`${label} is required.`); return; }
    const missing = (fields || []).find((f) => f.required && !String(values[f.name] || '').trim());
    if (missing) { setError(`${missing.label} is required.`); return; }
    setBusy(true);
    setError('');
    try {
      await onSubmit(fields ? values : value);
      onClose();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const control = (name, type, val, set, lbl, req) => (
    <div className="mb-3" key={name}>
      {lbl && <label className="form-label" htmlFor={`p-${name}`}>{lbl}{req && <span className="text-danger"> *</span>}</label>}
      {type === 'textarea'
        ? <textarea id={`p-${name}`} className="form-control" rows={4} value={val} onChange={(e) => set(e.target.value)} />
        : <input id={`p-${name}`} type={type} className="form-control" value={val} onChange={(e) => set(e.target.value)} />}
    </div>
  );

  return (
    <Modal show={show} title={title} onClose={onClose}>
      <form onSubmit={submit}>
        {message && <p>{message}</p>}
        {fields
          ? fields.map((f) => control(f.name, f.type || 'textarea', values[f.name] ?? '',
            (v) => setValues((s) => ({ ...s, [f.name]: v })), f.label, f.required))
          : inputType && control('value', inputType, value, setValue, label, required)}
        {error && <div className="alert alert-danger py-2">{error}</div>}
        <div className="d-flex justify-content-end gap-2">
          <button type="button" className="btn btn-outline-secondary" onClick={onClose}>Cancel</button>
          <button type="submit" className={`btn btn-${variant}`} disabled={busy}>
            {busy && <span className="spinner-border spinner-border-sm me-2" />}{confirmText}
          </button>
        </div>
      </form>
    </Modal>
  );
}
