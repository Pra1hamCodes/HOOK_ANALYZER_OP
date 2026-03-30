/* ═══════════════════════════════════════════════════════════
   Hook Architect — Frontend Application
   Hyper UI — Landing → Niche → App
   ═══════════════════════════════════════════════════════════ */

const API = window.location.origin;

// ── DOM Elements ──────────────────────────────────────────
const $ = id => document.getElementById(id);

// Pages
const $pageLanding = $('page-landing');
const $pageNiche = $('page-niche');
const $pageApp = $('page-app');

const $uploadSection = $('upload-section');
const $uploadZone = $('upload-zone');
const $fileInput = $('file-input');
const $progressSection = $('progress-section');
const $progressFill = $('progress-fill');
const $progressPct = $('progress-pct');
const $progressMsg = $('progress-msg');
const $platformSelect = $('platform-select');
const $resultsSection = $('results-section');
const $scoreRingFill = $('score-ring-fill');
const $scoreNumber = $('score-number');
const $summaryText = $('summary-text');
const $zoneBadges = $('zone-badges');
const $videoPlayer = $('video-player');
const $timelineHeatmap = $('timeline-heatmap');
const $timelinePlayhead = $('timeline-playhead');
const $timelineTimestamps = $('timeline-timestamps');
const $timelineContainer = $('timeline-container');
const $metaBar = $('meta-bar');
const $confidenceRow = $('confidence-row');
const $multispectralChartCanvas = $('multispectral-chart');
const $radarChartCanvas = $('radar-chart');
const $weightsChartCanvas = $('weights-chart');
const $weightsChartCard = $('weights-chart-card');
const $editorInsights = $('editor-insights');
const $zoneCards = $('zone-cards');
const $personaBanner = $('persona-banner');
const $adaptationFeedback = $('adaptation-feedback');
const $onboardingUsername = $('onboarding-username');
const $nicheGrid = $('niche-grid');
const $btnCreateProfile = $('btn-create-profile');
const $btnSkip = $('btn-skip-onboarding');
const $headerProfile = $('header-profile');
const $profileBadge = $('profile-badge');
const $profileSwitcher = $('profile-switcher');
const $btnNewProfile = $('btn-new-profile');
// Feature 3: Ledger
const $ledgerSidebar = $('ledger-sidebar');
const $ledgerOverlay = $('ledger-overlay');
const $ledgerContent = $('ledger-content');
const $btnOpenLedger = $('btn-open-ledger');
// Feature 4: References
const $referenceSection = $('reference-section');
const $referenceUploadZone = $('reference-upload-zone');
const $referenceFileInput = $('reference-file-input');
const $referenceBaselineStatus = $('reference-baseline-status');
const $referenceProgress = $('reference-progress');
const $refProgressFill = $('ref-progress-fill');
const $refProgressMsg = $('ref-progress-msg');
const $btnClearRefs = $('btn-clear-refs');
const $btnSkipReferences = $('btn-skip-references');
// Feature 6: Audio-Sync
const $audioSyncSection = $('audio-sync-section');
const $audioSyncCards = $('audio-sync-cards');
// Feature 7: Script Doctor
const $scriptDoctorResults = $('script-doctor-results');
const $refConsistencyBanner = $('ref-consistency-banner');

let multispectralChartInstance = null;
let radarChartInstance = null;
let weightsChartInstance = null;
let currentJobId = null;
let analysisResult = null;
let uploadedFile = null;
let pollTimer = null;
let activeWs = null;
let videoSyncController = null;
let highlightMode = false;
let autoSkipEnabled = false;
let activeProfileId = localStorage.getItem('hookArchitect_profileId') || null;
let activeProfile = null;
let allProfiles = [];
let selectedNiche = null;
let presets = [];
let zoneDetailChart = null;
let cachedAIInsights = null;
let activeGoalText = '';
let activeGoalKeywords = [];
let chatHistory = [];
let completedAnalyses = [];
let timelineTooltip = null;
let timelineDragState = { dragging: false, duration: 0 };
let isSharedView = false;
const $toastContainer = $('toast-container');
const $zoneDetailOverlay = $('zone-detail-overlay');


// ═══════════════════════════════════════════════════════════
// PAGE ROUTING
// ═══════════════════════════════════════════════════════════

function showPage(pageId) {
    document.querySelectorAll('.page').forEach(p => p.style.display = 'none');
    const page = $(pageId);
    if (page) page.style.display = 'block';
}

function sharedGuard(actionLabel = 'This action') {
    if (!isSharedView) return false;
    showToast(`${actionLabel} is disabled in read-only shared view.`, 'warning');
    return true;
}

// ═══════════════════════════════════════════════════════════
// CURSOR-REACTIVE BACKGROUND
// ═══════════════════════════════════════════════════════════

(function initBackground() {
    const canvas = $('bg-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let mouseX = 0, mouseY = 0;
    let particles = [];
    const PARTICLE_COUNT = 50;

    function resize() { canvas.width = window.innerWidth; canvas.height = window.innerHeight; }
    resize();
    window.addEventListener('resize', resize);
    document.addEventListener('mousemove', e => { mouseX = e.clientX; mouseY = e.clientY; });

    for (let i = 0; i < PARTICLE_COUNT; i++) {
        particles.push({
            x: Math.random() * window.innerWidth,
            y: Math.random() * window.innerHeight,
            vx: (Math.random() - 0.5) * 0.3,
            vy: (Math.random() - 0.5) * 0.3,
            size: Math.random() * 2 + 0.5,
            alpha: Math.random() * 0.3 + 0.05,
            hue: Math.random() > 0.5 ? 300 : 45,
        });
    }

    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Subtle radial glow following cursor
        const gradient = ctx.createRadialGradient(mouseX, mouseY, 0, mouseX, mouseY, 350);
        gradient.addColorStop(0, 'rgba(232, 121, 249, 0.03)');
        gradient.addColorStop(0.5, 'rgba(251, 191, 36, 0.015)');
        gradient.addColorStop(1, 'transparent');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Particles
        particles.forEach(p => {
            // Very gentle attraction toward cursor
            const dx = mouseX - p.x, dy = mouseY - p.y;
            const dist = Math.sqrt(dx * dx + dy * dy) || 1;
            if (dist < 300) {
                p.vx += (dx / dist) * 0.01;
                p.vy += (dy / dist) * 0.01;
            }
            p.x += p.vx; p.y += p.vy;
            p.vx *= 0.99; p.vy *= 0.99;
            // Wrap around screen
            if (p.x < 0) p.x = canvas.width;
            if (p.x > canvas.width) p.x = 0;
            if (p.y < 0) p.y = canvas.height;
            if (p.y > canvas.height) p.y = 0;

            ctx.beginPath();
            ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
            ctx.fillStyle = `hsla(${p.hue}, 70%, 60%, ${p.alpha})`;
            ctx.fill();
        });

        // Draw subtle connecting lines between nearby particles
        for (let i = 0; i < particles.length; i++) {
            for (let j = i + 1; j < particles.length; j++) {
                const dx = particles[i].x - particles[j].x;
                const dy = particles[i].y - particles[j].y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < 120) {
                    ctx.beginPath();
                    ctx.moveTo(particles[i].x, particles[i].y);
                    ctx.lineTo(particles[j].x, particles[j].y);
                    ctx.strokeStyle = `rgba(232, 121, 249, ${0.03 * (1 - dist / 120)})`;
                    ctx.lineWidth = 0.5;
                    ctx.stroke();
                }
            }
        }

        requestAnimationFrame(animate);
    }
    animate();
})();

// ═══════════════════════════════════════════════════════════
// INITIALIZATION
// ═══════════════════════════════════════════════════════════

(async function init() {
    await loadPresets();
    await loadProfiles();
    const loadedShared = await loadSharedIfPresent();
    if (loadedShared) return;
    if (activeProfileId) {
        activeProfile = allProfiles.find(p => p.id === activeProfileId) || null;
        if (!activeProfile) {
            activeProfileId = null;
            localStorage.removeItem('hookArchitect_profileId');
        }
    }
    // Routing: if user has a profile, go to app, else show landing
    if (allProfiles.length > 0 || activeProfileId) {
        showPage('page-app');
        updateProfileUI();
        checkReferencePortal();
    } else {
        showPage('page-landing');
    }
})();

async function loadSharedIfPresent() {
    const parts = window.location.pathname.split('/').filter(Boolean);
    if (!(parts.length === 2 && parts[0] === 'share')) return false;
    const shareId = parts[1];
    try {
        const res = await fetch(`${API}/api/share/${shareId}`);
        if (!res.ok) throw new Error('Shared report not available');
        const data = await res.json();
        if (!data.result) throw new Error('Invalid shared snapshot');
        isSharedView = true;
        analysisResult = data.result;
        currentJobId = analysisResult.job_id || null;
        showPage('page-app');
        $uploadSection.style.display = 'none';
        renderResults(analysisResult);
        showToast(`Read-only shared report. Expires in ${data.expires_in_hours}h`, 'info', 5000);
        return true;
    } catch (err) {
        showToast(`Shared report unavailable: ${err.message}`, 'error');
        return false;
    }
}

async function loadPresets() {
    try { const res = await fetch(`${API}/api/presets`); presets = await res.json(); renderNicheGrid(); }
    catch (e) { console.error('Failed to load presets:', e); }
}

async function loadProfiles() {
    try { const res = await fetch(`${API}/api/profiles`); allProfiles = await res.json(); renderProfileSwitcher(); }
    catch (e) { console.error('Failed to load profiles:', e); allProfiles = []; }
}

// ═══════════════════════════════════════════════════════════
// LANDING PAGE
// ═══════════════════════════════════════════════════════════

const $btnGetStarted = $('btn-get-started');
if ($btnGetStarted) {
    $btnGetStarted.addEventListener('click', () => {
        showPage('page-niche');
    });
}

// ═══════════════════════════════════════════════════════════
// NICHE SELECTION (Circular Bubbles)
// ═══════════════════════════════════════════════════════════

function renderNicheGrid() {
    if (!$nicheGrid) return;
    $nicheGrid.innerHTML = presets.map(p => `
        <div class="niche-bubble" data-niche="${p.niche}" id="niche-${p.niche}">
            <div class="niche-bubble__icon">${p.icon}</div>
            <div class="niche-bubble__label">${p.label}</div>
        </div>
    `).join('');
    document.querySelectorAll('.niche-bubble').forEach(bubble => {
        bubble.addEventListener('click', () => {
            document.querySelectorAll('.niche-bubble').forEach(b => b.classList.remove('selected'));
            bubble.classList.add('selected');
            selectedNiche = bubble.dataset.niche;
            validateOnboarding();
        });
    });
}

$onboardingUsername.addEventListener('input', validateOnboarding);
function validateOnboarding() { $btnCreateProfile.disabled = !($onboardingUsername.value.trim().length > 0 && selectedNiche); }

$btnCreateProfile.addEventListener('click', async () => {
    const username = $onboardingUsername.value.trim();
    if (!username || !selectedNiche) return;
    $btnCreateProfile.disabled = true;
    $btnCreateProfile.textContent = 'Creating...';
    try {
        const res = await fetch(`${API}/api/profiles`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, niche: selectedNiche }) });
        if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Failed'); }
        const profile = await res.json();
        activeProfileId = profile.id; activeProfile = profile;
        localStorage.setItem('hookArchitect_profileId', profile.id);
        await loadProfiles();
        showPage('page-app');
        updateProfileUI();
        checkReferencePortal();
    } catch (err) { showToast('Error: ' + err.message, 'error'); }
    finally { $btnCreateProfile.disabled = false; $btnCreateProfile.innerHTML = 'Create My Profile <span class="btn__arrow">→</span>'; }
});

$btnSkip.addEventListener('click', () => {
    activeProfileId = null; activeProfile = null;
    localStorage.removeItem('hookArchitect_profileId');
    showPage('page-app');
    updateProfileUI();
    $referenceSection.style.display = 'none';
    $uploadSection.style.display = '';
});

// ═══════════════════════════════════════════════════════════
// NAVBAR HANDLERS
// ═══════════════════════════════════════════════════════════

const $btnNavNewProject = $('btn-nav-new-project');
const $btnNavProfile = $('btn-nav-profile');
const $btnLogout = $('btn-logout');

if ($btnNavNewProject) {
    $btnNavNewProject.addEventListener('click', () => {
        $resultsSection.classList.remove('active');
        $progressSection.classList.remove('active');
        $uploadSection.style.display = '';
        if (activeProfileId) checkReferencePortal();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });
}

if ($btnNavProfile) {
    $btnNavProfile.addEventListener('click', () => {
        selectedNiche = null; $onboardingUsername.value = '';
        document.querySelectorAll('.niche-bubble').forEach(b => b.classList.remove('selected'));
        $btnCreateProfile.disabled = true;
        showPage('page-niche');
    });
}

if ($btnLogout) {
    $btnLogout.addEventListener('click', () => {
        activeProfileId = null; activeProfile = null;
        localStorage.removeItem('hookArchitect_profileId');
        showPage('page-landing');
    });
}

// ═══════════════════════════════════════════════════════════
// PROFILE MANAGEMENT
// ═══════════════════════════════════════════════════════════

function updateProfileUI() {
    if (activeProfile) {
        $headerProfile.style.display = 'flex';
        $btnOpenLedger.style.display = '';
        const preset = presets.find(p => p.niche === activeProfile.niche);
        const icon = preset ? preset.icon : '👤';
        $profileBadge.innerHTML = `${icon} <strong>${activeProfile.username}</strong> <span class="profile-badge__niche">${activeProfile.niche}</span> <span class="profile-badge__count">${activeProfile.video_count} videos</span>`;
    } else {
        $headerProfile.style.display = 'flex';
        $btnOpenLedger.style.display = 'none';
        $profileBadge.innerHTML = '<span class="profile-badge__none">No profile — using default scoring</span>';
    }
}

function renderProfileSwitcher() {
    $profileSwitcher.innerHTML = '<option value="">No Profile (Default)</option>';
    allProfiles.forEach(p => {
        const preset = presets.find(pr => pr.niche === p.niche);
        const icon = preset ? preset.icon : '';
        const opt = document.createElement('option');
        opt.value = p.id; opt.textContent = `${icon} ${p.username} (${p.niche})`;
        if (p.id === activeProfileId) opt.selected = true;
        $profileSwitcher.appendChild(opt);
    });
}

