import { useState } from 'react';

import { Card, DownloadButton, EmptyState, ErrorAlert, InfoRow, Loading, PageHeader, StatusBadge } from '../../components/common/ui';
import Field, { FormError, SubmitButton } from '../../components/forms/Field';
import PromptModal from '../../components/forms/PromptModal';
import { useToast } from '../../context/ToastContext';
import useFetch from '../../hooks/useFetch';
import useForm from '../../hooks/useForm';
import api, { toFormData } from '../../services/api';
import { formatDate, formatDateTime } from '../../services/format';

const EMPTY = {
  mode: 'directory', organization: '', organization_name: '', address: '', county: '', contact_person: '',
  phone_number: '', email: '', industry_category: '', attachment_period: '', start_date: '', end_date: '',
  supporting_document: null,
};

function PlacementForm({ placement, onDone, onCancel }) {
  const orgs = useFetch('/organizations/');
  const periods = useFetch('/attachment-periods/');
  const toast = useToast();
  const form = useForm(placement ? {
    ...EMPTY, organization: placement.organization.id, start_date: placement.start_date, end_date: placement.end_date,
    attachment_period: placement.attachment_period || '',
  } : EMPTY);
  const { values: v, onChange, errors } = form;
  const directory = v.mode === 'directory';

  const onSubmit = form.submit(async (vals) => {
    const { mode, ...rest } = vals;
    const payload = directory
      ? { organization: rest.organization, attachment_period: rest.attachment_period, start_date: rest.start_date,
        end_date: rest.end_date, supporting_document: rest.supporting_document }
      : { ...rest, organization: '' };
    const fd = toFormData(payload);
    if (placement) await api.put(`/placements/${placement.id}/`, fd);
    else await api.post('/placements/', fd);
    toast(placement ? 'Placement details resubmitted for approval.' : 'Placement submitted for approval.');
    onDone();
  });

  const f = (name, label, props = {}) => <Field name={name} label={label} value={v[name]} onChange={onChange} error={errors[name]} {...props} />;

  return (
    <form onSubmit={onSubmit} noValidate>
      <FormError error={form.error} />
      <div className="mb-3">
        <div className="form-check form-check-inline">
          <input className="form-check-input" type="radio" id="m-dir" name="mode" value="directory" checked={directory} onChange={onChange} />
          <label className="form-check-label" htmlFor="m-dir">Choose a registered organization</label>
        </div>
        <div className="form-check form-check-inline">
          <input className="form-check-input" type="radio" id="m-new" name="mode" value="new" checked={!directory} onChange={onChange} />
          <label className="form-check-label" htmlFor="m-new">My organization is not listed</label>
        </div>
      </div>
      {directory ? (
        f('organization', 'Organization', {
          required: true,
          options: (orgs.data || []).map((o) => ({ value: o.id, label: `${o.organization_name} — ${o.county}` })),
        })
      ) : (
        <div className="row">
          <div className="col-md-6">{f('organization_name', 'Organization name', { required: true })}</div>
          <div className="col-md-6">{f('industry_category', 'Industry / business category')}</div>
          <div className="col-md-6">{f('address', 'Organization address', { required: true })}</div>
          <div className="col-md-6">{f('county', 'Location (county)', { required: true })}</div>
          <div className="col-md-4">{f('contact_person', 'Contact person', { required: true })}</div>
          <div className="col-md-4">{f('phone_number', 'Contact telephone', { required: true, type: 'tel' })}</div>
          <div className="col-md-4">{f('email', 'Contact email', { required: true, type: 'email' })}</div>
        </div>
      )}
      <div className="row">
        <div className="col-md-4">
          {f('attachment_period', 'Attachment period', { options: (periods.data || []).map((p) => ({ value: p.id, label: p.name })), placeholder: 'Not specified' })}
        </div>
        <div className="col-md-4">{f('start_date', 'Attachment start date', { type: 'date', required: true })}</div>
        <div className="col-md-4">{f('end_date', 'Attachment completion date', { type: 'date', required: true })}</div>
      </div>
      {f('supporting_document', 'Supporting document (acceptance letter)', {
        type: 'file', accept: '.pdf,.doc,.docx,.jpg,.jpeg,.png', help: placement?.supporting_document_url ? 'Leave empty to keep the current document.' : 'PDF, Word or image, up to 10 MB.',
      })}
      <div className="d-flex gap-2">
        <SubmitButton submitting={form.submitting}>{placement ? 'Resubmit for approval' : 'Submit for approval'}</SubmitButton>
        {onCancel && <button type="button" className="btn btn-outline-secondary" onClick={onCancel}>Cancel</button>}
      </div>
    </form>
  );
}

