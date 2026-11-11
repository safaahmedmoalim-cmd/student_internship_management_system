/** Sidebar entries for each role's dashboard (Chapter 3 dashboard components). */
const common = [
  { to: '/announcements', label: 'Announcements', icon: 'megaphone' },
  { to: '/notifications', label: 'Notifications', icon: 'bell' },
  { to: '/profile', label: 'My Profile', icon: 'person-circle' },
];

const NAVIGATION = {
  student: [
    { to: '/student', label: 'Dashboard', icon: 'speedometer2', end: true },
    { to: '/student/placement', label: 'Placement', icon: 'building' },
    { to: '/student/logbook', label: 'Weekly Logbook', icon: 'journal-text' },
    { to: '/student/final-report', label: 'Final Report', icon: 'file-earmark-text' },
    { to: '/student/assessments', label: 'Assessment Results', icon: 'award' },
    ...common,
  ],
  academic: [
    { to: '/academic', label: 'Dashboard', icon: 'speedometer2', end: true },
    { to: '/academic/students', label: 'Assigned Students', icon: 'people' },
    { to: '/academic/logbooks', label: 'Logbook Review', icon: 'journal-check' },
    { to: '/academic/visits', label: 'Supervision Visits', icon: 'calendar-event' },
    { to: '/academic/final-reports', label: 'Final Reports', icon: 'file-earmark-check' },
    { to: '/academic/assessments', label: 'Student Evaluation', icon: 'clipboard-check' },
    { to: '/academic/reports', label: 'Reports', icon: 'bar-chart' },
    ...common,
  ],
  industrial: [
    { to: '/industrial', label: 'Dashboard', icon: 'speedometer2', end: true },
    { to: '/industrial/interns', label: 'Assigned Interns', icon: 'people' },
    { to: '/industrial/logbooks', label: 'Logbook Approval', icon: 'journal-check' },
    { to: '/industrial/attendance', label: 'Attendance', icon: 'calendar-check' },
    { to: '/industrial/evaluations', label: 'Workplace Evaluation', icon: 'clipboard-check' },
    { to: '/industrial/reports', label: 'Reports', icon: 'bar-chart' },
    ...common,
  ],
  admin: [
    { to: '/admin', label: 'Dashboard', icon: 'speedometer2', end: true },
    { heading: 'Management' },
    { to: '/admin/users', label: 'User Management', icon: 'people' },
    { to: '/admin/departments', label: 'Departments', icon: 'diagram-3' },
    { to: '/admin/organizations', label: 'Organizations', icon: 'buildings' },
    { to: '/admin/periods', label: 'Attachment Periods', icon: 'calendar-range' },
    { heading: 'Attachment' },
    { to: '/admin/placements', label: 'Placements', icon: 'building-check' },
    { to: '/admin/assignments', label: 'Supervisor Assignment', icon: 'person-check' },
    { to: '/admin/students', label: 'Students & Progress', icon: 'mortarboard' },
    { to: '/admin/logbooks', label: 'Logbook Monitoring', icon: 'journal-text' },
    { to: '/admin/visits', label: 'Supervision Visits', icon: 'calendar-event' },
    { to: '/admin/assessments', label: 'Assessments', icon: 'award' },
    { heading: 'Communication & Reports' },
    { to: '/admin/announcements', label: 'Announcements', icon: 'megaphone' },
    { to: '/admin/reports', label: 'Reports & Analytics', icon: 'bar-chart' },
    { to: '/admin/audit-logs', label: 'Audit Logs', icon: 'shield-check' },
    { to: '/admin/settings', label: 'System Settings', icon: 'gear' },
    { to: '/notifications', label: 'Notifications', icon: 'bell' },
    { to: '/profile', label: 'My Profile', icon: 'person-circle' },
  ],
};

export default NAVIGATION;
