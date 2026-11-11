import { useState } from 'react';
import { Link } from 'react-router-dom';

import { useToast } from '../../context/ToastContext';
import { downloadFile, errorMessage } from '../../services/api';
import { humanize } from '../../services/format';

const STATUS_COLORS = {
  success: ['approved', 'completed', 'released', 'active', 'present', 'yes'],
  warning: ['pending', 'submitted', 'scheduled', 'in_progress', 'not_started'],
  info: ['returned', 'under_review', 'rescheduled', 'late', 'excused'],
  danger: ['rejected', 'cancelled', 'terminated', 'absent', 'inactive', 'no'],
};

export function StatusBadge({ status, label }) {
  const color = Object.entries(STATUS_COLORS).find(([, list]) => list.includes(status))?.[0] || 'secondary';
  const text = color === 'warning' || color === 'info' ? 'text-dark' : '';
  return <span className={`badge rounded-pill bg-${color} ${text} status-badge`}>{label || humanize(status || 'none')}</span>;
}

export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="page-header d-flex flex-wrap justify-content-between align-items-start gap-2 mb-4">
      <div>
        <h1 className="h3 mb-1">{title}</h1>
        {subtitle && <p className="text-muted mb-0">{subtitle}</p>}
      </div>
      {actions && <div className="d-flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

export function StatCard({ label, value, icon, variant = 'primary', to, hint }) {
  const body = (
    <div className="card stat-card h-100">
      <div className="card-body d-flex align-items-center gap-3">
        <div className={`stat-icon bg-${variant}-subtle text-${variant}`}><i className={`bi bi-${icon}`} /></div>
        <div className="min-w-0">
          <div className="stat-value">{value ?? '—'}</div>
          <div className="stat-label text-muted">{label}</div>
          {hint && <div className="small text-muted">{hint}</div>}
        </div>
      </div>
    </div>
  );
  return to ? <Link to={to} className="text-decoration-none text-reset d-block h-100">{body}</Link> : body;
}

export function Loading({ text = 'Loading…' }) {
  return (
    <div className="d-flex align-items-center gap-2 text-muted py-4">
      <div className="spinner-border spinner-border-sm" role="status" /> {text}
    </div>
  );
}

export function ErrorAlert({ error, onRetry }) {
  if (!error) return null;
  return (
    <div className="alert alert-danger d-flex justify-content-between align-items-center gap-2" role="alert">
      <span><i className="bi bi-exclamation-triangle me-2" />{error}</span>
      {onRetry && <button type="button" className="btn btn-sm btn-outline-danger" onClick={onRetry}>Retry</button>}
    </div>
  );
}

export function EmptyState({ icon = 'inbox', text, children }) {
  return (
    <div className="text-center text-muted py-5 empty-state">
      <i className={`bi bi-${icon} display-6 d-block mb-2`} />
      <p className="mb-2">{text}</p>
      {children}
    </div>
  );
}

export function ProgressBar({ value = 0, label }) {
  const v = Math.max(0, Math.min(100, value || 0));
  return (
    <div>
      {label && <div className="d-flex justify-content-between small mb-1"><span>{label}</span><span>{v}%</span></div>}
      <div className="progress" role="progressbar" aria-valuenow={v} aria-valuemin="0" aria-valuemax="100">
        <div className={`progress-bar ${v >= 100 ? 'bg-success' : ''}`} style={{ width: `${v}%` }} />
      </div>
    </div>
  );
}

export function DownloadButton({ url, label = 'Download', className = 'btn btn-sm btn-outline-primary', name }) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  if (!url) return null;
  const click = async () => {
    setBusy(true);
    try { await downloadFile(url, name); } catch (e) { toast(errorMessage(e), 'danger'); } finally { setBusy(false); }
  };
  return (
    <button type="button" className={className} onClick={click} disabled={busy}>
      <i className="bi bi-download me-1" />{busy ? 'Downloading…' : label}
    </button>
  );
}

export function InfoRow({ label, children }) {
  return (
    <div className="row py-1 info-row">
      <div className="col-sm-4 text-muted small">{label}</div>
      <div className="col-sm-8">{children || '—'}</div>
    </div>
  );
}

export function Card({ title, actions, children, className = '', bodyClass = '' }) {
  return (
    <div className={`card mb-4 ${className}`}>
      {(title || actions) && (
        <div className="card-header bg-white d-flex flex-wrap justify-content-between align-items-center gap-2">
          <h2 className="h6 mb-0">{title}</h2>
          {actions && <div className="d-flex flex-wrap gap-2">{actions}</div>}
        </div>
      )}
      <div className={`card-body ${bodyClass}`}>{children}</div>
    </div>
  );
}
