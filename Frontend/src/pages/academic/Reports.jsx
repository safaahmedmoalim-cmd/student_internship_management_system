import { PageHeader } from '../../components/common/ui';
import ReportsView from '../../components/shared/ReportsView';

export default function AcademicReports() {
  return (
    <>
      <PageHeader title="Reports" subtitle="Progress, logbook and assessment reports for your students" />
      <ReportsView />
    </>
  );
}
