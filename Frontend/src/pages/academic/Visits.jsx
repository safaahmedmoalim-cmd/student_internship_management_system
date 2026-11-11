import { PageHeader } from '../../components/common/ui';
import VisitsManager from '../../components/shared/VisitsManager';

export default function AcademicVisits() {
  return (
    <>
      <PageHeader title="Supervision Visits" subtitle="Schedule physical or virtual visits and record visit reports" />
      <VisitsManager />
    </>
  );
}
