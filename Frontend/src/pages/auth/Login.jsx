import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';

import Field, { FormError, SubmitButton } from '../../components/forms/Field';
import { useAuth } from '../../context/AuthContext';
import useForm from '../../hooks/useForm';
import { ROLE_HOME } from '../../services/format';

export default function Login() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const form = useForm({ username: '', password: '' });

  if (user) return <Navigate to={ROLE_HOME[user.role]} replace />;

  const onSubmit = form.submit(async (v) => {
    const u = await login(v.username.trim(), v.password);
    const from = location.state?.from;
    navigate(from && from.startsWith(ROLE_HOME[u.role]) ? from : ROLE_HOME[u.role], { replace: true });
  });

  return (
    <>
      <h2 className="h3 fw-bold mb-1">Sign in</h2>
      <p className="text-muted mb-4">Students, supervisors and administrators use the same sign-in page.</p>
      <form onSubmit={onSubmit} noValidate>
        <FormError error={form.error} />
        <Field label="Username or email" name="username" value={form.values.username} onChange={form.onChange}
          autoComplete="username" required autoFocus />
        <Field label="Password" name="password" type="password" value={form.values.password} onChange={form.onChange}
          autoComplete="current-password" required />
        <div className="d-flex justify-content-between align-items-center mb-3">
          <Link to="/forgot-password" className="small">Forgot password?</Link>
        </div>
        <SubmitButton submitting={form.submitting} className="btn btn-primary w-100 py-2">Sign in</SubmitButton>
      </form>
      <p className="text-center mt-4 mb-0">
        New student? <Link to="/register">Create your account</Link>
      </p>
      <p className="text-center small text-muted mt-2">Supervisor accounts are created by the administrator.</p>
    </>
  );
}
