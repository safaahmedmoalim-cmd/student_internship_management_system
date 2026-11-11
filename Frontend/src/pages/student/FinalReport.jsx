import { Card, DownloadButton, EmptyState, ErrorAlert, Loading, PageHeader, StatusBadge } from '../../components/common/ui';
import Field, { FormError, SubmitButton } from '../../components/forms/Field';
import { useToast } from '../../context/ToastContext';
import useFetch from '../../hooks/useFetch';
import useForm from '../../hooks/useForm';
import api, { toFormData } from '../../services/api';
import { formatDateTime } from '../../services/format';

export default function StudentFinalReport() {
  const { data, loading, error, reload } = useFetch('/final-reports/');
  const toast = useToast();
  const form = useForm({ title: '', report_file: null });
  const versions = data || [];
  const latest = versions[0];
  const canUpload = !latest || latest.review_status === 'returned';

  const onSubmit = form.submit(async (v) => {
    const { data: r } = await api.post('/final-reports/', toFormData(v));
    toast(r.late ? 'Report uploaded (after the report deadline).' : 'Report submitted to your academic supervisor.', r.late ? 'warning' : 'success');
    form.reset();
    reload();
  });

  return (
    <>
      <PageHeader title="Final Attachment Report" subtitle="Upload your report for review by your academic supervisor" />
      <ErrorAlert error={error} onRetry={reload} />
      {loading ? <Loading /> : (
        <>
          {latest?.review_status === 'returned' && (
            <div className="alert alert-warning"><strong>Corrections requested:</strong> <span className="pre-wrap">{latest.feedback}</span></div>
          )}
          {latest?.review_status === 'approved' && (
            <div className="alert alert-success"><i className="bi bi-check-circle me-2" />Your final report has been approved.{latest.feedback && ` Feedback: ${latest.feedback}`}</div>
          )}
          {canUpload && (
            <Card title={latest ? `Upload corrected report (version ${latest.version + 1})` : 'Upload report'}>
              <form onSubmit={onSubmit} noValidate>
                <FormError error={form.error} />
                <Field label="Report title" name="title" value={form.values.title} onChange={form.onChange} error={form.errors.title} required />
                <Field label="Report file" name="report_file" type="file" accept=".pdf,.doc,.docx" onChange={form.onChange}
                  error={form.errors.report_file} help="PDF or Word document, up to 10 MB." required />
                <SubmitButton submitting={form.submitting}>Submit report</SubmitButton>
              </form>
            </Card>
          )}
          <Card title="Submission history" bodyClass="p-0">
            {versions.length === 0 ? <EmptyState icon="file-earmark" text="No report submitted yet." /> : (
              <div className="table-responsive">
                <table className="table mb-0 align-middle">
                  <thead><tr><th>Version</th><th>Title</th><th>Submitted</th><th>Status</th><th>Feedback</th><th /></tr></thead>
                  <tbody>
                    {versions.map((r) => (
                      <tr key={r.id}>
                        <td>v{r.version}</td>
                        <td>{r.title}</td>
                        <td className="small">{formatDateTime(r.submission_date)}</td>
                        <td><StatusBadge status={r.review_status} label={r.review_status_label} /></td>
                        <td className="small pre-wrap">{r.feedback || '—'}</td>
                        <td><DownloadButton url={r.download_url} label="File" name={r.original_filename} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </>
      )}
    </>
  );
}
