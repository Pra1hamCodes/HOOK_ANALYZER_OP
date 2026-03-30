/* ═══════════════════════════════════════════════════════════
   Hook Architect — Profile Page JS
   Everything functional: weights, history, ledger, refs, chat
   ═══════════════════════════════════════════════════════════ */

(function () {
    'use strict';

    const API = window.location.origin;
    const $ = id => document.getElementById(id);

    // ── State ─────────────────────────────────────────────
    let profileId = localStorage.getItem('hookArchitect_profileId') || null;
    let user = null;
    let profile = null;
    let chatHistory = [];
    let lastJobId = null;

    try { user = JSON.parse(localStorage.getItem('hookArchitect_user')); } catch (e) {}

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

    // ── Init ──────────────────────────────────────────────
    async function init() {
        if (!profileId) {
            $('profile-loading').innerHTML = '<p style="color:var(--text-muted);">No profile found. <a href="/signup">Create one</a> or <a href="/login">log in</a>.</p>';
            return;
        }

        setupSidebar();
        setupTabs();
        await loadProfile();
    }

    // ── Load Profile ─────────────────────────────────────
    async function loadProfile() {
        try {
            const res = await fetch(`${API}/api/profiles/${profileId}`);
            if (!res.ok) throw new Error('Profile not found');
            profile = await res.json();

            // Fill sidebar
            const username = profile.username || 'User';
            const niche = profile.niche || 'general';
            const initial = username.charAt(0).toUpperCase();
            $('sidebar-avatar').textContent = initial;
            $('sidebar-username').textContent = username;
            $('sidebar-niche').textContent = niche;

            // Fill hero
            $('hero-avatar').textContent = initial;
            $('hero-name').textContent = username;
            $('hero-niche').textContent = niche;
            $('hero-video-count').textContent = `${profile.video_count || 0} videos`;
            $('hero-joined').textContent = `Joined ${new Date(profile.created_at * 1000).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}`;

            // Hide loading, show hero
            $('profile-loading').style.display = 'none';
            $('profile-hero').classList.add('loaded');

            // Fill overview
            fillOverview(profile);
            fillWeightsPreview(profile);
            fillWeightSliders(profile);

            // Load other tabs
            loadHistory();
            loadLedger();
            loadReferences();
            setupChat();
            setupActions();

        } catch (e) {
            $('profile-loading').innerHTML = `<p style="color:var(--danger);">Failed to load profile: ${e.message}</p>`;
        }
    }

    // ── Overview ──────────────────────────────────────────
    function fillOverview(p) {
        $('ov-total-videos').textContent = p.video_count || 0;
        $('ov-avg-score').textContent = p.avg_score ? p.avg_score.toFixed(0) : '—';
        $('ov-green-pct').textContent = p.green_zone_pct ? `${p.green_zone_pct.toFixed(0)}%` : '—';
    }

    function fillWeightsPreview(p) {
        const weights = {
            'Audio': p.audio_weight,
            'Visual': p.visual_weight,
            'Transcript': p.transcript_weight,
            'Song': p.song_weight,
            'Temporal': p.temporal_weight,
            'Engagement': p.engagement_weight,
        };
        const container = $('weights-preview');
        container.innerHTML = Object.entries(weights).map(([k, v]) =>
            `<div class="weight-preview-item"><span class="weight-preview-item__label">${k}</span><span class="weight-preview-item__value">${v !== undefined && v !== null ? v.toFixed(2) : '—'}</span></div>`
        ).join('');
    }

    // ── Weight Sliders ───────────────────────────────────
    const WEIGHT_DEFS = [
        { key: 'audio_weight', label: '🎵 Audio Weight', min: 0, max: 1, step: 0.05 },
        { key: 'visual_weight', label: '👁 Visual Weight', min: 0, max: 1, step: 0.05 },
        { key: 'transcript_weight', label: '📝 Transcript Weight', min: 0, max: 1, step: 0.05 },
        { key: 'song_weight', label: '🎶 Song Weight', min: 0, max: 1, step: 0.05 },
        { key: 'temporal_weight', label: '⏱ Temporal Weight', min: 0, max: 1, step: 0.05 },
        { key: 'engagement_weight', label: '🔥 Engagement Weight', min: 0, max: 1, step: 0.05 },
        { key: 'green_threshold', label: '🟢 Green Threshold', min: 0, max: 100, step: 1 },
        { key: 'yellow_threshold', label: '🟡 Yellow Threshold', min: 0, max: 100, step: 1 },
    ];

    function fillWeightSliders(p) {
        const container = $('weight-sliders');
        container.innerHTML = WEIGHT_DEFS.map(w => {
            const val = p[w.key] !== undefined && p[w.key] !== null ? p[w.key] : (w.max <= 1 ? 0.3 : 50);
            return `
            <div class="weight-slider-group">
                <div class="weight-slider-group__header">
                    <span class="weight-slider-group__label">${w.label}</span>
                    <span class="weight-slider-group__value" id="wv-${w.key}">${w.max <= 1 ? val.toFixed(2) : val.toFixed(0)}</span>
                </div>
                <input type="range" id="ws-${w.key}" min="${w.min}" max="${w.max}" step="${w.step}" value="${val}" data-key="${w.key}">
            </div>`;
        }).join('');

        // Live update value displays
        container.querySelectorAll('input[type="range"]').forEach(slider => {
            slider.addEventListener('input', () => {
                const key = slider.dataset.key;
                const def = WEIGHT_DEFS.find(w => w.key === key);
                const display = $(`wv-${key}`);
                display.textContent = def.max <= 1 ? parseFloat(slider.value).toFixed(2) : parseFloat(slider.value).toFixed(0);
            });
        });

        // Save weights
        $('btn-save-weights').addEventListener('click', async () => {
            const payload = {};
            WEIGHT_DEFS.forEach(w => {
                const slider = $(`ws-${w.key}`);
                if (slider) payload[w.key] = parseFloat(slider.value);
            });

            try {
                const res = await fetch(`${API}/api/profiles/${profileId}/weights`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });
                if (!res.ok) throw new Error((await res.json()).detail || 'Save failed');
                showToast('Weights saved successfully!', 'success');
                // Refresh
                const updated = await res.json();
                fillWeightsPreview(updated);
            } catch (e) {
                showToast('Failed to save: ' + e.message, 'error');
            }
        });

        // Reset weights
        $('btn-reset-weights').addEventListener('click', async () => {
            if (!confirm('Reset weights to your niche preset?')) return;
            const niche = profile?.niche || 'vlog';
            try {
                const presetsRes = await fetch(`${API}/api/presets`);
                const presets = await presetsRes.json();
                const preset = presets.find(p => p.niche === niche) || presets[0];
                if (preset && preset.weights) {
                    const res = await fetch(`${API}/api/profiles/${profileId}/weights`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(preset.weights),
                    });
                    if (!res.ok) throw new Error('Reset failed');
                    showToast('Weights reset to preset!', 'success');
                    await loadProfile();
                }
            } catch (e) {
                showToast('Reset failed: ' + e.message, 'error');
            }
        });
    }

    // ── History ───────────────────────────────────────────
    async function loadHistory() {
        try {
            const res = await fetch(`${API}/api/profiles/${profileId}/history`);
            const data = await res.json();
            const videos = data.videos || [];

            if (videos.length === 0) return;

            // Store last job_id for chat
            if (videos[0]?.job_id) lastJobId = videos[0].job_id;

            const container = $('history-list');
            container.innerHTML = videos.map(v => {
                const score = v.overall_score?.toFixed(0) || '0';
                const scoreClass = score >= 75 ? 'green' : (score >= 45 ? 'yellow' : 'red');
                const date = v.uploaded_at ? new Date(v.uploaded_at * 1000).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '';
                const dur = v.duration ? `${v.duration.toFixed(0)}s` : '';
                const zones = v.zone_distribution || {};
                const total = (zones.green || 0) + (zones.yellow || 0) + (zones.red || 0) || 1;
                return `
                <div class="history-item">
                    <div class="history-item__score"><span class="score-badge score-badge--${scoreClass}">${score}</span></div>
                    <div class="history-item__info">
                        <div class="history-item__name">${v.filename || 'Video'}</div>
                        <div class="history-item__meta">${date}${dur ? ' · ' + dur : ''}</div>
                    </div>
                    <div class="history-item__zones">
                        <div class="history-item__zone-fill history-item__zone-fill--green" style="width:${((zones.green||0)/total*100).toFixed(0)}%"></div>
                        <div class="history-item__zone-fill history-item__zone-fill--yellow" style="width:${((zones.yellow||0)/total*100).toFixed(0)}%"></div>
                        <div class="history-item__zone-fill history-item__zone-fill--red" style="width:${((zones.red||0)/total*100).toFixed(0)}%"></div>
                    </div>
                </div>`;
            }).join('');
        } catch (e) {
            console.error('History load error:', e);
        }
    }

    // ── Ledger ────────────────────────────────────────────
    async function loadLedger() {
        try {
            const res = await fetch(`${API}/api/profiles/${profileId}/ledger`);
            const data = await res.json();
            const ledger = data.ledger || [];

            if (ledger.length === 0) return;

            const container = $('ledger-list');
            container.innerHTML = ledger.map((e, i) => {
                const score = e.overall_score?.toFixed(0) || '?';
                const scoreClass = score >= 75 ? 'green' : (score >= 45 ? 'yellow' : 'red');
                const date = e.uploaded_at ? new Date(e.uploaded_at * 1000).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : '';
                const changes = e.weight_changes ? Object.entries(e.weight_changes).map(([k, v]) =>
                    `${k.replace('_weight', '')}: <strong>${v > 0 ? '+' : ''}${v.toFixed(2)}</strong>`
                ).join(', ') : 'no changes';

                return `
                <div class="ledger-item">
                    <div class="ledger-item__index">${ledger.length - i}</div>
                    <div class="ledger-item__info">
                        <div class="ledger-item__name">${e.filename || 'Video'}</div>
                        <div class="ledger-item__changes">${changes}</div>
                    </div>
                    <div class="ledger-item__score">
                        <div class="ledger-item__score-val"><span class="score-badge score-badge--${scoreClass}">${score}</span></div>
                        <div class="ledger-item__date">${date}</div>
                    </div>
                </div>`;
            }).join('');
        } catch (e) {
            console.error('Ledger load error:', e);
        }
    }

    // ── References ────────────────────────────────────────
    async function loadReferences() {
        try {
            const res = await fetch(`${API}/api/profiles/${profileId}/references`);
            const data = await res.json();

            // Baseline
            const baseline = data.baseline;
            const baselineEl = $('ref-baseline');
            if (baseline) {
                $('ov-ref-count').textContent = baseline.video_count || 0;
                baselineEl.innerHTML = `
                <div class="ref-baseline-card">
                    <h4>📐 Aggregated Baseline (${baseline.video_count || 0} videos)</h4>
                    <div class="ref-baseline-grid">
                        <div class="ref-baseline-stat"><div class="ref-baseline-stat__value">${(baseline.avg_overall_score||0).toFixed(0)}</div><div class="ref-baseline-stat__label">Avg Score</div></div>
                        <div class="ref-baseline-stat"><div class="ref-baseline-stat__value">${(baseline.avg_energy||0).toFixed(0)}</div><div class="ref-baseline-stat__label">Avg Energy</div></div>
                        <div class="ref-baseline-stat"><div class="ref-baseline-stat__value">${(baseline.avg_pacing||0).toFixed(0)}</div><div class="ref-baseline-stat__label">Avg Pacing</div></div>
                        <div class="ref-baseline-stat"><div class="ref-baseline-stat__value">${(baseline.avg_motion||0).toFixed(0)}</div><div class="ref-baseline-stat__label">Avg Motion</div></div>
                        <div class="ref-baseline-stat"><div class="ref-baseline-stat__value">${(baseline.avg_bpm||0).toFixed(0)}</div><div class="ref-baseline-stat__label">Avg BPM</div></div>
                        <div class="ref-baseline-stat"><div class="ref-baseline-stat__value">${(baseline.avg_emotion_alignment||0).toFixed(0)}</div><div class="ref-baseline-stat__label">Emotion Sync</div></div>
                    </div>
                </div>`;
            }

            // Individual refs
            const refs = data.reference_videos || [];
            if (refs.length > 0) {
                const container = $('ref-list');
                container.innerHTML = refs.map(r => `
                <div class="ref-card">
                    <div class="ref-card__name">${r.filename || 'Reference'}</div>
                    <div class="ref-card__meta">
                        <span>Score: <strong>${(r.overall_score||0).toFixed(0)}</strong></span>
                        <span>Nature: ${r.video_nature || '?'} · ${r.dominant_emotion || '?'}</span>
                        <span>BPM: ${(r.avg_bpm||0).toFixed(0)} · Energy: ${(r.avg_energy||0).toFixed(0)}</span>
                    </div>
                </div>`).join('');
            }

            // Upload reference button
            $('btn-upload-ref').addEventListener('click', () => $('ref-file-input').click());
            $('ref-file-input').addEventListener('change', async (e) => {
                if (!e.target.files[0]) return;
                await uploadReference(e.target.files[0]);
            });

            // Clear all references
            $('btn-clear-refs').addEventListener('click', async () => {
                if (!confirm('Delete all reference videos and baseline? This cannot be undone.')) return;
                try {
                    await fetch(`${API}/api/profiles/${profileId}/references`, { method: 'DELETE' });
                    showToast('References cleared', 'success');
                    loadReferences();
                } catch (e) {
                    showToast('Failed: ' + e.message, 'error');
                }
            });

        } catch (e) {
            console.error('References load error:', e);
        }
    }

    async function uploadReference(file) {
        const formData = new FormData();
        formData.append('file', file);

        const progress = $('ref-progress');
        const fill = $('ref-progress-fill');
        const msg = $('ref-progress-msg');
        progress.classList.add('active');
        fill.style.width = '10%';
        msg.textContent = 'Uploading reference video...';

        try {
            const res = await fetch(`${API}/api/profiles/${profileId}/references`, {
                method: 'POST', body: formData
            });
            if (!res.ok) throw new Error((await res.json()).detail || 'Upload failed');
            const data = await res.json();
            const jobId = data.job_id;

            // Poll for completion
            fill.style.width = '30%';
            msg.textContent = 'Processing reference video...';

            const poll = setInterval(async () => {
                try {
                    const statusRes = await fetch(`${API}/api/jobs/${jobId}/status`);
                    const status = await statusRes.json();
                    fill.style.width = `${status.progress || 30}%`;
                    msg.textContent = status.message || 'Processing...';

                    if (status.status === 'complete') {
                        clearInterval(poll);
                        fill.style.width = '100%';
                        msg.textContent = 'Reference processed!';
                        showToast('Reference video added!', 'success');
                        setTimeout(() => {
                            progress.classList.remove('active');
                            loadReferences();
                        }, 1000);
                    } else if (status.status === 'failed') {
                        clearInterval(poll);
                        progress.classList.remove('active');
                        showToast('Reference processing failed: ' + status.message, 'error');
                    }
                } catch (e) {}
            }, 2000);

        } catch (e) {
            progress.classList.remove('active');
            showToast('Upload failed: ' + e.message, 'error');
        }
    }

    // ── Chat ──────────────────────────────────────────────
    function setupChat() {
        const input = $('chat-input');
        const btn = $('btn-chat-send');
        if (!input || !btn) return;

        async function sendMessage() {
            const msg = input.value.trim();
            if (!msg) return;

            // Add user message
            appendChatMsg(msg, 'user');
            input.value = '';
            btn.disabled = true;

            // Load last job_id if not available
            if (!lastJobId) {
                try {
                    const hRes = await fetch(`${API}/api/profiles/${profileId}/history`);
                    const hData = await hRes.json();
                    if (hData.videos && hData.videos.length > 0) lastJobId = hData.videos[0].job_id;
                } catch (e) {}
            }

            if (!lastJobId) {
                appendChatMsg("I don't have any video analysis to reference yet. Analyze a video first, then come back to chat about it!", 'bot');
                btn.disabled = false;
                return;
            }

            // Call API
            try {
                const res = await fetch(`${API}/api/chat`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        message: msg,
                        job_id: lastJobId,
                        history: chatHistory.slice(-10),
                    }),
                });

                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.detail || 'Chat failed');
                }

                const data = await res.json();
                const reply = data.reply || "I couldn't generate a response. Please try again.";
                appendChatMsg(reply, 'bot');
                chatHistory.push({ role: 'user', content: msg });
                chatHistory.push({ role: 'assistant', content: reply });
            } catch (e) {
                appendChatMsg('Sorry, something went wrong: ' + e.message, 'bot');
            }

            btn.disabled = false;
        }

        btn.addEventListener('click', sendMessage);
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    }

    function appendChatMsg(text, role) {
        const container = $('chat-messages');
        const initial = user?.username?.charAt(0).toUpperCase() || '?';
        const div = document.createElement('div');
        div.className = `chat-msg chat-msg--${role === 'user' ? 'user' : 'bot'}`;
        div.innerHTML = `
            <div class="chat-msg__avatar">${role === 'user' ? initial : '🤖'}</div>
            <div class="chat-msg__body">${escapeHtml(text)}</div>`;
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    }

    function escapeHtml(text) {
        return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>');
    }

    // ── Actions ───────────────────────────────────────────
    function setupActions() {
        // Delete profile
        $('btn-delete-profile')?.addEventListener('click', async () => {
            if (!confirm('Permanently delete your profile and all data? This cannot be undone.')) return;
            try {
                const res = await fetch(`${API}/api/profiles/${profileId}`, { method: 'DELETE' });
                if (!res.ok) throw new Error('Delete failed');
                localStorage.removeItem('hookArchitect_profileId');
                localStorage.removeItem('hookArchitect_user');
                showToast('Profile deleted.', 'success');
                setTimeout(() => window.location.href = '/', 1000);
            } catch (e) {
                showToast('Delete failed: ' + e.message, 'error');
            }
        });

        // Edit niche
        $('btn-edit-niche')?.addEventListener('click', async () => {
            const niches = ['action', 'educational', 'emotional', 'vlog', 'cinematic', 'comedy', 'music'];
            const current = profile?.niche || 'vlog';
            const newNiche = prompt(`Enter new niche (current: ${current})\nOptions: ${niches.join(', ')}`, current);
            if (!newNiche || newNiche === current) return;
            if (!niches.includes(newNiche.toLowerCase())) {
                showToast('Invalid niche. Choose from: ' + niches.join(', '), 'warning');
                return;
            }
            // Update via weights endpoint with niche preset
            try {
                const presetsRes = await fetch(`${API}/api/presets`);
                const presets = await presetsRes.json();
                const preset = presets.find(p => p.niche === newNiche.toLowerCase());
                if (preset && preset.weights) {
                    await fetch(`${API}/api/profiles/${profileId}/weights`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(preset.weights),
                    });
                }
                showToast(`Niche updated to ${newNiche}!`, 'success');
                await loadProfile();
            } catch (e) {
                showToast('Update failed: ' + e.message, 'error');
            }
        });

        // Ledger button
        $('btn-ledger')?.addEventListener('click', () => {
            // Switch to ledger tab
            document.querySelector('[data-tab="ledger"]')?.click();
        });
    }

    // ── Tabs ──────────────────────────────────────────────
    function setupTabs() {
        const tabs = document.querySelectorAll('#profile-tabs .tab');
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
                const target = $(`tab-${tab.dataset.tab}`);
                if (target) target.classList.add('active');
            });
        });
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

        $('btn-sidebar-logout')?.addEventListener('click', () => {
            localStorage.removeItem('hookArchitect_profileId');
            localStorage.removeItem('hookArchitect_user');
            window.location.href = '/';
        });
    }

    // ── Start ─────────────────────────────────────────────
    init();

})();
