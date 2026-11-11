import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import api, { tokens } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const onLogout = () => setUser(null);
    window.addEventListener('sims:logout', onLogout);
    if (tokens.access) {
      api.get('/auth/me/')
        .then((r) => setUser(r.data))
        .catch(() => tokens.clear())
        .finally(() => setReady(true));
    } else {
      setReady(true);
    }
    return () => window.removeEventListener('sims:logout', onLogout);
  }, []);

  const signIn = useCallback((data) => {
    tokens.set(data.access, data.refresh);
    setUser(data.user);
    return data.user;
  }, []);

  const login = useCallback(async (username, password) => {
    const { data } = await api.post('/auth/login/', { username, password });
    return signIn(data);
  }, [signIn]);

  const register = useCallback(async (payload) => {
    const { data } = await api.post('/auth/register/', payload);
    return signIn(data);
  }, [signIn]);

  const logout = useCallback(async () => {
    try { await api.post('/auth/logout/', { refresh: tokens.refresh }); } catch { /* token already invalid */ }
    tokens.clear();
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    const { data } = await api.get('/auth/me/');
    setUser(data);
    return data;
  }, []);

  const value = useMemo(() => ({ user, ready, login, register, logout, refreshUser, setUser }),
    [user, ready, login, register, logout, refreshUser]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
