import { PageHeader } from '../../components/common/ui';
import LogbookReviewList from '../../components/shared/LogbookReviewList';

export default function AdminLogbooks() {
  return (
    <>
      <PageHeader title="Logbook Monitoring" subtitle="All weekly logbook submissions and their review status" />
      <LogbookReviewList />
    </>
  );
}
