import { Link, Outlet } from 'react-router-dom';

import logo from '../assets/icons/logo.svg';

export default function AuthLayout() {
  return (
    <div className="auth-shell">
      <div className="auth-side d-none d-lg-flex">
        <div>
          <img src={logo} alt="" width="56" height="56" className="mb-4 auth-logo" />
          <h1 className="display-6 fw-bold">Student Internship &amp; Attachment Management System</h1>
          <p className="lead mt-3">Langata Technical and Vocational College</p>
          <ul className="list-unstyled mt-4 auth-points">
            <li><i className="bi bi-check2-circle me-2" />Placement applications and approval</li>
            <li><i className="bi bi-check2-circle me-2" />Weekly logbooks reviewed by both supervisors</li>
            <li><i className="bi bi-check2-circle me-2" />Supervision visits, assessments and final reports</li>
          </ul>
        </div>
      </div>
      <div className="auth-main">
        <div className="auth-card">
          <Link to="/login" className="d-flex d-lg-none align-items-center gap-2 mb-4 text-decoration-none">
            <img src={logo} alt="" width="32" height="32" />
            <strong className="text-dark">Langata TVC Attachment System</strong>
          </Link>
          <Outlet />
        </div>
      </div>
    </div>
  );
}