$profileSwitcher.addEventListener('change', async (e) => {
    const id = e.target.value;
    if (id) { activeProfileId = id; activeProfile = allProfiles.find(p => p.id === id) || null; localStorage.setItem('hookArchitect_profileId', id); }
    else { activeProfileId = null; activeProfile = null; localStorage.removeItem('hookArchitect_profileId'); }
    updateProfileUI(); checkReferencePortal();
});

$btnNewProfile.addEventListener('click', () => {
    selectedNiche = null; $onboardingUsername.value = '';
    document.querySelectorAll('.niche-bubble').forEach(b => b.classList.remove('selected'));
    $btnCreateProfile.disabled = true;
    showPage('page-niche');
});

// ═══════════════════════════════════════════════════════════
// REFERENCE PORTAL — STEP 0 (Feature 4)
// ═══════════════════════════════════════════════════════════

async function checkReferencePortal() {
    if (!activeProfileId) { $referenceSection.style.display = 'none'; return; }
    try {
        const res = await fetch(`${API}/api/profiles/${activeProfileId}/references`);
        const data = await res.json();
        if (data.has_baseline && data.baseline) {
            renderBaselineStatus(data.baseline, data.reference_videos);
            $referenceSection.style.display = 'block';
            $btnClearRefs.style.display = '';
        } else {
            $referenceBaselineStatus.innerHTML = '<div class="ref-status ref-status--empty">No reference baseline yet. Upload 1+ reference videos to create your Narrative Blueprint.</div>';
            $referenceSection.style.display = 'block';
            $btnClearRefs.style.display = 'none';
        }
    } catch (e) { console.error('Failed to check references:', e); }
}

function renderBaselineStatus(baseline, refs) {
    const bp = baseline.narrative_blueprint || '';
    $referenceBaselineStatus.innerHTML = `
        <div class="ref-status ref-status--active">
            <div class="ref-status__header">✅ Narrative Blueprint Active — ${baseline.video_count} reference video(s)</div>
            <div class="ref-status__blueprint">${bp}</div>
            <div class="ref-status__stats">
                <span>🎵 ${baseline.avg_bpm?.toFixed(0) || '—'} BPM</span>
                <span>⚡ ${baseline.avg_energy?.toFixed(0) || '—'}/100 energy</span>
                <span>🏃 ${baseline.avg_motion?.toFixed(0) || '—'}/100 motion</span>
                <span>📐 ${baseline.dominant_narrative_style || 'mixed'} / ${baseline.dominant_visual_style || 'mixed'}</span>
            </div>
        </div>`;
}

$referenceUploadZone.addEventListener('click', () => $referenceFileInput.click());
$referenceFileInput.addEventListener('change', (e) => { if (e.target.files[0]) handleReferenceUpload(e.target.files[0]); });
$referenceUploadZone.addEventListener('dragover', (e) => { e.preventDefault(); $referenceUploadZone.classList.add('drag-over'); });
$referenceUploadZone.addEventListener('dragleave', () => $referenceUploadZone.classList.remove('drag-over'));
$referenceUploadZone.addEventListener('drop', (e) => { e.preventDefault(); $referenceUploadZone.classList.remove('drag-over'); if (e.dataTransfer.files[0]) handleReferenceUpload(e.dataTransfer.files[0]); });

async function handleReferenceUpload(file) {
    if (!activeProfileId) { alert('Please create a profile first.'); return; }
    $referenceProgress.style.display = 'block';
    $refProgressFill.style.width = '5%';
    $refProgressMsg.textContent = 'Uploading reference video...';
    const formData = new FormData();
    formData.append('file', file);
    try {
        const res = await fetch(`${API}/api/profiles/${activeProfileId}/references`, { method: 'POST', body: formData });
        if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Upload failed'); }
        const data = await res.json();
        pollReferenceProgress(data.job_id);
    } catch (err) {
        $refProgressMsg.textContent = '❌ ' + err.message;
        setTimeout(() => { $referenceProgress.style.display = 'none'; }, 3000);
    }
}

function pollReferenceProgress(jobId) {
    const poll = async () => {
        try {
            const res = await fetch(`${API}/api/jobs/${jobId}/status`);
            const data = await res.json();
            $refProgressFill.style.width = `${data.progress || 0}%`;
            $refProgressMsg.textContent = data.message || '';
            if (data.status === 'complete') {
                $referenceProgress.style.display = 'none';
                $referenceFileInput.value = '';
                checkReferencePortal();
                return;
            }
            if (data.status === 'failed') {
                $refProgressMsg.textContent = '❌ ' + (data.message || 'Failed');
                setTimeout(() => { $referenceProgress.style.display = 'none'; }, 3000);
                return;
            }
        } catch (e) {}
        setTimeout(poll, 2000);
    };
    poll();
}

$btnClearRefs.addEventListener('click', async () => {
    if (!activeProfileId) return;
    if (!confirm('Clear all reference videos and reset your Narrative Blueprint?')) return;
    try {
        await fetch(`${API}/api/profiles/${activeProfileId}/references`, { method: 'DELETE' });
        checkReferencePortal();
    } catch (e) { alert('Failed to clear references.'); }
});

$btnSkipReferences.addEventListener('click', () => {
    $referenceSection.style.display = 'none';
    $uploadSection.style.display = '';
});

// ═══════════════════════════════════════════════════════════
// EVOLUTION LEDGER — SIDEBAR (Feature 3)
// ═══════════════════════════════════════════════════════════

$btnOpenLedger.addEventListener('click', () => openLedger());
$('btn-close-ledger').addEventListener('click', () => closeLedger());
$ledgerOverlay.addEventListener('click', () => closeLedger());

function openLedger() {
    $ledgerSidebar.classList.add('open');
    $ledgerOverlay.classList.add('open');
    loadLedgerData();
}
function closeLedger() {
    $ledgerSidebar.classList.remove('open');
    $ledgerOverlay.classList.remove('open');
}

async function loadLedgerData() {
    if (!activeProfileId) { $ledgerContent.innerHTML = '<div class="ledger-empty">No profile selected.</div>'; return; }
    $ledgerContent.innerHTML = '<div class="ledger-loading">Loading history...</div>';
    try {
        const res = await fetch(`${API}/api/profiles/${activeProfileId}/ledger`);
        const data = await res.json();
        renderLedger(data);
    } catch (e) { $ledgerContent.innerHTML = '<div class="ledger-empty">Failed to load history.</div>'; }
}

function renderLedger(data) {
    const ledger = data.ledger || [];
    if (ledger.length === 0) { $ledgerContent.innerHTML = '<div class="ledger-empty">No videos analyzed yet. Upload your first video!</div>'; return; }

    // Compute aggregate stats
    const avgScore = (ledger.reduce((s, e) => s + (e.overall_score || 0), 0) / ledger.length).toFixed(0);
    const bestScore = Math.max(...ledger.map(e => e.overall_score || 0)).toFixed(0);
    const totalDuration = ledger.reduce((s, e) => s + (e.duration || 0), 0);

    let html = `
    <div class="ledger-summary">
        <span>📊 <strong>${data.total_videos}</strong> videos analyzed</span>
        <div class="ledger-summary__stats">
            <span class="ledger-stat">Avg Score: <strong>${avgScore}</strong></span>
            <span class="ledger-stat">Best: <strong>${bestScore}</strong></span>
            <span class="ledger-stat">Total: <strong>${totalDuration.toFixed(0)}s</strong></span>
        </div>
    </div>`;

    ledger.forEach((entry, i) => {
        const date = new Date(entry.uploaded_at * 1000).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        const time = new Date(entry.uploaded_at * 1000).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
        const score = entry.overall_score?.toFixed(0) || '0';
        const scoreClass = score >= 75 ? 'green' : (score >= 45 ? 'yellow' : 'red');
        const nq = entry.niche_qualification || '';
        const entryId = `ledger-detail-${i}`;

        // Signal scores
        const audioScore = entry.audio_avg?.toFixed(0) || '—';
        const visualScore = entry.visual_avg?.toFixed(0) || '—';
        const transcriptScore = entry.transcript_score?.toFixed(0) || '—';
        const emotionScore = entry.emotion_alignment?.toFixed(0) || '—';
        const dominantEmotion = entry.dominant_emotion || '—';
        const videoNature = entry.video_nature || '—';
        const duration = entry.duration?.toFixed(1) || '—';

        // Zone distribution
        const zones = entry.zone_distribution || {};
        const greenZ = zones.green || 0;
        const yellowZ = zones.yellow || 0;
        const redZ = zones.red || 0;
        const totalZ = greenZ + yellowZ + redZ || 1;
        const greenPct = ((greenZ / totalZ) * 100).toFixed(0);
        const yellowPct = ((yellowZ / totalZ) * 100).toFixed(0);
        const redPct = ((redZ / totalZ) * 100).toFixed(0);

        // Weight deltas
        const deltas = entry.weight_deltas || {};
        let deltasHtml = '';
        if (Object.keys(deltas).length > 0) {
            const deltaItems = Object.entries(deltas).map(([k, v]) => {
                const name = k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()).replace('Weight', '').trim();
                const arrow = v > 0 ? '↑' : '↓';
                const color = v > 0 ? 'var(--zone-green)' : 'var(--zone-yellow)';
                return `<span class="delta-chip" style="color:${color}">${name} ${arrow}${Math.abs(v).toFixed(1)}%</span>`;
            }).join(' ');
            deltasHtml = `<div class="ledger-detail__row"><span class="ledger-detail__label">⚖️ Weight Changes</span><div class="ledger-entry__deltas">${deltaItems}</div></div>`;
        }

        // Semantic/vibe
        const sem = entry.semantic_summary || {};
        const vibeHtml = sem.vibe_check_message ? `<div class="ledger-detail__row"><span class="ledger-detail__label">🎭 Vibe Check</span><span>${sem.semantic_drift_detected ? '⚠️' : '✅'} ${sem.vibe_check_message}</span></div>` : '';
        const narrativeStyle = sem.narrative_style || '—';
        const visualStyle = sem.visual_style || '—';

        html += `
        <div class="ledger-entry ledger-entry--expandable" onclick="document.getElementById('${entryId}').classList.toggle('open'); this.classList.toggle('expanded')">
            <div class="ledger-entry__header">
                <span class="ledger-entry__num">#${ledger.length - i}</span>
                <span class="ledger-entry__date">${date}</span>
                <span class="ledger-entry__score ledger-entry__score--${scoreClass}">${score}</span>
                <span class="ledger-entry__expand">▼</span>
            </div>
            <div class="ledger-entry__filename">${entry.filename || 'unknown'}</div>
            <div class="ledger-entry__tags">
                ${nq ? `<span class="niche-tag">${nq}</span>` : ''}
                <span class="niche-tag niche-tag--nature">${videoNature}</span>
                <span class="niche-tag niche-tag--duration">⏱ ${duration}s</span>
            </div>
            <div class="ledger-entry__zone-bar">
                <div class="zone-bar__fill zone-bar__fill--green" style="width:${greenPct}%"></div>
                <div class="zone-bar__fill zone-bar__fill--yellow" style="width:${yellowPct}%"></div>
                <div class="zone-bar__fill zone-bar__fill--red" style="width:${redPct}%"></div>
            </div>
        </div>
        <div class="ledger-detail" id="${entryId}">
            <div class="ledger-detail__grid">
                <div class="ledger-detail__signal">
                    <div class="ledger-detail__signal-label">🎧 Audio</div>
                    <div class="ledger-detail__signal-value">${audioScore}</div>
                    <div class="ledger-detail__signal-bar"><div style="width:${audioScore === '—' ? 0 : audioScore}%;background:var(--accent-purple)"></div></div>
                </div>
                <div class="ledger-detail__signal">
                    <div class="ledger-detail__signal-label">👁 Visual</div>
                    <div class="ledger-detail__signal-value">${visualScore}</div>
                    <div class="ledger-detail__signal-bar"><div style="width:${visualScore === '—' ? 0 : visualScore}%;background:var(--accent-pink)"></div></div>
                </div>
                <div class="ledger-detail__signal">
                    <div class="ledger-detail__signal-label">🗣 Transcript</div>
                    <div class="ledger-detail__signal-value">${transcriptScore}</div>
                    <div class="ledger-detail__signal-bar"><div style="width:${transcriptScore === '—' ? 0 : transcriptScore}%;background:var(--accent-gold)"></div></div>
                </div>
                <div class="ledger-detail__signal">
                    <div class="ledger-detail__signal-label">💜 Emotion</div>
                    <div class="ledger-detail__signal-value">${emotionScore}</div>
                    <div class="ledger-detail__signal-bar"><div style="width:${emotionScore === '—' ? 0 : emotionScore}%;background:#06b6d4"></div></div>
                </div>
            </div>
            <div class="ledger-detail__row">
                <span class="ledger-detail__label">😊 Dominant Emotion</span>
                <span class="ledger-detail__value">${dominantEmotion}</span>
            </div>
            <div class="ledger-detail__row">
                <span class="ledger-detail__label">📐 Style</span>
                <span class="ledger-detail__value">${narrativeStyle} / ${visualStyle}</span>
            </div>
            <div class="ledger-detail__row">
                <span class="ledger-detail__label">🟢🟡🔴 Zones</span>
                <span class="ledger-detail__value">${greenZ}s safe · ${yellowZ}s risk · ${redZ}s drop</span>
            </div>
            <div class="ledger-detail__row">
                <span class="ledger-detail__label">📅 Uploaded</span>
                <span class="ledger-detail__value">${date} at ${time}</span>
            </div>
            ${vibeHtml}
            ${deltasHtml}
        </div>`;
    });
    $ledgerContent.innerHTML = html;
}

// ═══════════════════════════════════════════════════════════
// UPLOAD
// ═══════════════════════════════════════════════════════════

$uploadZone.addEventListener('click', () => $fileInput.click());
$fileInput.addEventListener('change', (e) => { if (e.target.files[0]) handleUpload(e.target.files[0]); });
$uploadZone.addEventListener('dragover', (e) => { e.preventDefault(); $uploadZone.classList.add('drag-over'); });
$uploadZone.addEventListener('dragleave', () => $uploadZone.classList.remove('drag-over'));
$uploadZone.addEventListener('drop', (e) => { e.preventDefault(); $uploadZone.classList.remove('drag-over'); if (e.dataTransfer.files[0]) handleUpload(e.dataTransfer.files[0]); });

