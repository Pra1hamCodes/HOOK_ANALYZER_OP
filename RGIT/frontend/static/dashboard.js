/* ═══════════════════════════════════════════════════════════
   Hook Architect — Dashboard JS
   Profile loading, upload flow, recent analyses, sidebar
   ═══════════════════════════════════════════════════════════ */

(function () {
    'use strict';

    const API = window.location.origin;
    const $ = id => document.getElementById(id);

    // ── State ─────────────────────────────────────────────
    let profileId = localStorage.getItem('hookArchitect_profileId') || null;
    let user = null;
    let currentJobId = null;
    let uploadedFile = null;
    let activeWs = null;
    let pollTimer = null;

    try {
        user = JSON.parse(localStorage.getItem('hookArchitect_user'));
    } catch (e) {}

    // ── Toast ─────────────────────────────────────────────
    function showToast(message, type = 'info', duration = 4000) {
        const container = $('toast-container');
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

    // ── Time of day greeting ──────────────────────────────
    function getGreeting() {
        const hour = new Date().getHours();
        if (hour < 12) return 'Good morning';
        if (hour < 17) return 'Good afternoon';
        return 'Good evening';
    }

    // ── Initialize ────────────────────────────────────────
    async function init() {
        // If no profile, redirect to signup
        if (!profileId && !user) {
            // Allow viewing but show minimal UI
        }

        // Update sidebar user info
        loadUserInfo();

        // Load recent analyses
        await loadRecentAnalyses();

        // Setup event listeners
        setupUpload();
        setupSidebar();
    }

    function loadUserInfo() {
        const username = user?.username || 'Guest';
        const niche = user?.niche || 'No profile';
        const initial = username.charAt(0).toUpperCase();

        $('sidebar-avatar').textContent = initial;
        $('sidebar-username').textContent = username;
        $('sidebar-niche').textContent = niche;
        $('main-greeting').textContent = `${getGreeting()}, ${username} 👋`;

        if (profileId) {
            $('main-sub-greeting').textContent = 'Upload a video to analyze its retention performance.';
        }
    }

    // ── Recent Analyses ───────────────────────────────────
    async function loadRecentAnalyses() {
        if (!profileId) return;

        try {
            const res = await fetch(`${API}/api/profiles/${profileId}/ledger`);
            const data = await res.json();
            const ledger = data.ledger || [];

            // Update stats
            updateStats(ledger, data.total_videos);

            if (ledger.length === 0) return;

            // Update sub-greeting
            const latest = ledger[0];
            $('main-sub-greeting').textContent =
                `Your last analysis: ${latest.filename || 'video'} — ${latest.overall_score?.toFixed(0) || '?'}/100`;

            // Render recent cards (last 5)
            renderRecentCards(ledger.slice(0, 5));
        } catch (e) {
            console.error('Failed to load ledger:', e);
        }
    }

    function updateStats(ledger, totalVideos) {
        $('stat-value-0').textContent = totalVideos || 0;

        if (ledger.length > 0) {
            const avgScore = ledger.reduce((s, e) => s + (e.overall_score || 0), 0) / ledger.length;
            $('stat-value-1').textContent = avgScore.toFixed(0);

            // Best hook score (use overall_score as proxy since hook_score may not be in ledger)
            const bestScore = Math.max(...ledger.map(e => e.overall_score || 0));
            $('stat-value-2').textContent = bestScore.toFixed(0);

            // Count total red zones
            const totalRed = ledger.reduce((s, e) => {
                const zones = e.zone_distribution || {};
                return s + (zones.red || 0);
            }, 0);
            $('stat-value-3').textContent = totalRed;
        }
    }

    function renderRecentCards(entries) {
        const grid = $('recent-grid');
        if (!grid || entries.length === 0) return;

        grid.innerHTML = entries.map((entry, i) => {
            const score = entry.overall_score?.toFixed(0) || '0';
            const scoreClass = score >= 75 ? 'green' : (score >= 45 ? 'yellow' : 'red');
            const date = new Date(entry.uploaded_at * 1000).toLocaleDateString('en-US', {
                month: 'short', day: 'numeric'
            });
            const duration = entry.duration?.toFixed(0) || '—';
            const zones = entry.zone_distribution || {};
            const total = (zones.green || 0) + (zones.yellow || 0) + (zones.red || 0) || 1;
            const greenPct = ((zones.green || 0) / total * 100).toFixed(0);
            const yellowPct = ((zones.yellow || 0) / total * 100).toFixed(0);
            const redPct = ((zones.red || 0) / total * 100).toFixed(0);

            return `
            <div class="analysis-card" onclick="window.location.href='/old'" data-index="${i}">
                <div class="analysis-card__header">
                    <div class="analysis-card__name">${entry.filename || 'Video'}</div>
                    <div class="score-badge score-badge--${scoreClass}">${score}</div>
                </div>
                <div class="analysis-card__meta">
                    <span class="analysis-card__date">📅 ${date}</span>
                    <span class="analysis-card__duration">⏱ ${duration}s</span>
                </div>
                <div class="analysis-card__zone-bar">
                    <div class="analysis-card__zone-fill analysis-card__zone-fill--green" style="width:${greenPct}%"></div>
                    <div class="analysis-card__zone-fill analysis-card__zone-fill--yellow" style="width:${yellowPct}%"></div>
                    <div class="analysis-card__zone-fill analysis-card__zone-fill--red" style="width:${redPct}%"></div>
                </div>
                <div class="analysis-card__footer">
                    <span class="analysis-card__action">View Report →</span>
                </div>
            </div>`;
        }).join('');
    }

    // ── Upload Flow ───────────────────────────────────────
    function setupUpload() {
        const dropzone = $('upload-dropzone');
        const fileInput = $('file-input');
        const startBtn = $('btn-start-upload');

        if (!dropzone || !fileInput) return;

        dropzone.addEventListener('click', () => fileInput.click());
        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('drag-over');
        });
        dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag-over'));
        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('drag-over');
            if (e.dataTransfer.files[0]) selectFile(e.dataTransfer.files[0]);
        });
        fileInput.addEventListener('change', (e) => {
            if (e.target.files[0]) selectFile(e.target.files[0]);
        });

        if (startBtn) {
            startBtn.addEventListener('click', () => {
                if (uploadedFile) startUpload(uploadedFile);
            });
        }
    }

    function selectFile(file) {
        uploadedFile = file;
        const dropzone = $('upload-dropzone');
        const startBtn = $('btn-start-upload');
        dropzone.querySelector('.upload-dropzone__title').textContent = file.name;
        dropzone.querySelector('.upload-dropzone__hint').textContent =
            `${(file.size / (1024 * 1024)).toFixed(1)} MB — Ready to analyze`;
        if (startBtn) startBtn.disabled = false;
    }

    async function startUpload(file) {
        const uploadCard = $('upload-card');
        const progressTracker = $('progress-tracker');
        const startBtn = $('btn-start-upload');

        if (startBtn) {
            startBtn.disabled = true;
            startBtn.innerHTML = '<span class="spinner"></span> Uploading...';
        }

        try {
            const formData = new FormData();
            formData.append('file', file);
            if (profileId) formData.append('user_id', profileId);
            const platform = $('platform-select')?.value || 'generic';
            formData.append('platform', platform);

            const res = await fetch(`${API}/api/upload`, { method: 'POST', body: formData });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Upload failed');
            }
            const data = await res.json();
            currentJobId = data.job_id;

            // Show progress tracker
            uploadCard.style.display = 'none';
            progressTracker.classList.add('active');

            // Connect for progress
            connectWebSocket(data.job_id);
            startPolling(data.job_id);
        } catch (err) {
            showToast('Upload error: ' + err.message, 'error');
            if (startBtn) {
                startBtn.disabled = false;
                startBtn.textContent = 'Start Analysis →';
            }
        }
    }

    function updateProgress(pct, message) {
        const fill = $('progress-fill');
        const pctEl = $('progress-pct');
        const msgEl = $('progress-msg');
        if (fill) fill.style.width = `${pct}%`;
        if (pctEl) pctEl.textContent = `${Math.round(pct)}%`;
        if (msgEl) msgEl.textContent = message;
    }

    function connectWebSocket(jobId) {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws/jobs/${jobId}`);
        activeWs = ws;
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            updateProgress(data.progress || 0, data.message || '');
            if (data.status === 'complete') {
                ws.close();
                activeWs = null;
                onAnalysisComplete(jobId);
            } else if (data.status === 'failed') {
                ws.close();
                activeWs = null;
                updateProgress(0, `❌ Failed: ${data.message}`);
                showToast('Analysis failed: ' + data.message, 'error');
            }
        };
        ws.onerror = () => {};
        ws.onclose = () => { activeWs = null; };
    }

    function startPolling(jobId) {
        const poll = async () => {
            if (currentJobId !== jobId) return;
            try {
                const res = await fetch(`${API}/api/jobs/${jobId}/status`);
                const data = await res.json();
                updateProgress(data.progress || 0, data.message || '');
                if (data.status === 'complete') {
                    onAnalysisComplete(jobId);
                    return;
                }
                if (data.status === 'failed') {
                    updateProgress(0, `❌ Failed: ${data.message}`);
                    return;
                }
            } catch (e) {}
            pollTimer = setTimeout(poll, 2000);
        };
        poll();
    }

    function onAnalysisComplete(jobId) {
        if (pollTimer) { clearTimeout(pollTimer); pollTimer = null; }
        showToast('Analysis complete! Redirecting...', 'success');
        // Redirect to analysis page (using old UI for now since analysis.html is coming next)
        setTimeout(() => {
            window.location.href = `/dashboard/analysis/${jobId}`;
        }, 800);
    }

    // ── Sidebar ───────────────────────────────────────────
    function setupSidebar() {
        const hamburger = $('hamburger');
        const sidebar = $('sidebar');
        const overlay = $('sidebar-overlay');

        if (hamburger) {
            hamburger.addEventListener('click', () => {
                sidebar.classList.toggle('open');
                overlay.classList.toggle('open');
            });
        }

        if (overlay) {
            overlay.addEventListener('click', () => {
                sidebar.classList.remove('open');
                overlay.classList.remove('open');
            });
        }

        // Logout
        $('btn-sidebar-logout')?.addEventListener('click', () => {
            localStorage.removeItem('hookArchitect_profileId');
            localStorage.removeItem('hookArchitect_user');
            window.location.href = '/';
        });

        // New Analysis button scrolls to upload
        $('btn-new-analysis')?.addEventListener('click', () => {
            const uploadCard = $('upload-card');
            if (uploadCard) {
                uploadCard.style.display = '';
                $('progress-tracker')?.classList.remove('active');
                uploadCard.scrollIntoView({ behavior: 'smooth' });
            }
            // Close mobile sidebar
            sidebar?.classList.remove('open');
            overlay?.classList.remove('open');
        });

        // Evolution Ledger (redirect to old UI for now)
        $('btn-ledger')?.addEventListener('click', () => {
            window.location.href = '/old';
        });
    }

    // ── Init ──────────────────────────────────────────────
    init();

})();
