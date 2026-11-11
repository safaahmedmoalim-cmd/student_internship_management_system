import { PageHeader } from '../../components/common/ui';
import ReportsView from '../../components/shared/ReportsView';

export default function AdminReports() {
  return (
    <>
      <PageHeader title="Reports & Analytics" subtitle="Generate student and attachment reports and export them to PDF or Excel" />
      <ReportsView />
    </>
  );
}
