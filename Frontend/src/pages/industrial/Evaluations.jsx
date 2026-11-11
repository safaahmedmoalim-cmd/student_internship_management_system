import { PageHeader } from '../../components/common/ui';
import AssessmentManager from '../../components/shared/AssessmentManager';

export default function IndustrialEvaluations() {
  return (
    <>
      <PageHeader title="Workplace Evaluation" subtitle="Rate each intern on the ten workplace skill areas" />
      <AssessmentManager />
    </>
  );
}
