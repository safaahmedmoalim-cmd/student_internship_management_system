import { PageHeader } from '../../components/common/ui';
import StudentsTable from '../../components/shared/StudentsTable';

export default function IndustrialInterns() {
  return (
    <>
      <PageHeader title="Assigned Interns" subtitle="Students on attachment at your organization who report to you" />
      <StudentsTable basePath="/industrial/interns" />
    </>
  );
}