async function handleUpload(file) {
    uploadedFile = file; cleanup();
    $uploadSection.style.display = 'none';
    $referenceSection.style.display = 'none';
    $resultsSection.classList.remove('active');
    $progressSection.classList.add('active');
    updateProgress(5, 'Uploading video...');
    $videoPlayer.src = URL.createObjectURL(file);
    try {
        const formData = new FormData();
        formData.append('file', file);
        if (activeProfileId) formData.append('user_id', activeProfileId);
        if (activeGoalText) formData.append('goal_text', activeGoalText);
        if ($platformSelect?.value) formData.append('platform', $platformSelect.value);
        const res = await fetch(`${API}/api/upload`, { method: 'POST', body: formData });
        if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Upload failed'); }
        const data = await res.json();
        currentJobId = data.job_id;
        connectWebSocket(data.job_id); startPolling(data.job_id);
    } catch (err) {
        updateProgress(0, `❌ Error: ${err.message}`);
        setTimeout(() => { $progressSection.classList.remove('active'); $uploadSection.style.display = ''; }, 3000);
    }
}

function cleanup() {
    if (pollTimer) { clearTimeout(pollTimer); pollTimer = null; }
    if (activeWs) { try { activeWs.close(); } catch (e) {} activeWs = null; }
    if (videoSyncController) { videoSyncController.abort(); videoSyncController = null; }
    highlightMode = false;
}

function updateProgress(pct, message) {
    $progressFill.style.width = `${pct}%`;
    $progressPct.textContent = `${Math.round(pct)}%`;
    $progressMsg.textContent = message;
}

