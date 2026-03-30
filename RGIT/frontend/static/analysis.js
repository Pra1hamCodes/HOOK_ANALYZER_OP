/* ═══════════════════════════════════════════════════════════
   Hook Architect — Analysis Results Page JS
   Fetches results, renders tabs, charts, heatmap, chat
   ═══════════════════════════════════════════════════════════ */

(function () {
    'use strict';

    const API = window.location.origin;
    const $ = id => document.getElementById(id);

    let result = null;
    let chatHistory = [];
    let retentionChart = null;
    let donutChart = null;
    let multiChart = null;
    let emotionChart = null;

    // ── Extract job_id from URL ───────────────────────────
    function getJobId() {
        const parts = window.location.pathname.split('/').filter(Boolean);
        // /dashboard/analysis/:job_id
        const idx = parts.indexOf('analysis');
        return idx >= 0 && parts[idx + 1] ? parts[idx + 1] : null;
    }

    // ── Toast ─────────────────────────────────────────────
    function showToast(msg, type = 'info', dur = 4000) {
        const c = $('toast-container');
        if (!c) return;
        const t = document.createElement('div');
        t.className = `toast toast--${type}`;
        t.textContent = msg;
        c.appendChild(t);
        setTimeout(() => { t.style.opacity = '0'; setTimeout(() => t.remove(), 300); }, dur);
    }

    // ── Tab Switcher ──────────────────────────────────────
    function setupTabs() {
        const tabs = document.querySelectorAll('.tab');
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                tabs.forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                tab.classList.add('active');
                const panel = $(`tab-${tab.dataset.tab}`);
                if (panel) panel.classList.add('active');
            });
        });
    }

    // ── Sidebar ───────────────────────────────────────────
    function setupSidebar() {
        const hamburger = $('hamburger');
        const sidebar = $('sidebar');
        const overlay = $('sidebar-overlay');

        hamburger?.addEventListener('click', () => {
            sidebar?.classList.toggle('open');
            overlay?.classList.toggle('open');
        });
        overlay?.addEventListener('click', () => {
            sidebar?.classList.remove('open');
            overlay?.classList.remove('open');
        });
        $('btn-sidebar-logout')?.addEventListener('click', () => {
            localStorage.removeItem('hookArchitect_profileId');
            localStorage.removeItem('hookArchitect_user');
            window.location.href = '/';
        });

        // Load user info
        try {
            const user = JSON.parse(localStorage.getItem('hookArchitect_user'));
            if (user) {
                $('sidebar-avatar').textContent = user.username?.charAt(0)?.toUpperCase() || '?';
                $('sidebar-username').textContent = user.username || 'Guest';
                $('sidebar-niche').textContent = user.niche || '';
            }
        } catch (e) {}
    }

    // ── Animate Number ────────────────────────────────────
    function animateNumber(el, from, to, duration = 1200) {
        const start = performance.now();
        function tick(now) {
            const p = Math.min((now - start) / duration, 1);
            const ease = 1 - Math.pow(1 - p, 3);
            el.textContent = Math.round(from + (to - from) * ease);
            if (p < 1) requestAnimationFrame(tick);
        }
        requestAnimationFrame(tick);
    }

    // ── Get Zone Color ────────────────────────────────────
    function zoneColor(score, green = 75, yellow = 45) {
        if (score >= green) return '#10B981';
        if (score >= yellow) return '#F59E0B';
        return '#EF4444';
    }

    // ══════════════════════════════════════════════════════
    // RENDER RESULTS
    // ══════════════════════════════════════════════════════

    function renderAll(r) {
        result = r;
        renderHeader(r);
        renderOverview(r);
        renderTimeline(r);
        renderSignals(r);
        renderCoach(r);
        renderReport(r);
        setupChat(r);
        setupActions(r);
    }

    // ── Header ────────────────────────────────────────────
    function renderHeader(r) {
        const fn = r.video_meta?.filename || 'Video Analysis';
        $('analysis-title').textContent = fn;
        document.title = `${fn} — Hook Architect`;

        const meta = [];
        if (r.video_meta?.duration) meta.push(`⏱ ${r.video_meta.duration.toFixed(1)}s`);
        if (r.video_meta?.resolution) meta.push(`📐 ${r.video_meta.resolution}`);
        if (r.video_meta?.fps) meta.push(`🎞 ${r.video_meta.fps} fps`);
        if (r.platform && r.platform !== 'generic') meta.push(`📱 ${r.platform}`);
        if (r.persona?.niche) meta.push(`🎯 ${r.persona.niche}`);
        $('analysis-meta').innerHTML = meta.map(m => `<span>${m}</span>`).join('');
    }

    // ── Overview Tab ──────────────────────────────────────
    function renderOverview(r) {
        const score = r.overall_score || 0;
        const circumference = 2 * Math.PI * 78;
        const offset = circumference - (score / 100) * circumference;
        const color = zoneColor(score);

        const ringFill = $('score-ring-fill');
        ringFill.style.stroke = color;
        ringFill.setAttribute('stroke-dasharray', circumference);
        setTimeout(() => {
            ringFill.style.strokeDashoffset = offset;
            animateNumber($('score-number'), 0, Math.round(score), 1500);
        }, 300);
        $('score-number').style.color = color;

        // Hook grade
        if (r.hook_score) {
            const grade = r.hook_score.grade || '—';
            $('hook-grade-letter').textContent = grade;
            $('hook-grade-letter').style.color = grade === 'A+' || grade === 'A' ? '#10B981' :
                grade === 'B' ? '#F59E0B' : '#EF4444';
            $('hook-grade-desc').textContent = `Score: ${r.hook_score.hook_score?.toFixed(0) || '?'}/100 — First 3 seconds`;
        }

        // Summary
        $('summary-text').textContent = r.summary || '';

        // Zone badges
        const timeline = r.timeline || [];
        const zones = r.zones || [];
        const greens = timeline.filter(t => t.zone === 'green').length;
        const yellows = zones.filter(z => z.zone === 'yellow').length;
        const reds = zones.filter(z => z.zone === 'red').length;

        let badgesHtml = '';
        if (greens > 0) badgesHtml += `<div class="zone-badge zone-badge--green"><span class="zone-badge__dot"></span>${greens}s safe</div>`;
        if (yellows > 0) badgesHtml += `<div class="zone-badge zone-badge--yellow"><span class="zone-badge__dot"></span>${yellows} at-risk</div>`;
        if (reds > 0) badgesHtml += `<div class="zone-badge zone-badge--red"><span class="zone-badge__dot"></span>${reds} critical</div>`;
        if (r.ml_zones_active) badgesHtml += `<div class="zone-badge zone-badge--ml">🤖 ML</div>`;
        $('zone-badges').innerHTML = badgesHtml;

        // Retention Curve Chart
        renderRetentionChart(r);

        // Zone Donut
        renderZoneDonut(r);

        // Multi-spectral
        renderMultiSpectral(r);
    }

    function renderRetentionChart(r) {
        const ctx = $('retention-chart');
        if (!ctx) return;

        const rd = r.retention_curve;
        let labels, data;
        if (rd?.curve_points) {
            labels = rd.curve_points.map(p => `${p.second}s`);
            data = rd.curve_points.map(p => p.retention_pct);
        } else {
            // Fallback: use timeline scores
            labels = (r.timeline || []).map((_, i) => `${i}s`);
            data = (r.timeline || []).map(t => t.score || 0);
        }

        if (retentionChart) retentionChart.destroy();
        retentionChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: [{
                    label: 'Retention %',
                    data,
                    borderColor: '#FF3B30',
                    backgroundColor: 'rgba(255, 59, 48, 0.08)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    borderWidth: 2,
                }]
            },
            options: chartOptions('Retention %', 0, 100)
        });
    }

    function renderZoneDonut(r) {
        const ctx = $('zone-donut-chart');
        if (!ctx) return;

        const tl = r.timeline || [];
        const g = tl.filter(t => t.zone === 'green').length;
        const y = tl.filter(t => t.zone === 'yellow').length;
        const rd2 = tl.filter(t => t.zone === 'red').length;

        if (donutChart) donutChart.destroy();
        donutChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Green (Safe)', 'Yellow (At-Risk)', 'Red (Drop)'],
                datasets: [{
                    data: [g, y, rd2],
                    backgroundColor: ['#10B981', '#FF8C00', '#FF3B30'],
                    borderColor: '#0F0F12',
                    borderWidth: 3,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '65%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: '#5A5A5D', font: { family: 'Inter', size: 12 }, padding: 16 }
                    }
                }
            }
        });
    }

    function renderMultiSpectral(r) {
        const ctx = $('multispectral-chart');
        if (!ctx) return;

        const audio = r.audio_signals || [];
        const visual = r.visual_signals || [];
        const tl = r.timeline || [];
        const labels = tl.map((_, i) => `${i}s`);

        if (multiChart) multiChart.destroy();
        multiChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: [
                    { label: 'Attention', data: tl.map(t => t.score || 0), borderColor: '#FF3B30', borderWidth: 1.5, pointRadius: 0, tension: 0.3 },
                    { label: 'Audio Energy', data: audio.map(a => a.energy || 0), borderColor: '#FF6B35', borderWidth: 1, pointRadius: 0, tension: 0.3 },
                    { label: 'Visual Motion', data: visual.map(v => v.motion_score || 0), borderColor: '#FF8C00', borderWidth: 1, pointRadius: 0, tension: 0.3 },
                ]
            },
            options: chartOptions('Score', 0, 100)
        });
    }

    function chartOptions(yLabel, yMin, yMax) {
        return {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            scales: {
                x: { grid: { color: 'rgba(255,255,255,0.03)' }, ticks: { color: '#5A5A5D', font: { size: 10 } } },
                y: { min: yMin, max: yMax, grid: { color: 'rgba(255,255,255,0.03)' }, ticks: { color: '#5A5A5D', font: { size: 10 } },
                    title: { display: true, text: yLabel, color: '#5A5A5D', font: { size: 11 } } }
            },
            plugins: {
                legend: { labels: { color: '#A8A8A0', font: { family: 'Inter', size: 11 }, boxWidth: 12, padding: 12 } },
                tooltip: { backgroundColor: '#1A1A1D', titleColor: '#F5F5F0', bodyColor: '#A8A8A0', borderColor: '#252528', borderWidth: 1 }
            }
        };
    }

    // ── Timeline Tab ──────────────────────────────────────
    function renderTimeline(r) {
        const tl = r.timeline || [];
        const bar = $('heatmap-bar');
        const timestamps = $('heatmap-timestamps');

        if (!bar) return;

        bar.innerHTML = tl.map((t, i) => {
            const color = t.zone === 'green' ? '#10B981' : t.zone === 'yellow' ? '#F59E0B' : '#EF4444';
            return `<div class="heatmap-bar__cell" style="background:${color}" title="Second ${i}: ${t.score?.toFixed(0)}/100 (${t.zone})"></div>`;
        }).join('');

        if (timestamps) {
            const duration = tl.length;
            const marks = [0, Math.floor(duration / 4), Math.floor(duration / 2), Math.floor(3 * duration / 4), duration - 1];
            timestamps.innerHTML = marks.map(m => `<span>${m}s</span>`).join('');
        }

        // Zone cards
        const zones = r.zones || [];
        const zoneCards = $('zone-cards');
        if (!zoneCards) return;

        if (zones.length === 0) {
            zoneCards.innerHTML = '<div class="empty-state"><div class="empty-state__icon">✅</div><div class="empty-state__title">No risk zones detected!</div></div>';
            return;
        }

        zoneCards.innerHTML = zones.map(z => {
            const flags = (z.flags || []).map(f => `<span class="zone-card__flag">${f}</span>`).join('');
            const startS = z.start?.toFixed(0) || '?';
            const endS = z.end?.toFixed(0) || '?';
            const fix = z.fix_hint || z.description || '';
            return `
            <div class="zone-card">
                <div class="zone-card__header">
                    <div class="zone-card__time">⏱ ${startS}s — ${endS}s</div>
                    <div class="zone-card__flags">${flags}</div>
                </div>
                <div class="zone-card__summary">${z.issue || z.summary || 'Viewer attention drops in this segment.'}</div>
                ${fix ? `<div class="zone-card__fix"><div class="zone-card__fix-label">💡 AI Suggestion</div>${fix}</div>` : ''}
            </div>`;
        }).join('');
    }

    // ── Signals Tab ───────────────────────────────────────
    function renderSignals(r) {
        const grid = $('signals-grid');
        if (!grid) return;

        const audio = r.audio_signals || [];
        const visual = r.visual_signals || [];
        const transcript = r.transcript_data;
        const emotion = r.emotion_data;
        const virality = r.virality_data;

        const avgAudio = audio.length ? (audio.reduce((s, a) => s + (a.energy || 0), 0) / audio.length).toFixed(0) : '—';
        const avgVisual = visual.length ? (visual.reduce((s, v) => s + (v.motion_score || 0), 0) / visual.length).toFixed(0) : '—';
        const transScore = transcript?.transcription_score?.toFixed(0) || '—';
        const emotionAlign = emotion?.alignment_score?.toFixed(0) || '—';
        const viralScore = virality?.song_score?.toFixed(0) || '—';
        const mlActive = r.ml_zones_active ? 'Active' : 'Inactive';

        const signals = [
            { icon: '🎧', name: 'Audio Energy', score: avgAudio, insights: `Average vocal energy across ${audio.length}s of audio. Higher energy keeps attention.`, color: '#FF6B35' },
            { icon: '👁', name: 'Visual Motion', score: avgVisual, insights: `Average visual dynamism. Scene cuts, motion, and object richness.`, color: '#FF8C00' },
            { icon: '🗣', name: 'Transcript', score: transScore, insights: transcript?.transcript ? `"${transcript.transcript.substring(0, 120)}..."` : 'No transcript detected.', color: '#FF8C00' },
            { icon: '💜', name: 'Emotion Sync', score: emotionAlign, insights: `Alignment between audio emotion and visual mood. Dominant: ${emotion?.dominant_facial_emotion || 'unknown'}.`, color: '#FF3B30' },
            { icon: '🎵', name: 'Virality & Sound', score: viralScore, insights: virality?.trend_match_summary || 'Audio-visual sync analysis.', color: '#10B981' },
            { icon: '🤖', name: 'ML Prediction', score: mlActive, insights: `Drop Zone Predictor: ${r.ml_zones_active ? 'Contributing to scoring' : 'Not enough training data yet.'}`, color: '#FF3B30' },
        ];

        grid.innerHTML = signals.map(s => `
        <div class="signal-card">
            <div class="signal-card__header">
                <div class="signal-card__name">${s.icon} ${s.name}</div>
                <div class="signal-card__score" style="color: ${s.color}">${s.score}</div>
            </div>
            <div class="signal-card__insights">${s.insights}</div>
        </div>`).join('');
    }

    // ── AI Coach Tab ──────────────────────────────────────
    function renderCoach(r) {
        // Emotion Arc Chart
        renderEmotionArc(r);

        // Multimodal critique
        if (r.multimodal_hook_critique) {
            $('multimodal-section').style.display = '';
            let html = `<div style="color: var(--text-secondary); font-size: 0.9rem; line-height: 1.6; margin-bottom: 16px;">${r.multimodal_hook_critique}</div>`;
            if (r.multimodal_red_zone_diagnoses?.length) {
                html += r.multimodal_red_zone_diagnoses.map(d => 
                    `<div style="background: var(--bg-primary); border-radius: var(--radius-md); padding: 12px 16px; margin-bottom: 8px; font-size: 0.85rem; color: var(--text-secondary);">${d}</div>`
                ).join('');
            }
            $('multimodal-content').innerHTML = html;
        }
    }

    function renderEmotionArc(r) {
        const ctx = $('emotion-arc-chart');
        if (!ctx) return;

        const arc = r.emotion_arc;
        if (!arc?.per_second_intensity) return;

        const labels = arc.per_second_intensity.map((_, i) => `${i}s`);

        if (emotionChart) emotionChart.destroy();
        emotionChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: [
                    { label: 'Emotional Intensity', data: arc.per_second_intensity, borderColor: '#FF3B30', backgroundColor: 'rgba(255, 59, 48, 0.08)', fill: true, tension: 0.4, pointRadius: 0, borderWidth: 2 },
                    ...(arc.per_second_valence ? [{ label: 'Valence', data: arc.per_second_valence, borderColor: '#FF6B35', borderWidth: 1, pointRadius: 0, tension: 0.4 }] : [])
                ]
            },
            options: chartOptions('Intensity', 0, 100)
        });
    }

    // ── Report Tab ────────────────────────────────────────
    function renderReport(r) {
        const preview = $('report-preview');
        if (!preview) return;

        // Generate a text-based report preview
        const lines = [];
        lines.push(`<h2>Hook Architect — Analysis Report</h2>`);
        lines.push(`<p><strong>File:</strong> ${r.video_meta?.filename || 'Video'}</p>`);
        lines.push(`<p><strong>Duration:</strong> ${r.video_meta?.duration?.toFixed(1) || '?'}s | <strong>Resolution:</strong> ${r.video_meta?.resolution || '?'} | <strong>FPS:</strong> ${r.video_meta?.fps || '?'}</p>`);
        lines.push(`<hr style="border-color: var(--border-subtle); margin: 16px 0;">`);
        lines.push(`<h3>Overall Score: ${r.overall_score?.toFixed(0) || 0}/100</h3>`);
        lines.push(`<p>${r.summary || ''}</p>`);

        if (r.hook_score) {
            lines.push(`<h3>Hook Strength: ${r.hook_score.grade || '?'} (${r.hook_score.hook_score?.toFixed(0) || '?'}/100)</h3>`);
        }
        if (r.retention_curve) {
            lines.push(`<h3>Retention Prediction</h3>`);
            lines.push(`<p>Avg Retention: ${r.retention_curve.predicted_avg_retention?.toFixed(0) || '?'}% | Watch-Through: ${r.retention_curve.predicted_watch_through_rate?.toFixed(0) || '?'}%</p>`);
        }

        const zones = r.zones || [];
        if (zones.length > 0) {
            lines.push(`<h3>Risk Zones (${zones.length})</h3>`);
            zones.forEach(z => {
                lines.push(`<p>⚠️ <strong>${z.start?.toFixed(0)}s–${z.end?.toFixed(0)}s:</strong> ${z.issue || z.summary || 'Attention drops here.'}</p>`);
            });
        }

        preview.innerHTML = lines.join('\n');
    }

    // ── Chat ──────────────────────────────────────────────
    function setupChat(r) {
        const input = $('chat-input');
        const btn = $('btn-send-chat');
        if (!input || !btn) return;

        input.addEventListener('input', () => { btn.disabled = !input.value.trim(); });
        input.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !btn.disabled) sendChat(); });
        btn.addEventListener('click', sendChat);
    }

    async function sendChat() {
        const input = $('chat-input');
        const btn = $('btn-send-chat');
        const messages = $('chat-messages');
        const msg = input.value.trim();
        if (!msg || !result) return;

        // Add user message
        messages.innerHTML += `
        <div class="chat-message chat-message--user">
            <div class="chat-message__avatar">👤</div>
            <div class="chat-message__text">${escapeHtml(msg)}</div>
        </div>`;
        input.value = '';
        btn.disabled = true;
        messages.scrollTop = messages.scrollHeight;

        chatHistory.push({ role: 'user', content: msg });

        try {
            const jobId = getJobId();
            const res = await fetch(`${API}/api/jobs/${jobId}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: msg, history: chatHistory, job_id: jobId })
            });
            const data = await res.json();
            const reply = data.response || 'Sorry, I could not process that.';

            messages.innerHTML += `
            <div class="chat-message">
                <div class="chat-message__avatar">🤖</div>
                <div class="chat-message__text">${escapeHtml(reply)}</div>
            </div>`;
            chatHistory.push({ role: 'assistant', content: reply });
        } catch (e) {
            messages.innerHTML += `
            <div class="chat-message">
                <div class="chat-message__avatar">🤖</div>
                <div class="chat-message__text" style="color: var(--danger);">Error: ${e.message}</div>
            </div>`;
        }
        messages.scrollTop = messages.scrollHeight;
    }

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // ── Actions (PDF, Share) ──────────────────────────────
    function setupActions(r) {
        const jobId = getJobId();

        // PDF Download
        const pdfHandler = () => {
            window.open(`${API}/api/results/${jobId}/pdf`, '_blank');
        };
        $('btn-download-pdf')?.addEventListener('click', pdfHandler);
        $('btn-download-pdf-2')?.addEventListener('click', pdfHandler);

        // Share
        const shareHandler = async () => {
            try {
                const res = await fetch(`${API}/api/results/${jobId}/share`, { method: 'POST' });
                if (!res.ok) throw new Error('Could not create share link');
                const data = await res.json();
                const url = `${window.location.origin}/share/${data.share_id}`;
                await navigator.clipboard.writeText(url);
                showToast('Share link copied to clipboard!', 'success');
            } catch (e) {
                showToast('Share failed: ' + e.message, 'error');
            }
        };
        $('btn-share')?.addEventListener('click', shareHandler);
        $('btn-share-2')?.addEventListener('click', shareHandler);
    }

    // ══════════════════════════════════════════════════════
    // INIT
    // ══════════════════════════════════════════════════════

    async function init() {
        setupTabs();
        setupSidebar();

        const jobId = getJobId();
        if (!jobId) {
            $('analysis-title').textContent = 'No analysis found';
            return;
        }

        try {
            const res = await fetch(`${API}/api/results/${jobId}`);
            if (!res.ok) throw new Error('Results not found');
            const data = await res.json();
            renderAll(data);
        } catch (e) {
            $('analysis-title').textContent = 'Analysis not found or expired';
            $('summary-text').textContent = e.message;
            showToast('Could not load analysis: ' + e.message, 'error');
        }
    }

    init();

})();
