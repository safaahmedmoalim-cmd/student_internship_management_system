import { useEffect } from 'react';

import { Card, ErrorAlert, Loading, PageHeader } from '../../components/common/ui';
import Field, { FormError, SubmitButton } from '../../components/forms/Field';
import { useToast } from '../../context/ToastContext';
import useFetch from '../../hooks/useFetch';
import useForm from '../../hooks/useForm';
import api from '../../services/api';
import { formatDateTime } from '../../services/format';

export default function AdminSettings() {
  const toast = useToast();
  const { data, loading, error, reload } = useFetch('/settings/');
  const form = useForm({ institution_name: '', allow_student_registration: true, required_logbook_weeks: 12 });
  const { setValues } = form;

  useEffect(() => { if (data) setValues(data); }, [data, setValues]);

  const onSubmit = form.submit(async (v) => {
    await api.patch('/settings/', {
      institution_name: v.institution_name, allow_student_registration: v.allow_student_registration,
      required_logbook_weeks: Number(v.required_logbook_weeks),
    });
    toast('Settings saved.');
    reload();
  });

  if (loading) return <Loading />;
  return (
    <>
      <PageHeader title="System Settings" subtitle="Institution-wide settings" />
      <ErrorAlert error={error} onRetry={reload} />
      <div className="row">
        <div className="col-lg-7">
          <Card title="General">
            <form onSubmit={onSubmit} noValidate>
              <FormError error={form.error} />
              <Field label="Institution name" name="institution_name" value={form.values.institution_name} onChange={form.onChange}
                error={form.errors.institution_name} help="Shown on exported reports." required />
              <Field label="Required number of approved weekly logbooks" name="required_logbook_weeks" type="number" min={1} max={52}
                value={form.values.required_logbook_weeks} onChange={form.onChange} error={form.errors.required_logbook_weeks} />
              <Field label="Allow students to register their own accounts" name="allow_student_registration" type="checkbox"
                value={form.values.allow_student_registration} onChange={form.onChange} />
              <SubmitButton submitting={form.submitting}>Save settings</SubmitButton>
              {data?.updated_at && <span className="small text-muted ms-3">Last changed {formatDateTime(data.updated_at)}</span>}
            </form>
          </Card>
        </div>
        <div className="col-lg-5">
          <Card title="Related settings">
            <ul className="mb-0 small">
              <li>Attachment periods and deadlines: <a href="/admin/periods">Attachment Periods</a></li>
              <li>Departments: <a href="/admin/departments">Departments</a></li>
              <li>Server settings (database, email, upload size, token lifetimes) are configured in <code>Backend/.env</code>.</li>
            </ul>
          </Card>
        </div>
      </div>
    </>
  );
}