function connectWebSocket(jobId) {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws/jobs/${jobId}`);
    activeWs = ws;
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        updateProgress(data.progress || 0, data.message || '');
        if (data.status === 'complete') { ws.close(); activeWs = null; fetchResults(jobId); }
        else if (data.status === 'failed') { ws.close(); activeWs = null; updateProgress(0, `❌ Failed: ${data.message}`); }
    };
    ws.onerror = () => { console.log('WebSocket error, polling fallback active.'); };
    ws.onclose = () => { activeWs = null; };
}

function startPolling(jobId) {
    const poll = async () => {
        if (currentJobId !== jobId) return;
        try {
            const res = await fetch(`${API}/api/jobs/${jobId}/status`);
            const data = await res.json();
            updateProgress(data.progress || 0, data.message || '');
            if (data.status === 'complete') { fetchResults(jobId); return; }
            if (data.status === 'failed') { updateProgress(0, `❌ Failed: ${data.message}`); return; }
        } catch (e) {}
        pollTimer = setTimeout(poll, 2000);
    }; poll();
}

async function fetchResults(jobId) {
    if (pollTimer) { clearTimeout(pollTimer); pollTimer = null; }
    try {
        const res = await fetch(`${API}/api/results/${jobId}`);
        if (!res.ok) throw new Error('Results not ready');
        analysisResult = await res.json();
        if (activeProfileId) {
            await loadProfiles();
            activeProfile = allProfiles.find(p => p.id === activeProfileId) || null;
            updateProfileUI();
        }
        renderResults(analysisResult);
    } catch (err) { setTimeout(() => fetchResults(jobId), 2000); }
}

// ═══════════════════════════════════════════════════════════
// RENDER RESULTS
// ═══════════════════════════════════════════════════════════

function renderResults(result) {
    $progressSection.classList.remove('active');
    $resultsSection.classList.add('active');
    renderPersonaBanner(result);
    renderRefConsistencyBanner(result);
    renderRefComparison(result);

    // Score Ring
    const score = result.overall_score;
    const circumference = 2 * Math.PI * 60;
    const offset = circumference - (score / 100) * circumference;
    const greenThr = result.persona?.weights_used?.green_threshold || 75;
    const yellowThr = result.persona?.weights_used?.yellow_threshold || 45;
    let ringColor;
    if (score >= greenThr) ringColor = 'var(--zone-green)';
    else if (score >= yellowThr) ringColor = 'var(--zone-yellow)';
    else ringColor = 'var(--zone-red)';
    $scoreRingFill.style.stroke = ringColor;
    $scoreNumber.style.color = ringColor;
    setTimeout(() => { $scoreRingFill.style.strokeDashoffset = offset; animateNumber($scoreNumber, 0, Math.round(score), 1500); }, 300);

    // Summary
    $summaryText.textContent = result.summary;
    renderConfidenceBadge(result);
    const reds = result.zones.filter(z => z.zone === 'red').length;
    const yellows = result.zones.filter(z => z.zone === 'yellow').length;
    const greens = result.timeline.filter(t => t.zone === 'green').length;
    $zoneBadges.innerHTML = `
        ${greens > 0 ? `<div class="zone-badge zone-badge--green"><span class="zone-badge__dot"></span>${greens}s safe</div>` : ''}
        ${yellows > 0 ? `<div class="zone-badge zone-badge--yellow"><span class="zone-badge__dot"></span>${yellows} at-risk</div>` : ''}
        ${reds > 0 ? `<div class="zone-badge zone-badge--red"><span class="zone-badge__dot"></span>${reds} critical</div>` : ''}
        ${result.ml_zones_active ? `<div class="zone-badge zone-badge--ml" title="Drop Zone Predictor active — ML-blended scoring">🤖 ML</div>` : ''}`;

    // Early score estimates
    const earlyEstEl = $('early-score-estimates');
    if (earlyEstEl) {
        const ests = result.early_score_estimates;
        if (ests && ests.length > 0) {
            earlyEstEl.style.display = 'flex';
            earlyEstEl.innerHTML = ests.map(e => `<span class="early-score-chip">📊 ${e.stage} estimate: <strong>${e.value}</strong></span>`).join('');
        } else {
            earlyEstEl.style.display = 'none';
        }
    }

    // Meta Bar
    const meta = result.video_meta;
    $metaBar.innerHTML = `
        <div class="meta-bar__item">⏱ <span class="meta-bar__value">${meta.duration.toFixed(1)}s</span></div>
        <div class="meta-bar__item">📐 <span class="meta-bar__value">${meta.resolution}</span></div>
        <div class="meta-bar__item">🎞 <span class="meta-bar__value">${meta.fps.toFixed(0)} fps</span></div>
        <div class="meta-bar__item">📄 <span class="meta-bar__value">${meta.filename}</span></div>
        <div class="meta-bar__item">📱 <span class="meta-bar__value">${(result.platform || 'generic').replaceAll('_', ' ')}</span></div>`;

    renderHeatmap(result.timeline, meta.duration);
    renderAudioSyncHUD(result);
    renderHookScore(result);
    renderEmotionArc(result);
    renderRetentionCurve(result);
    renderMultiSpectralChart(result.timeline);
    renderRadarChart(result);
    renderWeightsChart(result);
    renderEditorInsights(result);
    renderAdaptationFeedback(result);
    renderZoneCards(result.zones);
    setupVideoSync(meta.duration);
    rememberCompletedAnalysis(result);
    // Show report actions + chat section
    const $reportActionsSection = $('report-actions-section');
    const $chatSection = $('chat-section');
    if ($reportActionsSection) $reportActionsSection.style.display = 'block';
    if ($chatSection) { $chatSection.style.display = 'block'; chatHistory = []; resetChatMessages(); }
    // Render goal alignment if available
    renderGoalAlignment(result);
}

function renderConfidenceBadge(result) {
    if (!$confidenceRow) return;
    const value = Number(result.analysis_confidence ?? 100);
    const reasons = result.confidence_reasons || [];
    let cls = 'confidence-badge--high';
    let label = 'High confidence';
    if (value < 50) {
        cls = 'confidence-badge--low';
        label = 'Low confidence';
    } else if (value < 75) {
        cls = 'confidence-badge--medium';
        label = 'Medium confidence';
    }
    const reasonText = reasons.length > 0 ? ` — ${reasons.join(', ')}` : '';
    $confidenceRow.innerHTML = `
        <span class="confidence-badge ${cls}">${label} (${Math.round(value)}/100)</span>
        <span class="confidence-note">${reasonText}</span>
    `;
}

function renderPersonaBanner(result) {
    if (!result.persona || !result.persona.niche) { $personaBanner.style.display = 'none'; return; }
    const niche = result.persona.niche;
    const preset = presets.find(p => p.niche === niche);
    const icon = preset ? preset.icon : '🎯';
    const rewards = [];
    const w = result.persona.weights_used || {};
    if (w.slow_pacing_reward > 0) rewards.push('Slow pacing rewarded');
    if (w.high_energy_reward > 0) rewards.push('High energy bonus');
    $personaBanner.style.display = 'block';
    $personaBanner.innerHTML = `<div class="persona-banner__content"><span class="persona-banner__icon">${icon}</span><span class="persona-banner__text">Scoring as <strong>${niche.charAt(0).toUpperCase() + niche.slice(1)}</strong> creator${rewards.length > 0 ? ` <span class="persona-banner__rewards"> — ${rewards.join(' • ')}</span>` : ''}</span></div>`;
}

function renderRefConsistencyBanner(result) {
    const sem = result.semantic_data;
    if (!sem || sem.reference_overlap_score === null || sem.reference_overlap_score === undefined) {
        $refConsistencyBanner.style.display = 'none'; return;
    }
    const pct = sem.reference_overlap_score;
    const cls = pct >= 70 ? 'success' : (pct >= 40 ? 'warn' : 'danger');
    $refConsistencyBanner.style.display = 'block';
    $refConsistencyBanner.className = `reference-consistency-banner ref-banner--${cls}`;
    $refConsistencyBanner.innerHTML = `<div class="ref-banner__content">${sem.reference_comparison_message}</div>`;
}

function renderRefComparison(result) {
    const compSection = $('ref-comparison-section');
    const compMetrics = $('ref-comparison-metrics');
    const compVerdict = $('ref-comparison-verdict');
    const compSubtitle = $('ref-comparison-subtitle');
    if (!compSection || !compMetrics) return;
    
    const cmp = result.comparison;
    if (!cmp || !cmp.metrics) { compSection.style.display = 'none'; return; }
    
    compSection.style.display = 'block';
    compSubtitle.textContent = `Comparing against ${cmp.ref_video_count} reference video(s) · ${cmp.ref_narrative_style} / ${cmp.ref_visual_style}`;
    compVerdict.innerHTML = `<span class="ref-comparison-verdict__text">${cmp.verdict}</span>`;
    
    let html = '';
    cmp.metrics.forEach(m => {
        const mainPct = Math.min(Math.max(m.name === 'BPM' ? (m.main / 200) * 100 : (m.name === 'Sentiment' ? (m.main + 1) * 50 : m.main), 0), 100);
        const refPct = Math.min(Math.max(m.name === 'BPM' ? (m.ref / 200) * 100 : (m.name === 'Sentiment' ? (m.ref + 1) * 50 : m.ref), 0), 100);
        const deltaVal = m.delta;
        const deltaSign = deltaVal > 0 ? '+' : '';
        const deltaColor = deltaVal > 0 ? 'var(--zone-green)' : (deltaVal < 0 ? 'var(--zone-red)' : 'var(--text-muted)');
        const deltaArrow = deltaVal > 0 ? '↑' : (deltaVal < 0 ? '↓' : '=');

        html += `
        <div class="ref-cmp-metric">
            <div class="ref-cmp-metric__header">
                <span class="ref-cmp-metric__icon">${m.icon}</span>
                <span class="ref-cmp-metric__name">${m.name}</span>
                <span class="ref-cmp-metric__delta" style="color:${deltaColor}">${deltaArrow} ${deltaSign}${deltaVal}${m.unit === '/100' ? '' : m.unit}</span>
            </div>
            <div class="ref-cmp-metric__bars">
                <div class="ref-cmp-metric__row">
                    <span class="ref-cmp-metric__label">Your Video</span>
                    <div class="ref-cmp-metric__bar">
                        <div class="ref-cmp-metric__fill ref-cmp-metric__fill--main" style="width:${mainPct}%"></div>
                    </div>
                    <span class="ref-cmp-metric__value">${m.main}${m.unit}</span>
                </div>
                <div class="ref-cmp-metric__row">
                    <span class="ref-cmp-metric__label">Reference</span>
                    <div class="ref-cmp-metric__bar">
                        <div class="ref-cmp-metric__fill ref-cmp-metric__fill--ref" style="width:${refPct}%"></div>
                    </div>
                    <span class="ref-cmp-metric__value">${m.ref}${m.unit}</span>
                </div>
            </div>
        </div>`;
    });
    compMetrics.innerHTML = html;
}

// ═══════════════════════════════════════════════════════════
// AUDIO-SYNC COMPATIBILITY HUD (Feature 6)
// ═══════════════════════════════════════════════════════════

function renderAudioSyncHUD(result) {
    const recs = result.virality_data?.top_recommendations;
    if (!recs || recs.length === 0) { $audioSyncSection.style.display = 'none'; return; }
    $audioSyncSection.style.display = 'block';
    const ap = result.virality_data.audio_profile || {};
    let cardsHtml = `<div class="audio-sync-profile">Your video: ~${ap.estimated_bpm || '—'} BPM | ${ap.avg_energy?.toFixed(0) || '—'}/100 energy | ${ap.avg_pacing?.toFixed(0) || '—'}/100 pacing</div>`;
    recs.forEach((rec, i) => {
        const statusIcon = rec.trending_status === 'rising' ? '🔥' : rec.trending_status === 'peak' ? '📈' : rec.trending_status === 'declining' ? '⚠️' : '❌';
        const statusClass = rec.trending_status === 'rising' || rec.trending_status === 'peak' ? 'trending-up' : 'trending-down';
        cardsHtml += `
        <div class="audio-sync-card ${i === 0 ? 'audio-sync-card--best' : ''}">
            <div class="audio-sync-card__rank">${i === 0 ? '👑 Best Match' : `#${i + 1}`}</div>
            <div class="audio-sync-card__header">
                <div class="audio-sync-card__title">${rec.track_name}</div>
                <div class="audio-sync-card__artist">${rec.artist} • ${rec.bpm} BPM</div>
            </div>
            <div class="audio-sync-card__match">
                <div class="match-bar"><div class="match-bar__fill" style="width:${rec.match_pct}%;"></div></div>
                <span class="match-pct">${rec.match_pct.toFixed(0)}%</span>
            </div>
            <div class="audio-sync-card__detail">
                <span>🎵 BPM: ${rec.bpm_alignment_pct.toFixed(0)}%</span>
                <span>⚡ Pacing: ${rec.pacing_alignment_pct.toFixed(0)}%</span>
                <span>💜 Emotion: ${rec.emotion_resonance_pct.toFixed(0)}%</span>
                <span class="${statusClass}">${statusIcon} ${rec.trending_status.toUpperCase()}</span>
            </div>
            <div class="audio-sync-card__reasoning">${rec.reasoning}</div>
        </div>`;
    });
    $audioSyncCards.innerHTML = cardsHtml;
}

// ═══════════════════════════════════════════════════════════
// HEATMAP TIMELINE
// ═══════════════════════════════════════════════════════════

function renderHeatmap(timeline, duration) {
    $timelineHeatmap.innerHTML = '';
    if (!timeline || timeline.length === 0) return;
    const totalSeconds = Math.max(1, Math.ceil(duration || timeline.length));
    for (let sec = 0; sec < totalSeconds; sec++) {
        const point = timeline.find(p => Math.floor(p.t) === sec) || timeline[Math.min(sec, timeline.length - 1)] || null;
        if (!point) continue;
        const seg = document.createElement('div');
        seg.className = 'timeline-segment';
        seg.style.width = `${100 / totalSeconds}%`;
        seg.style.background = zoneColor(point.zone);
        seg.setAttribute('data-zone', point.zone);
        seg.setAttribute('data-time', String(sec));
        if (point.zone === 'red') seg.classList.add('timeline-segment--red-pulse');
        const tooltip = buildTimelineTooltip(point, sec);
        seg.addEventListener('mouseenter', (e) => showTimelineTooltip(tooltip, e.clientX, e.clientY));
        seg.addEventListener('mousemove', (e) => showTimelineTooltip(tooltip, e.clientX, e.clientY));
        seg.addEventListener('mouseleave', hideTimelineTooltip);
        seg.addEventListener('click', () => {
            $videoPlayer.currentTime = sec;
            $videoPlayer.play();
        });
        $timelineHeatmap.appendChild(seg);
    }
    const steps = Math.max(1, Math.min(10, Math.floor(duration)));
    const interval = duration / steps;
    $timelineTimestamps.innerHTML = '';
    for (let i = 0; i <= steps; i++) { const span = document.createElement('span'); span.textContent = formatTime(i * interval); $timelineTimestamps.appendChild(span); }
}

function buildTimelineTooltip(point, second) {
    const strengths = point.strengths || [];
    const faults = point.faults || [];
    const topFlag = (faults[0]?.label || faults[0]?.key || strengths[0]?.label || strengths[0]?.key || 'None');
    const objs = (point.detected_objects || []).slice(0, 2).map(o => `${o.class} (${Math.round((o.confidence || 0) * 100)}%)`).join(', ');
    return `
        <div><b>${formatTime(second)}</b></div>
        <div>Attention: ${Math.round(point.attention || 0)}/100</div>
        <div>Zone: ${(point.zone || 'unknown').toUpperCase()}</div>
        <div>Top flag: ${topFlag}</div>
        <div>Objects: ${objs || 'None'}</div>
    `;
}

function zoneColor(zone) {
    if (zone === 'green') return '#22c55e';
    if (zone === 'yellow') return '#eab308';
    return '#ef4444';
}

function setupVideoSync(duration) {
    if (videoSyncController) videoSyncController.abort();
    videoSyncController = new AbortController();
    const signal = videoSyncController.signal;
    $videoPlayer.addEventListener('timeupdate', () => {
        const pct = (duration > 0) ? ($videoPlayer.currentTime / duration) * 100 : 0;
        $timelinePlayhead.style.left = `${Math.min(pct, 100)}%`;
        if (autoSkipEnabled && analysisResult && analysisResult.zones) {
            const currentT = $videoPlayer.currentTime;
            for (const z of analysisResult.zones.filter(z => z.zone === 'red')) {
                if (currentT >= z.start && currentT < (z.end - 0.2)) { $videoPlayer.currentTime = z.end; break; }
            }
        }
    }, { signal });
    const seekByEvent = (e) => {
        const rect = $timelineContainer.getBoundingClientRect();
        const target = Math.max(0, Math.min(((e.clientX - rect.left) / rect.width) * duration, duration));
        $videoPlayer.currentTime = target;
    };
    $timelineContainer.addEventListener('click', seekByEvent, { signal });
    $timelineContainer.addEventListener('mousedown', (e) => {
        timelineDragState.dragging = true;
        timelineDragState.duration = duration;
        seekByEvent(e);
    }, { signal });
    document.addEventListener('mousemove', (e) => {
        if (!timelineDragState.dragging) return;
        seekByEvent(e);
    }, { signal });
    document.addEventListener('mouseup', () => {
        timelineDragState.dragging = false;
    }, { signal });
}

function ensureTimelineTooltip() {
    if (timelineTooltip) return;
    timelineTooltip = document.createElement('div');
    timelineTooltip.className = 'timeline-tooltip';
    document.body.appendChild(timelineTooltip);
}

function showTimelineTooltip(html, x, y) {
    ensureTimelineTooltip();
    timelineTooltip.innerHTML = html;
    timelineTooltip.style.display = 'block';
    timelineTooltip.style.left = `${x + 14}px`;
    timelineTooltip.style.top = `${y + 14}px`;
}

function hideTimelineTooltip() {
    if (!timelineTooltip) return;
    timelineTooltip.style.display = 'none';
}

// ═══════════════════════════════════════════════════════════
// CHARTS
// ═══════════════════════════════════════════════════════════

function renderMultiSpectralChart(timeline) {
    if (!$multispectralChartCanvas) return;
    if (multispectralChartInstance) multispectralChartInstance.destroy();
    const labels = timeline.map(t => formatTime(t.t));
    multispectralChartInstance = new Chart($multispectralChartCanvas, {
        type: 'line', data: { labels, datasets: [
            { label: 'Attention', data: timeline.map(t => t.attention), borderColor: '#06b6d4', backgroundColor: 'rgba(6,182,212,0.1)', fill: true, tension: 0.4, borderWidth: 3, order: 1 },
            { label: 'Audio', data: timeline.map(t => t.audio_score), borderColor: '#8b5cf6', backgroundColor: 'transparent', borderDash: [5,5], tension: 0.4, borderWidth: 2, order: 2 },
            { label: 'Visual', data: timeline.map(t => t.visual_score), borderColor: '#ec4899', backgroundColor: 'transparent', borderDash: [5,5], tension: 0.4, borderWidth: 2, order: 3 },
            { label: 'Transcript', data: timeline.map(t => t.transcript_score || 0), borderColor: '#eab308', backgroundColor: 'transparent', borderDash: [5,5], tension: 0.4, borderWidth: 2, order: 4 },
            { label: 'Viral Match', data: timeline.map(t => t.song_score || 0), borderColor: '#3b82f6', backgroundColor: 'transparent', borderDash: [5,5], tension: 0.4, borderWidth: 2, order: 5 },
        ]}, options: { responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false },
            plugins: { legend: { labels: { color: '#9ca3af', font: { family: "'JetBrains Mono', monospace" } } }, tooltip: { backgroundColor: 'rgba(10,10,15,0.9)', titleColor: '#fff', bodyColor: '#9ca3af', borderColor: 'rgba(255,255,255,0.1)', borderWidth: 1 } },
            scales: { x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#6b7280', maxTicksLimit: 10 } }, y: { min: 0, max: 100, grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#6b7280' } } }
    } });
}

function renderRadarChart(result) {
    if (!$radarChartCanvas) return;
    if (radarChartInstance) radarChartInstance.destroy();
    const currentScores = [result.overall_score || 0, result.virality_data?.sound_score || 0, result.transcript_data?.transcription_score || 0, result.emotion_data?.alignment_score || 0];
    const baselines = result.reference_baselines?.industry_baselines || {};
    const refScores = [baselines.target_attention_score || 85, baselines.target_sound_score || 80, baselines.target_transcription_score || 75, baselines.target_emotional_alignment || 80];
    radarChartInstance = new Chart($radarChartCanvas, {
        type: 'radar', data: { labels: ['Attention', 'Sound/Viral', 'Speech', 'Emotional Sync'], datasets: [
            { label: 'Your Video', data: currentScores, backgroundColor: 'rgba(139,92,246,0.2)', borderColor: '#8b5cf6', pointBackgroundColor: '#8b5cf6', borderWidth: 2 },
            { label: 'Viral Baseline', data: refScores, backgroundColor: 'rgba(34,197,94,0.1)', borderColor: '#22c55e', borderDash: [5,5], pointBackgroundColor: '#22c55e', borderWidth: 2 }
        ]}, options: { responsive: true, maintainAspectRatio: false,
            scales: { r: { min: 0, max: 100, ticks: { display: false, stepSize: 20 }, grid: { color: 'rgba(255,255,255,0.1)' }, angleLines: { color: 'rgba(255,255,255,0.1)' }, pointLabels: { color: '#9ca3af', font: { size: 11, family: "'JetBrains Mono', monospace" } } } },
            plugins: { legend: { position: 'bottom', labels: { color: '#9ca3af', boxWidth: 12 } } }
    } });
}

function renderWeightsChart(result) {
    if (!$weightsChartCanvas || !result.persona || !result.persona.niche) { if ($weightsChartCard) $weightsChartCard.style.display = 'none'; return; }
    $weightsChartCard.style.display = 'block';
    if (weightsChartInstance) weightsChartInstance.destroy();
    const w = result.persona.weights_used;
    const currentData = [(w.audio_weight||0)*100,(w.visual_weight||0)*100,(w.transcript_weight||0)*100,(w.song_weight||0)*100,(w.temporal_weight||0)*100,(w.engagement_weight||0)*100];
    const defaultData = [35, 30, 30, 30, 20, 15];
    weightsChartInstance = new Chart($weightsChartCanvas, {
        type: 'radar', data: { labels: ['Audio', 'Visual', 'Transcript', 'Song', 'Temporal', 'Engagement'], datasets: [
            { label: 'Your Weights', data: currentData, backgroundColor: 'rgba(6,182,212,0.2)', borderColor: '#06b6d4', pointBackgroundColor: '#06b6d4', borderWidth: 2 },
            { label: 'Default', data: defaultData, backgroundColor: 'rgba(255,255,255,0.05)', borderColor: 'rgba(255,255,255,0.3)', borderDash: [5,5], pointBackgroundColor: 'rgba(255,255,255,0.3)', borderWidth: 1 }
        ]}, options: { responsive: true, maintainAspectRatio: false,
            scales: { r: { min: 0, max: 60, ticks: { display: false, stepSize: 10 }, grid: { color: 'rgba(255,255,255,0.1)' }, angleLines: { color: 'rgba(255,255,255,0.1)' }, pointLabels: { color: '#9ca3af', font: { size: 11, family: "'JetBrains Mono', monospace" } } } },
            plugins: { legend: { position: 'bottom', labels: { color: '#9ca3af', boxWidth: 12 } } }
    } });
}

// ═══════════════════════════════════════════════════════════
// EDITOR INSIGHTS
// ═══════════════════════════════════════════════════════════

function renderEditorInsights(result) {
    if (!$editorInsights) return;
    $editorInsights.innerHTML = '';
    const insights = [];
    // Semantic Vibe Check
    if (result.semantic_data) {
        const sd = result.semantic_data;
        insights.push(`<div class="insight-item"><b>🎭 Dual-Track Vibe Check:</b> ${sd.vibe_check_message}<br><em>Narrative (What's said):</em> ${sd.transcript_narrative}<br><em>Visual (What's shown):</em> ${sd.visual_narrative}<br>🎯 Overlap: ${sd.semantic_overlap_score}/100 ${sd.semantic_drift_detected ? '⚠️ DRIFT DETECTED' : '✅ Aligned'}</div>`);
    }
    // Virality with trending status
    if (result.virality_data && result.virality_data.recommended_track) {
        const trk = result.virality_data.recommended_track;
        const statusBadge = trk.trending_status === 'rising' ? '🔥 Rising' : trk.trending_status === 'peak' ? '📈 Peak' : trk.trending_status === 'declining' ? '⚠️ Declining' : '❌ Stale';
        insights.push(`<div class="insight-item" style="border-left-color:var(--accent-purple)"><b>🎵 Trend Coach:</b> ${result.virality_data.reasoning}<br><em>Best Match:</em> ${trk.track_name} by ${trk.artist} (${trk.bpm} BPM) — ${trk.match_pct?.toFixed(0) || '—'}% match<br><span class="trending-badge">${statusBadge}</span></div>`);
    }
    // Keywords
    if (result.transcript_data?.keywords?.length > 0) {
        insights.push(`<div class="insight-item" style="border-left-color:var(--accent-pink)"><b>📝 Hook Keywords:</b> ${result.transcript_data.keywords.slice(0,3).join(', ')}.</div>`);
    }
    // Persona insight
    if (result.persona?.niche) {
        const w = result.persona.weights_used;
        const topWeight = Object.entries({Audio:w.audio_weight,Visual:w.visual_weight,Transcript:w.transcript_weight,'Song Match':w.song_weight}).sort((a,b)=>b[1]-a[1])[0];
        insights.push(`<div class="insight-item" style="border-left-color:#06b6d4"><b>🎯 Persona Scoring:</b> As <strong>${result.persona.niche}</strong> creator, top factor: <strong>${topWeight[0]}</strong> (${(topWeight[1]*100).toFixed(0)}%).${w.slow_pacing_reward > 0 ? '<br>✅ Slow pacing bonus active.' : ''}${w.high_energy_reward > 0 ? '<br>✅ High energy bonus active.' : ''}</div>`);
    }
    $editorInsights.innerHTML = insights.length > 0 ? insights.join('') : '<div class="insight-item">No insights available.</div>';
}

function renderAdaptationFeedback(result) {
    if (!$adaptationFeedback) return;
    const adaptation = result.adaptation;
    if (!adaptation || !adaptation.adapted) {
        if (adaptation?.recorded && !adaptation.adapted) {
            $adaptationFeedback.style.display = 'block';
            $adaptationFeedback.innerHTML = `<div class="adaptation-msg adaptation-msg--info">📊 Video recorded. ${adaptation.niche_qualification ? `Qualified as: <strong>${adaptation.niche_qualification}</strong>.` : ''} Weights adapt after 2+ videos.</div>`;
        } else { $adaptationFeedback.style.display = 'none'; }
        return;
    }
    const changes = adaptation.weight_changes;
    const changeLines = Object.entries(changes).map(([key, val]) => {
        const name = key.replace(/_/g,' ').replace(/\b\w/g, c=>c.toUpperCase());
        const diff = val.new - val.old; const arrow = diff > 0 ? '↑' : '↓';
        return `<span style="color:${diff>0?'var(--zone-green)':'var(--zone-yellow)'}">${name} ${arrow}${Math.abs(diff).toFixed(3)}</span>`;
    });
    $adaptationFeedback.style.display = 'block';
    $adaptationFeedback.innerHTML = `<div class="adaptation-msg adaptation-msg--success">🧠 <strong>Profile Updated!</strong> ${adaptation.niche_qualification ? `[${adaptation.niche_qualification}]` : ''}<div class="adaptation-changes">${changeLines.join(' • ')}</div></div>`;
}

function renderZoneCards(zones) {
    if (!zones || zones.length === 0) { $zoneCards.innerHTML = `<div class="zone-card" style="border-left:4px solid var(--zone-green)"><div class="zone-card__header"><div class="zone-card__time">🎉 No Risk Zones</div></div><p style="color:var(--text-secondary);font-size:14px">Great job!</p></div>`; return; }
    $zoneCards.innerHTML = zones.map((zone, i) => {
        const flagsHtml = (zone.flags || []).map(f => `<span class="flag-chip">${formatFlag(f)}</span>`).join('');
        return `<div class="zone-card zone-card--${zone.zone}" data-zone-idx="${i}"><div class="zone-card__header"><div class="zone-card__time">${formatTime(zone.start)} → ${formatTime(zone.end)}</div><div class="zone-card__score">${zone.avg_attention}</div></div><div class="zone-card__flags">${flagsHtml}</div><div class="zone-card__action">🔍 Click for details →</div></div>`;
    }).join('');
    $zoneCards.classList.add('stagger-children');
    // Attach zone detail click handlers
    document.querySelectorAll('.zone-card[data-zone-idx]').forEach(card => {
        card.addEventListener('click', () => {
            const idx = parseInt(card.getAttribute('data-zone-idx'));
            openZoneDetail(zones[idx], idx);
        });
    });
}

function seekToZone(time) { $videoPlayer.currentTime = time; $videoPlayer.play(); document.querySelector('.player-section').scrollIntoView({ behavior: 'smooth', block: 'center' }); }

// ═══════════════════════════════════════════════════════════
// BUTTON HANDLERS
// ═══════════════════════════════════════════════════════════

// Highlight Strengths
$('btn-highlight-strengths').addEventListener('click', (e) => {
    if (sharedGuard('Highlight mode')) return;
    highlightMode = !highlightMode;
    const btn = e.currentTarget; const segments = document.querySelectorAll('.timeline-segment');
    if (segments.length === 0) { highlightMode = false; return; }
    if (highlightMode) {
        document.querySelector('.timeline-wrapper')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        let g=0,o=0;
        segments.forEach(seg => { if (seg.getAttribute('data-zone')==='green') { seg.style.border='3px solid #22c55e'; seg.style.opacity='1'; seg.style.filter='brightness(1.5)'; g++; } else { seg.style.opacity='0.12'; seg.style.filter='grayscale(1) brightness(0.5)'; o++; }});
        btn.classList.add('btn--active'); btn.innerHTML = `💚 ON — ${g} strong / ${o} weak`;
    } else {
        segments.forEach(seg => { seg.style.border=''; seg.style.opacity=''; seg.style.filter=''; });
        btn.classList.remove('btn--active'); btn.innerHTML = '💚 Highlight Strengths';
    }
});

// Trim Drop-offs
$('btn-trim-dropoffs').addEventListener('click', async (e) => {
    if (sharedGuard('Auto-edit')) return;
    if (!analysisResult) return;
    const btn = e.currentTarget; btn.innerHTML = '⏳ Processing...'; btn.classList.add('btn--active'); btn.disabled = true;
    try {
        const res = await fetchWithRetry(`${API}/api/jobs/${currentJobId}/edit`, { method: 'POST' });
        if (!res.ok) throw new Error((await res.json()).detail || 'Failed');
        const editedBlob = await res.blob();
        const editedUrl = URL.createObjectURL(editedBlob);
        const a = document.createElement('a'); a.href = editedUrl; a.download = 'HookArchitect_AutoEdit.mp4'; a.click();
        btn.innerHTML = '✅ Downloaded';
        showToast('Auto-edit downloaded! Opening comparison mode...', 'success');
        // Open comparison mode
        startComparison($videoPlayer.src, editedUrl);
        setTimeout(() => { btn.innerHTML = '✂️ Trim <b>Boring Parts</b> (Auto-Edit)'; btn.classList.remove('btn--active'); btn.disabled = false; }, 5000);
    } catch (err) { showToast('Auto-edit failed: ' + err.message, 'error'); btn.innerHTML = '✂️ Trim <b>Boring Parts</b> (Auto-Edit)'; btn.classList.remove('btn--active'); btn.disabled = false; }
});

// Suggest Music
$('btn-suggest-music').addEventListener('click', () => {
    if (sharedGuard('Music suggestion')) return;
    if (!analysisResult?.virality_data) { alert("No viral audio data."); return; }
    const track = analysisResult.virality_data.recommended_track;
    if (track) window.open(`https://www.youtube.com/results?search_query=${encodeURIComponent(`${track.track_name} ${track.artist}`)}`, '_blank');
    else alert("No track recommended.");
});

