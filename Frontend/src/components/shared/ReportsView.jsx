import { useState } from 'react';

import { Card, DownloadButton, EmptyState, ErrorAlert, Loading } from '../common/ui';
import useFetch from '../../hooks/useFetch';
import { API_URL } from '../../services/api';

/** Report picker, preview table, summary and PDF / Excel export. */
export default function ReportsView() {
  const list = useFetch('/reports/');
  const departments = useFetch('/departments/');
  const [slug, setSlug] = useState('');
  const [department, setDepartment] = useState('');
  const active = slug || list.data?.[0]?.slug;
  const params = department ? { department } : undefined;
  const report = useFetch(active ? `/reports/${active}/` : null, params);
  const qs = department ? `&department=${department}` : '';
  const exportUrl = (fmt) => `${API_URL}/reports/${active}/?export=${fmt}${qs}`;

  if (list.loading) return <Loading />;
  return (
    <>
      <ErrorAlert error={list.error} onRetry={list.reload} />
      <div className="row g-3">
        <div className="col-lg-3">
          <div className="list-group">
            {(list.data || []).map((r) => (
              <button key={r.slug} type="button" onClick={() => setSlug(r.slug)}
                className={`list-group-item list-group-item-action ${active === r.slug ? 'active' : ''}`}>{r.title}</button>
            ))}
          </div>
          <div className="mt-3">
            <label className="form-label small" htmlFor="dept-filter">Department</label>
            <select id="dept-filter" className="form-select" value={department} onChange={(e) => setDepartment(e.target.value)}>
              <option value="">All departments</option>
              {(departments.data || []).map((d) => <option key={d.id} value={d.id}>{d.department_name}</option>)}
            </select>
          </div>
        </div>
        <div className="col-lg-9">
          {report.loading ? <Loading /> : report.error ? <ErrorAlert error={report.error} onRetry={report.reload} /> : report.data && (
            <Card title={report.data.title} actions={(
              <>
                <DownloadButton url={exportUrl('pdf')} label="PDF" className="btn btn-sm btn-outline-danger" />
                <DownloadButton url={exportUrl('xlsx')} label="Excel" className="btn btn-sm btn-outline-success" />
              </>
            )}>
              {Object.keys(report.data.summary || {}).length > 0 && (
                <div className="row g-2 mb-3">
                  {Object.entries(report.data.summary).map(([k, v]) => (
                    <div className="col-6 col-md-3" key={k}>
                      <div className="border rounded p-2 h-100"><div className="fw-bold fs-5">{v}</div><div className="small text-muted">{k}</div></div>
                    </div>
                  ))}
                </div>
              )}
              {report.data.rows.length === 0 ? <EmptyState text="No records for this report." /> : (
                <div className="table-responsive">
                  <table className="table table-sm table-striped mb-0">
                    <thead><tr>{report.data.columns.map((c) => <th key={c}>{c}</th>)}</tr></thead>
                    <tbody>
                      {report.data.rows.map((r, i) => (
                        // eslint-disable-next-line react/no-array-index-key
                        <tr key={i}>{r.map((v, j) => <td key={j}>{v === '' ? '—' : v}</td>)}</tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          )}
        </div>
      </div>
    </>
  );
}
