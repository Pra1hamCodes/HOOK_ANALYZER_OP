/* ═══════════════════════════════════════════════════════════
   Hook Architect — Auth JS
   Form validation, password strength, stub auth
   ═══════════════════════════════════════════════════════════ */

(function () {
    'use strict';

    const API = window.location.origin;

    // ── Toast helper ──────────────────────────────────────
    function showToast(message, type = 'info', duration = 4000) {
        const container = document.getElementById('toast-container');
        if (!container) return;
        const toast = document.createElement('div');
        toast.className = `toast toast--${type}`;
        toast.textContent = message;
        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(-10px)';
            toast.style.transition = 'all 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }

    // ── Password Strength ─────────────────────────────────
    function getPasswordStrength(password) {
        let score = 0;
        if (password.length >= 6) score++;
        if (password.length >= 10) score++;
        if (/[A-Z]/.test(password) && /[a-z]/.test(password)) score++;
        if (/\d/.test(password)) score++;
        if (/[^A-Za-z0-9]/.test(password)) score++;
        return Math.min(score, 4);
    }

    function updatePasswordStrength(password) {
        const strengthEl = document.querySelector('.password-strength');
        const labelEl = document.querySelector('.password-strength__label');
        if (!strengthEl || !labelEl) return;

        const strength = getPasswordStrength(password);
        strengthEl.setAttribute('data-strength', strength);

        const bars = strengthEl.querySelectorAll('.password-strength__bar');
        bars.forEach((bar, i) => {
            bar.classList.toggle('active', i < strength);
        });

        const labels = ['', 'Weak', 'Fair', 'Strong', 'Excellent'];
        labelEl.textContent = password ? labels[strength] || '' : '';
    }

    // ── Form Validation ───────────────────────────────────
    function showError(inputId, message) {
        const input = document.getElementById(inputId);
        const errorEl = input?.parentElement?.querySelector('.input-error');
        if (input) input.classList.add('input--error');
        if (errorEl) {
            errorEl.textContent = message;
            errorEl.classList.add('visible');
        }
    }

    function clearError(inputId) {
        const input = document.getElementById(inputId);
        const errorEl = input?.parentElement?.querySelector('.input-error');
        if (input) input.classList.remove('input--error');
        if (errorEl) errorEl.classList.remove('visible');
    }

    function clearAllErrors(form) {
        form.querySelectorAll('.input--error').forEach(el => el.classList.remove('input--error'));
        form.querySelectorAll('.input-error').forEach(el => el.classList.remove('visible'));
    }

    // ── Login Form ────────────────────────────────────────
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            clearAllErrors(loginForm);

            const email = document.getElementById('login-email').value.trim();
            const password = document.getElementById('login-password').value;

            let valid = true;
            if (!email) { showError('login-email', 'Email is required'); valid = false; }
            else if (!/\S+@\S+\.\S+/.test(email)) { showError('login-email', 'Enter a valid email'); valid = false; }
            if (!password) { showError('login-password', 'Password is required'); valid = false; }

            if (!valid) return;

            const btn = loginForm.querySelector('.auth-submit .btn');
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Logging in...';

            try {
                // Try to find profile by email or use first available profile
                const res = await fetch(`${API}/api/profiles`);
                const profiles = await res.json();
                
                if (profiles.length > 0) {
                    const profile = profiles[0];
                    localStorage.setItem('hookArchitect_profileId', profile.id);
                    localStorage.setItem('hookArchitect_user', JSON.stringify({
                        id: profile.id,
                        username: profile.username,
                        email: email,
                        niche: profile.niche
                    }));
                    showToast('Welcome back!', 'success');
                    setTimeout(() => { window.location.href = '/dashboard'; }, 500);
                } else {
                    showToast('No account found. Please sign up first.', 'warning');
                    setTimeout(() => { window.location.href = '/signup'; }, 1500);
                }
            } catch (err) {
                showToast('Login failed: ' + err.message, 'error');
            } finally {
                btn.disabled = false;
                btn.textContent = 'Sign In';
            }
        });
    }

    // ── Signup Form ───────────────────────────────────────
    const signupForm = document.getElementById('signup-form');
    if (signupForm) {
        // Password strength listener
        const passwordInput = document.getElementById('signup-password');
        if (passwordInput) {
            passwordInput.addEventListener('input', (e) => {
                updatePasswordStrength(e.target.value);
                clearError('signup-password');
            });
        }

        // Clear errors on input
        signupForm.querySelectorAll('.input').forEach(input => {
            input.addEventListener('input', () => clearError(input.id));
        });

        signupForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            clearAllErrors(signupForm);

            const username = document.getElementById('signup-username').value.trim();
            const email = document.getElementById('signup-email').value.trim();
            const password = document.getElementById('signup-password').value;
            const confirm = document.getElementById('signup-confirm').value;
            const niche = document.getElementById('signup-niche').value;

            let valid = true;
            if (!username || username.length < 2) { showError('signup-username', 'Username must be at least 2 characters'); valid = false; }
            if (!email) { showError('signup-email', 'Email is required'); valid = false; }
            else if (!/\S+@\S+\.\S+/.test(email)) { showError('signup-email', 'Enter a valid email'); valid = false; }
            if (!password || password.length < 6) { showError('signup-password', 'Password must be at least 6 characters'); valid = false; }
            if (password !== confirm) { showError('signup-confirm', 'Passwords do not match'); valid = false; }

            if (!valid) return;

            const btn = signupForm.querySelector('.auth-submit .btn');
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Creating account...';

            try {
                const res = await fetch(`${API}/api/profiles`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, niche })
                });
                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.detail || 'Signup failed');
                }
                const profile = await res.json();
                localStorage.setItem('hookArchitect_profileId', profile.id);
                localStorage.setItem('hookArchitect_user', JSON.stringify({
                    id: profile.id,
                    username: profile.username,
                    email: email,
                    niche: profile.niche
                }));
                showToast('Account created! Welcome to Hook Architect.', 'success');
                setTimeout(() => { window.location.href = '/dashboard'; }, 600);
            } catch (err) {
                showToast('Signup failed: ' + err.message, 'error');
            } finally {
                btn.disabled = false;
                btn.textContent = 'Create Account';
            }
        });
    }

})();