// Deep Dive
$('btn-deep-dive').addEventListener('click', () => {
    if (sharedGuard('Deep dive')) return;
    if (!analysisResult) return;
    const existing = document.getElementById('deep-dive-card');
    if (existing) { existing.remove(); return; }
    const t = analysisResult.transcript_data || {}, v = analysisResult.virality_data || {}, e = analysisResult.emotion_data || {}, p = analysisResult.persona || {};
    const f = val => val !== undefined ? Number(val).toFixed(1) : '0.0';
    const card = document.createElement('div'); card.id = 'deep-dive-card'; card.className = 'insight-item'; card.style.borderLeftColor = '#3b82f6'; card.style.marginTop = '15px'; card.style.backgroundColor = 'rgba(15,23,42,0.4)';
    card.innerHTML = `<div style="display:flex;flex-direction:column;gap:10px;padding:5px"><div style="font-size:14px;font-weight:600;color:#e2e8f0;border-bottom:1px solid rgba(255,255,255,0.1);padding-bottom:5px">🗣️ Transcript</div><div style="padding-left:10px;font-size:13px;color:#a5b4fc"><div><b>Speech:</b> "${t.transcript||"None"}"</div><div><b>Keywords:</b> ${(t.keywords||[]).join(', ')||"—"}</div><div style="color:var(--zone-green)"><b>Score:</b> ${f(t.transcription_score)}/100</div></div><div style="font-size:14px;font-weight:600;color:#e2e8f0;border-bottom:1px solid rgba(255,255,255,0.1);padding-bottom:5px;margin-top:10px">🎭 Emotion</div><div style="padding-left:10px;font-size:13px;color:#a5b4fc"><div><b>Face:</b> ${e.dominant_facial_emotion||"—"}</div><div><b>Voice:</b> ${e.dominant_vocal_emotion||"—"}</div><div style="color:var(--zone-green)"><b>Alignment:</b> ${f(e.alignment_score)}/100</div></div><div style="font-size:14px;font-weight:600;color:#e2e8f0;border-bottom:1px solid rgba(255,255,255,0.1);padding-bottom:5px;margin-top:10px">🎵 Trend</div><div style="padding-left:10px;font-size:13px;color:#a5b4fc"><div><b>Track:</b> ${v.recommended_track?v.recommended_track.track_name+' by '+v.recommended_track.artist:"—"}</div><div><b>Why:</b> ${v.song_meaning||v.reasoning||"—"}</div><div style="color:var(--zone-green)"><b>Viral Score:</b> ${f(v.sound_score)}/100</div></div></div>`;
    $editorInsights.appendChild(card);
});

// ═══════════════════════════════════════════════════════════
// SCRIPT DOCTOR — DROP FIXER (Feature 7)
// ═══════════════════════════════════════════════════════════

$('btn-fix-drops').addEventListener('click', async () => {
    if (sharedGuard('Script doctor')) return;
    if (!analysisResult || !currentJobId) return;
    const btn = $('btn-fix-drops');
    btn.innerHTML = '🩺 Analyzing Drops...'; btn.disabled = true; btn.classList.add('btn--active');
    $scriptDoctorResults.style.display = 'block';
    $scriptDoctorResults.innerHTML = '<div class="script-doctor-loading">🧠 AI Script Doctor is analyzing your drop zones...</div>';
    try {
        const res = await fetch(`${API}/api/jobs/${currentJobId}/fix-drops`, { method: 'POST' });
        if (!res.ok) throw new Error((await res.json()).detail || 'Failed');
        const data = await res.json();
        renderScriptDoctorResults(data);
    } catch (err) {
        $scriptDoctorResults.innerHTML = `<div class="script-doctor-error">❌ ${err.message}</div>`;
    } finally { btn.innerHTML = '🩺 AI Script Doctor'; btn.disabled = false; btn.classList.remove('btn--active'); }
});

function renderScriptDoctorResults(data) {
    if (!data.suggestions || data.suggestions.length === 0) {
        $scriptDoctorResults.innerHTML = `<div class="script-doctor-success">✅ ${data.message || 'No critical drops found!'}</div>`;
        return;
    }
    let html = `<div class="script-doctor-header"><h3>🩺 Script Doctor — ${data.drop_zones_count} Drop Zone(s)</h3><p>${data.message}</p></div>`;
    data.suggestions.forEach((s, i) => {
        const faultsHtml = (s.faults||[]).map(f => `<span class="flag-chip">${formatFlag(f)}</span>`).join(' ');
        // Hook alternatives
        let hookAltsHtml = '';
        if (s.hook_alternatives && s.hook_alternatives.length > 0) {
            hookAltsHtml = `<div class="hook-alternatives"><div class="hook-alternatives__title">🎣 Hook Alternatives</div>`;
            s.hook_alternatives.forEach((alt, j) => {
                hookAltsHtml += `<div class="hook-alt-card" data-suggestion-idx="${i}" data-alt-idx="${j}">
                    <div class="hook-alt-card__num">${j+1}</div>
                    <div class="hook-alt-card__text">"${alt}"</div>
                    <button class="hook-apply-btn" onclick="applyHook(${s.start}, ${s.end}, '${alt.replace(/'/g, '')}', event)">⚡ Apply</button>
                </div>`;
            });
            hookAltsHtml += '</div>';
        }
        // Pacing
        const pacingHtml = s.pacing_recommendation ? `<div class="pacing-recommendation">🏃 <b>Pacing:</b> ${s.pacing_recommendation}</div>` : '';
        // Frame analysis (Visual AI)
        let frameAnalysisHtml = '';
        if (s.frame_analysis) {
            const fa = s.frame_analysis;
            frameAnalysisHtml = `
                <div class="frame-analysis-callout">
                    <div class="frame-analysis-callout__title">👁 Frame Analysis (Visual AI)</div>
                    ${fa.visual_cause ? `<div class="frame-analysis-callout__row"><span class="fa-label">Root cause:</span> ${fa.visual_cause}</div>` : ''}
                    ${fa.visual_fix ? `<div class="frame-analysis-callout__row"><span class="fa-label">Frame fix:</span> ${fa.visual_fix}</div>` : ''}
                    ${fa.severity ? `<div class="frame-analysis-callout__row"><span class="fa-label">Severity:</span> ${fa.severity}</div>` : ''}
                </div>`;
        }
        html += `
        <div class="script-doctor-card">
            <div class="script-doctor-card__header">
                <span class="script-doctor-card__time">🕐 ${s.start_formatted} → ${s.end_formatted}</span>
                <span class="script-doctor-card__score">Score: ${s.avg_attention?.toFixed(0) || '?'}/100</span>
                <span class="script-doctor-card__source">${s.source === 'gemini' ? '🤖 Gemini AI' : '📋 Rule-Based'}</span>
            </div>
            ${faultsHtml ? `<div class="script-doctor-card__faults">${faultsHtml}</div>` : ''}
            ${frameAnalysisHtml}
            <div class="script-doctor-comparison">
                <div class="script-doctor-col script-doctor-col--current">
                    <div class="script-doctor-col__label">📜 Current</div>
                    <div class="script-doctor-col__text">${s.current_script}</div>
                </div>
                <div class="script-doctor-arrow">→</div>
                <div class="script-doctor-col script-doctor-col--ai">
                    <div class="script-doctor-col__label">✨ AI Suggestion</div>
                    <div class="script-doctor-col__text">${s.ai_suggestion}</div>
                </div>
            </div>
            <div class="script-doctor-card__format"><b>🎬 Format Recommendation:</b> ${s.format_recommendation}</div>
            <div class="script-doctor-card__reasoning"><b>💡 Why:</b> ${s.reasoning}</div>
            ${hookAltsHtml}
            ${pacingHtml}
            <div class="hook-preview-slot" id="hook-preview-${i}"></div>
        </div>`;
    });
    $scriptDoctorResults.innerHTML = html;
}

// ═══════════════════════════════════════════════════════════
// HOOK STRENGTH SCORER (Phase 3 Feature 2)
// ═══════════════════════════════════════════════════════════

let hookGaugeChart = null;

