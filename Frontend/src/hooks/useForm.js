import { useCallback, useState } from 'react';

import { errorMessage, fieldErrors } from '../services/api';

/** Small form helper: values, per-field errors, a general error and a submitting flag. */
export default function useForm(initial) {
  const [values, setValues] = useState(initial);
  const [errors, setErrors] = useState({});
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const onChange = useCallback((e) => {
    const { name, type, value, checked, files } = e.target;
    let v = value;
    if (type === 'checkbox') v = checked;
    else if (type === 'file') v = files?.[0] || null;
    setValues((s) => ({ ...s, [name]: v }));
    setErrors((s) => ({ ...s, [name]: undefined }));
  }, []);

  const submit = useCallback((fn) => async (e) => {
    e?.preventDefault?.();
    setSubmitting(true);
    setError('');
    setErrors({});
    try {
      return await fn(values);
    } catch (err) {
      setErrors(fieldErrors(err));
      setError(errorMessage(err));
      return undefined;
    } finally {
      setSubmitting(false);
    }
  }, [values]);

  return { values, setValues, onChange, errors, error, setError, submitting, submit, reset: () => setValues(initial) };
}
