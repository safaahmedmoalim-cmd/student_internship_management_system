import { useState } from 'react';

import { PageHeader, StatusBadge } from '../../components/common/ui';
import CrudTable from '../../components/shared/CrudTable';
import { useToast } from '../../context/ToastContext';
import api, { errorMessage } from '../../services/api';

const STATUS = [{ value: 'active', label: 'Active' }, { value: 'pending', label: 'Pending Verification' }, { value: 'inactive', label: 'Inactive' }];
const FIELDS = [
  { name: 'organization_name', label: 'Organization name', required: true, col: 'col-md-8' },
  { name: 'status', label: 'Status', options: STATUS, placeholder: false, default: 'active', col: 'col-md-4' },
  { name: 'address', label: 'Physical address', required: true, col: 'col-md-8' },
  { name: 'county', label: 'County', required: true, col: 'col-md-4' },
  { name: 'contact_person', label: 'Contact person', required: true, col: 'col-md-4' },
  { name: 'phone_number', label: 'Telephone', required: true, col: 'col-md-4' },
  { name: 'email', label: 'Email', type: 'email', required: true, col: 'col-md-4' },
  { name: 'industry_category', label: 'Industry / business category' },
];
const COLUMNS = [
  { key: 'organization_name', label: 'Organization', render: (o) => <><div className="fw-semibold">{o.organization_name}</div><div className="small text-muted">{o.industry_category}</div></> },
  { key: 'county', label: 'Location', render: (o) => <span className="small">{o.address}, {o.county}</span> },
  { key: 'contact', label: 'Contact', render: (o) => <span className="small">{o.contact_person}<br />{o.phone_number} · {o.email}</span> },
  { key: 'placement_count', label: 'Placements' },
  { key: 'supervisor_count', label: 'Supervisors' },
  { key: 'status', label: 'Status', render: (o) => <StatusBadge status={o.status} label={o.status_label} /> },
];

export default function AdminOrganizations() {
  const toast = useToast();
  const [status, setStatus] = useState('');
  const verify = async (o, reload) => {
    try {
      await api.patch(`/organizations/${o.id}/`, { status: 'active' });
      toast(`${o.organization_name} verified.`);
      reload();
    } catch (e) { toast(errorMessage(e), 'danger'); }
  };
  return (
    <>
      <PageHeader title="Host Organizations" subtitle="Directory of organizations offering internship and attachment opportunities" />
      <CrudTable endpoint="/organizations/" params={status ? { status } : undefined} columns={COLUMNS} fields={FIELDS} noun="Organization"
        toolbar={(
          <select className="form-select" value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Filter by status">
            <option value="">All statuses</option>
            {STATUS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>
        )}
        rowActions={(o, reload) => o.status === 'pending' && (
          <button type="button" className="btn btn-sm btn-success" onClick={() => verify(o, reload)}>Verify</button>
        )} />
    </>
  );
}
