import { Card, EmptyState, ErrorAlert, Loading, PageHeader } from '../../components/common/ui';
import ScoreRubric from '../../components/forms/ScoreRubric';
import useFetch from '../../hooks/useFetch';
import { formatDate } from '../../services/format';

export default function StudentAssessments() {
  const { data, loading, error, reload } = useFetch('/assessments/');
  const list = data || [];
  const avg = list.length ? Math.round(list.reduce((s, a) => s + Number(a.marks), 0) / list.length * 100) / 100 : null;
  return (
    <>
      <PageHeader title="Assessment Results" subtitle="Released academic and workplace assessments" />
      <ErrorAlert error={error} onRetry={reload} />
      {loading ? <Loading /> : list.length === 0 ? (
        <EmptyState icon="award" text="No results have been released yet." />
      ) : (
        <>
          {list.length > 1 && <div className="alert alert-primary">Average mark: <strong>{avg}%</strong></div>}
          <div className="row">
            {list.map((a) => (
              <div className="col-lg-6" key={a.id}>
                <Card title={a.assessment_type_label} actions={<span className="badge bg-primary fs-6">{Number(a.marks)}%</span>}>
                  <div className="small text-muted mb-2">Assessed by {a.supervisor_name} · {formatDate(a.assessment_date)}</div>
                  <ScoreRubric criteria={Object.keys(a.assessment_criteria)} scores={a.assessment_criteria} readOnly />
                  {a.comments && <><div className="fw-semibold mt-3">Comments</div><p className="pre-wrap mb-2">{a.comments}</p></>}
                  {a.recommendations && <><div className="fw-semibold">Recommendations</div><p className="pre-wrap mb-0">{a.recommendations}</p></>}
                </Card>
              </div>
            ))}
          </div>
        </>
      )}
    </>
  );
}
