/* ═══════════════════════════════════════════════════════════
   Hook Architect — Cursor Trail Animation
   Inspired by Antigravity-style cursor glow effects
   Red/Orange particle trail following the mouse
   ═══════════════════════════════════════════════════════════ */

(function () {
    'use strict';

    // Don't run on mobile
    if ('ontouchstart' in window || window.innerWidth < 768) return;

    // ── Configuration ─────────────────────────────────────
    const CONFIG = {
        particleCount: 18,
        trailLength: 12,
        baseSize: 6,
        fadeSpeed: 0.025,
        colors: [
            'rgba(255, 59, 48, 0.8)',    // Crimson red
            'rgba(255, 107, 53, 0.7)',   // Burnt orange
            'rgba(255, 140, 0, 0.6)',    // Deep orange
            'rgba(255, 69, 0, 0.5)',     // Red-orange
            'rgba(255, 99, 71, 0.4)',    // Tomato
        ],
        glowColor: 'rgba(255, 59, 48, 0.15)',
        ringColor: 'rgba(255, 59, 48, 0.35)',
    };

    // ── Main Cursor Glow ──────────────────────────────────
    const cursorGlow = document.createElement('div');
    cursorGlow.id = 'cursor-glow';
    Object.assign(cursorGlow.style, {
        position: 'fixed',
        width: '480px',
        height: '480px',
        borderRadius: '50%',
        background: `radial-gradient(circle, ${CONFIG.glowColor} 0%, transparent 70%)`,
        pointerEvents: 'none',
        zIndex: '9999',
        transform: 'translate(-50%, -50%)',
        transition: 'opacity 0.3s ease',
        opacity: '0',
        mixBlendMode: 'screen',
    });
    document.body.appendChild(cursorGlow);

    // ── Cursor Ring (small precise follower) ──────────────
    const cursorRing = document.createElement('div');
    cursorRing.id = 'cursor-ring';
    Object.assign(cursorRing.style, {
        position: 'fixed',
        width: '28px',
        height: '28px',
        borderRadius: '50%',
        border: `2px solid ${CONFIG.ringColor}`,
        pointerEvents: 'none',
        zIndex: '10001',
        transform: 'translate(-50%, -50%)',
        transition: 'width 0.2s ease, height 0.2s ease, border-color 0.2s ease',
        opacity: '0',
    });
    document.body.appendChild(cursorRing);

    // ── Cursor Dot (tiny center dot) ──────────────────────
    const cursorDot = document.createElement('div');
    cursorDot.id = 'cursor-dot';
    Object.assign(cursorDot.style, {
        position: 'fixed',
        width: '5px',
        height: '5px',
        borderRadius: '50%',
        background: '#FF3B30',
        pointerEvents: 'none',
        zIndex: '10002',
        transform: 'translate(-50%, -50%)',
        opacity: '0',
        boxShadow: '0 0 8px rgba(255, 59, 48, 0.6)',
    });
    document.body.appendChild(cursorDot);

    // ── Particle Trail System ─────────────────────────────
    const canvas = document.createElement('canvas');
    canvas.id = 'cursor-canvas';
    Object.assign(canvas.style, {
        position: 'fixed',
        top: '0',
        left: '0',
        width: '100vw',
        height: '100vh',
        pointerEvents: 'none',
        zIndex: '10000',
    });
    document.body.appendChild(canvas);

    const ctx = canvas.getContext('2d');
    let mouseX = 0, mouseY = 0;
    let ringX = 0, ringY = 0;
    let particles = [];
    let frameCount = 0;
    let isHovering = false;

    function resize() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }
    resize();
    window.addEventListener('resize', resize);

    // ── Particle Class ────────────────────────────────────
    class Particle {
        constructor(x, y) {
            this.x = x;
            this.y = y;
            this.size = Math.random() * CONFIG.baseSize + 2;
            this.speedX = (Math.random() - 0.5) * 2;
            this.speedY = (Math.random() - 0.5) * 2;
            this.opacity = 0.8;
            this.color = CONFIG.colors[Math.floor(Math.random() * CONFIG.colors.length)];
            this.life = 1;
            this.decay = CONFIG.fadeSpeed + Math.random() * 0.02;
        }

        update() {
            this.x += this.speedX;
            this.y += this.speedY;
            this.speedX *= 0.96;
            this.speedY *= 0.96;
            this.life -= this.decay;
            this.size *= 0.97;
        }

        draw(ctx) {
            if (this.life <= 0) return;
            ctx.save();
            ctx.globalAlpha = this.life * this.opacity;
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
            ctx.fillStyle = this.color;
            ctx.shadowColor = this.color;
            ctx.shadowBlur = 8;
            ctx.fill();
            ctx.restore();
        }
    }

    // ── Mouse Move Handler ────────────────────────────────
    document.addEventListener('mousemove', (e) => {
        mouseX = e.clientX;
        mouseY = e.clientY;

        // Show cursor elements
        cursorGlow.style.opacity = '1';
        cursorRing.style.opacity = '1';
        cursorDot.style.opacity = '1';

        // Move glow (instant)
        cursorGlow.style.left = mouseX + 'px';
        cursorGlow.style.top = mouseY + 'px';

        // Move dot (instant)
        cursorDot.style.left = mouseX + 'px';
        cursorDot.style.top = mouseY + 'px';

        // Spawn particles (throttled)
        if (frameCount % 2 === 0) {
            particles.push(new Particle(mouseX, mouseY));
            if (isHovering) {
                particles.push(new Particle(mouseX, mouseY));
            }
        }
    });

    document.addEventListener('mouseleave', () => {
        cursorGlow.style.opacity = '0';
        cursorRing.style.opacity = '0';
        cursorDot.style.opacity = '0';
    });

    // ── Hover Effects on Interactive Elements ─────────────
    function setupHoverEffects() {
        const interactables = document.querySelectorAll('a, button, .btn, .card, .feature-card, .analysis-card, .sidebar__link, .tab, input, select, .upload-dropzone, .niche-pill');
        interactables.forEach(el => {
            el.addEventListener('mouseenter', () => {
                isHovering = true;
                cursorRing.style.width = '44px';
                cursorRing.style.height = '44px';
                cursorRing.style.borderColor = 'rgba(255, 140, 0, 0.5)';
            });
            el.addEventListener('mouseleave', () => {
                isHovering = false;
                cursorRing.style.width = '28px';
                cursorRing.style.height = '28px';
                cursorRing.style.borderColor = CONFIG.ringColor;
            });
        });
    }

    // ── Click Burst Effect ────────────────────────────────
    document.addEventListener('click', (e) => {
        for (let i = 0; i < 8; i++) {
            const p = new Particle(e.clientX, e.clientY);
            p.speedX = (Math.random() - 0.5) * 6;
            p.speedY = (Math.random() - 0.5) * 6;
            p.size = Math.random() * 4 + 3;
            particles.push(p);
        }
    });

    // ── Animation Loop ────────────────────────────────────
    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Smooth ring follow
        ringX += (mouseX - ringX) * 0.15;
        ringY += (mouseY - ringY) * 0.15;
        cursorRing.style.left = ringX + 'px';
        cursorRing.style.top = ringY + 'px';

        // Update & draw particles
        particles = particles.filter(p => p.life > 0);
        particles.forEach(p => {
            p.update();
            p.draw(ctx);
        });

        // Cap max particles
        if (particles.length > 150) {
            particles = particles.slice(-100);
        }

        frameCount++;
        requestAnimationFrame(animate);
    }

    // ── Hide default cursor on landing page ───────────────
    const style = document.createElement('style');
    style.textContent = `
        body { cursor: none !important; }
        a, button, input, select, textarea, .btn, .card, .sidebar__link, .tab { cursor: none !important; }
    `;
    document.head.appendChild(style);

    // ── Init ──────────────────────────────────────────────
    setupHoverEffects();
    animate();

    // Re-setup hover observers after dynamic content loads
    const mo = new MutationObserver(() => setupHoverEffects());
    mo.observe(document.body, { childList: true, subtree: true });

})();
