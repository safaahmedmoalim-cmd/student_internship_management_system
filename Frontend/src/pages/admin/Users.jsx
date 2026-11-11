import { useState } from 'react';

import Modal from '../../components/common/Modal';
import { EmptyState, ErrorAlert, Loading, PageHeader, StatusBadge } from '../../components/common/ui';
import Field, { FormError, SubmitButton } from '../../components/forms/Field';
import PromptModal from '../../components/forms/PromptModal';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import useFetch from '../../hooks/useFetch';
import useForm from '../../hooks/useForm';
import useMeta from '../../hooks/useMeta';
import api, { errorMessage } from '../../services/api';
import { formatDateTime, ROLE_LABEL } from '../../services/format';

const PROFILE_FIELDS = {
  student: ['registration_number', 'first_name', 'last_name', 'phone_number', 'department', 'academic_year'],
  academic: ['staff_number', 'first_name', 'last_name', 'phone_number', 'department'],
  industrial: ['organization', 'employee_number', 'first_name', 'last_name', 'phone_number', 'job_title'],
  admin: [],
};
const LABELS = {
  registration_number: 'Registration number', staff_number: 'Staff number', employee_number: 'Employee number',
  first_name: 'First name', last_name: 'Last name', phone_number: 'Phone number', department: 'Department',
  academic_year: 'Academic year', organization: 'Organization', job_title: 'Job title',
};
const REQUIRED = new Set(['registration_number', 'staff_number', 'first_name', 'last_name', 'department', 'academic_year', 'organization', 'job_title']);

function UserForm({ user, role, onDone, onCancel }) {
  const meta = useMeta();
  const departments = useFetch('/departments/');
  const orgs = useFetch('/organizations/');
  const toast = useToast();
  const p = user?.profile || {};
  const fields = PROFILE_FIELDS[role];
  const form = useForm({
    username: user?.username || '', email: user?.email || '', password: '',
    ...Object.fromEntries(fields.map((f) => [f, p[f] ?? ''])),
  });
  const { values: v, onChange, errors } = form;
  const options = {
    department: (departments.data || []).map((d) => ({ value: d.id, label: d.department_name })),
    organization: (orgs.data || []).filter((o) => o.status !== 'inactive').map((o) => ({ value: o.id, label: o.organization_name })),
    academic_year: meta?.academic_years || [],
  };

  const onSubmit = form.submit(async (vals) => {
    const profile = Object.fromEntries(fields.map((f) => [f, vals[f]]));
    const body = { username: vals.username, email: vals.email, profile: fields.length ? profile : undefined };
    if (vals.password) body.password = vals.password;
    if (user) {
      await api.patch(`/users/${user.id}/`, body);
      toast('Account updated.');
      onDone();
    } else {
      const { data } = await api.post('/users/', { ...body, role });
      toast('Account created.');
      onDone(data.temporary_password ? { username: data.username, password: data.temporary_password } : null);
    }
  });

  return (
    <form onSubmit={onSubmit} noValidate>
      <FormError error={form.error} />
      <div className="row">
        <div className="col-md-6"><Field label="Username" name="username" value={v.username} onChange={onChange} error={errors.username} required /></div>
        <div className="col-md-6"><Field label="Email" name="email" type="email" value={v.email} onChange={onChange} error={errors.email} required /></div>
        {fields.map((f) => (
          <div key={f} className="col-md-6">
            <Field label={LABELS[f]} name={f} value={v[f]} onChange={onChange} error={errors[f]} required={REQUIRED.has(f)} options={options[f]} />
          </div>
        ))}
        <div className="col-md-6">
          <Field label={user ? 'New password (optional)' : 'Password (optional)'} name="password" type="password" value={v.password}
            onChange={onChange} error={errors.password} autoComplete="new-password"
            help={user ? 'Leave empty to keep the current password.' : 'Leave empty to generate a temporary password.'} />
        </div>
      </div>
      <div className="d-flex justify-content-end gap-2">
        <button type="button" className="btn btn-outline-secondary" onClick={onCancel}>Cancel</button>
        <SubmitButton submitting={form.submitting}>{user ? 'Save changes' : 'Create account'}</SubmitButton>
      </div>
    </form>
  );
}