function renderHookScore(result) {
    const hs = result.hook_score;
    const section = $('hook-score-section');
    if (!hs || !section) { if (section) section.style.display = 'none'; return; }
    section.style.display = 'block';

    // Grade badge
    const gradeEl = $('hook-grade');
    gradeEl.textContent = hs.grade;
    const scoreVal = hs.hook_score;
    gradeEl.style.color = scoreVal >= 70 ? 'var(--zone-green)' : scoreVal >= 50 ? 'var(--zone-yellow)' : 'var(--zone-red)';

    // Score value
    const scoreNumEl = $('hook-score-value');
    animateNumber(scoreNumEl, 0, Math.round(scoreVal), 1200);

    // Gauge canvas (doughnut chart)
    const gaugeCanvas = $('hook-gauge-canvas');
    if (hookGaugeChart) hookGaugeChart.destroy();
    const gaugeColor = scoreVal >= 70 ? '#22c55e' : scoreVal >= 50 ? '#f59e0b' : '#ef4444';
    hookGaugeChart = new Chart(gaugeCanvas, {
        type: 'doughnut',
        data: {
            datasets: [{
                data: [scoreVal, 100 - scoreVal],
                backgroundColor: [gaugeColor, 'rgba(255,255,255,0.04)'],
                borderWidth: 0,
            }]
        },
        options: {
            responsive: false, cutout: '78%', rotation: -90, circumference: 180,
            plugins: { legend: { display: false }, tooltip: { enabled: false } },
        }
    });

    // Breakdown bars
    const bd = hs.breakdown;
    const breakdownEl = $('hook-breakdown');
    breakdownEl.innerHTML = ['transcript', 'visual', 'audio', 'face'].map(key => {
        const val = bd[key] || 0;
        const clr = val >= 65 ? 'var(--zone-green)' : val >= 40 ? 'var(--zone-yellow)' : 'var(--zone-red)';
        const labels = { transcript: '📝 Transcript Hook', visual: '👁 Visual Energy', audio: '🔊 Audio Punch', face: '👤 Face Presence' };
        return `<div class="hook-breakdown-item">
            <div class="hook-breakdown-item__label">${labels[key]}</div>
            <div class="hook-breakdown-item__bar"><div class="hook-breakdown-item__fill" style="width:${val}%;background:${clr};"></div></div>
            <div class="hook-breakdown-item__value">${val.toFixed(0)}</div>
        </div>`;
    }).join('');

    // Suggestions
    const sugEl = $('hook-suggestions');
    if (hs.suggestions && hs.suggestions.length > 0) {
        sugEl.innerHTML = '<div class="hook-suggestions-title">💡 How to improve your hook:</div>' +
            hs.suggestions.map(s => `<div class="hook-suggestion-item"><span class="hook-suggestion-cat">${s.category}</span> ${s.text}</div>`).join('');
    } else {
        sugEl.innerHTML = '<div class="hook-suggestions-title">✅ Your hook is strong — no major improvements needed!</div>';
    }

    // First words
    const fwEl = $('hook-first-words');
    if (hs.first_words && hs.first_words !== '(no speech detected)') {
        fwEl.style.display = 'block';
        fwEl.innerHTML = `<b>Opening words:</b> <em>"${hs.first_words}..."</em>`;
    } else {
        fwEl.style.display = 'none';
    }

    // Visual AI Hook Critique (LLaVA)
    const critiqueEl = $('hook-visual-critique');
    if (critiqueEl) {
        const vc = result.multimodal_hook_critique;
        if (vc && result.multimodal_llm_active) {
            critiqueEl.style.display = 'block';
            critiqueEl.innerHTML = `
                <div class="visual-ai-badge">👁 Visual AI</div>
                <div class="visual-critique-grid">
                    ${vc.first_impression ? `<div class="vcrit-row"><span class="vcrit-label">🎯 First impression</span><span class="vcrit-val">${vc.first_impression}</span></div>` : ''}
                    ${vc.visual_weakness ? `<div class="vcrit-row"><span class="vcrit-label">⚠️ Weakness</span><span class="vcrit-val">${vc.visual_weakness}</span></div>` : ''}
                    ${vc.visual_fix ? `<div class="vcrit-row"><span class="vcrit-label">✅ Visual fix</span><span class="vcrit-val">${vc.visual_fix}</span></div>` : ''}
                    ${vc.hook_strength !== undefined ? `<div class="vcrit-row"><span class="vcrit-label">💪 Visual hook strength</span><span class="vcrit-val">${vc.hook_strength}/10</span></div>` : ''}
                </div>`;
        } else {
            critiqueEl.style.display = 'none';
        }
    }
}

// ═══════════════════════════════════════════════════════════
// EMOTION ARC MAPPING (Phase 3 Feature 1)
// ═══════════════════════════════════════════════════════════

let emotionArcChart = null;

