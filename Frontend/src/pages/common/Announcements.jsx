import { EmptyState, ErrorAlert, Loading, PageHeader } from '../../components/common/ui';
import useFetch from '../../hooks/useFetch';
import { formatDate, formatDateTime } from '../../services/format';

export default function Announcements() {
  const { data, loading, error, reload } = useFetch('/announcements/');
  return (
    <>
      <PageHeader title="Announcements" subtitle="Notices from the attachment office" />
      <ErrorAlert error={error} onRetry={reload} />
      {loading ? <Loading /> : (data || []).length === 0 ? <EmptyState icon="megaphone" text="No announcements right now." /> : (
        (data || []).map((a) => (
          <div key={a.id} className="card mb-3">
            <div className="card-body">
              <div className="d-flex justify-content-between flex-wrap gap-2">
                <h2 className="h5 mb-1">{a.title}</h2>
                <span className="badge bg-light text-dark border">{a.target_audience_label}</span>
              </div>
              <div className="small text-muted mb-2">
                {formatDateTime(a.publication_date)}{a.administrator_name && ` · ${a.administrator_name}`}
                {a.expiry_date && ` · until ${formatDate(a.expiry_date)}`}
              </div>
              <p className="mb-0 pre-wrap">{a.message}</p>
            </div>
          </div>
        ))
      )}
    </>
  );
}
