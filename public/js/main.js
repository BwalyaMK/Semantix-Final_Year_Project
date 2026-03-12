/**
 * Main JavaScript for Semantix
 * Handles common functionality across pages
 */

// API helper
const api = {
  async get(url) {
    const response = await fetch(url);
    return response.json();
  },

  async post(url, data) {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return response.json();
  },

  async delete(url) {
    const response = await fetch(url, { method: 'DELETE' });
    return response.json();
  }
};

// Check auth status and update UI
async function checkAuth() {
  try {
    const data = await api.get('/auth/me');
    const authSection = document.getElementById('authSection');

    if (data.authenticated && authSection) {
      authSection.innerHTML = `
                <span class="user-name">${data.user.name || data.user.email}</span>
                <button onclick="logout()" class="btn btn-outline">Logout</button>
            `;
    }
  } catch (error) {
    console.error('Auth check failed:', error);
  }
}

async function logout() {
  await api.post('/auth/logout');
  window.location.href = '/login.html';
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  checkAuth();

  // Handle quick topic buttons on home page
  document.querySelectorAll('.topic-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const query = btn.dataset.query;
      window.location.href = `/chat.html?q=${encodeURIComponent(query)}`;
    });
  });

  // Handle main search on home page only
  const homeSearchInput = document.getElementById('homeSearchInput');
  const homeSearchBtn = document.getElementById('homeSearchBtn');

  if (homeSearchBtn && homeSearchInput) {
    homeSearchBtn.addEventListener('click', () => {
      const query = homeSearchInput.value.trim();
      if (query) {
        window.location.href = `/chat.html?q=${encodeURIComponent(query)}`;
      }
    });

    homeSearchInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        homeSearchBtn.click();
      }
    });
  }
});

// Helper: Format authors
function formatAuthors(authors) {
  if (!authors || authors.length === 0) return 'Unknown authors';
  if (authors.length <= 3) return authors.join(', ');
  return `${authors.slice(0, 3).join(', ')} et al.`;
}

// Helper: Truncate text
function truncate(text, maxLength) {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength - 3) + '...';
}

// Helper: Get intent color class
function getIntentClass(intent) {
  const classes = {
    'software_engineering': 'software_engineering',
    'cloud': 'cloud',
    'devops': 'devops',
    'ai_ml': 'ai_ml',
    'general': 'general'
  };
  return classes[intent] || 'general';
}

// Helper: Format intent for display
function formatIntent(intent) {
  const names = {
    'software_engineering': 'Software Engineering',
    'cloud': 'Cloud',
    'devops': 'DevOps',
    'ai_ml': 'AI/ML',
    'general': 'General'
  };
  return names[intent] || intent;
}

// Export for use in other files
window.api = api;
window.formatAuthors = formatAuthors;
window.truncate = truncate;
window.getIntentClass = getIntentClass;
window.formatIntent = formatIntent;
