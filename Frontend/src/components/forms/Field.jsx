/** Labelled input / select / textarea with Bootstrap validation styling. */
export default function Field({
  label, name, type = 'text', value, onChange, error, options, as, help, required, className = 'mb-3',
  placeholder, children, ...rest
}) {
  const id = `f-${name}`;
  const invalid = error ? 'is-invalid' : '';
  let control;
  if (as === 'select' || options) {
    control = (
      <select id={id} name={name} className={`form-select ${invalid}`} value={value ?? ''} onChange={onChange}
        required={required} {...rest}>
        {placeholder !== false && <option value="">{placeholder || 'Select…'}</option>}
        {(options || []).map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
        {children}
      </select>
    );
  } else if (as === 'textarea') {
    control = (
      <textarea id={id} name={name} className={`form-control ${invalid}`} value={value ?? ''} onChange={onChange}
        required={required} rows={rest.rows || 3} placeholder={placeholder} {...rest} />
    );
  } else if (type === 'file') {
    control = <input id={id} name={name} type="file" className={`form-control ${invalid}`} onChange={onChange} {...rest} />;
  } else if (type === 'checkbox') {
    return (
      <div className={`form-check ${className}`}>
        <input id={id} name={name} type="checkbox" className={`form-check-input ${invalid}`} checked={Boolean(value)}
          onChange={onChange} {...rest} />
        <label className="form-check-label" htmlFor={id}>{label}</label>
        {error && <div className="invalid-feedback d-block">{error}</div>}
      </div>
    );
  } else {
    control = (
      <input id={id} name={name} type={type} className={`form-control ${invalid}`} value={value ?? ''}
        onChange={onChange} required={required} placeholder={placeholder} {...rest} />
    );
  }
  return (
    <div className={className}>
      {label && <label htmlFor={id} className="form-label">{label}{required && <span className="text-danger"> *</span>}</label>}
      {control}
      {help && !error && <div className="form-text">{help}</div>}
      {error && <div className="invalid-feedback d-block">{error}</div>}
    </div>
  );
}

export function FormError({ error }) {
  return error ? <div className="alert alert-danger py-2">{error}</div> : null;
}

export function SubmitButton({ submitting, children, className = 'btn btn-primary', ...rest }) {
  return (
    <button type="submit" className={className} disabled={submitting} {...rest}>
      {submitting && <span className="spinner-border spinner-border-sm me-2" />}
      {children}
    </button>
  );
}
