// src/context/AuthContext.jsx
// Holds: token, user, shop, loading + login / signup / logout / saveShop.
// On page refresh it restores the session from the saved token (GET /api/auth/me, then GET /api/shop).
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { apiFetch, SESSION_EXPIRED_EVENT, TOKEN_KEY } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState(null);
  const [shop, setShop] = useState(null);
  const [loading, setLoading] = useState(true);       // true until the first session check is finished

  const clearSession = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
    setShop(null);
  }, []);

  // apiFetch fires this event when the server answers 401 (expired or invalid token)
  useEffect(() => {
    const onExpired = () => {
      setToken(null);
      setUser(null);
      setShop(null);
    };
    window.addEventListener(SESSION_EXPIRED_EVENT, onExpired);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired);
  }, []);

  // Load the user and the shop. A 404 on /shop only means "not set up yet" (new user).
  const bootstrap = useCallback(async () => {
    try {
      const me = await apiFetch("/api/auth/me");
      setUser(me);
      try {
        setShop(await apiFetch("/api/shop"));
      } catch (e) {
        if (e.status === 404) setShop(null);
        else throw e;
      }
    } catch (e) {
      if (e.status === 401) clearSession();            // expired or invalid token
      // other errors (server down): keep the token, the app shows its own error states
    }
  }, [clearSession]);

  useEffect(() => {
    if (!localStorage.getItem(TOKEN_KEY)) {
      setLoading(false);
      return;
    }
    bootstrap().finally(() => setLoading(false));
  }, [bootstrap]);

  // The backend may name the token field access_token or accessToken - accept both.
  const storeToken = (data) => {
    const t = data?.accessToken ?? data?.access_token ?? data?.token;
    if (!t) throw new Error("Login response did not contain a token");
    localStorage.setItem(TOKEN_KEY, t);
    setToken(t);
  };

  const login = async (email, password) => {
    const data = await apiFetch("/api/auth/login", { method: "POST", body: { email, password } });
    storeToken(data);
    await bootstrap();
  };

  // body = exactly what your signup endpoint expects, e.g. { fullName, email, password }
  const signup = async (body) => {
    const data = await apiFetch("/api/auth/signup", { method: "POST", body });
    if (data && (data.accessToken || data.access_token || data.token)) {
      storeToken(data);                                  // signup already logs in
      await bootstrap();
    } else {
      await login(body.email, body.password);            // otherwise log in right after signup
    }
  };

  const logout = () => clearSession();

  // Create the shop the first time, update it afterwards
  const saveShop = async (data) => {
    const saved = await apiFetch("/api/shop", { method: shop ? "PUT" : "POST", body: data });
    setShop(saved);
    return saved;
  };

  const value = useMemo(
    () => ({ token, user, shop, loading, login, signup, logout, saveShop, refreshShop: bootstrap }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [token, user, shop, loading, bootstrap]
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
