import { useState } from 'react';
import { Link } from 'react-router-dom';

import Field, { FormError, SubmitButton } from '../../components/forms/Field';
import useForm from '../../hooks/useForm';
import api from '../../services/api';

export default function ForgotPassword() {
  const form = useForm({ email: '' });
  const [sent, setSent] = useState('');

  const onSubmit = form.submit(async (v) => {
    const { data } = await api.post('/auth/password-reset/', { email: v.email.trim() });
    setSent(data.detail);
  });

  return (
    <>
      <h2 className="h3 fw-bold mb-1">Reset your password</h2>
      <p className="text-muted mb-4">Enter your account email and we will send you a reset link.</p>
      {sent ? (
        <div className="alert alert-success">{sent}</div>
      ) : (
        <form onSubmit={onSubmit} noValidate>
          <FormError error={form.error} />
          <Field label="Email" name="email" type="email" value={form.values.email} onChange={form.onChange}
            error={form.errors.email} required autoFocus />
          <SubmitButton submitting={form.submitting} className="btn btn-primary w-100">Send reset link</SubmitButton>
        </form>
      )}
      <p className="text-center mt-4"><Link to="/login">Back to sign in</Link></p>
      <p className="small text-muted text-center">If you no longer have access to your email, ask the administrator to reset your password.</p>
    </>
  );
}
