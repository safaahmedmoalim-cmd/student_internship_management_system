import { useState } from 'react';

import { EmptyState, ErrorAlert, Loading, PageHeader } from '../../components/common/ui';
import useFetch from '../../hooks/useFetch';
import { formatDateTime } from '../../services/format';

const ACTIONS = ['auth', 'user', 'placement', 'assignment', 'logbook', 'visit', 'assessment', 'report', 'announcement',
  'organization', 'department', 'period', 'attendance', 'settings'];

export default function AdminAuditLogs() {
  const [filters, setFilters] = useState({ action: '', search: '', date_from: '', date_to: '' });
  const [applied, setApplied] = useState({});
  const { data, loading, error, reload } = useFetch('/audit-logs/', applied);
  const set = (k) => (e) => setFilters((f) => ({ ...f, [k]: e.target.value }));

  return (
    <>
      <PageHeader title="Audit Logs" subtitle="Important system activities (latest 500 matching entries)" />
      <form className="filter-bar" onSubmit={(e) => { e.preventDefault(); setApplied(Object.fromEntries(Object.entries(filters).filter(([, v]) => v))); }}>
        <select className="form-select" value={filters.action} onChange={set('action')} aria-label="Module">
          <option value="">All modules</option>{ACTIONS.map((a) => <option key={a} value={a}>{a}</option>)}
        </select>
        <input className="form-control" placeholder="Search description or user" value={filters.search} onChange={set('search')} aria-label="Search" />
        <input type="date" className="form-control" value={filters.date_from} onChange={set('date_from')} aria-label="From date" />
        <input type="date" className="form-control" value={filters.date_to} onChange={set('date_to')} aria-label="To date" />
        <button type="submit" className="btn btn-outline-primary" style={{ flex: '0 0 auto' }}>Filter</button>
      </form>
      <ErrorAlert error={error} onRetry={reload} />
      {loading ? <Loading /> : (data || []).length === 0 ? <EmptyState icon="shield-check" text="No matching activity." /> : (
        <div className="card table-responsive">
          <table className="table table-sm mb-0 align-middle">
            <thead><tr><th>Time</th><th>User</th><th>Action</th><th>Description</th><th>IP address</th></tr></thead>
            <tbody>
              {data.map((l) => (
                <tr key={l.id}>
                  <td className="small text-nowrap">{formatDateTime(l.timestamp)}</td>
                  <td className="small">{l.username || '—'}</td>
                  <td><code className="small">{l.action}</code></td>
                  <td className="small">{l.description}</td>
                  <td className="small text-muted">{l.ip_address || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
