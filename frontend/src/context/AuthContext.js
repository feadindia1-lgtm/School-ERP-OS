import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  // null = checking, false = anonymous, object = authenticated
  const [user, setUser] = useState(null);
  const [tenant, setTenant] = useState(null);
  const [impersonation, setImpersonation] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const { data } = await api.get("/auth/session");
      setUser(data.user);
      setTenant(data.tenant || null);
      setImpersonation(data.impersonation || null);
      return data.user;
    } catch {
      setUser(false);
      setTenant(null);
      setImpersonation(null);
      return null;
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const login = async (email, password, tenant_slug) => {
    try {
      const { data } = await api.post("/auth/login", { email, password, tenant_slug: tenant_slug || null });
      setUser(data.user);
      setTenant(data.tenant || null);
      setImpersonation(data.impersonation || null);
      return { ok: true, user: data.user };
    } catch (e) {
      return { ok: false, error: formatApiError(e) };
    }
  };

  const registerSchool = async (payload) => {
    try {
      const { data } = await api.post("/auth/register-school", payload);
      setUser(data.user);
      setTenant(data.tenant || null);
      return { ok: true, user: data.user };
    } catch (e) {
      return { ok: false, error: formatApiError(e) };
    }
  };

  const logout = async () => {
    try { await api.post("/auth/logout"); } catch {}
    setUser(false); setTenant(null); setImpersonation(null);
  };

  const exitImpersonation = async () => {
    try {
      await api.post("/platform/impersonate/exit");
      await refresh();
      return { ok: true };
    } catch (e) {
      return { ok: false, error: formatApiError(e) };
    }
  };

  return (
    <AuthContext.Provider value={{ user, tenant, impersonation, login, logout, registerSchool, refresh, exitImpersonation, setUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
