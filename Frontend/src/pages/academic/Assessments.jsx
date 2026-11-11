import { PageHeader } from '../../components/common/ui';
import AssessmentManager from '../../components/shared/AssessmentManager';

export default function AcademicAssessments() {
  return (
    <>
      <PageHeader title="Student Evaluation" subtitle="Assess each student with the academic rubric" />
      <AssessmentManager />
    </>
  );
}
