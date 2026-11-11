import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import Field, { FormError, SubmitButton } from '../../components/forms/Field';
import useForm from '../../hooks/useForm';
import api from '../../services/api';

export default function ResetPassword() {
  const [params] = useSearchParams();
  const form = useForm({ new_password: '', confirm_password: '' });
  const [done, setDone] = useState('');
  const uid = params.get('uid');
  const token = params.get('token');

  const onSubmit = form.submit(async (v) => {
    const { data } = await api.post('/auth/password-reset/confirm/', { uid, token, ...v });
    setDone(data.detail);
  });

  if (!uid || !token) {
    return <div className="alert alert-warning">This reset link is incomplete. <Link to="/forgot-password">Request a new one</Link>.</div>;
  }

  return (
    <>
      <h2 className="h3 fw-bold mb-4">Choose a new password</h2>
      {done ? (
        <div className="alert alert-success">{done} <Link to="/login">Sign in</Link></div>
      ) : (
        <form onSubmit={onSubmit} noValidate>
          <FormError error={form.error} />
          <Field label="New password" name="new_password" type="password" value={form.values.new_password}
            onChange={form.onChange} error={form.errors.new_password} required autoComplete="new-password" />
          <Field label="Confirm new password" name="confirm_password" type="password" value={form.values.confirm_password}
            onChange={form.onChange} error={form.errors.confirm_password} required autoComplete="new-password" />
          <SubmitButton submitting={form.submitting} className="btn btn-primary w-100">Reset password</SubmitButton>
        </form>
      )}
    </>
  );
}
