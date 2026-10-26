/*!
 * lead-attribution.js — first-touch attribution for Globalucar inquiries
 *
 * Why this exists: 28 days of site-wide data showed 137 clicks total, and no way to tell
 * whether an OE detail page or a blog article produced an inquiry. Without that split,
 * every decision about the OE release cadence is guesswork.
 *
 * What it does (all client side, no cookies, no PII beyond what the buyer types into the form):
 *   1. Records first-touch landing page, external referrer and timestamp in localStorage
 *   2. Tags every link to contact.html with ?ref=<current page slug>
 *   3. Tags every mailto: link with a prefilled subject and body naming the current page
 *   4. Exposes window.__GU_LEAD__ so contact.html can append the fields to its submission
 *
 * Load it on every page. It never throws, never blocks render, and degrades to a no-op
 * when localStorage is unavailable (private mode, embedded webviews).
 */
(function () {
  'use strict';
  var KEY = 'gu_lead_v1';

  function safeUrl(u) {
    try { return new URL(u); } catch (e) { return null; }
  }

  function sourceType(ref) {
    var qs = location.search || '';
    if (/[?&](gclid|fbclid|msclkid|utm_source|utm_medium|utm_campaign)=/.test(qs)) return 'campaign';
    if (!ref) return 'direct';
    var u = safeUrl(ref);
    if (!u) return 'unknown';
    var h = u.hostname.toLowerCase();
    if (/google\./.test(h)) return 'organic';
    if (/bing\.com|yahoo\.|duckduckgo|yandex\.|baidu\.|search\.|ecosia|startpage/.test(h)) return 'organic';
    if (/facebook\.|instagram\.|linkedin\.|twitter\.|x\.com|t\.co|youtube\.|tiktok\./.test(h)) return 'social';
    if (/global-ucars\.com/.test(h)) return 'internal';
    return 'referral';
  }

  function searchTerm(ref) {
    var u = safeUrl(ref);
    if (!u) return '';
    var q = u.searchParams && u.searchParams.get('q');
    return q ? q.slice(0, 120) : '';
  }

  function pageType(path) {
    if (/^\/(oe|blog)\//.test(path)) return path.indexOf('/oe/') === 0 ? 'oe' : 'blog';
    if (/^\/(parts|vehicles|oem-parts-lookup)/.test(path)) return 'hub';
    if (path === '/' || /^\/(index\.html)?$/.test(path)) return 'home';
    if (/\/product-detail\.html/.test(path)) return 'product';
    if (/\/blog\.html/.test(path)) return 'blog_index';
    if (/\/contact\.html/.test(path)) return 'contact';
    return 'other';
  }

  function slugOf(path) {
    var m = path.replace(/\.html$/, '').split('/');
    return m[m.length - 1] || 'home';
  }

  // ---- 1. first-touch record -------------------------------------------------
  var s = null;
  try { s = JSON.parse(window.localStorage.getItem(KEY) || 'null'); } catch (e) { s = null; }
  var nowIso = new Date().toISOString();
  if (!s || !s.lp) {
    s = {
      lp: location.href,
      lp_path: location.pathname,
      lp_type: pageType(location.pathname),
      lp_slug: slugOf(location.pathname),
      ref: document.referrer || '',
      ts: nowIso,
      pages: 1
    };
  } else {
    s.pages = (s.pages || 1) + 1;
  }
  s.last = location.href;
  s.last_type = pageType(location.pathname);
  s.last_slug = slugOf(location.pathname);
  s.now = nowIso;
  try { window.localStorage.setItem(KEY, JSON.stringify(s)); } catch (e) { /* private mode */ }
  window.__GU_LEAD__ = s;

  // Derived, computed fresh each page view rather than stored.
  s.source = sourceType(s.ref);
  s.term = searchTerm(s.ref);
  s.path = location.pathname;
  s.type = pageType(location.pathname);
  s.slug = slugOf(location.pathname);

  // ---- 2/3. tag the call-to-action links ------------------------------------
  function tagLinks() {
    var pageUrl = location.href;
    var slug = s.slug;

    // contact.html?ref=<slug>
    var links = document.querySelectorAll('a[href*="contact.html"]');
    for (var i = 0; i < links.length; i++) {
      var a = links[i];
      if (a.getAttribute('data-gu-tagged')) continue;
      var href = a.getAttribute('href') || '';
      if (href.indexOf('?') !== -1) continue;
      a.setAttribute('href', href + '?ref=' + encodeURIComponent(slug));
      a.setAttribute('data-gu-tagged', '1');
    }

    // mailto: with the page named in subject and body
    var mails = document.querySelectorAll('a[href^="mailto:"]');
    for (var j = 0; j < mails.length; j++) {
      var m = mails[j];
      if (m.getAttribute('data-gu-tagged')) continue;
      var mh = m.getAttribute('href') || '';
      var sep = mh.indexOf('?') === -1 ? '?' : '&';
      var subject = 'Inquiry from ' + slug;
      var body = 'Page: ' + pageUrl + '\n(Sent from the Globalucar website — please keep this line so we can answer accurately.)';
      m.setAttribute('href', mh + sep + 'subject=' + encodeURIComponent(subject) +
        '&body=' + encodeURIComponent(body));
      m.setAttribute('data-gu-tagged', '1');
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', tagLinks);
  } else {
    tagLinks();
  }
})();
