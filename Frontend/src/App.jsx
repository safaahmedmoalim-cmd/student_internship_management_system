import { Navigate, Route, Routes } from 'react-router-dom';

import ProtectedRoute from './components/common/ProtectedRoute';
import { Loading } from './components/common/ui';
import { useAuth } from './context/AuthContext';
import AuthLayout from './layouts/AuthLayout';
import DashboardLayout from './layouts/DashboardLayout';
import { ROLE_HOME } from './services/format';

import ForgotPassword from './pages/auth/ForgotPassword';
import Login from './pages/auth/Login';
import Register from './pages/auth/Register';
import ResetPassword from './pages/auth/ResetPassword';

import Announcements from './pages/common/Announcements';
import NotFound from './pages/common/NotFound';
import Notifications from './pages/common/Notifications';
import Profile from './pages/common/Profile';

import StudentAssessments from './pages/student/Assessments';
import StudentDashboard from './pages/student/Dashboard';
import StudentFinalReport from './pages/student/FinalReport';
import StudentLogbook from './pages/student/Logbook';
import StudentPlacement from './pages/student/Placement';

import AcademicAssessments from './pages/academic/Assessments';
import AcademicDashboard from './pages/academic/Dashboard';
import AcademicFinalReports from './pages/academic/FinalReports';
import AcademicLogbooks from './pages/academic/LogbookReview';
import AcademicReports from './pages/academic/Reports';
import AcademicStudentDetail from './pages/academic/StudentDetail';
import AcademicStudents from './pages/academic/Students';
import AcademicVisits from './pages/academic/Visits';

import IndustrialAttendance from './pages/industrial/Attendance';
import IndustrialDashboard from './pages/industrial/Dashboard';
import IndustrialEvaluations from './pages/industrial/Evaluations';
import IndustrialInternDetail from './pages/industrial/InternDetail';
import IndustrialInterns from './pages/industrial/Interns';
import IndustrialLogbooks from './pages/industrial/LogbookApproval';
import IndustrialReports from './pages/industrial/Reports';

import AdminAnnouncements from './pages/admin/Announcements';
import AdminAssessments from './pages/admin/Assessments';
import AdminAssignments from './pages/admin/Assignments';
import AdminAuditLogs from './pages/admin/AuditLogs';
import AdminDashboard from './pages/admin/Dashboard';
import AdminDepartments from './pages/admin/Departments';
import AdminLogbooks from './pages/admin/Logbooks';
import AdminOrganizations from './pages/admin/Organizations';
import AdminPeriods from './pages/admin/Periods';
import AdminPlacements from './pages/admin/Placements';
import AdminReports from './pages/admin/Reports';
import AdminSettings from './pages/admin/Settings';
import AdminStudentDetail from './pages/admin/StudentDetail';
import AdminStudents from './pages/admin/Students';
import AdminUsers from './pages/admin/Users';
import AdminVisits from './pages/admin/Visits';

function Home() {
  const { user, ready } = useAuth();
  if (!ready) return <div className="container py-5"><Loading /></div>;
  return <Navigate to={user ? ROLE_HOME[user.role] : '/login'} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />

      <Route element={<AuthLayout />}>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route element={<DashboardLayout />}>
          <Route path="/profile" element={<Profile />} />
          <Route path="/notifications" element={<Notifications />} />
          <Route path="/announcements" element={<Announcements />} />

          <Route element={<ProtectedRoute roles={['student']} />}>
            <Route path="/student" element={<StudentDashboard />} />
            <Route path="/student/placement" element={<StudentPlacement />} />
            <Route path="/student/logbook" element={<StudentLogbook />} />
            <Route path="/student/final-report" element={<StudentFinalReport />} />
            <Route path="/student/assessments" element={<StudentAssessments />} />
          </Route>

          <Route element={<ProtectedRoute roles={['academic']} />}>
            <Route path="/academic" element={<AcademicDashboard />} />
            <Route path="/academic/students" element={<AcademicStudents />} />
            <Route path="/academic/students/:id" element={<AcademicStudentDetail />} />
            <Route path="/academic/logbooks" element={<AcademicLogbooks />} />
            <Route path="/academic/visits" element={<AcademicVisits />} />
            <Route path="/academic/final-reports" element={<AcademicFinalReports />} />
            <Route path="/academic/assessments" element={<AcademicAssessments />} />
            <Route path="/academic/reports" element={<AcademicReports />} />
          </Route>

          <Route element={<ProtectedRoute roles={['industrial']} />}>
            <Route path="/industrial" element={<IndustrialDashboard />} />
            <Route path="/industrial/interns" element={<IndustrialInterns />} />
            <Route path="/industrial/interns/:id" element={<IndustrialInternDetail />} />
            <Route path="/industrial/logbooks" element={<IndustrialLogbooks />} />
            <Route path="/industrial/attendance" element={<IndustrialAttendance />} />
            <Route path="/industrial/evaluations" element={<IndustrialEvaluations />} />
            <Route path="/industrial/reports" element={<IndustrialReports />} />
          </Route>

          <Route element={<ProtectedRoute roles={['admin']} />}>
            <Route path="/admin" element={<AdminDashboard />} />
            <Route path="/admin/users" element={<AdminUsers />} />
            <Route path="/admin/departments" element={<AdminDepartments />} />
            <Route path="/admin/organizations" element={<AdminOrganizations />} />
            <Route path="/admin/periods" element={<AdminPeriods />} />
            <Route path="/admin/placements" element={<AdminPlacements />} />
            <Route path="/admin/assignments" element={<AdminAssignments />} />
            <Route path="/admin/students" element={<AdminStudents />} />
            <Route path="/admin/students/:id" element={<AdminStudentDetail />} />
            <Route path="/admin/logbooks" element={<AdminLogbooks />} />
            <Route path="/admin/visits" element={<AdminVisits />} />
            <Route path="/admin/assessments" element={<AdminAssessments />} />
            <Route path="/admin/announcements" element={<AdminAnnouncements />} />
            <Route path="/admin/reports" element={<AdminReports />} />
            <Route path="/admin/audit-logs" element={<AdminAuditLogs />} />
            <Route path="/admin/settings" element={<AdminSettings />} />
          </Route>

          <Route path="*" element={<NotFound />} />
        </Route>
      </Route>
    </Routes>
  );
}
