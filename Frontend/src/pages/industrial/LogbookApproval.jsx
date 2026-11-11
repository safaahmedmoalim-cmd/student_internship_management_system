import { PageHeader } from '../../components/common/ui';
import LogbookReviewList from '../../components/shared/LogbookReviewList';

export default function IndustrialLogbookApproval() {
  return (
    <>
      <PageHeader title="Logbook Approval" subtitle="Approve satisfactory entries; reject unsatisfactory ones with an explanation" />
      <LogbookReviewList />
    </>
  );
}
