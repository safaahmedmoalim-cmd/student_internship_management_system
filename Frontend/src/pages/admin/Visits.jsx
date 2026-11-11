import { PageHeader } from '../../components/common/ui';
import VisitsManager from '../../components/shared/VisitsManager';

export default function AdminVisits() {
  return (
    <>
      <PageHeader title="Supervision Visits"
        subtitle="Monitor supervision progress. Visits scheduled here are assigned to the student's academic supervisor." />
      <VisitsManager />
    </>
  );
}
