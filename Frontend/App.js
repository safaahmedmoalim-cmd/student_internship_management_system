/* =========================================================
   Langata College – Internship & Attachment Portal
   app.js  (front-end only)

   - All data is kept in the browser (localStorage) so the
     portal works without a server.
   - Every place that would call a back-end later is marked
     with  // API:  so it is easy to swap in real requests.
   - Passwords are stored in plain text because this is a
     browser-only prototype. A real back-end must hash passwords.
   ========================================================= */
(function () {
  'use strict';

  /* ---------------------------------------------------------
     1. CONFIG
  --------------------------------------------------------- */
  const STORAGE_KEY = 'langata_iams_v1';
  const SESSION_KEY = 'langata_iams_session';
  const TARGET_HOURS = 400;                 // required attachment hours
  const COORDINATOR_CODE = 'LANGATA-COORD'; // needed to register as coordinator
  const COURSES = [
    'Diploma in ICT',
    'Diploma in Business Management',
    'Diploma in Accounting',
    'Diploma in Hospitality Management',
    'Diploma in Electrical Engineering',
    'Certificate in Community Development'
  ];
  const CRITERIA = [
    'Punctuality & attendance',
    'Technical skills',
    'Teamwork',
    'Initiative',
    'Communication'
  ];

  /* ---------------------------------------------------------
     2. SMALL HELPERS
  --------------------------------------------------------- */
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const e = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const uid = (p = 'id') => p + '_' + Math.random().toString(36).slice(2, 9);
  const cap = s => s ? s.charAt(0).toUpperCase() + s.slice(1) : '';
  const first = n => String(n || '').split(' ')[0];
  const initials = n => String(n || '?').split(' ').filter(Boolean).slice(0, 2).map(w => w[0].toUpperCase()).join('');
  const today = () => new Date().toISOString().slice(0, 10);
  const addDays = (d, n) => { const x = new Date(d); x.setDate(x.getDate() + n); return x.toISOString().slice(0, 10); };
  const fmtDate = d => {
    if (!d) return '—';
    const x = new Date(d);
    return isNaN(x) ? '—' : x.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
  };
  let idCounter = 0;
  const fid = () => 'f' + (++idCounter);

  const ICONS = {
    home: '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
    briefcase: '<rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>',
    book: '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
    file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>',
    user: '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    users: '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    check: '<polyline points="20 6 9 17 4 12"/>',
    calendar: '<rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>',
    clipboard: '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1"/>',
    bell: '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>',
    chart: '<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>',
    star: '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
    clock: '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>',
    cap: '<path d="M22 10L12 5 2 10l10 5 10-5z"/><path d="M6 12v5c3 3 9 3 12 0v-5"/>'
  };
  const icon = n => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${ICONS[n] || ''}</svg>`;

  /* ---------------------------------------------------------
     3. ROLE DEFINITIONS
  --------------------------------------------------------- */
  const ROLES = {
    student: {
      label: 'Student', short: 'Student', icon: 'user',
      nav: [['overview', 'Overview', 'home'], ['placement', 'My placement', 'briefcase'], ['logbook', 'Weekly logbook', 'book'], ['report', 'Final report', 'file'], ['profile', 'Profile', 'user']]
    },
    academic: {
      label: 'Academic Supervisor', short: 'Academic', icon: 'book',
      nav: [['overview', 'Overview', 'home'], ['students', 'My students', 'users'], ['logbooks', 'Logbook review', 'book'], ['visits', 'Supervisor visits', 'calendar'], ['assessments', 'Assessments', 'star'], ['profile', 'Profile', 'user']]
    },
    industrial: {
      label: 'Industrial Supervisor', short: 'Industry', icon: 'briefcase',
      nav: [['overview', 'Overview', 'home'], ['interns', 'My interns', 'users'], ['approvals', 'Logbook approvals', 'check'], ['evaluation', 'Evaluation', 'star'], ['profile', 'Profile', 'user']]
    },
    coordinator: {
      label: 'Coordinator', short: 'Coordinator', icon: 'clipboard',
      nav: [['overview', 'Overview', 'home'], ['placements', 'Placements', 'briefcase'], ['students', 'Students', 'users'], ['supervisors', 'Supervisors', 'clipboard'], ['announcements', 'Announcements', 'bell'], ['reports', 'Reports', 'chart'], ['profile', 'Profile', 'user']]
    }
  };

  const ROLE_FIELDS = {
    student: [
      { n: 'admNo', l: 'Admission number', ph: 'e.g. LC/2024/0101', lock: true },
      { n: 'course', l: 'Course', opts: COURSES },
      { n: 'year', l: 'Year of study', opts: ['Year 1', 'Year 2', 'Year 3'] }
    ],
    academic: [
      { n: 'staffNo', l: 'Staff number', ph: 'e.g. LC-A-014', lock: true },
      { n: 'department', l: 'Department', ph: 'e.g. ICT' }
    ],
    industrial: [
      { n: 'company', l: 'Company / organisation', ph: 'Organisation name' },
      { n: 'position', l: 'Position', ph: 'e.g. Operations Manager' },
      { n: 'companyLocation', l: 'Company location', ph: 'Town / area' }
    ],
    coordinator: [
      { n: 'staffNo', l: 'Staff number', ph: 'e.g. LC-C-001', lock: true }
    ]
  };

  /* ---------------------------------------------------------
     4. DATA LAYER (localStorage)
  --------------------------------------------------------- */
  function seedDB() {
    const now = new Date().toISOString();
    const users = [];
    const placements = [];
    const logbooks = [];
    const assessments = [];
    const visits = [];
    const announcements = [];
    return { users, placements, logbooks, assessments, visits, announcements, reports: [] };
  }

  function loadDB() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) return JSON.parse(raw);
    } catch (err) { /* fall through to seed */ }
    const fresh = seedDB();
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(fresh)); } catch (err) { /* storage blocked */ }
    return fresh;
  }
  function save() {
    // API: replace with POST/PUT requests to your server
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(db)); } catch (err) { /* storage blocked */ }
  }

  let db = loadDB();
  let session = null;
  try { session = localStorage.getItem(SESSION_KEY); } catch (err) { /* ignore */ }
  const ui = { authMode: 'login', authRole: 'student', section: 'overview', preselect: null };

  /* ---------- selectors ---------- */
  const me = () => db.users.find(u => u.id === session);
  const byId = id => db.users.find(u => u.id === id);
  const students = () => db.users.filter(u => u.role === 'student');
  const supervisorsOf = role => db.users.filter(u => u.role === role);
  const myStudents = () => {
    const u = me();
    if (u.role === 'coordinator') return students();
    if (u.role === 'academic') return students().filter(s => s.academicSup === u.id);
    if (u.role === 'industrial') return students().filter(s => s.industrialSup === u.id);
    return [];
  };
  const placementOf = sid => db.placements.find(p => p.studentId === sid);
  const logsOf = sid => db.logbooks.filter(l => l.studentId === sid).sort((a, b) => a.week - b.week);
  const approvedHours = sid => logsOf(sid).filter(l => l.status === 'approved').reduce((t, l) => t + Number(l.hours), 0);
  const loggedHours = sid => logsOf(sid).reduce((t, l) => t + Number(l.hours), 0);
  const evalsOf = (sid, role) => db.assessments.filter(a => a.studentId === sid && (!role || a.role === role));
  const avgMarks = (sid, role) => {
    const list = evalsOf(sid, role);
    return list.length ? Math.round(list.reduce((t, a) => t + Number(a.marks), 0) / list.length) : null;
  };
  const reportOf = sid => db.reports.find(r => r.studentId === sid);
  const pct = (a, b) => b ? Math.min(100, Math.round(a / b * 100)) : 0;

  /* ---------------------------------------------------------
     5. UI HELPERS
  --------------------------------------------------------- */
  const badge = s => `<span class="badge b-${e(s)}">${e(cap(s))}</span>`;
  const pageHead = (t, s) => `<div class="page-head"><h2>${e(t)}</h2>${s ? `<p>${e(s)}</p>` : ''}</div>`;
  const stat = (label, value, sub, ic, tone = '') =>
    `<div class="stat"><span class="stat-icon ${tone}">${icon(ic)}</span><div><small>${e(label)}</small><b>${e(value)}</b><span>${e(sub)}</span></div></div>`;
  const cardBody = (title, html, actions = '') =>
    `<section class="card"><div class="card-head"><h3>${title}</h3>${actions}</div><div class="card-body">${html}</div></section>`;
  const cardFlush = (title, html, actions = '') =>
    `<section class="card"><div class="card-head"><h3>${title}</h3>${actions}</div>${html}</section>`;
  const emptyBox = (t, m) => `<div class="empty"><strong>${e(t)}</strong>${e(m || '')}</div>`;
  const tableHTML = (heads, rows, emptyTitle, emptyMsg) => rows.length
    ? `<div class="table-wrap"><table><thead><tr>${heads.map(h => `<th>${h}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`
    : emptyBox(emptyTitle, emptyMsg);
  const progressBar = (v, max) => `<div class="progress" role="progressbar" aria-valuenow="${v}" aria-valuemin="0" aria-valuemax="${max}"><span style="width:${pct(v, max)}%"></span></div>`;

  /* form fields */
  const fld = (name, label, type = 'text', o = {}) => {
    const id = fid();
    return `<div class="field ${o.full ? 'full' : ''}"><label for="${id}">${e(label)}</label>
      <input id="${id}" name="${name}" type="${type}" ${o.required === false ? '' : 'required'} ${o.attrs || ''} ${o.disabled ? 'disabled' : ''} value="${e(o.value == null ? '' : o.value)}" placeholder="${e(o.ph || '')}">
      ${o.hint ? `<small>${e(o.hint)}</small>` : ''}</div>`;
  };
  const pwFld = (name, label, o = {}) => {
    const id = fid();
    return `<div class="field ${o.full ? 'full' : ''}"><label for="${id}">${e(label)}</label>
      <div class="pw-wrap"><input id="${id}" name="${name}" type="password" required minlength="${o.min || 1}" autocomplete="${o.auto || 'current-password'}" placeholder="${e(o.ph || '')}">
      <button type="button" class="pw-toggle" data-action="toggle-pw">Show</button></div>
      ${o.hint ? `<small>${e(o.hint)}</small>` : ''}</div>`;
  };
  const sel = (name, label, options, o = {}) => {
    const id = fid();
    const opts = options.map(x => Array.isArray(x) ? x : [x, x]);
    return `<div class="field ${o.full ? 'full' : ''}"><label for="${id}">${e(label)}</label>
      <select id="${id}" name="${name}" ${o.required === false ? '' : 'required'}>
        ${o.placeholder ? `<option value="">${e(o.placeholder)}</option>` : ''}
        ${opts.map(([v, t]) => `<option value="${e(v)}" ${String(o.value) === String(v) ? 'selected' : ''}>${e(t)}</option>`).join('')}
      </select></div>`;
  };
  const txt = (name, label, o = {}) => {
    const id = fid();
    return `<div class="field full"><label for="${id}">${e(label)}</label>
      <textarea id="${id}" name="${name}" ${o.required === false ? '' : 'required'} placeholder="${e(o.ph || '')}">${e(o.value || '')}</textarea></div>`;
  };
  const roleInputs = (role, vals = {}, inProfile = false) => ROLE_FIELDS[role].map(f => {
    if (f.opts) return sel(f.n, f.l, f.opts, { value: vals[f.n] });
    return fld(f.n, f.l, 'text', { value: vals[f.n], ph: f.ph, disabled: inProfile && f.lock });
  }).join('');

  /* modal & toast */
  function openModal(title, body) {
    $('#modalRoot').innerHTML = `<div class="modal-backdrop" data-action="close-modal"><div class="modal" role="dialog" aria-modal="true" aria-label="${e(title)}">
      <div class="modal-head"><h3>${e(title)}</h3><button class="modal-close" data-action="close-modal" aria-label="Close">&times;</button></div>
      <div class="modal-body">${body}</div></div></div>`;
  }
  const closeModal = () => { $('#modalRoot').innerHTML = ''; };
  function toast(msg, type = '') {
    const t = document.createElement('div');
    t.className = 'toast ' + type;
    t.textContent = msg;
    $('#toastRoot').appendChild(t);
    setTimeout(() => t.remove(), 3600);
  }
  function formError(form, msg) {
    const box = $('.alert-error', form);
    if (box) { box.textContent = msg; box.classList.remove('hidden'); box.scrollIntoView({ block: 'nearest' }); }
    else toast(msg, 'error');
    return false;
  }

  /* views */
  function showView(name) {
    $$('.view').forEach(v => v.classList.toggle('hidden', v.id !== 'view-' + name));
    window.scrollTo(0, 0);
  }

  /* ---------------------------------------------------------
     6. AUTH (login + sign up)
  --------------------------------------------------------- */
  function openAuth(mode, role) {
    ui.authMode = mode || 'login';
    if (role && ROLES[role]) ui.authRole = role;
    renderAuth();
    showView('auth');
  }

  function renderAuth() {
    const { authMode: mode, authRole: role } = ui;
    const cfg = ROLES[role];
    const tabs = Object.entries(ROLES).map(([k, r]) =>
      `<button type="button" class="role-tab ${k === role ? 'active' : ''}" data-tab="${k}">${icon(r.icon)}<span>${r.short}</span></button>`).join('');

    let body;
    if (mode === 'login') {
      body = `
        <h2>Welcome back</h2>
        <p class="auth-sub">Log in to your ${e(cfg.label.toLowerCase())} account.</p>
        <div class="role-tabs" role="tablist">${tabs}</div>
        <form class="form" data-form="login" novalidate>
          <div class="alert alert-error hidden" role="alert"></div>
          ${fld('email', 'Email address', 'email', { ph: 'you@example.com', attrs: 'autocomplete="username"' })}
          ${pwFld('password', 'Password', { ph: 'Enter your password' })}
          <div style="display:flex; justify-content:space-between; align-items:center; gap:12px; margin:-4px 0 12px;">
            <button class="link" type="button" data-action="forgot-password">Forgot password?</button>
          </div>
          <button class="btn btn-primary btn-block btn-lg" type="submit">Log in as ${e(cfg.label)}</button>
        </form>
        <p class="auth-switch">New here? <button class="link" data-action="switch-auth" data-mode="signup">Create an account</button></p>`;
    } else {
      body = `
        <h2>Create your account</h2>
        <p class="auth-sub">Choose your role and fill in your details.</p>
        <div class="role-tabs" role="tablist">${tabs}</div>
        <form class="form" data-form="signup" novalidate>
          <div class="alert alert-error hidden" role="alert"></div>
          <div class="form-grid">
            ${fld('name', 'Full name', 'text', { ph: 'e.g. Jane Wanjiru', full: true, attrs: 'autocomplete="name"' })}
            ${fld('email', 'Email address', 'email', { ph: 'you@example.com', attrs: 'autocomplete="username"' })}
            ${fld('phone', 'Phone number', 'tel', { ph: '07xx xxx xxx', attrs: 'autocomplete="tel"' })}
            ${roleInputs(role, {})}
            ${role === 'coordinator' ? fld('code', 'Coordinator access code', 'text', { hint: 'Given by the college administration.', full: true }) : ''}
            ${pwFld('password', 'Password', { min: 8, auto: 'new-password', hint: 'At least 8 characters' })}
            ${pwFld('confirm', 'Confirm password', { min: 8, auto: 'new-password' })}
          </div>
          <button class="btn btn-primary btn-block btn-lg" type="submit">Create ${e(cfg.short.toLowerCase())} account</button>
        </form>
        <p class="auth-switch">Already registered? <button class="link" data-action="switch-auth" data-mode="login">Log in</button></p>`;
    }
    $('#authCard').innerHTML = body;
  }

  function startSession(u) {
    session = u.id;
    try { localStorage.setItem(SESSION_KEY, u.id); } catch (err) { /* ignore */ }
    ui.section = 'overview';
    showView('dashboard');
    renderDashboard();
    toast('Welcome, ' + first(u.name) + '!', 'success');
  }
  function logout() {
    session = null;
    try { localStorage.removeItem(SESSION_KEY); } catch (err) { /* ignore */ }
    $('#sidebar').classList.remove('open');
    $('.sidebar-backdrop').classList.remove('show');
    closeModal();
    showView('landing');
  }

  /* ---------------------------------------------------------
     7. DASHBOARD SHELL
  --------------------------------------------------------- */
  function navBadge(role, key) {
    let n = 0;
    if (role === 'academic' && key === 'logbooks') {
      const ids = myStudents().map(s => s.id);
      n = db.logbooks.filter(l => ids.includes(l.studentId) && !l.acadComment).length;
    }
    if (role === 'industrial' && key === 'approvals') {
      const ids = myStudents().map(s => s.id);
      n = db.logbooks.filter(l => ids.includes(l.studentId) && l.status === 'pending').length;
    }
    if (role === 'coordinator' && key === 'placements') n = db.placements.filter(p => p.status === 'pending').length;
    return n ? `<span class="nav-count">${n}</span>` : '';
  }

  function renderDashboard() {
    const u = me();
    if (!u) { logout(); return; }
    const cfg = ROLES[u.role];
    if (!cfg.nav.some(n => n[0] === ui.section)) ui.section = 'overview';

    $('#sidebar').innerHTML = `
      <div class="sb-brand"><span class="brand-mark">${icon('cap')}</span><div><strong>Langata College</strong><small>Attachment Portal</small></div></div>
      <div class="sb-role">${e(cfg.label)}</div>
      <nav class="sb-nav" aria-label="Dashboard">
        ${cfg.nav.map(([k, l, i]) => `<button class="nav-item ${ui.section === k ? 'active' : ''}" data-nav="${k}">${icon(i)}<span>${l}</span>${navBadge(u.role, k)}</button>`).join('')}
      </nav>
      <div class="sb-foot">
        <div class="sb-user"><span class="avatar">${e(initials(u.name))}</span><div><strong>${e(u.name)}</strong><small>${e(u.email)}</small></div></div>
        <button class="logout-btn" data-action="logout">${icon('logout')}Log out</button>
      </div>`;

    const current = cfg.nav.find(n => n[0] === ui.section);
    $('#pageTitle').textContent = current ? current[1] : 'Dashboard';
    $('#topbarUser').innerHTML = `<div style="text-align:right"><strong>${e(u.name)}</strong><span>${e(cfg.label)}</span></div><span class="avatar avatar-sm">${e(initials(u.name))}</span>`;

    const render = SECTIONS[u.role][ui.section] || SECTIONS[u.role].overview;
    $('#content').innerHTML = render();
    $('#sidebar').classList.remove('open');
    $('.sidebar-backdrop').classList.remove('show');
  }
  const go = (section) => { ui.section = section; renderDashboard(); window.scrollTo(0, 0); };

  /* ---------------------------------------------------------
     8. SHARED SECTIONS / WIDGETS
  --------------------------------------------------------- */
  function announcementsCard() {
    const list = db.announcements.slice().sort((a, b) => b.date.localeCompare(a.date)).slice(0, 4);
    const html = list.length
      ? `<div class="list">${list.map(a => `<div class="list-item"><div class="grow"><strong>${e(a.title)}</strong><p>${e(a.body)}</p></div><time>${fmtDate(a.date)}</time></div>`).join('')}</div>`
      : emptyBox('No announcements yet');
    return cardFlush('Announcements', html);
  }

  function logDetailHTML(l) {
    const s = byId(l.studentId);
    return `<dl class="kv">
      <dt>Student</dt><dd>${e(s ? s.name : '—')}</dd>
      <dt>Week</dt><dd>Week ${e(l.week)} (from ${fmtDate(l.weekStart)})</dd>
      <dt>Hours</dt><dd>${e(l.hours)}</dd>
      <dt>Status</dt><dd>${badge(l.status)}</dd>
      <dt>Activities</dt><dd>${e(l.activities)}</dd>
      <dt>Skills learned</dt><dd>${e(l.skills || '—')}</dd>
      <dt>Industrial feedback</dt><dd>${e(l.indComment || '—')}</dd>
      <dt>Academic feedback</dt><dd>${e(l.acadComment || '—')}</dd>
    </dl>`;
  }

  function profileSection() {
    const u = me();
    const profile = cardBody('Personal details', `
      <form class="form" data-form="profile">
        <div class="form-grid">
          ${fld('name', 'Full name', 'text', { value: u.name })}
          ${fld('email', 'Email address', 'email', { value: u.email, disabled: true })}
          ${fld('phone', 'Phone number', 'tel', { value: u.phone, required: false })}
          ${roleInputs(u.role, u, true)}
        </div>
        <div class="form-actions"><button class="btn btn-primary" type="submit">Save changes</button></div>
      </form>`);
    const pw = cardBody('Change password', `
      <form class="form" data-form="password">
        <div class="alert alert-error hidden" role="alert"></div>
        <div class="form-grid">
          ${pwFld('current', 'Current password', { full: true })}
          ${pwFld('next', 'New password', { min: 8, auto: 'new-password', hint: 'At least 8 characters' })}
          ${pwFld('confirm', 'Confirm new password', { min: 8, auto: 'new-password' })}
        </div>
        <div class="form-actions"><button class="btn btn-outline" type="submit">Update password</button></div>
      </form>`);
    return pageHead('Profile', 'Manage your account information.') + profile + pw;
  }

  function logbookTable(entries, showStudent) {
    const rows = entries.map(l => {
      const s = byId(l.studentId);
      return `<tr>
        ${showStudent ? `<td><strong>${e(s ? s.name : '—')}</strong><span class="sub">${e(s ? s.admNo : '')}</span></td>` : ''}
        <td>Week ${e(l.week)}<span class="sub">${fmtDate(l.weekStart)}</span></td>
        <td>${e(l.hours)} hrs</td>
        <td>${badge(l.status)}</td>
        <td class="clip">${e(l.indComment || l.acadComment || '—')}</td>
        <td class="actions"><button class="btn btn-sm btn-outline" data-action="view-log" data-id="${l.id}">View</button></td>
      </tr>`;
    });
    return tableHTML([...(showStudent ? ['Student'] : []), 'Week', 'Hours', 'Status', 'Feedback', ''], rows, 'No logbook entries yet');
  }

  /* ---------------------------------------------------------
     9. SECTIONS PER ROLE
  --------------------------------------------------------- */
  const SECTIONS = { student: {}, academic: {}, industrial: {}, coordinator: {} };

  /* ===================== STUDENT ===================== */
  SECTIONS.student.overview = () => {
    const u = me(), p = placementOf(u.id), logs = logsOf(u.id);
    const hrs = approvedHours(u.id);
    const ac = byId(u.academicSup), ind = byId(u.industrialSup);
    const avg = avgMarks(u.id);
    const recent = logs.slice(-3).reverse();
    const feedback = evalsOf(u.id).slice().reverse();

    const sup = `
      <dl class="kv">
        <dt>Academic supervisor</dt><dd>${ac ? `${e(ac.name)}<br><small style="color:var(--muted)">${e(ac.email)}</small>` : '<span style="color:var(--muted)">Not assigned yet</span>'}</dd>
        <dt>Industrial supervisor</dt><dd>${ind ? `${e(ind.name)}<br><small style="color:var(--muted)">${e(ind.company)} · ${e(ind.email)}</small>` : '<span style="color:var(--muted)">Not assigned yet</span>'}</dd>
      </dl>`;

    return pageHead('Welcome back, ' + first(u.name), `${u.course} · ${u.admNo}`) + `
      ${!p ? `<div class="alert alert-info" style="margin-bottom:22px">You have not submitted your placement yet. <button class="link" data-nav="placement">Submit placement details</button></div>` : ''}
      <div class="stats">
        ${stat('Placement', p ? cap(p.status) : 'Not submitted', p ? p.company : 'Submit your details', 'briefcase', p && p.status === 'approved' ? 'green' : 'gold')}
        ${stat('Approved hours', String(hrs), `of ${TARGET_HOURS} required`, 'clock')}
        ${stat('Logbook entries', `${logs.filter(l => l.status === 'approved').length}/${logs.length}`, 'approved / submitted', 'book')}
        ${stat('Average score', avg == null ? '—' : avg + '%', avg == null ? 'No assessment yet' : 'From supervisors', 'star', 'gold')}
      </div>
      ${cardBody('Attachment progress', `
        <div class="progress-meta"><span><b>${hrs}</b> of ${TARGET_HOURS} hours approved</span><b>${pct(hrs, TARGET_HOURS)}%</b></div>
        ${progressBar(hrs, TARGET_HOURS)}
        ${p ? `<p style="margin-top:12px;color:var(--muted);font-size:.88rem">${fmtDate(p.startDate)} – ${fmtDate(p.endDate)} · ${e(p.company)}</p>` : ''}`)}
      <div class="grid-2">
        ${cardBody('My supervisors', sup)}
        ${announcementsCard()}
      </div>
      ${cardFlush('Recent logbook entries', logbookTable(recent, false), logs.length ? `<button class="btn btn-sm btn-outline" data-nav="logbook">View all</button>` : '')}
      ${feedback.length ? cardFlush('Assessment feedback', `<div class="list">${feedback.map(a => {
        const by = byId(a.byId);
        return `<div class="list-item"><div class="grow"><strong>${e(a.type)} · ${e(a.marks)}%</strong><p>${e(a.comment || 'No comment')} — ${e(by ? by.name : '')}</p></div><time>${fmtDate(a.date)}</time></div>`;
      }).join('')}</div>`) : ''}`;
  };

  SECTIONS.student.placement = () => {
    const u = me(), p = placementOf(u.id);
    const inds = supervisorsOf('industrial');
    const form = `
      <form class="form" data-form="placement">
        <div class="alert alert-error hidden" role="alert"></div>
        <div class="form-grid">
          ${fld('company', 'Host organisation', 'text', { ph: 'Company name' })}
          ${fld('location', 'Town / location', 'text', { ph: 'e.g. Westlands, Nairobi' })}
          ${fld('department', 'Department / role', 'text', { ph: 'e.g. IT Support' })}
          ${sel('industrialSup', 'Industrial supervisor', [['', 'My supervisor is not registered yet'], ...inds.map(i => [i.id, `${i.name} — ${i.company}`])], { required: false })}
          ${fld('startDate', 'Start date', 'date')}
          ${fld('endDate', 'End date', 'date')}
        </div>
        <div class="form-actions"><button class="btn btn-primary" type="submit">Submit placement</button></div>
      </form>`;
    if (!p) return pageHead('My placement', 'Tell us where you will do your attachment.') + cardBody('Placement details', form);

    const ind = byId(p.industrialSup);
    const details = `
      <dl class="kv">
        <dt>Status</dt><dd>${badge(p.status)}</dd>
        <dt>Organisation</dt><dd>${e(p.company)}</dd>
        <dt>Location</dt><dd>${e(p.location)}</dd>
        <dt>Department / role</dt><dd>${e(p.department)}</dd>
        <dt>Period</dt><dd>${fmtDate(p.startDate)} – ${fmtDate(p.endDate)}</dd>
        <dt>Industrial supervisor</dt><dd>${ind ? e(ind.name) : 'To be assigned'}</dd>
        ${p.comment ? `<dt>Coordinator note</dt><dd>${e(p.comment)}</dd>` : ''}
      </dl>`;
    const msg = p.status === 'pending' ? '<div class="alert alert-warn" style="margin-bottom:18px">Waiting for the coordinator to review your placement.</div>'
      : p.status === 'rejected' ? '<div class="alert alert-error" style="margin-bottom:18px">Your placement was not approved. Please withdraw it and submit new details.</div>'
        : '<div class="alert alert-success" style="margin-bottom:18px">Your placement is approved. You can now fill in your weekly logbook.</div>';
    const action = p.status !== 'approved' ? `<button class="btn btn-sm btn-outline" data-action="placement-withdraw" data-id="${p.id}">Withdraw &amp; resubmit</button>` : '';
    return pageHead('My placement', 'Your host organisation and approval status.') + cardBody('Placement details', msg + details, action);
  };

  SECTIONS.student.logbook = () => {
    const u = me(), p = placementOf(u.id), logs = logsOf(u.id);
    const canLog = p && p.status === 'approved';
    const nextWeek = logs.length ? Math.max(...logs.map(l => l.week)) + 1 : 1;
    const form = canLog ? cardBody('Add weekly entry', `
      <form class="form" data-form="logbook">
        <div class="alert alert-error hidden" role="alert"></div>
        <div class="form-grid">
          ${fld('week', 'Week number', 'number', { value: nextWeek, attrs: 'min="1" max="30"' })}
          ${fld('weekStart', 'Week starting', 'date', { value: logs.length ? addDays(logs[logs.length - 1].weekStart, 7) : p.startDate })}
          ${fld('hours', 'Hours worked', 'number', { value: 40, attrs: 'min="1" max="60"' })}
          ${txt('activities', 'Activities carried out', { ph: 'Describe what you did this week...' })}
          ${txt('skills', 'Skills and knowledge gained', { required: false, ph: 'Optional' })}
        </div>
        <div class="form-actions"><button class="btn btn-primary" type="submit">Submit entry</button></div>
      </form>`)
      : `<div class="alert alert-info" style="margin-bottom:22px">${p ? 'You can add logbook entries once your placement is approved.' : 'Submit and get your placement approved before adding logbook entries.'} <button class="link" data-nav="placement">Go to placement</button></div>`;

    const rows = logs.map(l => `<tr>
      <td>Week ${e(l.week)}<span class="sub">${fmtDate(l.weekStart)}</span></td>
      <td>${e(l.hours)} hrs</td>
      <td>${badge(l.status)}</td>
      <td class="clip">${e(l.indComment || l.acadComment || '—')}</td>
      <td class="actions">
        <button class="btn btn-sm btn-outline" data-action="view-log" data-id="${l.id}">View</button>
        ${l.status !== 'approved' ? `<button class="btn btn-sm btn-ghost" data-action="delete-log" data-id="${l.id}">Delete</button>` : ''}
      </td></tr>`);
    return pageHead('Weekly logbook', 'Record your activities every week for supervisor approval.') + form +
      cardFlush('My entries', tableHTML(['Week', 'Hours', 'Status', 'Feedback', ''], rows, 'No entries yet', 'Your weekly entries will appear here.'));
  };

  SECTIONS.student.report = () => {
    const u = me(), r = reportOf(u.id);
    const current = r ? cardBody('Submitted report', `
      <dl class="kv">
        <dt>Status</dt><dd>${badge(r.status)}</dd>
        <dt>Title</dt><dd>${e(r.title)}</dd>
        <dt>File</dt><dd>${e(r.fileName)} (${e(r.size)})</dd>
        <dt>Submitted</dt><dd>${fmtDate(r.date)}</dd>
        <dt>Summary</dt><dd>${e(r.summary)}</dd>
      </dl>`) : '';
    const locked = r && r.status === 'reviewed';
    const form = locked
      ? '<div class="alert alert-success">Your report has been reviewed by your academic supervisor.</div>'
      : `<form class="form" data-form="report">
          <div class="alert alert-error hidden" role="alert"></div>
          <div class="form-grid">
            ${fld('title', 'Report title', 'text', { full: true, value: r ? r.title : '', ph: 'e.g. Industrial Attachment Report at Savannah Tech Ltd' })}
            ${txt('summary', 'Short summary', { value: r ? r.summary : '', ph: 'Briefly describe what your report covers' })}
            <div class="field full"><label for="reportFile">Report file (PDF or Word, max 10 MB)</label>
              <input id="reportFile" name="file" type="file" accept=".pdf,.doc,.docx" required></div>
          </div>
          <div class="form-actions"><button class="btn btn-primary" type="submit">${r ? 'Replace report' : 'Submit report'}</button></div>
        </form>`;
    return pageHead('Final report', 'Submit your attachment report for your academic supervisor.') + current + cardBody(r ? 'Resubmit' : 'Submit your report', form);
  };
  SECTIONS.student.profile = profileSection;

  /* ===================== ACADEMIC SUPERVISOR ===================== */
  SECTIONS.academic.overview = () => {
    const u = me(), list = myStudents(), ids = list.map(s => s.id);
    const visits = db.visits.filter(v => v.acadId === u.id && v.status === 'scheduled').sort((a, b) => a.date.localeCompare(b.date));
    const logs = db.logbooks.filter(l => ids.includes(l.studentId));
    const toReview = logs.filter(l => !l.acadComment).length;
    const done = db.assessments.filter(a => a.byId === u.id).length;
    const visitList = visits.length ? `<div class="list">${visits.slice(0, 4).map(v => {
      const s = byId(v.studentId);
      return `<div class="list-item"><div class="grow"><strong>${e(s ? s.name : '—')}</strong><p>${e(v.mode)} visit · ${e(v.notes || 'No notes')}</p></div><time>${fmtDate(v.date)}</time></div>`;
    }).join('')}</div>` : emptyBox('No upcoming visits');
    return pageHead('Welcome, ' + first(u.name), u.department || 'Academic supervisor') + `
      <div class="stats">
        ${stat('Assigned students', String(list.length), 'under your supervision', 'users')}
        ${stat('Upcoming visits', String(visits.length), 'scheduled', 'calendar', 'gold')}
        ${stat('Entries to review', String(toReview), 'without your comment', 'book', 'red')}
        ${stat('Assessments done', String(done), 'submitted by you', 'star', 'green')}
      </div>
      <div class="grid-2">
        ${cardFlush('Upcoming visits', visitList, '<button class="btn btn-sm btn-outline" data-nav="visits">Manage</button>')}
        ${announcementsCard()}
      </div>`;
  };

  SECTIONS.academic.students = () => {
    const rows = myStudents().map(s => {
      const p = placementOf(s.id), r = reportOf(s.id), avg = avgMarks(s.id, 'academic');
      const hrs = approvedHours(s.id);
      return `<tr>
        <td><strong>${e(s.name)}</strong><span class="sub">${e(s.admNo)} · ${e(s.course)}</span></td>
        <td>${p ? `${e(p.company)}<span class="sub">${badge(p.status)}</span>` : '<span class="sub">No placement</span>'}</td>
        <td style="min-width:150px"><div class="progress-meta"><span>${hrs}/${TARGET_HOURS} hrs</span></div>${progressBar(hrs, TARGET_HOURS)}</td>
        <td>${r ? badge(r.status) : '<span class="sub">Not submitted</span>'}</td>
        <td>${avg == null ? '—' : avg + '%'}</td>
        <td class="actions">
          <button class="btn btn-sm btn-outline" data-action="student-logs" data-id="${s.id}">Logbook</button>
          <button class="btn btn-sm btn-primary" data-action="assess-student" data-id="${s.id}">Assess</button>
          ${r && r.status === 'submitted' ? `<button class="btn btn-sm btn-success" data-action="review-report" data-id="${s.id}">Mark report reviewed</button>` : ''}
        </td></tr>`;
    });
    return pageHead('My students', 'Students assigned to you by the coordinator.') +
      cardFlush('Assigned students', tableHTML(['Student', 'Placement', 'Progress', 'Report', 'Your score', ''], rows, 'No students assigned yet', 'The coordinator will assign students to you.'));
  };

  SECTIONS.academic.logbooks = () => {
    const ids = myStudents().map(s => s.id);
    const entries = db.logbooks.filter(l => ids.includes(l.studentId)).sort((a, b) => b.submitted.localeCompare(a.submitted) || b.week - a.week);
    const rows = entries.map(l => {
      const s = byId(l.studentId);
      return `<tr>
        <td><strong>${e(s ? s.name : '—')}</strong><span class="sub">${e(s ? s.admNo : '')}</span></td>
        <td>Week ${e(l.week)}<span class="sub">${e(l.hours)} hrs</span></td>
        <td>${badge(l.status)}</td>
        <td class="clip">${e(l.acadComment || '—')}</td>
        <td class="actions">
          <button class="btn btn-sm btn-outline" data-action="view-log" data-id="${l.id}">View</button>
          <button class="btn btn-sm btn-primary" data-action="comment-log" data-id="${l.id}">${l.acadComment ? 'Edit comment' : 'Comment'}</button>
        </td></tr>`;
    });
    return pageHead('Logbook review', 'Read your students’ entries and leave feedback.') +
      cardFlush('Student entries', tableHTML(['Student', 'Week', 'Industry status', 'Your comment', ''], rows, 'No entries to review yet'));
  };

  SECTIONS.academic.visits = () => {
    const u = me(), list = myStudents();
    const visits = db.visits.filter(v => v.acadId === u.id).sort((a, b) => b.date.localeCompare(a.date));
    const form = list.length ? cardBody('Schedule a visit', `
      <form class="form" data-form="visit">
        <div class="form-grid">
          ${sel('studentId', 'Student', list.map(s => [s.id, s.name]), { placeholder: 'Select student' })}
          ${fld('date', 'Visit date', 'date', { value: today() })}
          ${sel('mode', 'Visit type', ['Physical', 'Virtual'])}
          ${fld('notes', 'Purpose / notes', 'text', { required: false, ph: 'Optional' })}
        </div>
        <div class="form-actions"><button class="btn btn-primary" type="submit">Schedule visit</button></div>
      </form>`) : '<div class="alert alert-info" style="margin-bottom:22px">You need assigned students before you can schedule visits.</div>';
    const rows = visits.map(v => {
      const s = byId(v.studentId);
      return `<tr>
        <td><strong>${e(s ? s.name : '—')}</strong></td>
        <td>${fmtDate(v.date)}</td><td>${e(v.mode)}</td>
        <td class="clip">${e(v.notes || '—')}</td>
        <td>${badge(v.status)}</td>
        <td class="actions">${v.status === 'scheduled' ? `<button class="btn btn-sm btn-success" data-action="visit-complete" data-id="${v.id}">Complete</button><button class="btn btn-sm btn-ghost" data-action="visit-cancel" data-id="${v.id}">Cancel</button>` : ''}</td></tr>`;
    });
    return pageHead('Supervisor visits', 'Plan and record visits to your students.') + form +
      cardFlush('All visits', tableHTML(['Student', 'Date', 'Type', 'Notes', 'Status', ''], rows, 'No visits scheduled'));
  };

  SECTIONS.academic.assessments = () => {
    const u = me(), list = myStudents();
    const pre = ui.preselect; ui.preselect = null;
    const form = list.length ? cardBody('New assessment', `
      <form class="form" data-form="assessment">
        <div class="form-grid">
          ${sel('studentId', 'Student', list.map(s => [s.id, s.name]), { placeholder: 'Select student', value: pre })}
          ${sel('type', 'Assessment type', ['Mid-attachment visit', 'Final assessment'])}
          ${fld('marks', 'Marks (0 – 100)', 'number', { attrs: 'min="0" max="100"' })}
          ${txt('comment', 'Comments and recommendation', { ph: 'Strengths, areas to improve...' })}
        </div>
        <div class="form-actions"><button class="btn btn-primary" type="submit">Save assessment</button></div>
      </form>`) : '<div class="alert alert-info" style="margin-bottom:22px">You have no assigned students to assess yet.</div>';
    const mine = db.assessments.filter(a => a.byId === u.id).sort((a, b) => b.date.localeCompare(a.date));
    const rows = mine.map(a => {
      const s = byId(a.studentId);
      return `<tr><td><strong>${e(s ? s.name : '—')}</strong></td><td>${e(a.type)}</td><td>${e(a.marks)}%</td><td class="clip">${e(a.comment || '—')}</td><td>${fmtDate(a.date)}</td></tr>`;
    });
    return pageHead('Assessments', 'Record marks and comments for your students.') + form +
      cardFlush('Assessments you have submitted', tableHTML(['Student', 'Type', 'Marks', 'Comments', 'Date'], rows, 'No assessments yet'));
  };
  SECTIONS.academic.profile = profileSection;

  /* ===================== INDUSTRIAL SUPERVISOR ===================== */
  SECTIONS.industrial.overview = () => {
    const u = me(), list = myStudents(), ids = list.map(s => s.id);
    const logs = db.logbooks.filter(l => ids.includes(l.studentId));
    const pending = logs.filter(l => l.status === 'pending');
    const evals = db.assessments.filter(a => a.byId === u.id).length;
    const pendList = pending.length ? `<div class="list">${pending.slice(0, 5).map(l => {
      const s = byId(l.studentId);
      return `<div class="list-item"><div class="grow"><strong>${e(s ? s.name : '—')} · Week ${e(l.week)}</strong><p>${e(l.activities.slice(0, 90))}${l.activities.length > 90 ? '…' : ''}</p></div><button class="btn btn-sm btn-outline" data-action="view-log" data-id="${l.id}">Open</button></div>`;
    }).join('')}</div>` : emptyBox('All caught up', 'No entries waiting for approval.');
    return pageHead('Welcome, ' + first(u.name), `${u.position || 'Industrial supervisor'} · ${u.company || ''}`) + `
      <div class="stats">
        ${stat('Interns', String(list.length), 'under your supervision', 'users')}
        ${stat('Pending approvals', String(pending.length), 'logbook entries', 'check', 'gold')}
        ${stat('Approved entries', String(logs.filter(l => l.status === 'approved').length), 'in total', 'book', 'green')}
        ${stat('Evaluations', String(evals), 'submitted by you', 'star')}
      </div>
      <div class="grid-2">
        ${cardFlush('Waiting for approval', pendList, '<button class="btn btn-sm btn-outline" data-nav="approvals">Review all</button>')}
        ${announcementsCard()}
      </div>`;
  };

  SECTIONS.industrial.interns = () => {
    const rows = myStudents().map(s => {
      const p = placementOf(s.id), avg = avgMarks(s.id, 'industrial');
      return `<tr>
        <td><strong>${e(s.name)}</strong><span class="sub">${e(s.admNo)} · ${e(s.course)}</span></td>
        <td>${p ? `${e(p.department)}<span class="sub">${fmtDate(p.startDate)} – ${fmtDate(p.endDate)}</span>` : '—'}</td>
        <td>${approvedHours(s.id)} <span class="sub">of ${loggedHours(s.id)} logged</span></td>
        <td>${avg == null ? '<span class="sub">Not evaluated</span>' : avg + '%'}</td>
        <td class="actions">
          <button class="btn btn-sm btn-outline" data-action="student-logs" data-id="${s.id}">Logbook</button>
          <button class="btn btn-sm btn-primary" data-action="evaluate-student" data-id="${s.id}">Evaluate</button>
        </td></tr>`;
    });
    return pageHead('My interns', 'Students placed with your organisation.') +
      cardFlush('Interns', tableHTML(['Intern', 'Department / period', 'Approved hours', 'Your evaluation', ''], rows, 'No interns yet', 'Interns appear here once the coordinator approves their placement with you.'));
  };

  SECTIONS.industrial.approvals = () => {
    const ids = myStudents().map(s => s.id);
    const all = db.logbooks.filter(l => ids.includes(l.studentId)).sort((a, b) => b.submitted.localeCompare(a.submitted) || b.week - a.week);
    const pending = all.filter(l => l.status === 'pending');
    const rows = pending.map(l => {
      const s = byId(l.studentId);
      return `<tr>
        <td><strong>${e(s ? s.name : '—')}</strong><span class="sub">${e(s ? s.admNo : '')}</span></td>
        <td>Week ${e(l.week)}<span class="sub">${fmtDate(l.weekStart)}</span></td>
        <td>${e(l.hours)} hrs</td>
        <td class="clip">${e(l.activities)}</td>
        <td class="actions">
          <button class="btn btn-sm btn-outline" data-action="view-log" data-id="${l.id}">View</button>
          <button class="btn btn-sm btn-success" data-action="approve-log" data-id="${l.id}">Approve</button>
          <button class="btn btn-sm btn-danger" data-action="reject-log" data-id="${l.id}">Reject</button>
        </td></tr>`;
    });
    const history = all.filter(l => l.status !== 'pending');
    return pageHead('Logbook approvals', 'Approve or reject your interns’ weekly entries.') +
      cardFlush(`Pending (${pending.length})`, tableHTML(['Intern', 'Week', 'Hours', 'Activities', ''], rows, 'Nothing pending', 'New entries from your interns will show up here.')) +
      cardFlush('History', logbookTable(history, true));
  };

  SECTIONS.industrial.evaluation = () => {
    const u = me(), list = myStudents();
    const pre = ui.preselect; ui.preselect = null;
    const form = list.length ? cardBody('Intern evaluation', `
      <form class="form" data-form="evaluation">
        ${sel('studentId', 'Intern', list.map(s => [s.id, s.name]), { placeholder: 'Select intern', value: pre })}
        <div class="rating-grid">
          ${CRITERIA.map((c, i) => `<label for="cr${i}" style="font-weight:600;font-size:.9rem">${e(c)}</label>
            <select id="cr${i}" name="cr${i}" required style="padding:9px;border:1px solid #cbd5e1;border-radius:8px;font:inherit">
              <option value="">Rate</option><option value="5">5 – Excellent</option><option value="4">4 – Very good</option><option value="3">3 – Good</option><option value="2">2 – Fair</option><option value="1">1 – Poor</option>
            </select>`).join('')}
        </div>
        ${txt('comment', 'Overall comments', { ph: 'Describe the intern’s performance...' })}
        <div class="form-actions"><button class="btn btn-primary" type="submit">Submit evaluation</button></div>
      </form>`) : '<div class="alert alert-info" style="margin-bottom:22px">You have no interns to evaluate yet.</div>';
    const mine = db.assessments.filter(a => a.byId === u.id).sort((a, b) => b.date.localeCompare(a.date));
    const rows = mine.map(a => {
      const s = byId(a.studentId);
      return `<tr><td><strong>${e(s ? s.name : '—')}</strong></td><td>${e(a.marks)}%</td><td class="clip">${e(a.comment || '—')}</td><td>${fmtDate(a.date)}</td></tr>`;
    });
    return pageHead('Evaluation', 'Rate your interns on key workplace skills.') + form +
      cardFlush('Evaluations you have submitted', tableHTML(['Intern', 'Score', 'Comments', 'Date'], rows, 'No evaluations yet'));
  };
  SECTIONS.industrial.profile = profileSection;

  /* ===================== COORDINATOR ===================== */
  SECTIONS.coordinator.overview = () => {
    const u = me(), sts = students();
    const counts = { none: 0, pending: 0, approved: 0, rejected: 0 };
    sts.forEach(s => { const p = placementOf(s.id); counts[p ? p.status : 'none']++; });
    const total = sts.length || 1;
    const bars = [['No placement', counts.none], ['Pending', counts.pending], ['Approved', counts.approved], ['Rejected', counts.rejected]]
      .map(([l, n]) => `<div class="bar-row"><span>${l}</span>${progressBar(n, total)}<b>${n}</b></div>`).join('');
    const recent = sts.slice().sort((a, b) => b.created.localeCompare(a.created)).slice(0, 5);
    const recentList = recent.length ? `<div class="list">${recent.map(s => `<div class="list-item"><span class="avatar avatar-sm">${e(initials(s.name))}</span><div class="grow"><strong>${e(s.name)}</strong><p>${e(s.admNo)} · ${e(s.course)}</p></div><time>${fmtDate(s.created)}</time></div>`).join('')}</div>` : emptyBox('No students yet');
    return pageHead('Welcome, ' + first(u.name), 'Coordinator overview') + `
      <div class="stats">
        ${stat('Students', String(sts.length), 'registered', 'users')}
        ${stat('Placed', String(counts.approved), 'approved placements', 'briefcase', 'green')}
        ${stat('Pending placements', String(counts.pending), 'need your review', 'clock', 'gold')}
        ${stat('Supervisors', String(supervisorsOf('academic').length + supervisorsOf('industrial').length), `${supervisorsOf('academic').length} academic · ${supervisorsOf('industrial').length} industrial`, 'clipboard')}
      </div>
      <div class="grid-2">
        ${cardBody('Placement status', `<div class="bars">${bars}</div>`)}
        ${cardFlush('Recent registrations', recentList)}
      </div>
      ${announcementsCard()}`;
  };

  SECTIONS.coordinator.placements = () => {
    const list = db.placements.slice().sort((a, b) => (a.status === 'pending' ? -1 : 1) - (b.status === 'pending' ? -1 : 1));
    const rows = list.map(p => {
      const s = byId(p.studentId), ind = byId(p.industrialSup);
      return `<tr>
        <td><strong>${e(s ? s.name : '—')}</strong><span class="sub">${e(s ? s.admNo : '')}</span></td>
        <td>${e(p.company)}<span class="sub">${e(p.location)} · ${e(p.department)}</span></td>
        <td>${fmtDate(p.startDate)}<span class="sub">to ${fmtDate(p.endDate)}</span></td>
        <td>${ind ? e(ind.name) : '<span class="sub">Not set</span>'}</td>
        <td>${badge(p.status)}</td>
        <td class="actions">${p.status === 'pending' ? `<button class="btn btn-sm btn-success" data-action="placement-approve" data-id="${p.id}">Approve</button><button class="btn btn-sm btn-danger" data-action="placement-reject" data-id="${p.id}">Reject</button>` : ''}</td></tr>`;
    });
    return pageHead('Placements', 'Review and approve student placements.') +
      cardFlush('All placements', tableHTML(['Student', 'Organisation', 'Period', 'Industrial supervisor', 'Status', ''], rows, 'No placements submitted yet'));
  };

  SECTIONS.coordinator.students = () => {
    const acads = supervisorsOf('academic'), inds = supervisorsOf('industrial');
    const opts = (arr, cur) => `<option value="">— Not assigned —</option>${arr.map(a => `<option value="${a.id}" ${a.id === cur ? 'selected' : ''}>${e(a.name)}</option>`).join('')}`;
    const rows = students().map(s => {
      const p = placementOf(s.id);
      return `<tr>
        <td><strong>${e(s.name)}</strong><span class="sub">${e(s.admNo)} · ${e(s.course)}</span></td>
        <td>${p ? badge(p.status) : '<span class="sub">None</span>'}</td>
        <td><select data-assign="academicSup" data-id="${s.id}" aria-label="Academic supervisor for ${e(s.name)}">${opts(acads, s.academicSup)}</select></td>
        <td><select data-assign="industrialSup" data-id="${s.id}" aria-label="Industrial supervisor for ${e(s.name)}">${opts(inds, s.industrialSup)}</select></td>
        <td><button class="btn btn-sm btn-outline" data-action="student-logs" data-id="${s.id}">Logbook</button></td></tr>`;
    });
    return pageHead('Students', 'Assign supervisors to each student.') +
      cardFlush('Registered students', tableHTML(['Student', 'Placement', 'Academic supervisor', 'Industrial supervisor', ''], rows, 'No students registered yet'));
  };

  SECTIONS.coordinator.supervisors = () => {
    const acRows = supervisorsOf('academic').map(a => `<tr><td><strong>${e(a.name)}</strong><span class="sub">${e(a.email)}</span></td><td>${e(a.department || '—')}</td><td>${students().filter(s => s.academicSup === a.id).length}</td></tr>`);
    const inRows = supervisorsOf('industrial').map(a => `<tr><td><strong>${e(a.name)}</strong><span class="sub">${e(a.email)}</span></td><td>${e(a.company || '—')}<span class="sub">${e(a.position || '')}</span></td><td>${students().filter(s => s.industrialSup === a.id).length}</td></tr>`);
    return pageHead('Supervisors', 'Registered academic and industrial supervisors.') +
      cardFlush('Academic supervisors', tableHTML(['Name', 'Department', 'Students'], acRows, 'No academic supervisors yet')) +
      cardFlush('Industrial supervisors', tableHTML(['Name', 'Organisation', 'Interns'], inRows, 'No industrial supervisors yet'));
  };

  SECTIONS.coordinator.announcements = () => {
    const list = db.announcements.slice().sort((a, b) => b.date.localeCompare(a.date));
    const items = list.length ? `<div class="list">${list.map(a => `<div class="list-item"><div class="grow"><strong>${e(a.title)}</strong><p>${e(a.body)}</p></div><time>${fmtDate(a.date)}</time><button class="btn btn-sm btn-ghost" data-action="delete-announcement" data-id="${a.id}">Delete</button></div>`).join('')}</div>` : emptyBox('No announcements yet');
    return pageHead('Announcements', 'Share notices with every user of the portal.') +
      cardBody('New announcement', `
        <form class="form" data-form="announcement">
          ${fld('title', 'Title', 'text', { ph: 'e.g. Supervisor visits begin next week' })}
          ${txt('body', 'Message', { ph: 'Write your announcement...' })}
          <div class="form-actions"><button class="btn btn-primary" type="submit">Post announcement</button></div>
        </form>`) +
      cardFlush('Posted announcements', items);
  };

  function reportRows() {
    return students().map(s => {
      const p = placementOf(s.id), r = reportOf(s.id);
      const ac = avgMarks(s.id, 'academic'), ind = avgMarks(s.id, 'industrial');
      const parts = [ac, ind].filter(x => x != null);
      const overall = parts.length ? Math.round(parts.reduce((t, x) => t + x, 0) / parts.length) : null;
      return { s, p, r, hrs: approvedHours(s.id), ac, ind, overall };
    });
  }
  SECTIONS.coordinator.reports = () => {
    const rows = reportRows().map(x => `<tr>
      <td><strong>${e(x.s.name)}</strong><span class="sub">${e(x.s.admNo)} · ${e(x.s.course)}</span></td>
      <td>${x.p ? e(x.p.company) : '—'}</td>
      <td>${x.hrs}/${TARGET_HOURS}</td>
      <td>${x.ac == null ? '—' : x.ac + '%'}</td>
      <td>${x.ind == null ? '—' : x.ind + '%'}</td>
      <td><strong>${x.overall == null ? '—' : x.overall + '%'}</strong></td>
      <td>${x.r ? badge(x.r.status) : '<span class="sub">None</span>'}</td></tr>`);
    return pageHead('Reports', 'Summary of progress and assessment results.') +
      cardFlush('Student summary', tableHTML(['Student', 'Organisation', 'Hours', 'Academic', 'Industrial', 'Overall', 'Final report'], rows, 'No data yet'),
        '<button class="btn btn-sm btn-outline" data-action="export-csv">Export CSV</button>');
  };
  SECTIONS.coordinator.profile = profileSection;

  /* ---------------------------------------------------------
     10. FORM HANDLERS
  --------------------------------------------------------- */
  const FORMS = {
    login(d, form) {
      const email = (d.email || '').trim().toLowerCase();
      if (!email || !d.password) return formError(form, 'Enter your email and password.');
      const any = db.users.find(u => u.email === email);
      if (any && any.role !== ui.authRole && any.password === d.password) {
        return formError(form, `This email is registered as ${ROLES[any.role].label}. Choose that role tab and try again.`);
      }
      const u = db.users.find(x => x.email === email && x.role === ui.authRole);
      // API: POST /auth/login
      if (!u || u.password !== d.password) return formError(form, 'Incorrect email or password for this role.');
      startSession(u);
    },

    signup(d, form) {
      const role = ui.authRole;
      const name = (d.name || '').trim(), email = (d.email || '').trim().toLowerCase();
      if (name.length < 3) return formError(form, 'Please enter your full name.');
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return formError(form, 'Enter a valid email address.');
      if (db.users.some(u => u.email === email)) return formError(form, 'An account with this email already exists. Try logging in.');
      for (const f of ROLE_FIELDS[role]) if (!(d[f.n] || '').trim()) return formError(form, `Please fill in: ${f.l}.`);
      if (role === 'student' && db.users.some(u => u.role === 'student' && u.admNo.toLowerCase() === d.admNo.trim().toLowerCase()))
        return formError(form, 'That admission number is already registered.');
      if (role === 'coordinator' && (d.code || '').trim() !== COORDINATOR_CODE) return formError(form, 'Invalid coordinator access code.');
      if ((d.password || '').length < 8) return formError(form, 'Password must be at least 8 characters.');
      if (d.password !== d.confirm) return formError(form, 'Passwords do not match.');

      const user = { id: uid('u'), role, name, email, phone: (d.phone || '').trim(), password: d.password, created: new Date().toISOString() };
      ROLE_FIELDS[role].forEach(f => { user[f.n] = (d[f.n] || '').trim(); });
      if (role === 'student') { user.academicSup = ''; user.industrialSup = ''; }
      // API: POST /auth/register
      db.users.push(user); save();
      startSession(user);
    },

    profile(d) {
      const u = me();
      u.name = (d.name || u.name).trim();
      u.phone = (d.phone || '').trim();
      ROLE_FIELDS[u.role].forEach(f => { if (!f.lock && d[f.n] != null) u[f.n] = d[f.n].trim(); });
      save(); renderDashboard(); toast('Profile updated.', 'success');
    },

    'recover-password'(d, form) {
      const email = (d.email || '').trim().toLowerCase();
      if (!email) return formError(form, 'Enter your email address.');
      const user = db.users.find(u => (u.email || '').toLowerCase() === email);
      if (!user) return formError(form, 'No account was found with that email address.');
      closeModal();
      toast('Password reset instructions were sent to ' + email + '.', 'success');
    },

    password(d, form) {
      const u = me();
      if (d.current !== u.password) return formError(form, 'Current password is incorrect.');
      if ((d.next || '').length < 8) return formError(form, 'New password must be at least 8 characters.');
      if (d.next !== d.confirm) return formError(form, 'New passwords do not match.');
      u.password = d.next; save(); form.reset(); toast('Password updated.', 'success');
    },

    placement(d, form) {
      if (d.endDate <= d.startDate) return formError(form, 'End date must be after the start date.');
      const u = me();
      db.placements = db.placements.filter(p => p.studentId !== u.id);
      db.placements.push({ id: uid('p'), studentId: u.id, company: d.company.trim(), location: d.location.trim(), department: d.department.trim(), startDate: d.startDate, endDate: d.endDate, industrialSup: d.industrialSup || '', status: 'pending', comment: '', submitted: new Date().toISOString() });
      save(); renderDashboard(); toast('Placement submitted for approval.', 'success');
    },

    logbook(d, form) {
      const u = me(), week = Number(d.week), hours = Number(d.hours);
      if (!week || week < 1) return formError(form, 'Enter a valid week number.');
      if (!hours || hours < 1 || hours > 60) return formError(form, 'Hours must be between 1 and 60.');
      if (logsOf(u.id).some(l => l.week === week)) return formError(form, `Week ${week} already has an entry.`);
      db.logbooks.push({ id: uid('l'), studentId: u.id, week, weekStart: d.weekStart, hours, activities: d.activities.trim(), skills: (d.skills || '').trim(), status: 'pending', indComment: '', acadComment: '', submitted: new Date().toISOString() });
      save(); renderDashboard(); toast('Logbook entry submitted.', 'success');
    },

    report(d, form) {
      const file = $('input[type=file]', form).files[0];
      if (!file) return formError(form, 'Choose a file to upload.');
      if (file.size > 10 * 1024 * 1024) return formError(form, 'File is larger than 10 MB.');
      if (!/\.(pdf|docx?)$/i.test(file.name)) return formError(form, 'Only PDF or Word files are accepted.');
      const u = me();
      const size = file.size > 1048576 ? (file.size / 1048576).toFixed(1) + ' MB' : Math.max(1, Math.round(file.size / 1024)) + ' KB';
      db.reports = db.reports.filter(r => r.studentId !== u.id);
      // API: upload the file with multipart/form-data. Here only the file name is stored.
      db.reports.push({ id: uid('r'), studentId: u.id, title: d.title.trim(), summary: d.summary.trim(), fileName: file.name, size, date: new Date().toISOString(), status: 'submitted' });
      save(); renderDashboard(); toast('Report submitted.', 'success');
    },

    visit(d) {
      db.visits.push({ id: uid('v'), studentId: d.studentId, acadId: me().id, date: d.date, mode: d.mode, notes: (d.notes || '').trim(), status: 'scheduled' });
      save(); renderDashboard(); toast('Visit scheduled.', 'success');
    },

    assessment(d, form) {
      const marks = Number(d.marks);
      if (isNaN(marks) || marks < 0 || marks > 100) return formError(form, 'Marks must be between 0 and 100.');
      db.assessments.push({ id: uid('a'), studentId: d.studentId, byId: me().id, role: 'academic', type: d.type, marks, comment: d.comment.trim(), date: new Date().toISOString() });
      save(); renderDashboard(); toast('Assessment saved.', 'success');
    },

    evaluation(d) {
      const ratings = {}; let sum = 0;
      CRITERIA.forEach((c, i) => { ratings[c] = Number(d['cr' + i]); sum += ratings[c]; });
      const marks = Math.round(sum / (CRITERIA.length * 5) * 100);
      db.assessments.push({ id: uid('a'), studentId: d.studentId, byId: me().id, role: 'industrial', type: 'Industrial evaluation', marks, ratings, comment: d.comment.trim(), date: new Date().toISOString() });
      save(); renderDashboard(); toast(`Evaluation submitted (${marks}%).`, 'success');
    },

    announcement(d) {
      db.announcements.push({ id: uid('n'), title: d.title.trim(), body: d.body.trim(), date: new Date().toISOString(), authorId: me().id });
      save(); renderDashboard(); toast('Announcement posted.', 'success');
    },

    comment(d) {
      const l = db.logbooks.find(x => x.id === d.id);
      if (l) { l.acadComment = d.comment.trim(); save(); }
      closeModal(); renderDashboard(); toast('Comment saved.', 'success');
    },

    reject(d) {
      if (d.kind === 'log') {
        const l = db.logbooks.find(x => x.id === d.id);
        if (l) { l.status = 'rejected'; l.indComment = d.reason.trim(); }
      } else {
        const p = db.placements.find(x => x.id === d.id);
        if (p) { p.status = 'rejected'; p.comment = d.reason.trim(); }
      }
      save(); closeModal(); renderDashboard(); toast('Rejected with feedback.', 'success');
    }
  };

  /* ---------------------------------------------------------
     11. CLICK ACTIONS
  --------------------------------------------------------- */
  const ACTIONS = {
    'go-home'() { showView('landing'); },
    logout,
    'toggle-sidebar'() { $('#sidebar').classList.toggle('open'); $('.sidebar-backdrop').classList.toggle('show'); },
    'close-sidebar'() { $('#sidebar').classList.remove('open'); $('.sidebar-backdrop').classList.remove('show'); },
    'close-modal'() { closeModal(); },
    'toggle-pw'(t) {
      const input = $('input', t.parentElement);
      const show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      t.textContent = show ? 'Hide' : 'Show';
    },
    'switch-auth'(t) { ui.authMode = t.dataset.mode; renderAuth(); },
    'forgot-password'() {
      openModal('Reset your password', `
        <form class="form" data-form="recover-password">
          <div class="alert alert-error hidden" role="alert"></div>
          ${fld('email', 'Email address', 'email', { ph: 'Enter your registered email', full: true, attrs: 'autocomplete="username"' })}
          <p style="margin:0 0 18px;color:var(--muted);font-size:.9rem;">We will send reset instructions to this email if an account exists.</p>
          <div class="form-actions"><button class="btn btn-ghost" type="button" data-action="close-modal">Cancel</button><button class="btn btn-primary" type="submit">Send reset link</button></div>
        </form>`);
    },

    'view-log'(t) {
      const l = db.logbooks.find(x => x.id === t.dataset.id);
      if (l) openModal(`Week ${l.week} logbook entry`, logDetailHTML(l));
    },
    'student-logs'(t) {
      const s = byId(t.dataset.id);
      const entries = logsOf(s.id);
      openModal(`${s.name} — logbook`, entries.length
        ? `<div class="table-wrap"><table><thead><tr><th>Week</th><th>Hours</th><th>Status</th><th>Activities</th></tr></thead><tbody>${entries.map(l => `<tr><td>Week ${e(l.week)}</td><td>${e(l.hours)}</td><td>${badge(l.status)}</td><td>${e(l.activities)}</td></tr>`).join('')}</tbody></table></div>`
        : emptyBox('No entries yet'));
    },
    'delete-log'(t) {
      if (!confirm('Delete this logbook entry?')) return;
      db.logbooks = db.logbooks.filter(l => l.id !== t.dataset.id);
      save(); renderDashboard(); toast('Entry deleted.');
    },
    'comment-log'(t) {
      const l = db.logbooks.find(x => x.id === t.dataset.id);
      const s = byId(l.studentId);
      openModal(`Comment on Week ${l.week} — ${s.name}`, `
        <form class="form" data-form="comment">
          <input type="hidden" name="id" value="${l.id}">
          ${txt('comment', 'Your comment', { value: l.acadComment, ph: 'Write feedback for the student...' })}
          <div class="form-actions"><button class="btn btn-ghost" type="button" data-action="close-modal">Cancel</button><button class="btn btn-primary" type="submit">Save comment</button></div>
        </form>`);
    },
    'approve-log'(t) {
      const l = db.logbooks.find(x => x.id === t.dataset.id);
      if (l) { l.status = 'approved'; if (!l.indComment) l.indComment = 'Approved.'; save(); renderDashboard(); toast('Entry approved.', 'success'); }
    },
    'reject-log'(t) { rejectModal('log', t.dataset.id, 'Reject logbook entry'); },
    'placement-approve'(t) {
      const p = db.placements.find(x => x.id === t.dataset.id);
      if (!p) return;
      p.status = 'approved'; p.comment = '';
      const s = byId(p.studentId);
      if (s && p.industrialSup && !s.industrialSup) s.industrialSup = p.industrialSup;
      save(); renderDashboard(); toast('Placement approved.', 'success');
    },
    'placement-reject'(t) { rejectModal('placement', t.dataset.id, 'Reject placement'); },
    'placement-withdraw'(t) {
      if (!confirm('Withdraw this placement and submit new details?')) return;
      db.placements = db.placements.filter(p => p.id !== t.dataset.id);
      save(); renderDashboard();
    },
    'visit-complete'(t) { setVisit(t.dataset.id, 'completed'); },
    'visit-cancel'(t) { setVisit(t.dataset.id, 'cancelled'); },
    'delete-announcement'(t) {
      if (!confirm('Delete this announcement?')) return;
      db.announcements = db.announcements.filter(a => a.id !== t.dataset.id);
      save(); renderDashboard();
    },
    'review-report'(t) {
      const r = reportOf(t.dataset.id);
      if (r) { r.status = 'reviewed'; save(); renderDashboard(); toast('Report marked as reviewed.', 'success'); }
    },
    'assess-student'(t) { ui.preselect = t.dataset.id; go('assessments'); },
    'evaluate-student'(t) { ui.preselect = t.dataset.id; go('evaluation'); },
    'export-csv'() {
      const header = ['Name', 'Admission No', 'Course', 'Organisation', 'Approved hours', 'Academic %', 'Industrial %', 'Overall %', 'Final report'];
      const lines = reportRows().map(x => [x.s.name, x.s.admNo, x.s.course, x.p ? x.p.company : '', x.hrs, x.ac ?? '', x.ind ?? '', x.overall ?? '', x.r ? x.r.status : 'none']
        .map(v => '"' + String(v).replace(/"/g, '""') + '"').join(','));
      const blob = new Blob([[header.join(','), ...lines].join('\n')], { type: 'text/csv' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'langata-attachment-report.csv';
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    }
  };

  function setVisit(id, status) {
    const v = db.visits.find(x => x.id === id);
    if (v) { v.status = status; save(); renderDashboard(); toast('Visit ' + status + '.', 'success'); }
  }
  function rejectModal(kind, id, title) {
    openModal(title, `
      <form class="form" data-form="reject">
        <input type="hidden" name="kind" value="${kind}">
        <input type="hidden" name="id" value="${id}">
        ${txt('reason', 'Reason (the student will see this)', { ph: 'Explain what needs to change...' })}
        <div class="form-actions"><button class="btn btn-ghost" type="button" data-action="close-modal">Cancel</button><button class="btn btn-danger" type="submit">Reject</button></div>
      </form>`);
  }

  /* ---------------------------------------------------------
     12. EVENT WIRING
  --------------------------------------------------------- */
  document.addEventListener('click', ev => {
    const t = ev.target.closest('[data-action],[data-nav],[data-auth],[data-tab],[data-scroll]');
    if (!t) return;

    if (t.dataset.auth) { openAuth(t.dataset.auth, t.dataset.role); return; }
    if (t.dataset.scroll) {
      ev.preventDefault();
      const id = t.dataset.scroll;
      if (id === 'top') window.scrollTo({ top: 0, behavior: 'smooth' });
      else { const el = document.getElementById(id); if (el) el.scrollIntoView({ behavior: 'smooth' }); }
      return;
    }
    if (t.dataset.tab) { ui.authRole = t.dataset.tab; renderAuth(); return; }
    if (t.dataset.nav) { go(t.dataset.nav); return; }

    const action = t.dataset.action;
    if (action === 'close-modal' && t.classList.contains('modal-backdrop') && ev.target !== t) return;
    if (ACTIONS[action]) ACTIONS[action](t, ev);
  });

  document.addEventListener('submit', ev => {
    const form = ev.target.closest('form[data-form]');
    if (!form) return;
    ev.preventDefault();
    const box = $('.alert-error', form);
    if (box) box.classList.add('hidden');
    const handler = FORMS[form.dataset.form];
    if (!handler) return;
    // Native validation (skipped for forms marked novalidate, which validate in code)
    if (!form.noValidate && !form.checkValidity()) { form.reportValidity(); return; }
    handler(Object.fromEntries(new FormData(form)), form);
  });

  document.addEventListener('change', ev => {
    const s = ev.target.closest('select[data-assign]');
    if (!s) return;
    const st = byId(s.dataset.id);
    if (!st) return;
    st[s.dataset.assign] = s.value;
    save(); renderDashboard();
    toast('Supervisor assignment updated.', 'success');
  });

  document.addEventListener('keydown', ev => { if (ev.key === 'Escape') closeModal(); });

  /* ---------------------------------------------------------
     13. START
  --------------------------------------------------------- */
  const yr = new Date().getFullYear();
  $('#year').textContent = yr;
  $('#year2').textContent = yr;

  if (session && me()) { showView('dashboard'); renderDashboard(); }
  else { session = null; showView('landing'); }
})();