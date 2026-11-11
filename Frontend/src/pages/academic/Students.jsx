import { PageHeader } from '../../components/common/ui';
import StudentsTable from '../../components/shared/StudentsTable';

export default function AcademicStudents() {
  return (
    <>
      <PageHeader title="Assigned Students" subtitle="Students you supervise, their host organizations and progress" />
      <StudentsTable basePath="/academic/students" />
    </>
  );
}
