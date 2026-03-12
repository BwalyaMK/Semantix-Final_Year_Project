/**
 * Authentication Page JavaScript
 */

document.addEventListener('DOMContentLoaded', () => {
  const tabBtns = document.querySelectorAll('.tab-btn');
  const loginForm = document.getElementById('loginForm');
  const registerForm = document.getElementById('registerForm');

  // Tab switching
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tabBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      if (btn.dataset.tab === 'login') {
        loginForm.classList.add('active');
        registerForm.classList.remove('active');
      } else {
        registerForm.classList.add('active');
        loginForm.classList.remove('active');
      }
    });
  });

  // Login form
  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    const remember = document.getElementById('rememberMe').checked;
    const errorDiv = document.getElementById('loginError');

    try {
      const response = await fetch('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, remember })
      });

      const data = await response.json();

      if (data.success) {
        window.location.href = '/';
      } else {
        errorDiv.textContent = data.error || 'Login failed';
        errorDiv.classList.remove('hidden');
      }
    } catch (error) {
      errorDiv.textContent = 'An error occurred. Please try again.';
      errorDiv.classList.remove('hidden');
    }
  });

  // Register form
  registerForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const name = document.getElementById('registerName').value;
    const email = document.getElementById('registerEmail').value;
    const password = document.getElementById('registerPassword').value;
    const confirm = document.getElementById('confirmPassword').value;
    const errorDiv = document.getElementById('registerError');

    if (password !== confirm) {
      errorDiv.textContent = 'Passwords do not match';
      errorDiv.classList.remove('hidden');
      return;
    }

    try {
      const response = await fetch('/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, password })
      });

      const data = await response.json();

      if (data.success) {
        window.location.href = '/';
      } else {
        errorDiv.textContent = data.error || 'Registration failed';
        errorDiv.classList.remove('hidden');
      }
    } catch (error) {
      errorDiv.textContent = 'An error occurred. Please try again.';
      errorDiv.classList.remove('hidden');
    }
  });
});
