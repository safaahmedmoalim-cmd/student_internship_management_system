import { Card, InfoRow, PageHeader } from '../../components/common/ui';
import Field, { FormError, SubmitButton } from '../../components/forms/Field';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import useForm from '../../hooks/useForm';
import api, { tokens } from '../../services/api';
import { formatDateTime } from '../../services/format';

const EDITABLE = {
  student: ['first_name', 'last_name', 'phone_number'],
  academic: ['first_name', 'last_name', 'phone_number'],
  industrial: ['first_name', 'last_name', 'phone_number', 'job_title'],
  admin: [],
};
const LABELS = { first_name: 'First name', last_name: 'Last name', phone_number: 'Phone number', job_title: 'Job title' };

export default function Profile() {
  const { user, setUser } = useAuth();
  const toast = useToast();
  const p = user.profile || {};
  const editable = EDITABLE[user.role];
  const details = useForm({ email: user.email, ...Object.fromEntries(editable.map((f) => [f, p[f] || ''])) });
  const pw = useForm({ current_password: '', new_password: '', confirm_password: '' });

  const saveDetails = details.submit(async (v) => {
    const { data } = await api.patch('/auth/me/', v);
    setUser(data);
    toast('Profile updated.');
  });
  const changePassword = pw.submit(async (v) => {
    const { data } = await api.post('/auth/change-password/', v);
    tokens.set(data.access, data.refresh);
    pw.reset();
    toast('Password changed. Other sessions have been signed out.');
  });

  return (
    <>
      <PageHeader title="My Profile" subtitle="Your account and personal information" />
      <div className="row">
        <div className="col-lg-6">
          <Card title="Account information">
            <InfoRow label="Username">{user.username}</InfoRow>
            <InfoRow label="Role">{user.role_label}</InfoRow>
            {user.role === 'student' && (
              <>
                <InfoRow label="Registration no.">{p.registration_number}</InfoRow>
                <InfoRow label="Department">{p.department_name}</InfoRow>
                <InfoRow label="Academic year">{p.academic_year}</InfoRow>
              </>
            )}
            {user.role === 'academic' && (
              <>
                <InfoRow label="Staff number">{p.staff_number}</InfoRow>
                <InfoRow label="Department">{p.department_name}</InfoRow>
              </>
            )}
            {user.role === 'industrial' && (
              <>
                <InfoRow label="Organization">{p.organization_name}</InfoRow>
                <InfoRow label="Employee number">{p.employee_number}</InfoRow>
              </>
            )}
            <InfoRow label="Member since">{formatDateTime(user.date_joined)}</InfoRow>
            <InfoRow label="Last login">{formatDateTime(user.last_login)}</InfoRow>
            <p className="small text-muted mt-3 mb-0">
              Registration, staff and department details are managed by the administrator.
            </p>
          </Card>
        </div>
        <div className="col-lg-6">
          <Card title="Edit personal information">
            <form onSubmit={saveDetails} noValidate>
              <FormError error={details.error} />
              <Field label="Email" name="email" type="email" value={details.values.email} onChange={details.onChange}
                error={details.errors.email} required />
              {editable.map((f) => (
                <Field key={f} label={LABELS[f]} name={f} value={details.values[f]} onChange={details.onChange}
                  error={details.errors[f]} />
              ))}
              <SubmitButton submitting={details.submitting}>Save changes</SubmitButton>
            </form>
          </Card>
          <Card title="Change password">
            <form onSubmit={changePassword} noValidate>
              <FormError error={pw.error} />
              <Field label="Current password" name="current_password" type="password" value={pw.values.current_password}
                onChange={pw.onChange} error={pw.errors.current_password} autoComplete="current-password" />
              <Field label="New password" name="new_password" type="password" value={pw.values.new_password}
                onChange={pw.onChange} error={pw.errors.new_password} autoComplete="new-password" />
              <Field label="Confirm new password" name="confirm_password" type="password" value={pw.values.confirm_password}
                onChange={pw.onChange} error={pw.errors.confirm_password} autoComplete="new-password" />
              <SubmitButton submitting={pw.submitting}>Change password</SubmitButton>
            </form>
          </Card>
        </div>
      </div>
    </>
  );
}
