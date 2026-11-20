/**
 * Cliente API – Consultoría Médica
 */
const API_BASE = "";  // mismo origen (FastAPI sirve el frontend)

function getToken() {
  return localStorage.getItem("token");
}

function getUsuario() {
  const raw = localStorage.getItem("usuario");
  return raw ? JSON.parse(raw) : null;
}

function setSession(token, usuario) {
  localStorage.setItem("token", token);
  localStorage.setItem("usuario", JSON.stringify(usuario));
}

function clearSession() {
  localStorage.removeItem("token");
  localStorage.removeItem("usuario");
}

function requireAuth() {
  if (!getToken()) {
    window.location.href = "/login";
    return false;
  }
  return true;
}

async function api(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(API_BASE + path, {
    ...options,
    headers,
  });

  let data = null;
  const text = await res.text();
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { detail: text };
  }

  if (!res.ok) {
    const msg = data?.detail || data?.message || `Error ${res.status}`;
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return data;
}

// Auth
async function registro(payload) {
  return api("/api/auth/registro", { method: "POST", body: JSON.stringify(payload) });
}

async function login(email, password) {
  const data = await api("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setSession(data.access_token, data.usuario);
  return data;
}

async function me() {
  return api("/api/auth/me");
}

// Citas
async function crearCita(payload) {
  return api("/api/citas", { method: "POST", body: JSON.stringify(payload) });
}

async function misCitas() {
  return api("/api/citas/mias");
}

async function actualizarEstadoCita(id, estado) {
  return api(`/api/citas/${id}/estado`, {
    method: "PATCH",
    body: JSON.stringify({ estado }),
  });
}

// Bot
async function botChat(message, sessionId) {
  return api("/api/bot/chat", {
    method: "POST",
    body: JSON.stringify({ message, session_id: sessionId }),
  });
}

// Visión
async function estadoIdentidad() {
  return api("/api/vision/estado-identidad");
}
