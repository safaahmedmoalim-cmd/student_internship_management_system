import { PageHeader } from '../../components/common/ui';
import StudentsTable from '../../components/shared/StudentsTable';

export default function AdminStudents() {
  return (
    <>
      <PageHeader title="Students & Progress" subtitle="Every registered student and their attachment progress" />
      <StudentsTable basePath="/admin/students" />
    </>
  );
}
