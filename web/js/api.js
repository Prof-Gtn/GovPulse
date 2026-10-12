// GovPulse — Shared API client
// Talks to the FastAPI backend at http://localhost:8000

const API_BASE = "http://localhost:8000";


// -----------------------------------------------------------------
// TOKEN MANAGEMENT
// -----------------------------------------------------------------
function saveToken(token, user) {
    localStorage.setItem("govpulse_token", token);
    localStorage.setItem("govpulse_user", JSON.stringify(user));
}

function getToken() {
    return localStorage.getItem("govpulse_token");
}

function getUser() {
    const userStr = localStorage.getItem("govpulse_user");
    return userStr ? JSON.parse(userStr) : null;
}

function clearSession() {
    localStorage.removeItem("govpulse_token");
    localStorage.removeItem("govpulse_user");
}

function isLoggedIn() {
    return !!getToken();
}


// -----------------------------------------------------------------
// FETCH WRAPPER
// -----------------------------------------------------------------
async function apiFetch(path, options = {}) {
    const headers = {
        "Content-Type": "application/json",
        ...(options.headers || {}),
    };

    const token = getToken();
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers,
    });

    // If token expired, force logout
    if (response.status === 401) {
        clearSession();
        window.location.href = "login.html";
        throw new Error("Session expired");
    }

    return response;
}


// -----------------------------------------------------------------
// AUTH
// -----------------------------------------------------------------
async function login(username, password) {
    const r = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
    });

    if (!r.ok) {
        const err = await r.json();
        throw new Error(err.detail || "Login failed");
    }

    const data = await r.json();
    saveToken(data.access_token, {
        username,
        name: data.name,
        role: data.role,
        ministry: data.ministry,
    });
    return data;
}


// -----------------------------------------------------------------
// GUARDS
// -----------------------------------------------------------------
function requireLogin() {
    if (!isLoggedIn()) {
        window.location.href = "login.html";
        return false;
    }
    return true;
}

function logout() {
    clearSession();
    window.location.href = "login.html";
}