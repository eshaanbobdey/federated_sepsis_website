/* ============================================
   FedSepsis — Frontend JavaScript
   ============================================ */

// ---- Configuration ----
const CONFIG = {
  // Replace with your actual Google Client ID from Google Cloud Console
  GOOGLE_CLIENT_ID: '345679535396-qa195u4rclok1b4he866p8fmu28fujb8.apps.googleusercontent.com',
  API_BASE: '',  // Same origin
};

// ---- Auth Helpers ----

function getToken() {
  return localStorage.getItem('fedsepsis_token');
}

function setToken(token) {
  localStorage.setItem('fedsepsis_token', token);
}

function getUser() {
  const raw = localStorage.getItem('fedsepsis_user');
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function setUser(user) {
  localStorage.setItem('fedsepsis_user', JSON.stringify(user));
}

function clearAuth() {
  localStorage.removeItem('fedsepsis_token');
  localStorage.removeItem('fedsepsis_user');
}

function logout() {
  clearAuth();
  window.location.href = '/';
}

/**
 * Auth guard: redirects if not authenticated or wrong role.
 * Call at top of dashboard/admin pages.
 */
function requireAuth(requiredRole) {
  const token = getToken();
  const user = getUser();

  if (!token || !user) {
    window.location.href = '/';
    return;
  }

  if (requiredRole && user.role !== requiredRole) {
    // Wrong role — redirect to their correct page
    if (user.role === 'admin') {
      window.location.href = '/admin.html';
    } else {
      window.location.href = '/dashboard.html';
    }
    return;
  }

  // Also verify token with server (async, non-blocking)
  apiGet('/api/auth/me')
    .then(data => {
      if (!data.user) {
        clearAuth();
        window.location.href = '/';
      } else {
        // Update cached user in case role changed
        setUser(data.user);
      }
    })
    .catch(() => {
      clearAuth();
      window.location.href = '/';
    });
}


// ---- API Helpers ----

async function apiGet(path) {
  const token = getToken();
  const res = await fetch(`${CONFIG.API_BASE}${path}`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

async function apiPost(path, body) {
  const token = getToken();
  const res = await fetch(`${CONFIG.API_BASE}${path}`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

async function apiDelete(path) {
  const token = getToken();
  const res = await fetch(`${CONFIG.API_BASE}${path}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }

  return res.json();
}


// ---- Toast Notification System ----

function showToast(type, title, message, duration = 5000) {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const icons = {
    success: '✓',
    error: '✕',
    info: 'ℹ',
    warning: '⚠',
  };

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <div class="toast-icon">${icons[type] || 'ℹ'}</div>
    <div class="toast-content">
      <h4>${title}</h4>
      <p>${message}</p>
    </div>
  `;

  container.appendChild(toast);

  // Auto-remove
  setTimeout(() => {
    toast.classList.add('toast-out');
    setTimeout(() => toast.remove(), 300);
  }, duration);
}


// ---- Formatting Utilities ----

function formatFileSize(bytes) {
  if (bytes == null || bytes === 0) return '—';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function formatDate(isoString) {
  if (!isoString) return '—';
  const d = new Date(isoString);
  const now = new Date();
  const diffMs = now - d;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: d.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
    hour: '2-digit',
    minute: '2-digit',
  });
}
