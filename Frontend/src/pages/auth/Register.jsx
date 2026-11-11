import { Link, Navigate, useNavigate } from 'react-router-dom';

import { Loading } from '../../components/common/ui';
import Field, { FormError, SubmitButton } from '../../components/forms/Field';
import { useAuth } from '../../context/AuthContext';
import useFetch from '../../hooks/useFetch';
import useForm from '../../hooks/useForm';
import useMeta from '../../hooks/useMeta';

export default function Register() {
  const { user, register } = useAuth();
  const navigate = useNavigate();
  const meta = useMeta();
  const settings = useFetch('/settings/public/');
  const departments = useFetch('/departments/');
  const form = useForm({
    first_name: '', last_name: '', registration_number: '', department: '', academic_year: '', phone_number: '',
    username: '', email: '', password: '', confirm_password: '',
  });

  if (user) return <Navigate to="/" replace />;
  if (settings.loading) return <Loading />;
  if (settings.data && !settings.data.allow_student_registration) {
    return (
      <div className="alert alert-warning">
        Student self-registration is currently closed. Please contact the attachment office.
        <div className="mt-2"><Link to="/login">Back to sign in</Link></div>
      </div>
    );
  }

  const { values, onChange, errors } = form;
  const onSubmit = form.submit(async (v) => {
    await register({ ...v, department: Number(v.department) });
    navigate('/student', { replace: true });
  });
  const f = (name, label, props = {}) => (
    <Field name={name} label={label} value={values[name]} onChange={onChange} error={errors[name]} {...props} />
  );

  return (
    <>
      <h2 className="h3 fw-bold mb-1">Student registration</h2>
      <p className="text-muted mb-4">Use your college registration details.</p>
      <form onSubmit={onSubmit} noValidate>
        <FormError error={form.error} />
        <div className="row">
          <div className="col-sm-6">{f('first_name', 'First name', { required: true })}</div>
          <div className="col-sm-6">{f('last_name', 'Last name', { required: true })}</div>
          <div className="col-sm-6">{f('registration_number', 'Registration number', { required: true, placeholder: 'e.g. LTV/ICT/001/2024' })}</div>
          <div className="col-sm-6">{f('phone_number', 'Phone number', { type: 'tel' })}</div>
          <div className="col-sm-7">
            {f('department', 'Department', {
              required: true,
              options: (departments.data || []).map((d) => ({ value: d.id, label: d.department_name })),
            })}
          </div>
          <div className="col-sm-5">{f('academic_year', 'Academic year', { required: true, options: meta?.academic_years || [] })}</div>
          <div className="col-sm-6">{f('username', 'Username', { required: true, autoComplete: 'username' })}</div>
          <div className="col-sm-6">{f('email', 'Email', { type: 'email', required: true, autoComplete: 'email' })}</div>
          <div className="col-sm-6">{f('password', 'Password', { type: 'password', required: true, autoComplete: 'new-password', help: 'At least 8 characters, not only numbers.' })}</div>
          <div className="col-sm-6">{f('confirm_password', 'Confirm password', { type: 'password', required: true, autoComplete: 'new-password' })}</div>
        </div>
        <SubmitButton submitting={form.submitting} className="btn btn-primary w-100 py-2">Create account</SubmitButton>
      </form>
      <p className="text-center mt-4">Already registered? <Link to="/login">Sign in</Link></p>
    </>
  );
}
