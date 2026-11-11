import { PageHeader, StatusBadge } from '../../components/common/ui';
import CrudTable from '../../components/shared/CrudTable';
import { formatDate } from '../../services/format';

const FIELDS = [
  { name: 'name', label: 'Name', required: true, placeholder: 'e.g. May - August 2027' },
  { name: 'start_date', label: 'Start date', type: 'date', required: true, col: 'col-md-6' },
  { name: 'end_date', label: 'End date', type: 'date', required: true, col: 'col-md-6' },
  { name: 'application_deadline', label: 'Placement application deadline', type: 'date', required: true, col: 'col-md-6' },
  { name: 'report_deadline', label: 'Final report deadline', type: 'date', required: true, col: 'col-md-6' },
  { name: 'is_active', label: 'Active (students can apply for this period)', type: 'checkbox', default: true },
];
const COLUMNS = [
  { key: 'name', label: 'Period' },
  { key: 'dates', label: 'Dates', render: (p) => `${formatDate(p.start_date)} – ${formatDate(p.end_date)}` },
  { key: 'application_deadline', label: 'Application deadline', render: (p) => formatDate(p.application_deadline) },
  { key: 'report_deadline', label: 'Report deadline', render: (p) => formatDate(p.report_deadline) },
  { key: 'is_active', label: 'Status', render: (p) => <StatusBadge status={p.is_active ? 'active' : 'inactive'} /> },
];

export default function AdminPeriods() {
  return (
    <>
      <PageHeader title="Attachment Periods" subtitle="Attachment periods and their deadlines" />
      <CrudTable endpoint="/attachment-periods/" columns={COLUMNS} fields={FIELDS} noun="Attachment period" canDelete={false} />
    </>
  );
}