function PlacementDetails({ p }) {
  return (
    <>
      <InfoRow label="Status"><StatusBadge status={p.application_status} label={p.application_status_label} /></InfoRow>
      <InfoRow label="Organization">{p.organization.organization_name}</InfoRow>
      <InfoRow label="Address">{p.organization.address}, {p.organization.county}</InfoRow>
      <InfoRow label="Contact">{p.organization.contact_person} · {p.organization.phone_number} · {p.organization.email}</InfoRow>
      <InfoRow label="Period">{p.attachment_period_name}</InfoRow>
      <InfoRow label="Dates">{formatDate(p.start_date)} – {formatDate(p.end_date)}</InfoRow>
      <InfoRow label="Applied on">{formatDateTime(p.application_date)}</InfoRow>
      {p.application_status === 'approved' && (
        <InfoRow label="Attachment status"><StatusBadge status={p.attachment_status} label={p.attachment_status_label} /></InfoRow>
      )}
      {p.approval_comments && <InfoRow label="Administrator comments"><em>{p.approval_comments}</em></InfoRow>}
      {p.withdrawal_reason && <InfoRow label="Withdrawal reason">{p.withdrawal_reason}</InfoRow>}
      {p.supporting_document_url && <InfoRow label="Document"><DownloadButton url={p.supporting_document_url} /></InfoRow>}
      {p.assignment && (
        <>
          <InfoRow label="Academic supervisor">{p.assignment.academic_supervisor.full_name} ({p.assignment.academic_supervisor.email})</InfoRow>
          <InfoRow label="Industrial supervisor">{p.assignment.industrial_supervisor.full_name} ({p.assignment.industrial_supervisor.email})</InfoRow>
        </>
      )}
    </>
  );
}

export default function StudentPlacement() {
  const { data, loading, error, reload } = useFetch('/placements/');
  const [editing, setEditing] = useState(false);
  const [withdrawing, setWithdrawing] = useState(null);
  const toast = useToast();

  if (loading) return <Loading />;
  const list = data || [];
  const open = list.find((p) => ['pending', 'returned'].includes(p.application_status));
  const running = list.find((p) => p.application_status === 'approved' && ['not_started', 'active'].includes(p.attachment_status));
  const current = open || running;
  const canApply = !current;

  return (
    <>
      <PageHeader title="Placement" subtitle="Submit your organization details to the administrator for approval" />
      <ErrorAlert error={error} onRetry={reload} />

      {current && !editing && (
        <Card title="Current placement"
          actions={open && (
            <>
              <button type="button" className="btn btn-sm btn-primary" onClick={() => setEditing(true)}>
                <i className="bi bi-pencil me-1" />{open.application_status === 'returned' ? 'Correct and resubmit' : 'Edit'}
              </button>
              <button type="button" className="btn btn-sm btn-outline-danger" onClick={() => setWithdrawing(open)}>Withdraw</button>
            </>
          )}>
          {open?.application_status === 'returned' && (
            <div className="alert alert-warning">The administrator returned this application for correction. Update the details and resubmit.</div>
          )}
          <PlacementDetails p={current} />
        </Card>
      )}

      {(editing || canApply) && (
        <Card title={editing ? 'Update placement details' : 'New placement application'}>
          <PlacementForm placement={editing ? open : null}
            onDone={() => { setEditing(false); reload(); }}
            onCancel={editing ? () => setEditing(false) : null} />
        </Card>
      )}

      <Card title="Application history" bodyClass="p-0">
        {list.length === 0 ? <EmptyState text="No applications yet." /> : (
          <div className="table-responsive">
            <table className="table mb-0 align-middle">
              <thead><tr><th>Applied</th><th>Organization</th><th>Dates</th><th>Status</th><th>Comments</th></tr></thead>
              <tbody>
                {list.map((p) => (
                  <tr key={p.id}>
                    <td>{formatDate(p.application_date)}</td>
                    <td>{p.organization.organization_name}</td>
                    <td className="small">{formatDate(p.start_date)} – {formatDate(p.end_date)}</td>
                    <td><StatusBadge status={p.application_status} label={p.application_status_label} /></td>
                    <td className="small">{p.approval_comments || p.withdrawal_reason || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <PromptModal show={Boolean(withdrawing)} title="Withdraw application" label="Reason for withdrawal" required
        variant="danger" confirmText="Withdraw" onClose={() => setWithdrawing(null)}
        onSubmit={async (reason) => {
          await api.post(`/placements/${withdrawing.id}/withdraw/`, { reason });
          toast('Application withdrawn.');
          reload();
        }} />
    </>
  );
}