function renderEmotionArc(result) {
    const arc = result.emotion_arc;
    const section = $('emotion-arc-section');
    if (!arc || !arc.arc_points || !section) { if (section) section.style.display = 'none'; return; }
    section.style.display = 'block';

    // Summary
    const summaryEl = $('emotion-arc-summary');
    summaryEl.innerHTML = `<div class="emotion-arc-summary-text">${arc.arc_summary}</div>
        <div class="emotion-arc-shape-badge">
            <span class="arc-shape-label">Arc Shape:</span>
            <span class="arc-shape-value">${arc.arc_shape}</span>
        </div>`;

    // Phases
    const phasesEl = $('emotion-arc-phases');
    const phaseIcons = { hook: '🎣', build: '📈', peak: '⛰', valley: '📉', recovery: '🔄', outro: '🏁' };
    phasesEl.innerHTML = arc.phases.map(p =>
        `<span class="arc-phase-chip"><span>${phaseIcons[p.phase] || '📍'}</span> ${p.label}</span>`
    ).join('');

    // Chart
    const canvas = $('emotion-arc-chart');
    if (emotionArcChart) emotionArcChart.destroy();

    const labels = arc.arc_points.map(p => formatTime(p.t));
    const intensities = arc.arc_points.map(p => p.intensity);

    // Build phase background bands
    const phaseColors = {
        hook: 'rgba(6,182,212,0.08)', build: 'rgba(139,92,246,0.06)',
        peak: 'rgba(34,197,94,0.1)', valley: 'rgba(239,68,68,0.08)',
        recovery: 'rgba(245,158,11,0.06)', outro: 'rgba(100,116,139,0.06)'
    };

    // Transition annotations
    const annotations = {};
    (arc.transitions || []).forEach((tr, i) => {
        annotations[`tr${i}`] = {
            type: 'line', xMin: tr.t, xMax: tr.t, borderColor: tr.type === 'drop_point' ? 'rgba(239,68,68,0.5)' : 'rgba(34,197,94,0.5)',
            borderWidth: 2, borderDash: [4, 4],
            label: { display: true, content: tr.type === 'drop_point' ? '↓ Drop' : '↑ Recovery', position: 'start', font: { size: 10 } }
        };
    });

    emotionArcChart = new Chart(canvas, {
        type: 'line',
        data: {
            labels,
            datasets: [
                {
                    label: 'Emotional Intensity',
                    data: intensities,
                    borderColor: '#8b5cf6',
                    backgroundColor: 'rgba(139,92,246,0.1)',
                    fill: true, tension: 0.4, pointRadius: 2, pointHoverRadius: 5,
                    borderWidth: 2,
                },
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            scales: {
                y: { min: 0, max: 100, title: { display: true, text: 'Intensity', color: '#64748b', font: { size: 11 } }, grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#64748b' } },
                x: { title: { display: true, text: 'Time', color: '#64748b', font: { size: 11 } }, grid: { display: false }, ticks: { color: '#64748b', maxTicksLimit: 15 } },
            },
            plugins: {
                legend: { labels: { color: '#94a3b8' } },
                tooltip: {
                    callbacks: {
                        afterLabel: (ctx) => {
                            const pt = arc.arc_points[ctx.dataIndex];
                            return pt ? `Emotion: ${pt.emotion}` : '';
                        }
                    }
                }
            },
        }
    });

    // Transitions list
    const transEl = $('emotion-arc-transitions');
    if (arc.transitions && arc.transitions.length > 0) {
        transEl.innerHTML = '<div class="arc-transitions-title">⚡ Emotional Transitions:</div>' +
            arc.transitions.map(tr => {
                const icon = tr.type === 'drop_point' ? '🔴' : '🟢';
                return `<div class="arc-transition-item">${icon} <b>${formatTime(tr.t)}</b> — ${tr.description}</div>`;
            }).join('');
    } else {
        transEl.innerHTML = '<div class="arc-transitions-title">✅ Smooth emotional flow — no jarring transitions.</div>';
    }
}

// ═══════════════════════════════════════════════════════════
// RETENTION CURVE PREDICTOR (Phase 3 Feature 3)
// ═══════════════════════════════════════════════════════════

let retentionChart = null;

function renderRetentionCurve(result) {
    const rc = result.retention_curve;
    const section = $('retention-curve-section');
    if (!rc || !rc.curve_points || !section) { if (section) section.style.display = 'none'; return; }
    section.style.display = 'block';

    // Metrics bar
    const metricsEl = $('retention-curve-metrics');
    const gradeColor = rc.predicted_avg_retention >= 60 ? 'var(--zone-green)' : rc.predicted_avg_retention >= 40 ? 'var(--zone-yellow)' : 'var(--zone-red)';
    metricsEl.innerHTML = `
        <div class="retention-metrics-grid">
            <div class="retention-metric">
                <div class="retention-metric__label">Avg Retention</div>
                <div class="retention-metric__value" style="color:${gradeColor}">${rc.predicted_avg_retention}%</div>
            </div>
            <div class="retention-metric">
                <div class="retention-metric__label">Watch-Through</div>
                <div class="retention-metric__value">${rc.predicted_watch_through_rate}%</div>
            </div>
            <div class="retention-metric">
                <div class="retention-metric__label">Retention Grade</div>
                <div class="retention-metric__value" style="color:${gradeColor}">${rc.retention_grade}</div>
            </div>
        </div>`;

    // Chart
    const canvas = $('retention-curve-chart');
    if (retentionChart) retentionChart.destroy();
    const labels = rc.curve_points.map(p => formatTime(p.t));
    const retData = rc.curve_points.map(p => p.retention_pct);

    // YouTube-style gradient
    const ctx = canvas.getContext('2d');
    const gradient = ctx.createLinearGradient(0, 0, 0, 300);
    gradient.addColorStop(0, 'rgba(6,182,212,0.3)');
    gradient.addColorStop(0.5, 'rgba(139,92,246,0.15)');
    gradient.addColorStop(1, 'rgba(239,68,68,0.05)');

    retentionChart = new Chart(canvas, {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: 'Viewer Retention %',
                data: retData,
                borderColor: '#06b6d4',
                backgroundColor: gradient,
                fill: true, tension: 0.3, pointRadius: 0, pointHoverRadius: 4,
                borderWidth: 2,
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            scales: {
                y: { min: 0, max: 105, title: { display: true, text: 'Viewers Remaining (%)', color: '#64748b', font: { size: 11 } }, grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#64748b', callback: v => v + '%' } },
                x: { title: { display: true, text: 'Time', color: '#64748b', font: { size: 11 } }, grid: { display: false }, ticks: { color: '#64748b', maxTicksLimit: 15 } },
            },
            plugins: {
                legend: { labels: { color: '#94a3b8' } },
                tooltip: { callbacks: { label: (ctx) => `${ctx.parsed.y.toFixed(1)}% viewers remaining` } },
            },
        }
    });

    // Key moments
    const momentsEl = $('retention-curve-moments');
    if (rc.key_moments && rc.key_moments.length > 0) {
        momentsEl.innerHTML = '<div class="retention-moments-title">📌 Key Moments:</div>' +
            rc.key_moments.map(m => {
                const icon = m.event === 'sharp_drop' ? '🔴' : m.event === 'stabilization' ? '🟢' : '📍';
                return `<div class="retention-moment-item">${icon} <b>${formatTime(m.t)}</b> — ${m.description}</div>`;
            }).join('');
    } else {
        momentsEl.innerHTML = '';
    }

    // Sections analysis
    const sectionsEl = $('retention-curve-sections');
    const sa = rc.sections_analysis;
    if (sa) {
        sectionsEl.innerHTML = `
        <div class="retention-sections-title">📊 Section Breakdown:</div>
        <div class="retention-sections-grid">
            <div class="retention-section-chip">
                <div class="retention-section-chip__label">Opening</div>
                <div class="retention-section-chip__value">${sa.opening.start_retention?.toFixed(0) || 100}% → ${sa.opening.end_retention?.toFixed(0) || '?'}%</div>
                <div class="retention-section-chip__drop">-${sa.opening.drop?.toFixed(1) || 0}%</div>
            </div>
            <div class="retention-section-chip">
                <div class="retention-section-chip__label">Middle</div>
                <div class="retention-section-chip__value">${sa.middle.start_retention?.toFixed(0) || '?'}% → ${sa.middle.end_retention?.toFixed(0) || '?'}%</div>
                <div class="retention-section-chip__drop">-${sa.middle.drop?.toFixed(1) || 0}%</div>
            </div>
            <div class="retention-section-chip">
                <div class="retention-section-chip__label">Closing</div>
                <div class="retention-section-chip__value">${sa.closing.start_retention?.toFixed(0) || '?'}% → ${sa.closing.end_retention?.toFixed(0) || '?'}%</div>
                <div class="retention-section-chip__drop">-${sa.closing.drop?.toFixed(1) || 0}%</div>
            </div>
        </div>`;
    }
}

// ═══════════════════════════════════════════════════════════
// UTILITIES
// ═══════════════════════════════════════════════════════════

function formatTime(seconds) { const m = Math.floor(seconds / 60); const s = Math.floor(seconds % 60); return `${m}:${String(s).padStart(2, '0')}`; }
function formatFlag(flag) {
    const map = { low_energy:'🔇 Low Energy', monotone:'😐 Monotone', silence:'🔕 Silence', slow_pacing:'🐌 Slow', static:'📸 Static', no_face:'👻 No Face', no_cut:'✂️ No Cut', high_energy:'🔊 Energy', expressive:'🎤 Expressive', fast_pacing:'⚡ Fast', high_motion:'🏃 Motion', face_anchor:'👤 Face', scene_cut:'🎬 Cut', energy_bonus:'🔥 Bonus' };
    return map[flag] || flag;
}
function animateNumber(el, from, to, duration) {
    const start = performance.now();
    const update = (now) => { const p = Math.min((now - start) / duration, 1); el.textContent = Math.round(from + (to - from) * (1 - Math.pow(1 - p, 3))); if (p < 1) requestAnimationFrame(update); };
    requestAnimationFrame(update);
}


// ═══════════════════════════════════════════════════════════
// TOAST NOTIFICATION SYSTEM
// ═══════════════════════════════════════════════════════════

function showToast(message, type = 'info', duration = 4000) {
    const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
    const toast = document.createElement('div');
    toast.className = `toast toast--${type}`;
    toast.innerHTML = `<span class="toast__icon">${icons[type] || icons.info}</span><span class="toast__text">${message}</span><button class="toast__close" onclick="this.parentElement.classList.add('toast--exiting');setTimeout(()=>this.parentElement.remove(),300)">&times;</button>`;
    if ($toastContainer) $toastContainer.appendChild(toast);
    toast.addEventListener('click', () => { toast.classList.add('toast--exiting'); setTimeout(() => toast.remove(), 300); });
    setTimeout(() => { if (toast.parentElement) { toast.classList.add('toast--exiting'); setTimeout(() => toast.remove(), 300); } }, duration);
}


// ═══════════════════════════════════════════════════════════
// FETCH WITH RETRY (exponential backoff)
// ═══════════════════════════════════════════════════════════

async function fetchWithRetry(url, options = {}, retries = 3) {
    for (let attempt = 0; attempt < retries; attempt++) {
        try {
            const res = await fetch(url, options);
            if (res.ok || res.status < 500) return res;
            throw new Error(`Server error: ${res.status}`);
        } catch (err) {
            if (attempt === retries - 1) throw err;
            const delay = Math.pow(2, attempt) * 500;
            showToast(`Retrying in ${delay/1000}s... (${attempt+1}/${retries})`, 'warning', delay);
            await new Promise(r => setTimeout(r, delay));
        }
    }
}


// ═══════════════════════════════════════════════════════════
// ZONE DETAIL MODAL (Phase 2)
// ═══════════════════════════════════════════════════════════

const $zoneDetailModal = $('zone-detail-modal');
const $zoneDetailTitle = $('zone-detail-title');
const $zoneDetailSignals = $('zone-detail-signals');
const $zoneDetailFaults = $('zone-detail-faults');
const $zoneDetailStrengths = $('zone-detail-strengths');
const $zoneDetailAI = $('zone-detail-ai');

if ($('btn-close-zone-detail')) $('btn-close-zone-detail').addEventListener('click', closeZoneDetail);
if ($zoneDetailOverlay) $zoneDetailOverlay.addEventListener('click', (e) => { if (e.target === $zoneDetailOverlay) closeZoneDetail(); });

function openZoneDetail(zone, zoneIndex) {
    if (!$zoneDetailOverlay || !analysisResult) return;
    $zoneDetailOverlay.classList.add('active');
    
    const start = zone.start, end = zone.end;
    $zoneDetailTitle.textContent = `${zone.zone.toUpperCase()} Zone — ${formatTime(start)} → ${formatTime(end)}`;
    
    // Get per-second signals for this zone
    const zonePoints = (analysisResult.timeline || []).filter(p => p.t >= start && p.t < end);
    const avgAudio = zonePoints.reduce((s,p) => s + (p.audio_score||0), 0) / Math.max(zonePoints.length, 1);
    const avgVisual = zonePoints.reduce((s,p) => s + (p.visual_score||0), 0) / Math.max(zonePoints.length, 1);
    const avgTranscript = zonePoints.reduce((s,p) => s + (p.transcript_score||0), 0) / Math.max(zonePoints.length, 1);
    
    const scoreColor = (v) => v >= 65 ? 'var(--zone-green)' : v >= 40 ? 'var(--zone-yellow)' : 'var(--zone-red)';
    
    $zoneDetailSignals.innerHTML = [
        { icon: '🔊', label: 'Audio', value: avgAudio },
        { icon: '👁', label: 'Visual', value: avgVisual },
        { icon: '📝', label: 'Script', value: avgTranscript },
    ].map(s => `<div class="zone-signal-card"><div class="zone-signal-card__icon">${s.icon}</div><div class="zone-signal-card__label">${s.label}</div><div class="zone-signal-card__value" style="color:${scoreColor(s.value)}">${s.value.toFixed(0)}</div></div>`).join('');
    
    // Mini chart
    renderZoneDetailChart(zonePoints);
    
    // Faults & Strengths
    const faults = new Set(), strengths = new Set();
    zonePoints.forEach(p => {
        (p.faults||[]).forEach(f => faults.add(typeof f === 'object' ? f.label : f));
        (p.strengths||[]).forEach(s => strengths.add(typeof s === 'object' ? s.label : s));
    });
    $zoneDetailFaults.innerHTML = faults.size > 0 ? [...faults].map(f => `<span class="zone-fault-chip">🔴 ${formatFlag(f)}</span>`).join('') : '<span style="color:var(--text-muted);font-size:13px">No faults detected</span>';
    $zoneDetailStrengths.innerHTML = strengths.size > 0 ? [...strengths].map(s => `<span class="zone-strength-chip">🟢 ${formatFlag(s)}</span>`).join('') : '<span style="color:var(--text-muted);font-size:13px">No notable strengths</span>';
    
    // Fetch AI insights
    $zoneDetailAI.innerHTML = '<div class="zone-detail-ai__loading">🧠 Loading AI insights...</div>';
    fetchZoneAIInsights(zoneIndex);
}

function closeZoneDetail() {
    if ($zoneDetailOverlay) $zoneDetailOverlay.classList.remove('active');
}

function renderZoneDetailChart(zonePoints) {
    const canvas = $('zone-detail-chart');
    if (!canvas) return;
    if (zoneDetailChart) zoneDetailChart.destroy();
    const labels = zonePoints.map(p => formatTime(p.t));
    zoneDetailChart = new Chart(canvas, {
        type: 'line',
        data: { labels, datasets: [
            { label: 'Audio', data: zonePoints.map(p => p.audio_score||0), borderColor: '#8b5cf6', borderWidth: 2, tension: 0.4, pointRadius: 2 },
            { label: 'Visual', data: zonePoints.map(p => p.visual_score||0), borderColor: '#ec4899', borderWidth: 2, tension: 0.4, pointRadius: 2 },
            { label: 'Attention', data: zonePoints.map(p => p.attention||0), borderColor: '#06b6d4', borderWidth: 3, tension: 0.4, pointRadius: 2, fill: { target: 'origin', above: 'rgba(6,182,212,0.08)' } },
        ]},
        options: {
            responsive: true, maintainAspectRatio: false,
            scales: { y: { min: 0, max: 100, grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#64748b', font: { size: 10 } } }, x: { grid: { display: false }, ticks: { color: '#64748b', font: { size: 10 } } } },
            plugins: { legend: { labels: { color: '#94a3b8', boxWidth: 10, font: { size: 11 } } } },
        },
    });
}

async function fetchZoneAIInsights(zoneIndex) {
    if (!currentJobId) return;
    // Use cached insights if available
    if (cachedAIInsights) {
        renderZoneAIInsight(cachedAIInsights.find(i => i.zone_index === zoneIndex));
        return;
    }
    try {
        const res = await fetchWithRetry(`${API}/api/jobs/${currentJobId}/ai-insights`, { method: 'POST' });
        if (!res.ok) throw new Error('Failed to get insights');
        const data = await res.json();
        cachedAIInsights = data.insights;
        renderZoneAIInsight(data.insights.find(i => i.zone_index === zoneIndex));
    } catch (err) {
        $zoneDetailAI.innerHTML = `<div style="color:var(--zone-red);font-size:13px">❌ ${err.message}</div>`;
    }
}

function renderZoneAIInsight(insight) {
    if (!insight) { $zoneDetailAI.innerHTML = '<div style="color:var(--text-muted);font-size:13px">No AI insight available for this zone.</div>'; return; }
    const actionsHtml = (insight.fix_actions||[]).map(a => {
        const impactClass = a.impact === 'high' ? 'high' : a.impact === 'medium' ? 'medium' : 'low';
        return `<div class="zone-ai-action"><span class="zone-ai-action__impact zone-ai-action__impact--${impactClass}">${a.impact}</span><span>${a.action}</span></div>`;
    }).join('');
    const diagnosisHtml = insight.signal_diagnosis ? `<div style="margin-top:8px;font-size:12px;color:var(--text-muted)">📊 <b>Weakest signal:</b> ${insight.signal_diagnosis.weakest} — ${insight.signal_diagnosis.explanation}</div>` : '';
    $zoneDetailAI.innerHTML = `
        <div class="zone-ai-advice"><strong>🧠 AI Coach:</strong> ${insight.overall_advice}</div>
        ${diagnosisHtml}
        <div class="zone-ai-actions">${actionsHtml}</div>
        <div style="margin-top:10px;font-size:11px;color:var(--text-muted);text-align:right">${insight.source === 'gemini' ? '🤖 Powered by Gemini AI' : '📋 Rule-based analysis'}</div>`;
}


// ═══════════════════════════════════════════════════════════
// VIDEO COMPARISON MODE (Phase 3)
// ═══════════════════════════════════════════════════════════

function startComparison(originalUrl, editedUrl) {
    const section = $('comparison-section');
    const originalVid = $('comparison-original');
    const editedVid = $('comparison-edited');
    if (!section || !originalVid || !editedVid) return;
    
    originalVid.src = originalUrl;
    editedVid.src = editedUrl;
    section.style.display = 'block';
    section.scrollIntoView({ behavior: 'smooth', block: 'start' });
    
    // Render timeline diff
    renderComparisonTimeline();
    
    showToast('Comparison mode active — play both videos synced!', 'info');
}

function renderComparisonTimeline() {
    const ct = $('comparison-timeline');
    if (!ct || !analysisResult) return;
    const timeline = analysisResult.timeline || [];
    if (timeline.length === 0) return;
    const segWidth = 100 / timeline.length;
    let html = '<div style="display:flex;height:24px;border-radius:6px;overflow:hidden;">';
    timeline.forEach(p => {
        const color = p.zone === 'red' ? 'rgba(239,68,68,0.6)' : p.zone === 'yellow' ? 'rgba(245,158,11,0.5)' : 'rgba(34,197,94,0.5)';
        const striped = p.zone === 'red' ? 'background-image:repeating-linear-gradient(45deg,transparent,transparent 3px,rgba(0,0,0,0.3) 3px,rgba(0,0,0,0.3) 6px);' : '';
        html += `<div style="width:${segWidth}%;background:${color};${striped}" title="${formatTime(p.t)} — ${p.zone}"></div>`;
    });
    html += '</div><div style="display:flex;justify-content:space-between;font-size:10px;color:var(--text-muted);margin-top:4px;"><span>Red = removed</span><span>Green/Yellow = kept</span></div>';
    ct.innerHTML = html;
}

// Sync controls
if ($('btn-sync-play')) $('btn-sync-play').addEventListener('click', () => {
    const orig = $('comparison-original'), edit = $('comparison-edited');
    if (orig) orig.play();
    if (edit) edit.play();
});
if ($('btn-sync-pause')) $('btn-sync-pause').addEventListener('click', () => {
    const orig = $('comparison-original'), edit = $('comparison-edited');
    if (orig) orig.pause();
    if (edit) edit.pause();
});
if ($('btn-close-comparison')) $('btn-close-comparison').addEventListener('click', () => {
    const section = $('comparison-section');
    if (section) section.style.display = 'none';
    const orig = $('comparison-original'), edit = $('comparison-edited');
    if (orig) { orig.pause(); orig.src = ''; }
    if (edit) { edit.pause(); edit.src = ''; }
});


// ═══════════════════════════════════════════════════════════
// GOAL KEYWORDS PROCESSING
// ═══════════════════════════════════════════════════════════

const $goalTextInput = $('goal-text-input');
const $btnProcessGoal = $('btn-process-goal');
const $goalProcessing = $('goal-processing');
const $goalKeywords = $('goal-keywords');

if ($goalTextInput) {
    $goalTextInput.addEventListener('input', () => {
        $btnProcessGoal.disabled = !$goalTextInput.value.trim();
    });
    $goalTextInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && $goalTextInput.value.trim()) {
            e.preventDefault();
            $btnProcessGoal.click();
        }
    });
}

if ($btnProcessGoal) {
    $btnProcessGoal.addEventListener('click', async () => {
        const text = $goalTextInput.value.trim();
        if (!text) return;
        
        $btnProcessGoal.disabled = true;
        $goalProcessing.style.display = 'flex';
        $goalKeywords.style.display = 'none';
        
        try {
            const res = await fetch(`${API}/api/goals/process`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ goal_text: text }),
            });
            if (!res.ok) throw new Error((await res.json()).detail || 'Failed');
            const data = await res.json();
            
            activeGoalText = text;
            activeGoalKeywords = data.keywords || [];
            
            // Render keywords
            let html = `<div class="goal-keywords__title">🎯 Evaluation Keywords</div>`;
            html += `<div class="goal-keywords__chips">`;
            (data.keywords || []).forEach(k => {
                html += `<span class="goal-keyword-chip">🔑 ${k}</span>`;
            });
            html += `</div>`;
            if (data.category) {
                html += `<span class="goal-category-badge">${data.category}</span> `;
            }
            if (data.summary) {
                html += `<span style="font-size:12px;color:var(--text-muted);margin-left:6px">${data.summary}</span>`;
            }
            if (data.evaluation_criteria && data.evaluation_criteria.length > 0) {
                html += `<ul class="goal-criteria">`;
                data.evaluation_criteria.forEach(c => { html += `<li>${c}</li>`; });
                html += `</ul>`;
            }
            $goalKeywords.innerHTML = html;
            $goalKeywords.style.display = 'block';
            showToast(`Extracted ${data.keywords?.length || 0} evaluation keywords!`, 'success');
        } catch (err) {
            showToast('Failed to process goal: ' + err.message, 'error');
            $goalKeywords.innerHTML = `<div style="color:var(--zone-red);font-size:13px">❌ ${err.message}</div>`;
            $goalKeywords.style.display = 'block';
        } finally {
            $goalProcessing.style.display = 'none';
            $btnProcessGoal.disabled = false;
        }
    });
}

function renderGoalAlignment(result) {
    if (!result.goal_keywords || result.goal_keywords.length === 0) return;
    const banner = document.createElement('div');
    banner.className = 'persona-banner';
    banner.style.display = 'block';
    banner.style.marginTop = '12px';
    const score = result.goal_alignment_score ?? 0;
    const cls = score >= 70 ? '🟢' : score >= 40 ? '🟡' : '🔴';
    banner.innerHTML = `<div class="persona-banner__content"><span class="persona-banner__icon">🎯</span><span class="persona-banner__text">Goal Alignment: <strong>${score}/100</strong> ${cls} — Keywords: ${result.goal_keywords.join(', ')}${result.goal_evaluation_summary ? ` — ${result.goal_evaluation_summary}` : ''}</span></div>`;
    $personaBanner.insertAdjacentElement('afterend', banner);
}


