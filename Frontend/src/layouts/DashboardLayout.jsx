import { useEffect, useState } from 'react';
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';

import logo from '../assets/icons/logo.svg';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import { ROLE_LABEL } from '../services/format';
import NAVIGATION from './navigation';

export default function DashboardLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const [menu, setMenu] = useState(false);

  useEffect(() => { setOpen(false); setMenu(false); }, [location.pathname]);

  useEffect(() => {
    let alive = true;
    const load = () => api.get('/notifications/unread-count/').then((r) => alive && setUnread(r.data.unread)).catch(() => {});
    load();
    const t = setInterval(load, 60000);
    window.addEventListener('sims:notifications', load);
    return () => { alive = false; clearInterval(t); window.removeEventListener('sims:notifications', load); };
  }, [location.pathname]);

  const doLogout = async () => { await logout(); navigate('/login'); };
  const items = NAVIGATION[user.role] || [];

  return (
    <div className="app-shell">
      <aside className={`sidebar ${open ? 'open' : ''}`} aria-label="Main navigation">
        <Link to="/" className="sidebar-brand">
          <img src={logo} alt="" width="28" height="28" />
          <span><strong>Langata TVC</strong><small>Attachment System</small></span>
        </Link>
        <nav className="nav flex-column">
          {items.map((item, i) => (item.heading
            ? <div key={`h${i}`} className="sidebar-heading">{item.heading}</div>
            : (
              <NavLink key={item.to} to={item.to} end={item.end} className="nav-link">
                <i className={`bi bi-${item.icon}`} />
                <span>{item.label}</span>
                {item.to === '/notifications' && unread > 0 && <span className="badge bg-danger ms-auto">{unread}</span>}
              </NavLink>
            )))}
        </nav>
      </aside>
      {open && <div className="sidebar-backdrop" onClick={() => setOpen(false)} aria-hidden="true" />}

      <div className="main-area">
        <header className="topbar">
          <button type="button" className="btn btn-link text-dark d-lg-none p-0 me-2" aria-label="Open menu" onClick={() => setOpen(true)}>
            <i className="bi bi-list fs-3" />
          </button>
          <div className="me-auto small text-muted d-none d-sm-block">{ROLE_LABEL[user.role]} portal</div>
          <Link to="/notifications" className="btn btn-link text-dark position-relative me-2" aria-label={`Notifications (${unread} unread)`}>
            <i className="bi bi-bell fs-5" />
            {unread > 0 && <span className="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-danger">{unread > 99 ? '99+' : unread}</span>}
          </Link>
          <div className="position-relative">
            <button type="button" className="btn btn-light d-flex align-items-center gap-2" onClick={() => setMenu((m) => !m)} aria-expanded={menu}>
              <span className="avatar">{(user.full_name || user.username).slice(0, 1).toUpperCase()}</span>
              <span className="d-none d-md-inline text-start lh-sm">
                <span className="d-block fw-semibold">{user.full_name}</span>
                <small className="text-muted">{user.role_label}</small>
              </span>
              <i className="bi bi-chevron-down small" />
            </button>
            {menu && (
              <div className="dropdown-menu dropdown-menu-end show mt-1" style={{ right: 0, left: 'auto' }}>
                <Link className="dropdown-item" to="/profile"><i className="bi bi-person me-2" />My profile</Link>
                <div className="dropdown-divider" />
                <button type="button" className="dropdown-item text-danger" onClick={doLogout}><i className="bi bi-box-arrow-right me-2" />Log out</button>
              </div>
            )}
          </div>
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
