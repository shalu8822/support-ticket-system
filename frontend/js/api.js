/**
 * Thin wrapper around the Fetch API: attaches the JWT, talks JSON or
 * multipart/form-data, and redirects to login on an expired/invalid token.
 */
const API_BASE = window.API_BASE_URL || "http://127.0.0.1:8000";

const Auth = {
  getToken: () => localStorage.getItem("cst_token"),
  getRole: () => localStorage.getItem("cst_role"),
  setSession: (token, role) => {
    localStorage.setItem("cst_token", token);
    localStorage.setItem("cst_role", role);
  },
  clearSession: () => {
    localStorage.removeItem("cst_token");
    localStorage.removeItem("cst_role");
  },
  isLoggedIn: () => !!localStorage.getItem("cst_token"),
  requireLogin: () => {
    if (!Auth.isLoggedIn()) {
      window.location.href = "login.html";
    }
  },
  requireAdmin: () => {
    Auth.requireLogin();
    if (Auth.getRole() !== "admin") {
      window.location.href = "dashboard.html";
    }
  },
  logout: () => {
    Auth.clearSession();
    window.location.href = "login.html";
  },
};

/**
 * @param {string} path        e.g. "/tickets" or "/admin/users/3"
 * @param {object} options     { method, body, isForm, params }
 */
async function apiFetch(path, options = {}) {
  if (!Auth.isLoggedIn() && path !== "/login" && path !== "/register") {
    Auth.logout();
    return;
  }
  const { method = "GET", body, isForm = false, params } = options;

  let url = `${API_BASE}${path}`;
  if (params) {
    const query = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "")
    ).toString();
    if (query) url += `?${query}`;
  }

  const headers = {};
  const token = Auth.getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let fetchBody;
  if (body !== undefined) {
    if (isForm) {
      fetchBody = body; // caller passes a FormData instance directly
    } else {
      headers["Content-Type"] = "application/json";
      fetchBody = JSON.stringify(body);
    }
  }

  const response = await fetch(url, { method, headers, body: fetchBody });

  if (response.status === 401) {
    Auth.clearSession();
    window.location.href = "login.html";
    throw new Error("Session expired. Please log in again.");
  }

  if (response.status === 204) return null;

  let data = null;
  try {
    data = await response.json();
  } catch (_) {
    /* no JSON body (e.g. some error responses) */
  }

  if (!response.ok) {
    const message = (data && (data.detail || data.message)) || `Request failed (${response.status})`;
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }

  return data;
}

/** Login uses OAuth2's form-encoded username/password, not JSON. */
async function loginRequest(email, password) {
  const form = new URLSearchParams();
  form.append("username", email);
  form.append("password", password);

  const response = await fetch(`${API_BASE}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form,
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Login failed.");
  }
  return data;
}
