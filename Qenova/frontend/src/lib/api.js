import axios from 'axios';

const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
export const api = axios.create({ baseURL });

// ---- JWT: attach access token to every request ---------------------------
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// ---- JWT: on 401, refresh once (single-flight) and retry ------------------
let refreshing = null;

function refreshAccessToken() {
  const refresh = localStorage.getItem('refresh');
  if (!refresh) return Promise.reject(new Error('No refresh token'));
  if (!refreshing) {
    // plain axios (not `api`) so this call does not go through the interceptors again
    refreshing = axios
      .post(`${baseURL}/auth/token/refresh/`, { refresh })
      .then((r) => {
        localStorage.setItem('access', r.data.access);
        if (r.data.refresh) localStorage.setItem('refresh', r.data.refresh); // rotation
        return r.data.access;
      })
      .finally(() => { refreshing = null; });
  }
  return refreshing;
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    const isAuthCall = original?.url?.includes('/auth/token');
    if (error.response?.status === 401 && original && !original._retry && !isAuthCall) {
      original._retry = true;
      try {
        const access = await refreshAccessToken();
        original.headers.Authorization = `Bearer ${access}`;
        return api(original);
      } catch {
        clearSession();
        if (location.pathname !== '/login') location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export const setTokens = (d) => {
  localStorage.setItem('access', d.access);
  localStorage.setItem('refresh', d.refresh);
};

function clearSession() {
  localStorage.removeItem('access');
  localStorage.removeItem('refresh');
}

// Blacklists the refresh token on the server, then clears the browser session.
export const logout = async () => {
  const refresh = localStorage.getItem('refresh');
  try { if (refresh) await axios.post(`${baseURL}/auth/logout/`, { refresh }); } catch { /* ignore */ }
  clearSession();
  location.href = '/login';
};
