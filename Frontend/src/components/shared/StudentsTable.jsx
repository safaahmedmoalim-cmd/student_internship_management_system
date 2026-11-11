import { useState } from 'react';
import { Link } from 'react-router-dom';

import { EmptyState, ErrorAlert, Loading, StatusBadge } from '../common/ui';
import useFetch from '../../hooks/useFetch';
import { humanize } from '../../services/format';

/** Students visible to the signed-in user (assigned students / interns, or everyone for the administrator). */
export default function StudentsTable({ basePath, showSupervisors = true }) {
  const [search, setSearch] = useState('');
  const [query, setQuery] = useState('');
  const { data, loading, error, reload } = useFetch('/students/', query ? { search: query } : undefined);

  return (
    <div className="card">
      <div className="card-body border-bottom">
        <form className="d-flex gap-2" onSubmit={(e) => { e.preventDefault(); setQuery(search.trim()); }}>
          <input className="form-control" placeholder="Search by name, registration number or email" value={search}
            onChange={(e) => setSearch(e.target.value)} aria-label="Search students" />
          <button className="btn btn-outline-primary" type="submit"><i className="bi bi-search" /></button>
        </form>
      </div>
      <ErrorAlert error={error} onRetry={reload} />
      {loading ? <div className="px-3"><Loading /></div> : (data || []).length === 0 ? <EmptyState icon="people" text="No students found." /> : (
        <div className="table-responsive">
          <table className="table table-hover mb-0 align-middle">
            <thead>
              <tr>
                <th>Student</th><th>Department</th><th>Organization</th><th>Placement</th>
                {showSupervisors && <th>Supervisors</th>}
                <th>Logbooks</th><th>Visits</th><th>Report</th>
              </tr>
            </thead>
            <tbody>
              {data.map((s) => (
                <tr key={s.id}>
                  <td>
                    <Link to={`${basePath}/${s.id}`} className="fw-semibold">{s.full_name}</Link>
                    <div className="small text-muted">{s.registration_number}</div>
                  </td>
                  <td className="small">{s.department_name}<div className="text-muted">{s.academic_year}</div></td>
                  <td className="small">{s.organization_name || '—'}</td>
                  <td>
                    <StatusBadge status={s.placement_status} label={s.placement_status === 'none' ? 'None' : undefined} />
                    {s.attachment_status && s.placement_status === 'approved' && <div className="small text-muted">{humanize(s.attachment_status)}</div>}
                  </td>
                  {showSupervisors && (
                    <td className="small">
                      <div><i className="bi bi-mortarboard me-1" />{s.academic_supervisor_name || '—'}</div>
                      <div><i className="bi bi-briefcase me-1" />{s.industrial_supervisor_name || '—'}</div>
                    </td>
                  )}
                  <td className="small">{s.logbooks_approved}/{s.logbooks_total} approved{s.logbooks_rejected > 0 && <div className="text-danger">{s.logbooks_rejected} rejected</div>}</td>
                  <td>{s.visits_completed}</td>
                  <td><StatusBadge status={s.report_status || 'none'} label={s.report_status ? undefined : 'None'} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