export default function AdminUsers() {
  const { user: me } = useAuth();
  const toast = useToast();
  const [role, setRole] = useState('student');
  const [active, setActive] = useState('');
  const [search, setSearch] = useState('');
  const [query, setQuery] = useState('');
  const params = { role, ...(active ? { is_active: active } : {}), ...(query ? { search: query } : {}) };
  const { data, loading, error, reload } = useFetch('/users/', params);
  const [editing, setEditing] = useState(null); // 'new' | user
  const [credentials, setCredentials] = useState(null);
  const [resetting, setResetting] = useState(null);

  const toggle = async (u) => {
    try {
      await api.post(`/users/${u.id}/${u.is_active ? 'deactivate' : 'activate'}/`);
      toast(`${u.username} ${u.is_active ? 'deactivated' : 'activated'}.`);
      reload();
    } catch (e) { toast(errorMessage(e), 'danger'); }
  };

  const idOf = (u) => u.profile?.registration_number || u.profile?.staff_number || u.profile?.employee_number || '—';
  const unitOf = (u) => u.profile?.department_name || u.profile?.organization_name || '—';

  return (
    <>
      <PageHeader title="User Management" subtitle="Register and manage students, supervisors and administrators"
        actions={<button type="button" className="btn btn-primary" onClick={() => setEditing('new')}><i className="bi bi-person-plus me-1" />New {ROLE_LABEL[role].toLowerCase()}</button>} />
      <ul className="nav nav-tabs mb-3">
        {Object.entries(ROLE_LABEL).map(([k, label]) => (
          <li className="nav-item" key={k}><button type="button" className={`nav-link ${role === k ? 'active' : ''}`} onClick={() => setRole(k)}>{label}s</button></li>
        ))}
      </ul>
      <form className="filter-bar" onSubmit={(e) => { e.preventDefault(); setQuery(search.trim()); }}>
        <input className="form-control" placeholder="Search name, username, email, number" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search users" />
        <select className="form-select" value={active} onChange={(e) => setActive(e.target.value)} aria-label="Filter by account status">
          <option value="">Active and inactive</option><option value="true">Active only</option><option value="false">Inactive only</option>
        </select>
        <button type="submit" className="btn btn-outline-primary" style={{ flex: '0 0 auto' }}>Search</button>
      </form>
      <ErrorAlert error={error} onRetry={reload} />
      {loading ? <Loading /> : (data || []).length === 0 ? <EmptyState icon="people" text="No accounts found." /> : (
        <div className="card table-responsive">
          <table className="table table-hover mb-0 align-middle">
            <thead><tr><th>Name</th><th>Username / email</th>{role !== 'admin' && <><th>Number</th><th>{role === 'industrial' ? 'Organization' : 'Department'}</th></>}<th>Last login</th><th>Status</th><th /></tr></thead>
            <tbody>
              {data.map((u) => (
                <tr key={u.id}>
                  <td className="fw-semibold">{u.full_name}</td>
                  <td className="small">{u.username}<div className="text-muted">{u.email}</div></td>
                  {role !== 'admin' && <><td className="small">{idOf(u)}</td><td className="small">{unitOf(u)}</td></>}
                  <td className="small">{formatDateTime(u.last_login)}</td>
                  <td><StatusBadge status={u.is_active ? 'active' : 'inactive'} /></td>
                  <td className="text-end text-nowrap">
                    <button type="button" className="btn btn-sm btn-outline-primary me-1" onClick={() => setEditing(u)} aria-label="Edit"><i className="bi bi-pencil" /></button>
                    <button type="button" className="btn btn-sm btn-outline-secondary me-1" onClick={() => setResetting(u)} title="Reset password"><i className="bi bi-key" /></button>
                    {u.id !== me.id && (
                      <button type="button" className={`btn btn-sm ${u.is_active ? 'btn-outline-danger' : 'btn-outline-success'}`} onClick={() => toggle(u)}>
                        {u.is_active ? 'Deactivate' : 'Activate'}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Modal show={Boolean(editing)} size="lg" onClose={() => setEditing(null)}
        title={editing === 'new' ? `New ${ROLE_LABEL[role].toLowerCase()} account` : `Edit ${editing?.username}`}>
        {editing && (
          <UserForm user={editing === 'new' ? null : editing} role={editing === 'new' ? role : editing.role}
            onCancel={() => setEditing(null)}
            onDone={(creds) => { setEditing(null); if (creds) setCredentials(creds); reload(); }} />
        )}
      </Modal>
      <Modal show={Boolean(credentials)} title="Temporary password" onClose={() => setCredentials(null)}
        footer={<button type="button" className="btn btn-primary" onClick={() => setCredentials(null)}>Done</button>}>
        <p>Give these sign-in details to the user. The password is shown only once; ask them to change it after signing in.</p>
        <div className="border rounded p-3 bg-light font-monospace">
          <div>Username: {credentials?.username}</div>
          <div>Password: {credentials?.password}</div>
        </div>
      </Modal>
      <PromptModal show={Boolean(resetting)} title={`Reset password for ${resetting?.username}`} inputType="password"
        label="New password (leave empty to generate one)" confirmText="Reset password" variant="warning"
        message="The user will be signed out of every device." onClose={() => setResetting(null)}
        onSubmit={async (pw) => {
          const { data: r } = await api.post(`/users/${resetting.id}/reset-password/`, { new_password: pw });
          setCredentials({ username: resetting.username, password: r.temporary_password });
        }} />
    </>
  );
}
