import { PageHeader } from '../../components/common/ui';
import LogbookReviewList from '../../components/shared/LogbookReviewList';

export default function AcademicLogbookReview() {
  return (
    <>
      <PageHeader title="Logbook Review" subtitle="Approve weekly entries or return them to the student with comments" />
      <LogbookReviewList />
    </>
  );
}
