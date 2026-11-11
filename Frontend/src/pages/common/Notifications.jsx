import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { EmptyState, ErrorAlert, Loading, PageHeader } from '../../components/common/ui';
import useFetch from '../../hooks/useFetch';
import api from '../../services/api';
import { formatDateTime } from '../../services/format';

const ICONS = {
  placement: 'building', assignment: 'person-check', logbook: 'journal-text', visit: 'calendar-event',
  assessment: 'award', report: 'file-earmark-text', announcement: 'megaphone', deadline: 'alarm', account: 'person',
};

export default function Notifications() {
  const [unreadOnly, setUnreadOnly] = useState(false);
  const { data, loading, error, reload } = useFetch('/notifications/', unreadOnly ? { unread: 'true' } : undefined);
  const navigate = useNavigate();

  const changed = () => { reload(); window.dispatchEvent(new Event('sims:notifications')); };
  const open = async (n) => {
    if (!n.is_read) { await api.post(`/notifications/${n.id}/read/`); changed(); }
    if (n.link) navigate(n.link);
  };
  const readAll = async () => { await api.post('/notifications/read-all/'); changed(); };
  const remove = async (n) => { await api.delete(`/notifications/${n.id}/`); changed(); };

  return (
    <>
      <PageHeader title="Notifications" subtitle="Updates about placements, logbooks, visits, assessments and reports"
        actions={(
          <>
            <button type="button" className={`btn btn-sm ${unreadOnly ? 'btn-primary' : 'btn-outline-primary'}`} onClick={() => setUnreadOnly((u) => !u)}>
              {unreadOnly ? 'Show all' : 'Unread only'}
            </button>
            <button type="button" className="btn btn-sm btn-outline-secondary" onClick={readAll}>Mark all as read</button>
          </>
        )} />
      <ErrorAlert error={error} onRetry={reload} />
      {loading ? <Loading /> : (
        <div className="list-group">
          {(data || []).length === 0 && <EmptyState icon="bell-slash" text="No notifications." />}
          {(data || []).map((n) => (
            <div key={n.id} className={`list-group-item d-flex gap-3 align-items-start ${n.is_read ? '' : 'list-group-item-primary'}`}>
              <i className={`bi bi-${ICONS[n.notification_type] || 'bell'} fs-5 mt-1`} />
              <button type="button" className="btn btn-link text-start text-reset text-decoration-none p-0 flex-grow-1" onClick={() => open(n)}>
                <div className="fw-semibold">{n.title}</div>
                <div className="small pre-wrap">{n.message}</div>
                <div className="small text-muted mt-1">{n.notification_type_label} · {formatDateTime(n.created_at)}</div>
              </button>
              <button type="button" className="btn btn-sm btn-link text-muted" aria-label="Delete notification" onClick={() => remove(n)}>
                <i className="bi bi-x-lg" />
              </button>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
