/* ═══════════════════════════════════════════════════════════
   Hook Architect — Landing Page JS
   Scroll animations, navbar behavior, smooth scroll
   ═══════════════════════════════════════════════════════════ */

(function () {
    'use strict';

    // ── Navbar scroll behavior ────────────────────────────
    const navbar = document.getElementById('navbar');
    let lastScrollY = 0;

    function handleScroll() {
        const scrollY = window.scrollY;
        if (scrollY > 60) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
        lastScrollY = scrollY;
    }

    window.addEventListener('scroll', handleScroll, { passive: true });

    // ── Intersection Observer for scroll animations ───────
    const observerOptions = {
        threshold: 0.15,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    document.querySelectorAll('.animate-on-scroll').forEach(el => {
        observer.observe(el);
    });

    // ── Smooth scroll for anchor links ────────────────────
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    // ── Watch Demo button (scroll to how-it-works) ────────
    const btnDemo = document.getElementById('btn-watch-demo');
    if (btnDemo) {
        btnDemo.addEventListener('click', () => {
            const section = document.getElementById('how-it-works');
            if (section) {
                section.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    }

})();