// ═══════════════════════════════════════════════════════════
// YOUTUBE REFERENCE DOWNLOAD
// ═══════════════════════════════════════════════════════════

const $youtubeUrlInput = $('youtube-url-input');
const $btnAddYoutube = $('btn-add-youtube');
const $youtubeProgress = $('youtube-progress');
const $ytProgressFill = $('yt-progress-fill');
const $ytProgressMsg = $('yt-progress-msg');

if ($youtubeUrlInput) {
    $youtubeUrlInput.addEventListener('input', () => {
        const url = $youtubeUrlInput.value.trim();
        $btnAddYoutube.disabled = !url || !url.match(/youtube\.com|youtu\.be/);
    });
    $youtubeUrlInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !$btnAddYoutube.disabled) {
            e.preventDefault();
            $btnAddYoutube.click();
        }
    });
}

if ($btnAddYoutube) {
    $btnAddYoutube.addEventListener('click', async () => {
        if (!activeProfileId) { showToast('Please create a profile first.', 'warning'); return; }
        const url = $youtubeUrlInput.value.trim();
        if (!url) return;
        
        $btnAddYoutube.disabled = true;
        $btnAddYoutube.textContent = '⏳ Downloading...';
        $youtubeProgress.style.display = 'block';
        $ytProgressFill.style.width = '5%';
        $ytProgressMsg.textContent = 'Starting YouTube download...';
        
        try {
            const res = await fetch(`${API}/api/profiles/${activeProfileId}/references/youtube`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url }),
            });
            if (!res.ok) throw new Error((await res.json()).detail || 'Failed');
            const data = await res.json();
            pollYouTubeProgress(data.job_id);
        } catch (err) {
            showToast('YouTube download failed: ' + err.message, 'error');
            $ytProgressMsg.textContent = '❌ ' + err.message;
            setTimeout(() => { $youtubeProgress.style.display = 'none'; }, 3000);
        } finally {
            $btnAddYoutube.textContent = '🔗 Add from YouTube';
            $btnAddYoutube.disabled = false;
        }
    });
}

function pollYouTubeProgress(jobId) {
    const poll = async () => {
        try {
            const res = await fetch(`${API}/api/jobs/${jobId}/status`);
            const data = await res.json();
            $ytProgressFill.style.width = `${data.progress || 0}%`;
            $ytProgressMsg.textContent = data.message || '';
            if (data.status === 'complete') {
                $youtubeProgress.style.display = 'none';
                $youtubeUrlInput.value = '';
                checkReferencePortal();
                showToast('YouTube reference processed!', 'success');
                return;
            }
            if (data.status === 'failed') {
                $ytProgressMsg.textContent = '❌ ' + (data.message || 'Failed');
                showToast('YouTube reference failed: ' + (data.message || ''), 'error');
                setTimeout(() => { $youtubeProgress.style.display = 'none'; }, 4000);
                return;
            }
        } catch (e) {}
        setTimeout(poll, 2000);
    };
    poll();
}


// ═══════════════════════════════════════════════════════════
// PDF REPORT DOWNLOAD
// ═══════════════════════════════════════════════════════════

const $btnDownloadPdf = $('btn-download-pdf');
const $btnNewAnalysis = $('btn-new-analysis');
const $btnShareReport = $('btn-share-report');
const $btnCompareAnalyses = $('btn-compare-analyses');

if ($btnDownloadPdf) {
    $btnDownloadPdf.addEventListener('click', async () => {
        if (sharedGuard('PDF export')) return;
        if (!currentJobId) { showToast('No analysis results available.', 'warning'); return; }
        
        $btnDownloadPdf.disabled = true;
        $btnDownloadPdf.textContent = '⏳ Generating PDF...';
        
        try {
            const res = await fetch(`${API}/api/jobs/${currentJobId}/report-pdf`);
            if (!res.ok) {
                let detail = 'PDF generation failed';
                try { const err = await res.json(); detail = err.detail || detail; } catch(e) { detail = `Server error (${res.status})`; }
                throw new Error(detail);
            }
            
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `HookArchitect_Report.pdf`;
            a.click();
            URL.revokeObjectURL(url);
            
            showToast('PDF report downloaded!', 'success');
        } catch (err) {
            showToast('PDF download failed: ' + err.message, 'error');
        } finally {
            $btnDownloadPdf.disabled = false;
            $btnDownloadPdf.textContent = '📄 Download PDF Report';
        }
    });
}

if ($btnNewAnalysis) {
    $btnNewAnalysis.addEventListener('click', () => {
        $resultsSection.classList.remove('active');
        $uploadSection.style.display = '';
        if (activeProfileId) checkReferencePortal();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });
}

if ($btnShareReport) {
    $btnShareReport.addEventListener('click', async () => {
        if (isSharedView) {
            showToast('Sharing is disabled in read-only shared view.', 'warning');
            return;
        }
        if (!currentJobId) return;
        try {
            const res = await fetch(`${API}/api/results/${currentJobId}/share`, { method: 'POST' });
            if (!res.ok) throw new Error((await res.json()).detail || 'Share failed');
            const data = await res.json();
            const url = `${window.location.origin}${data.share_url}`;
            await navigator.clipboard.writeText(url);
            showToast('Share URL copied to clipboard!', 'success');
        } catch (err) {
            showToast(`Share failed: ${err.message}`, 'error');
        }
    });
}

function rememberCompletedAnalysis(result) {
    if (!result || !result.job_id) return;
    const existing = completedAnalyses.find(r => r.job_id === result.job_id);
    if (!existing) completedAnalyses.push(result);
    if ($btnCompareAnalyses) $btnCompareAnalyses.disabled = completedAnalyses.length < 2;
}

if ($btnCompareAnalyses) {
    $btnCompareAnalyses.disabled = true;
    $btnCompareAnalyses.addEventListener('click', async () => {
        if (isSharedView) {
            showToast('Compare is disabled in read-only shared view.', 'warning');
            return;
        }
        if (completedAnalyses.length < 2) {
            showToast('Analyze two videos first.', 'warning');
            return;
        }
        const a = completedAnalyses[completedAnalyses.length - 2];
        const b = completedAnalyses[completedAnalyses.length - 1];
        try {
            const res = await fetch(`${API}/api/compare`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ job_id_a: a.job_id, job_id_b: b.job_id }),
            });
            if (!res.ok) throw new Error((await res.json()).detail || 'Compare failed');
            const data = await res.json();
            renderComparisonSummary(a, b, data.diff);
            showToast('Comparison ready.', 'success');
        } catch (err) {
            showToast(`Compare failed: ${err.message}`, 'error');
        }
    });
}

function renderComparisonSummary(a, b, diff) {
    const section = $('comparison-section');
    if (!section) return;
    section.style.display = 'block';
    const timeline = $('comparison-timeline');
    const overlay = diff.retention_curve_overlay || [];
    const labels = overlay.map(p => formatTime(p.t));
    const aVals = overlay.map(p => p.a);
    const bVals = overlay.map(p => p.b);
    timeline.innerHTML = `
        <div class="insight-item" style="margin-bottom:10px;border-left-color:#3b82f6">
            Δ Overall: <b>${diff.overall_score_delta > 0 ? '+' : ''}${diff.overall_score_delta}</b>,
            Δ Hook: <b>${diff.hook_score_delta > 0 ? '+' : ''}${diff.hook_score_delta}</b>,
            Winner: <b>${diff.winner.toUpperCase()}</b>
        </div>
        <canvas id="ab-retention-chart" height="180"></canvas>
    `;
    const canvas = $('ab-retention-chart');
    new Chart(canvas, {
        type: 'line',
        data: {
            labels,
            datasets: [
                { label: `A (${a.job_id.slice(0, 8)})`, data: aVals, borderColor: '#a78bfa', tension: 0.3 },
                { label: `B (${b.job_id.slice(0, 8)})`, data: bVals, borderColor: '#22c55e', tension: 0.3 },
            ]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });
}


// ═══════════════════════════════════════════════════════════
// AI CHAT ASSISTANT
// ═══════════════════════════════════════════════════════════

const $chatMessages = $('chat-messages');
const $chatInput = $('chat-input');
const $btnSendChat = $('btn-send-chat');

if ($chatInput) {
    $chatInput.addEventListener('input', () => {
        $btnSendChat.disabled = !$chatInput.value.trim();
    });
    $chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !$btnSendChat.disabled && $chatInput.value.trim()) {
            e.preventDefault();
            $btnSendChat.click();
        }
    });
}

if ($btnSendChat) {
    $btnSendChat.addEventListener('click', async () => {
        if (sharedGuard('AI chat')) return;
        if (!currentJobId || !$chatInput.value.trim()) return;
        
        const message = $chatInput.value.trim();
        $chatInput.value = '';
        $btnSendChat.disabled = true;
        
        // Add user message
        appendChatMessage('user', message);
        chatHistory.push({ role: 'user', content: message });
        
        // Show typing indicator
        const typingEl = appendChatTyping();
        
        try {
            const res = await fetch(`${API}/api/jobs/${currentJobId}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message, history: chatHistory }),
            });
            if (!res.ok) throw new Error((await res.json()).detail || 'Chat failed');
            const data = await res.json();
            
            // Remove typing indicator and add response
            typingEl.remove();
            appendChatMessage('assistant', data.response);
            chatHistory.push({ role: 'assistant', content: data.response });
        } catch (err) {
            typingEl.remove();
            appendChatMessage('assistant', `❌ Sorry, something went wrong: ${err.message}`);
        }
        
        $btnSendChat.disabled = false;
        $chatInput.focus();
    });
}

function appendChatMessage(role, text) {
    const msg = document.createElement('div');
    msg.className = `chat-message chat-message--${role}`;
    const avatar = role === 'user' ? '👤' : '🤖';
    // Simple markdown-like formatting
    const formatted = text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code style="background:rgba(139,92,246,0.15);padding:1px 4px;border-radius:3px;font-size:12px">$1</code>')
        .replace(/\n/g, '<br>');
    msg.innerHTML = `
        <div class="chat-message__avatar">${avatar}</div>
        <div class="chat-message__content">
            <div class="chat-message__text">${formatted}</div>
        </div>`;
    $chatMessages.appendChild(msg);
    $chatMessages.scrollTop = $chatMessages.scrollHeight;
}

function appendChatTyping() {
    const el = document.createElement('div');
    el.className = 'chat-message chat-message--assistant';
    el.innerHTML = `
        <div class="chat-message__avatar">🤖</div>
        <div class="chat-message__content">
            <div class="chat-typing">
                <div class="chat-typing__dot"></div>
                <div class="chat-typing__dot"></div>
                <div class="chat-typing__dot"></div>
            </div>
        </div>`;
    $chatMessages.appendChild(el);
    $chatMessages.scrollTop = $chatMessages.scrollHeight;
    return el;
}

function resetChatMessages() {
    if (!$chatMessages) return;
    $chatMessages.innerHTML = `
        <div class="chat-message chat-message--assistant">
            <div class="chat-message__avatar">🤖</div>
            <div class="chat-message__content">
                <div class="chat-message__text">Hi! I've analyzed your video. Ask me anything about the results — weaknesses, improvements, specific timestamps, or optimization tips.</div>
            </div>
        </div>`;
    chatHistory = [];
}


// ═══════════════════════════════════════════════════════════
// ONE-CLICK HOOK APPLY (Phase 4)
// ═══════════════════════════════════════════════════════════

window.applyHook = async function(start, end, overlayText, event) {
    if (sharedGuard('Hook preview')) return;
    if (event) event.stopPropagation();
    if (!currentJobId) { showToast('No active analysis', 'error'); return; }
    
    const btn = event?.target;
    if (btn) { btn.disabled = true; btn.textContent = '⏳ Generating...'; }
    
    try {
        const res = await fetchWithRetry(`${API}/api/jobs/${currentJobId}/apply-hook`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ start, end, overlay_text: overlayText, speed: 1.0 }),
        });
        
        if (!res.ok) throw new Error((await res.json()).detail || 'Preview generation failed');
        
        const blob = await res.blob();
        const previewUrl = URL.createObjectURL(blob);
        
        // Find the preview slot
        const card = btn?.closest('.script-doctor-card');
        const previewSlot = card?.querySelector('.hook-preview-slot');
        
        if (previewSlot) {
            previewSlot.innerHTML = `
                <div class="hook-preview">
                    <video src="${previewUrl}" controls autoplay></video>
                    <div class="hook-preview__bar">
                        <span>⚡ Preview: ${formatTime(start)} → ${formatTime(end)} with overlay</span>
                        <a href="${previewUrl}" download="HookArchitect_Preview.mp4" style="color:var(--accent-cyan);text-decoration:none;font-weight:600;">📥 Download</a>
                    </div>
                </div>`;
        }
        
        showToast('Hook preview generated!', 'success');
    } catch (err) {
        showToast('Preview failed: ' + err.message, 'error');
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = '⚡ Apply'; }
    }
};


// ═══════════════════════════════════════════════════════════
// SCROLL REVEAL (Phase 3)
// ═══════════════════════════════════════════════════════════

const scrollRevealObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('revealed');
            scrollRevealObserver.unobserve(entry.target);
        }
    });
}, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });

function initScrollReveal() {
    document.querySelectorAll('.chart-card, .hook-score-card, .editor-card, .audio-sync-section, .zones-section').forEach(el => {
        el.classList.add('scroll-reveal');
        scrollRevealObserver.observe(el);
    });
}

// Add scroll reveal after results render
const _originalRenderResults = renderResults;
renderResults = function(result) {
    _originalRenderResults(result);
    cachedAIInsights = null; // Clear cache for new analysis
    setTimeout(initScrollReveal, 100);
};


// ═══════════════════════════════════════════════════════════
// BUTTON RIPPLE EFFECT (Phase 3)
// ═══════════════════════════════════════════════════════════

document.addEventListener('click', (e) => {
    const btn = e.target.closest('.btn');
    if (!btn) return;
    const ripple = document.createElement('span');
    ripple.className = 'ripple';
    const rect = btn.getBoundingClientRect();
    ripple.style.left = (e.clientX - rect.left - 10) + 'px';
    ripple.style.top = (e.clientY - rect.top - 10) + 'px';
    btn.appendChild(ripple);
    setTimeout(() => ripple.remove(), 600);
});
