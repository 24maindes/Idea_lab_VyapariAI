// src/api/client.js
// The ONLY place that talks to the backend. Every page uses apiFetch(...).
//  - base URL from VITE_API_URL (default http://127.0.0.1:8000)
//  - attaches the Bearer token saved at login
//  - throws Error(message) with the server's "detail" text; error.status holds the HTTP code

const BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
export const TOKEN_KEY = "vyapariToken";
export const SESSION_MESSAGE_KEY = "vyapariSessionMessage";
export const SESSION_EXPIRED_EVENT = "vyapari-session-expired";

// login / signup return 401 for wrong credentials: that is NOT an expired session
const AUTH_PATHS = ["/api/auth/login", "/api/auth/signup"];

// FastAPI sends detail as a string (our own errors) or as a list (validation errors, 422)
function readableError(detail, fallback) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) {
    return detail
      .map((d) => {
        const field = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : "";
        return field && field !== "body" ? `${field}: ${d.msg}` : d.msg;
      })
      .join("; ");
  }
  return fallback;
}

/**
 * apiFetch("/api/shop")                                  -> GET
 * apiFetch("/api/shop", { method: "POST", body: {...} })  -> body is a plain object, sent as JSON
 */
export async function apiFetch(path, { method = "GET", body, headers = {} } = {}) {
  const token = localStorage.getItem(TOKEN_KEY);
  const options = {
    method,
    headers: {
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
  };
  if (body !== undefined) options.body = JSON.stringify(body);

  let res;
  try {
    res = await fetch(`${BASE_URL}${path}`, options);
  } catch {
    // network down / server not running / CORS blocked
    throw Object.assign(new Error("Cannot reach the server. Is the backend running?"), { status: 0 });
  }

  if (res.status === 204) return null;
  let data = null;
  try {
    data = await res.json();
  } catch {
    /* empty or non-JSON body */
  }

  if (res.status === 401 && token && !AUTH_PATHS.some((p) => path.startsWith(p))) {
    // the saved token is no longer valid: forget it and tell AuthContext, which sends the user to /login
    sessionStorage.setItem(SESSION_MESSAGE_KEY, "Session expired, please log in again.");
    localStorage.removeItem(TOKEN_KEY);
    window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
  }

  if (!res.ok) {
    throw Object.assign(new Error(readableError(data?.detail, `Request failed (${res.status})`)), { status: res.status });
  }
  return data;
}
