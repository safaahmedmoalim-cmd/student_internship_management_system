import { Navigate, Outlet, useLocation } from 'react-router-dom';

import { useAuth } from '../../context/AuthContext';
import { ROLE_HOME } from '../../services/format';
import { Loading } from './ui';

/** Role-based page access: only signed-in users whose role is in `roles` (any role when omitted). */
export default function ProtectedRoute({ roles }) {
  const { user, ready } = useAuth();
  const location = useLocation();
  if (!ready) return <div className="container py-5"><Loading /></div>;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (roles && !roles.includes(user.role)) return <Navigate to={ROLE_HOME[user.role] || '/login'} replace />;
  return <Outlet />;
}
