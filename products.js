/**
 * products.js — Globalucar Product Listing Engine v3.0
 * Reads from products-data.json (or window.PRODUCTS_INLINE_DATA)
 * Supports: category filter, parts sub-system filter, keyword search, sort, pagination, detail page links
 */
(function () {
  'use strict';

  const PRODUCTS_JSON = 'products-data.json';
  const PER_PAGE = 9; // 3x3 grid per page

  // ── Helpers ──────────────────────────────────────
  function catLabel(cat) {
    return { new_car: 'New Car', used_car: 'Used Car', parts: 'Auto Parts' }[cat] || cat;
  }

  function catColor(cat, sys) {
    if (cat === 'parts') {
      return { engine: '#e67e22', cooling: '#2980b9', suspension: '#27ae60', electrical: '#8e44ad' }[sys] || '#555';
    }
    return { new_car: '#c8102e', used_car: '#0d1f3c' }[cat] || '#888';
  }

  function sysLabel(sys) {
    return { engine: 'Engine', cooling: 'Cooling', suspension: 'Suspension', electrical: 'Electrical' }[sys] || sys;
  }

  function getImage(p) {
    // local_image may be a path string or a boolean (legacy)
    if (p.local_image && typeof p.local_image === 'string') return p.local_image;
    // fall back to image field (preferred for used_car entries)
    if (p.image && typeof p.image === 'string') return p.image;
    if (p.images && p.images.length > 0 && p.images[0]) return p.images[0];
    return '';
  }

  // ── Build product card HTML ───────────────────────
  function buildCard(p) {
    const imgSrc = getImage(p);
    const fallbackIcon = p.category === 'parts' ? '🔧' : '🚗';
    // SEO: use alt_text field for meaningful image alt attribute
    const imgAlt = p.alt_text || escHtml(p.name) + ' wholesale China export';
    const imgHtml = imgSrc
      ? `<img src="${escHtml(imgSrc)}" alt="${escHtml(imgAlt)}" loading="lazy" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'" /><div class="card-no-img" style="display:none">${fallbackIcon}</div>`
      : `<div class="card-no-img">${fallbackIcon}</div>`;

    const tagsHtml = (p.tags || []).slice(0, 3)
      .map(t => `<span class="product-tag">${escHtml(t)}</span>`).join('');

    const badgeColor = catColor(p.category, p.part_system);
    const badgeText = p.category === 'parts'
      ? sysLabel(p.part_system)
      : catLabel(p.category);
    const priceDisplay = p.price || 'Contact for Price';
    const subCatHtml = p.sub_category
      ? `<div class="card-sub-cat">${escHtml(p.sub_category)}</div>` : '';

    return `
      <article class="product-card" data-id="${p.id}" data-cat="${p.category}" onclick="window.location='product-detail.html?id=${p.id}'" style="cursor:pointer">
        <div class="card-img-wrap">
          ${imgHtml}
          <div class="card-badge" style="background:${badgeColor}">${badgeText}</div>
          ${p.featured ? '<div class="card-featured-badge">★ Featured</div>' : ''}
        </div>
        <div class="card-body">
          <h3 class="card-title">${escHtml(p.name)}</h3>
          ${subCatHtml}
          <div class="card-tags">${tagsHtml}</div>
          <div class="card-price">${escHtml(priceDisplay)}</div>
          <div class="card-moq">Min. Order: ${escHtml(p.moq || '1 Piece')}</div>
          <div class="card-actions">
            <a href="product-detail.html?id=${p.id}" class="btn-detail" onclick="event.stopPropagation()">View Details</a>
            <a href="contact.html?product=${encodeURIComponent(p.name)}&id=${p.id}" class="btn-inquire" onclick="event.stopPropagation()">Get Quote</a>
          </div>
        </div>
      </article>`;
  }

  function escHtml(s) {
    return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // ── State ─────────────────────────────────────────
  let allProducts = [];
  let filtered = [];
  let currentPage = 1;
  let currentCat = 'all';
  let currentSystem = 'all'; // parts sub-system
  let currentFuel = 'all';   // new car fuel type filter
  let currentSearch = '';
  let currentSort = 'default';

  // ── Init ──────────────────────────────────────────
  function init() {
    const listingPage = document.getElementById('products-grid');
    const homeFeatured = document.getElementById('featured-products');

    if (!listingPage && !homeFeatured) return;

    // Prefer inline data (works with file:// protocol, no CORS issues)
    if (window.PRODUCTS_INLINE_DATA) {
      allProducts = window.PRODUCTS_INLINE_DATA.products || [];
      if (listingPage) setupListingPage();
      if (homeFeatured) renderHomeFeatured();
      return;
    }

    // Fallback: fetch from JSON (works when served via HTTP)
    fetch(PRODUCTS_JSON)
      .then(r => {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(data => {
        allProducts = data.products || [];
        if (listingPage) setupListingPage();
        if (homeFeatured) renderHomeFeatured();
      })
      .catch(err => {
        console.error('Failed to load products-data.json:', err);
        const grid = document.getElementById('products-grid');
        if (grid) grid.innerHTML = '<p class="error-msg">Failed to load products. Please try again later.</p>';
      });
  }

  // ── Listing Page ──────────────────────────────────
  function setupListingPage() {
    // Read URL params for initial state
    const params = new URLSearchParams(window.location.search);
    if (params.get('cat')) currentCat = params.get('cat');
    if (params.get('system')) currentSystem = params.get('system');
    if (params.get('fuel')) currentFuel = params.get('fuel');
    if (params.get('q')) currentSearch = params.get('q');

    // Wire up category filter buttons
    document.querySelectorAll('[data-filter]').forEach(btn => {
      btn.addEventListener('click', () => {
        currentCat = btn.dataset.filter;
        currentPage = 1;
        document.querySelectorAll('[data-filter]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        // Show/hide sub-system filter
        const sysFilter = document.getElementById('parts-system-filter');
        if (sysFilter) {
          sysFilter.style.display = currentCat === 'parts' ? 'flex' : 'none';
        }
        if (currentCat !== 'parts') currentSystem = 'all';

        // Show/hide fuel type filter
        const fuelFilter = document.getElementById('fuel-type-filter');
        if (fuelFilter) {
          fuelFilter.style.display = currentCat === 'new_car' ? 'flex' : 'none';
        }
        if (currentCat !== 'new_car') currentFuel = 'all';

        applyFilters();
      });
      if (btn.dataset.filter === currentCat) {
        btn.classList.add('active');
      }
    });

    // Wire up parts sub-system filter
    document.querySelectorAll('[data-system]').forEach(btn => {
      btn.addEventListener('click', () => {
        currentSystem = btn.dataset.system;
        currentPage = 1;
        document.querySelectorAll('[data-system]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        applyFilters();
      });
      if (btn.dataset.system === currentSystem) btn.classList.add('active');
    });

    // Wire up fuel type filter
    document.querySelectorAll('[data-fuel]').forEach(btn => {
      btn.addEventListener('click', () => {
        currentFuel = btn.dataset.fuel;
        currentPage = 1;
        document.querySelectorAll('[data-fuel]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        applyFilters();
      });
      if (btn.dataset.fuel === currentFuel) btn.classList.add('active');
    });

    // Show parts/fuel filter if starting on respective view
    if (currentCat === 'parts') {
      const sysFilter = document.getElementById('parts-system-filter');
      if (sysFilter) sysFilter.style.display = 'flex';
    }
    if (currentCat === 'new_car') {
      const fuelFilter = document.getElementById('fuel-type-filter');
      if (fuelFilter) fuelFilter.style.display = 'flex';
    }

    // Search input
    const searchInput = document.getElementById('product-search');
    if (searchInput) {
      searchInput.value = currentSearch;
      searchInput.addEventListener('input', () => {
        currentSearch = searchInput.value.trim();
        currentPage = 1;
        applyFilters();
      });
    }

    // Sort
    const sortEl = document.getElementById('product-sort');
    if (sortEl) {
      sortEl.addEventListener('change', () => {
        currentSort = sortEl.value;
        currentPage = 1;
        applyFilters();
      });
    }

    applyFilters();
  }

  function applyFilters() {
    let result = [...allProducts];

    // Category filter
    if (currentCat && currentCat !== 'all') {
      result = result.filter(p => p.category === currentCat);
    }

    // Parts sub-system filter
    if (currentCat === 'parts' && currentSystem && currentSystem !== 'all') {
      result = result.filter(p => p.part_system === currentSystem);
    }

    // Fuel type filter (new cars only)
    if (currentCat === 'new_car' && currentFuel && currentFuel !== 'all') {
      result = result.filter(p => {
        const ft = (p.fuel_type || '').toUpperCase();
        const target = currentFuel.toUpperCase();
        return ft === target || ft.includes(target);
      });
    }

    // Search
    if (currentSearch) {
      const q = currentSearch.toLowerCase();
      result = result.filter(p =>
        (p.name || '').toLowerCase().includes(q) ||
        (p.description || '').toLowerCase().includes(q) ||
        (p.sub_category || '').toLowerCase().includes(q) ||
        (p.brand || '').toLowerCase().includes(q) ||
        (p.fuel_type || '').toLowerCase().includes(q) ||
        (p.tags || []).some(t => t.toLowerCase().includes(q))
      );
    }

    // Sort
    if (currentSort === 'price-asc') {
      result.sort((a, b) => parsePrice(a.price) - parsePrice(b.price));
    } else if (currentSort === 'price-desc') {
      result.sort((a, b) => parsePrice(b.price) - parsePrice(a.price));
    } else if (currentSort === 'name') {
      result.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
    }

    filtered = result;
    renderPage();
    renderPagination();
    updateResultCount();
  }


  function parsePrice(priceStr) {
    if (!priceStr) return 0;
    const m = String(priceStr).match(/[\d,\.]+/);
    return m ? parseFloat(m[0].replace(/,/g, '')) : 0;
  }

  function renderPage() {
    const grid = document.getElementById('products-grid');
    if (!grid) return;

    const start = (currentPage - 1) * PER_PAGE;
    const page = filtered.slice(start, start + PER_PAGE);

    if (page.length === 0) {
      grid.innerHTML = '<div class="no-results"><p>No products found matching your criteria.</p><a href="products.html" class="btn-reset">Clear Filters</a></div>';
      return;
    }

    grid.innerHTML = page.map(buildCard).join('');
  }

  function renderPagination() {
    const paginationEl = document.getElementById('pagination');
    if (!paginationEl) return;

    const totalPages = Math.ceil(filtered.length / PER_PAGE);
    if (totalPages <= 1) {
      paginationEl.innerHTML = '';
      return;
    }

    let html = '';
    // Prev button
    if (currentPage > 1) {
      html += `<button class="page-btn page-nav-btn" onclick="gotoPage(${currentPage - 1})">&laquo; Prev</button>`;
    } else {
      html += `<span class="page-btn page-nav-btn page-disabled">&laquo; Prev</span>`;
    }

    // Smart page number display with ellipsis
    const pages = buildPageNumbers(currentPage, totalPages);
    for (const p of pages) {
      if (p === '...') {
        html += `<span class="page-ellipsis">...</span>`;
      } else {
        html += `<button class="page-btn ${p === currentPage ? 'active' : ''}" onclick="gotoPage(${p})">${p}</button>`;
      }
    }

    // Next button
    if (currentPage < totalPages) {
      html += `<button class="page-btn page-nav-btn" onclick="gotoPage(${currentPage + 1})">Next &raquo;</button>`;
    } else {
      html += `<span class="page-btn page-nav-btn page-disabled">Next &raquo;</span>`;
    }

    paginationEl.innerHTML = html;
  }

  function buildPageNumbers(current, total) {
    // Always show first page, last page, current page, and neighbors
    const delta = 2; // pages to show on each side of current
    const range = [];
    const rangeWithEllipsis = [];

    for (let i = 1; i <= total; i++) {
      if (i === 1 || i === total || (i >= current - delta && i <= current + delta)) {
        range.push(i);
      }
    }

    let prev = 0;
    for (const i of range) {
      if (prev && i - prev > 1) {
        rangeWithEllipsis.push('...');
      }
      rangeWithEllipsis.push(i);
      prev = i;
    }

    return rangeWithEllipsis;
  }

  function updateResultCount() {
    const countEl = document.getElementById('result-count');
    if (countEl) {
      const label = currentCat === 'parts' ? 'part' : currentCat === 'used_car' ? 'used car' : currentCat === 'new_car' ? 'new car' : 'product';
      const plural = filtered.length !== 1 ? (label.endsWith('r') ? label + 's' : label + 's') : label;
      countEl.textContent = `${filtered.length} ${plural} found`;
    }
  }

  window.gotoPage = function (n) {
    currentPage = n;
    renderPage();
    renderPagination();
    window.scrollTo({ top: 200, behavior: 'smooth' });
  };

  // ── Homepage Featured (renders in #featured-products) ──
  function renderHomeFeatured() {
    const el = document.getElementById('featured-products');
    if (!el) return;

    const featured = allProducts.filter(p => p.featured).slice(0, 6);
    if (featured.length === 0) {
      el.innerHTML = '<p>No featured products available.</p>';
      return;
    }
    el.innerHTML = featured.map(buildCard).join('');
  }

  // ── Boot ──────────────────────────────────────────
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
