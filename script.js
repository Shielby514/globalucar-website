/**
 * script.js – Globalucar Global Scripts
 * Mobile nav · Scroll effects · Contact form · Back-to-top
 */
(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {

    /* ── Mobile Navigation ───────────────────────────────────────── */
    const menuBtn  = document.querySelector('.mobile-menu-btn');
    const navMenu  = document.querySelector('.nav-menu');

    if (menuBtn && navMenu) {
      menuBtn.addEventListener('click', function () {
        const open = navMenu.classList.toggle('open');
        menuBtn.setAttribute('aria-expanded', open);
      });
      // Close on link click
      navMenu.querySelectorAll('a').forEach(a => {
        a.addEventListener('click', () => {
          navMenu.classList.remove('open');
          menuBtn.setAttribute('aria-expanded', 'false');
        });
      });
      // Close on outside click
      document.addEventListener('click', function (e) {
        if (!menuBtn.contains(e.target) && !navMenu.contains(e.target)) {
          navMenu.classList.remove('open');
          menuBtn.setAttribute('aria-expanded', 'false');
        }
      });
    }

    /* ── Scroll: navbar shadow ───────────────────────────────────── */
    const navbar = document.querySelector('.navbar');
    function onScroll() {
      if (!navbar) return;
      navbar.style.boxShadow = window.scrollY > 60
        ? '0 4px 24px rgba(0,0,0,0.4)'
        : 'none';

      // Back to top
      const btn = document.getElementById('backToTop');
      if (btn) btn.classList.toggle('visible', window.scrollY > 400);
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();

    /* ── Back to Top ─────────────────────────────────────────────── */
    const btt = document.createElement('button');
    btt.id          = 'backToTop';
    btt.textContent = '↑';
    btt.setAttribute('aria-label', 'Back to top');
    btt.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
    document.body.appendChild(btt);

    /* ── Scroll-in animation ─────────────────────────────────────── */
    if ('IntersectionObserver' in window) {
      const obs = new IntersectionObserver((entries) => {
        entries.forEach(e => {
          if (e.isIntersecting) {
            e.target.style.opacity  = '1';
            e.target.style.transform = 'translateY(0)';
            obs.unobserve(e.target);
          }
        });
      }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

      document.querySelectorAll(
        '.why-card,.testi-card,.value-card,.logi-card,.order-step,.stat-card,.tl-item,.cinfo-card,.svc-info,.usp-item'
      ).forEach(el => {
        el.style.opacity   = '0';
        el.style.transform = 'translateY(22px)';
        el.style.transition = 'opacity 0.55s ease, transform 0.55s ease';
        obs.observe(el);
      });

      // Hero
      const hero = document.querySelector('.hero-content');
      if (hero) {
        hero.style.opacity   = '0';
        hero.style.transform = 'translateY(30px)';
        hero.style.transition = 'opacity 0.8s ease, transform 0.8s ease';
        requestAnimationFrame(() => requestAnimationFrame(() => {
          hero.style.opacity   = '1';
          hero.style.transform = 'translateY(0)';
        }));
      }
    }

    /* ── Contact Form ────────────────────────────────────────────── */
    const form = document.getElementById('contactForm');
    if (form) {
      form.addEventListener('submit', function (e) {
        e.preventDefault();

        const fname   = (form.fname   ? form.fname.value   : form.name?.value  || '').trim();
        const email   = (form.email?.value || '').trim();
        const service = (form.service?.value || '').trim();
        const message = (form.message?.value || '').trim();
        const privacy = form.privacy ? form.privacy.checked : true;

        if (!fname || !email || !service || !message) {
          showFormMsg(form, 'error', 'Please fill in all required fields.');
          return;
        }
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
          showFormMsg(form, 'error', 'Please enter a valid email address.');
          return;
        }
        if (!privacy) {
          showFormMsg(form, 'error', 'Please agree to the data use policy.');
          return;
        }

        const btn = form.querySelector('button[type="submit"]');
        btn.textContent = 'Sending…'; btn.disabled = true;

        // ── Dual-route Formspree setup ──────────────────────────────────────
        // Register free at https://formspree.io → create TWO forms → paste IDs below
        //   Form 1 (Globalucar Vehicle): set email to ucars@global-ucars.com
        //   Form 2 (Kingmay Auto Parts): set email to ku@kingmay-autoparts.com
        const FORMSPREE_VEHICLE = 'XXXXXXXX'; // ← Globalucar form ID (ucars@global-ucars.com)
        const FORMSPREE_PARTS   = 'YYYYYYYY'; // ← Kingmay   form ID (ku@kingmay-autoparts.com)

        // Route by inquiry type: auto_parts → Kingmay; everything else → Globalucar
        const isPartsInquiry = (service === 'auto_parts');
        const targetId       = isPartsInquiry ? FORMSPREE_PARTS : FORMSPREE_VEHICLE;
        const fallbackEmail  = isPartsInquiry ? 'ku@kingmay-autoparts.com' : 'ucars@global-ucars.com';
        const teamLabel      = isPartsInquiry ? 'Kingmay Auto Parts (Miss UU)' : 'Globalucar Vehicle (Mr Didi)';

        const formData = new FormData(form);
        // Tag the inquiry so inbox shows which team it is for
        formData.set('_subject', (isPartsInquiry ? '[Kingmay Parts Inquiry]' : '[Globalucar Vehicle Inquiry]') + ' from ' + fname);

        if (targetId === 'XXXXXXXX' || targetId === 'YYYYYYYY') {
          // Fallback: open mailto when Formspree IDs not yet set
          const subject = encodeURIComponent((isPartsInquiry ? '[Kingmay] ' : '[Globalucar] ') + 'Inquiry from ' + fname + ' - ' + service);
          const body = encodeURIComponent(
            'Name: ' + fname + '\nEmail: ' + email + '\nService: ' + service + '\n\n' + message
          );
          window.open('mailto:' + fallbackEmail + '?subject=' + subject + '&body=' + body);
          showFormMsg(form, 'success',
            '✅ Thank you! Your email client has been opened.\nPlease send the pre-filled email to ' + teamLabel + '.\nOr contact us directly: ' + fallbackEmail
          );
          btn.textContent = 'Submit Inquiry'; btn.disabled = false;
        } else {
          fetch('https://formspree.io/f/' + targetId, {
            method: 'POST',
            body: formData,
            headers: { 'Accept': 'application/json' }
          }).then(function(resp) {
            if (resp.ok) {
              showFormMsg(form, 'success',
                '✅ Thank you! Your inquiry has been sent to ' + teamLabel + '.\nWe will respond within 24 hours.\n\nFor faster response, add us on WeChat: Globalucar'
              );
              form.reset();
            } else {
              resp.json().then(function(data) {
                var errMsg = data.errors ? data.errors.map(function(e){return e.message;}).join(', ') : 'Submission failed.';
                showFormMsg(form, 'error', '⚠️ ' + errMsg + ' Please email us directly: ' + fallbackEmail);
              });
            }
            btn.textContent = 'Submit Inquiry'; btn.disabled = false;
          }).catch(function() {
            showFormMsg(form, 'error', '⚠️ Network error. Please email us directly at ' + fallbackEmail);
            btn.textContent = 'Submit Inquiry'; btn.disabled = false;
          });
        }
      });
    }

    function showFormMsg(form, type, text) {
      let el = form.querySelector('.form-message');
      if (!el) { el = document.createElement('div'); el.className = 'form-message'; form.prepend(el); }
      el.textContent = text;
      el.style.cssText = `padding:14px 18px;border-radius:8px;margin-bottom:18px;font-size:.93rem;line-height:1.5;
        background:${type === 'success' ? '#d1fae5' : '#fee2e2'};
        color:${type === 'success' ? '#065f46' : '#991b1b'};
        border:1px solid ${type === 'success' ? '#6ee7b7' : '#fca5a5'};`;
      setTimeout(() => { if (el) el.remove(); }, 7000);
    }

  }); // DOMContentLoaded

})();
