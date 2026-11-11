import { PageHeader } from '../../components/common/ui';
import CrudTable from '../../components/shared/CrudTable';

const FIELDS = [
  { name: 'department_name', label: 'Department name', required: true, col: 'col-md-8' },
  { name: 'department_code', label: 'Code', required: true, col: 'col-md-4' },
  { name: 'description', label: 'Description', as: 'textarea' },
];
const COLUMNS = [
  { key: 'department_code', label: 'Code' },
  { key: 'department_name', label: 'Department' },
  { key: 'description', label: 'Description', className: 'small' },
  { key: 'student_count', label: 'Students' },
  { key: 'supervisor_count', label: 'Academic supervisors' },
];

export default function AdminDepartments() {
  return (
    <>
      <PageHeader title="Departments" subtitle="Academic departments students and lecturers belong to" />
      <CrudTable endpoint="/departments/" columns={COLUMNS} fields={FIELDS} noun="Department" />
    </>
  );
}
