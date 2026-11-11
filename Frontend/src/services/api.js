import axios from 'axios';

export const API_URL = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api').replace(/\/$/, '');
const API_ORIGIN = new URL(API_URL).origin;

const ACCESS_KEY = 'sims.access';
const REFRESH_KEY = 'sims.refresh';

function read(key) {
  try { return localStorage.getItem(key); } catch { return null; }
}

export const tokens = {
  get access() { return read(ACCESS_KEY); },
  get refresh() { return read(REFRESH_KEY); },
  set(access, refresh) {
    try {
      localStorage.setItem(ACCESS_KEY, access);
      if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
    } catch { /* storage unavailable */ }
  },
  clear() {
    try { localStorage.removeItem(ACCESS_KEY); localStorage.removeItem(REFRESH_KEY); } catch { /* ignore */ }
  },
};

const api = axios.create({ baseURL: API_URL });

api.interceptors.request.use((config) => {
  const token = tokens.access;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// When the access token expires, get a new one with the refresh token (once) and retry.
let refreshing = null;
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    const status = error.response?.status;
    if (status === 401 && original && !original._retry && tokens.refresh && !original.url.includes('/auth/')) {
      original._retry = true;
      try {
        refreshing = refreshing || axios.post(`${API_URL}/auth/refresh/`, { refresh: tokens.refresh })
          .finally(() => { refreshing = null; });
        const { data } = await refreshing;
        tokens.set(data.access, data.refresh);
        original.headers.Authorization = `Bearer ${data.access}`;
        return api(original);
      } catch {
        tokens.clear();
        window.dispatchEvent(new Event('sims:logout'));
      }
    }
    return Promise.reject(error);
  },
);

/** Human readable message from an API error. */
export function errorMessage(err) {
  const data = err?.response?.data;
  if (!err?.response) return 'Cannot reach the server. Check your connection and that the backend is running.';
  if (typeof data === 'string') return `Server error (${err.response.status}).`;
  if (data?.detail) return Array.isArray(data.detail) ? data.detail.join(' ') : data.detail;
  if (data?.non_field_errors) return data.non_field_errors.join(' ');
  if (Array.isArray(data)) return data.join(' ');
  if (data && typeof data === 'object') {
    const [field, msg] = Object.entries(data)[0] || [];
    if (field) return `${field.replace(/_/g, ' ')}: ${flatten(msg)}`;
  }
  return 'Something went wrong.';
}

function flatten(msg) {
  if (Array.isArray(msg)) return msg.map(flatten).join(' ');
  if (msg && typeof msg === 'object') return Object.entries(msg).map(([k, v]) => `${k.replace(/_/g, ' ')}: ${flatten(v)}`).join(' ');
  return String(msg);
}

/** {field: "message"} for showing errors under form inputs. */
export function fieldErrors(err) {
  const data = err?.response?.data;
  if (!data || typeof data !== 'object' || Array.isArray(data)) return {};
  const out = {};
  for (const [k, v] of Object.entries(data)) {
    if (k === 'detail' || k === 'non_field_errors') continue;
    if (v && typeof v === 'object' && !Array.isArray(v)) {
      for (const [k2, v2] of Object.entries(v)) out[k2] = flatten(v2);  // nested e.g. {profile: {...}}
    }
    out[k] = flatten(v);
  }
  return out;
}

/** Turn a plain object into FormData (for uploads). Empty values and null files are skipped. */
export function toFormData(values) {
  const fd = new FormData();
  Object.entries(values).forEach(([k, v]) => {
    if (v === undefined || v === null || v === '') return;
    if (typeof v === 'object' && !(v instanceof File) && !(v instanceof Blob)) fd.append(k, JSON.stringify(v));
    else fd.append(k, v);
  });
  return fd;
}

/** Download a protected file (the API needs the JWT, so a normal link would not work). */
export async function downloadFile(path, fallbackName = 'download') {
  const url = path.startsWith('http') ? path : `${API_ORIGIN}${path}`;
  const response = await api.get(url, { responseType: 'blob' });
  const disposition = response.headers['content-disposition'] || '';
  const match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(disposition);
  const name = match ? decodeURIComponent(match[1]) : fallbackName;
  const href = URL.createObjectURL(response.data);
  const a = document.createElement('a');
  a.href = href;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(href), 1000);
}

export default api;
