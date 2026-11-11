import { PageHeader, StatusBadge } from '../../components/common/ui';
import CrudTable from '../../components/shared/CrudTable';
import { formatDate, formatDateTime } from '../../services/format';

const AUDIENCE = [
  { value: 'all', label: 'All users' }, { value: 'student', label: 'Students' },
  { value: 'academic', label: 'Academic supervisors' }, { value: 'industrial', label: 'Industrial supervisors' },
];
const FIELDS = [
  { name: 'title', label: 'Title', required: true },
  { name: 'message', label: 'Message', as: 'textarea', rows: 5, required: true },
  { name: 'target_audience', label: 'Send to', options: AUDIENCE, placeholder: false, default: 'all', col: 'col-md-6' },
  { name: 'expiry_date', label: 'Expiry date (optional)', type: 'date', col: 'col-md-6' },
];
const COLUMNS = [
  { key: 'title', label: 'Announcement', render: (a) => <><div className="fw-semibold">{a.title}</div><div className="small text-muted text-truncate" style={{ maxWidth: 380 }}>{a.message}</div></> },
  { key: 'target_audience', label: 'Audience', render: (a) => a.target_audience_label },
  { key: 'publication_date', label: 'Published', render: (a) => <span className="small">{formatDateTime(a.publication_date)}</span> },
  { key: 'expiry_date', label: 'Expires', render: (a) => <span className="small">{a.expiry_date ? formatDate(a.expiry_date) : 'Never'}</span> },
  { key: 'state', label: 'State', render: (a) => <StatusBadge status={a.is_expired ? 'inactive' : 'active'} label={a.is_expired ? 'Expired' : 'Visible'} /> },
];

export default function AdminAnnouncements() {
  return (
    <>
      <PageHeader title="Announcements" subtitle="Publish notices to all users or to selected groups. Recipients are notified immediately." />
      <CrudTable endpoint="/announcements/" columns={COLUMNS} fields={FIELDS} noun="Announcement" />
    </>
  );
}
