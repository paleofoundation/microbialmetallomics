/* Microbial Metallomics — interactions */
(function () {
  var root = document.documentElement;

  // ---- active nav highlight ----
  try {
    var path = location.pathname.replace(/\/$/, '') || '/';
    document.querySelectorAll('.nav-links a, .mega-col a').forEach(function (a) {
      var href = a.getAttribute('href');
      if (!href) return;
      var clean = href.replace(/\/$/, '') || '/';
      if (clean !== '/' && path.indexOf(clean) === 0) a.classList.add('active');
    });
  } catch (e) {}

  // ---- theme ----
  function applyTheme(t) {
    if (t === 'dark' || t === 'light') root.setAttribute('data-theme', t);
    else root.removeAttribute('data-theme');
  }
  try { var saved = localStorage.getItem('mm-theme'); if (saved) applyTheme(saved); } catch (e) {}
  function currentIsDark() {
    var t = root.getAttribute('data-theme');
    if (t) return t === 'dark';
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  }

  // ---- mega menu ----
  function closeMenu() {
    var m = document.getElementById('mega-menu');
    if (m) m.classList.remove('open');
    document.querySelectorAll('[data-menu-toggle]').forEach(function (b) { b.setAttribute('aria-expanded', 'false'); });
  }

  document.addEventListener('click', function (e) {
    var toggle = e.target.closest('[data-theme-toggle]');
    if (toggle) {
      var next = currentIsDark() ? 'light' : 'dark';
      applyTheme(next);
      try { localStorage.setItem('mm-theme', next); } catch (err) {}
    }
    var menu = e.target.closest('[data-menu-toggle]');
    if (menu) {
      var m = document.getElementById('mega-menu');
      if (m) {
        var open = m.classList.toggle('open');
        menu.setAttribute('aria-expanded', open ? 'true' : 'false');
        if (open) closeSearch();
      }
      return;
    }
    var copy = e.target.closest('[data-copy]');
    if (copy) {
      try {
        navigator.clipboard.writeText(copy.getAttribute('data-copy'));
        var orig = copy.textContent; copy.textContent = '✓';
        setTimeout(function () { copy.textContent = orig; }, 1200);
      } catch (x) {}
      return;
    }
    if (e.target.closest('[data-search-toggle]')) { openSearch(); return; }
    // click a mega-menu link closes it; click outside closes it
    if (e.target.closest('.mega-col a')) { closeMenu(); return; }
    if (!e.target.closest('.mega-menu') && !e.target.closest('[data-menu-toggle]')) closeMenu();
  });

  // ---- search overlay ----
  var index = null, results = [], sel = -1;
  var overlay = document.getElementById('search-overlay');
  var input = document.getElementById('search-input');
  var resBox = document.getElementById('search-results');

  function loadIndex(cb) {
    if (index) { cb(); return; }
    fetch('/search-index.json').then(function (r) { return r.json(); }).then(function (d) {
      index = d; cb();
    }).catch(function () { index = []; cb(); });
  }
  function openSearch() {
    if (!overlay) return;
    closeMenu();
    overlay.classList.add('open');
    overlay.setAttribute('aria-hidden', 'false');
    loadIndex(function () { if (input) { input.value = ''; input.focus(); render(''); } });
  }
  function closeSearch() {
    if (overlay) { overlay.classList.remove('open'); overlay.setAttribute('aria-hidden', 'true'); }
  }
  function render(q) {
    if (!resBox) return;
    q = (q || '').trim().toLowerCase();
    if (!q) {
      results = (index || []).filter(function (x) { return x.kind === 'Glossary' || x.kind === 'Blog'; }).slice(0, 8);
    } else {
      results = (index || []).map(function (x) {
        var t = x.title.toLowerCase(), d = (x.desc || '').toLowerCase();
        var score = t.indexOf(q) === 0 ? 0 : (t.indexOf(q) > -1 ? 1 : (d.indexOf(q) > -1 ? 2 : 99));
        return { x: x, s: score };
      }).filter(function (o) { return o.s < 99; }).sort(function (a, b) { return a.s - b.s; }).slice(0, 12).map(function (o) { return o.x; });
    }
    sel = results.length ? 0 : -1;
    if (!results.length) { resBox.innerHTML = '<div class="sr-empty">No matches — try a metal, a term, or a topic.</div>'; return; }
    resBox.innerHTML = results.map(function (r, i) {
      return '<a href="' + r.url + '" class="' + (i === sel ? 'sel' : '') + '"><div class="sr-kind">' + r.kind + '</div><div class="sr-title">' + r.title + '</div></a>';
    }).join('');
  }
  function move(d) {
    if (!results.length) return;
    sel = (sel + d + results.length) % results.length;
    var links = resBox.querySelectorAll('a');
    links.forEach(function (a, i) { a.classList.toggle('sel', i === sel); });
    if (links[sel]) links[sel].scrollIntoView({ block: 'nearest' });
  }
  if (input) {
    input.addEventListener('input', function () { render(input.value); });
    input.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown') { e.preventDefault(); move(1); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); move(-1); }
      else if (e.key === 'Enter') { if (results[sel]) location.href = results[sel].url; }
    });
  }
  if (overlay) overlay.addEventListener('click', function (e) { if (e.target === overlay) closeSearch(); });

  document.addEventListener('keydown', function (e) {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); openSearch(); }
    else if (e.key === 'Escape') { closeSearch(); closeMenu(); }
  });

  // ---- scroll-spy for TOC ----
  var tocLinks = Array.prototype.slice.call(document.querySelectorAll('.toc a, .toc-sidebar nav a'));
  if (tocLinks.length && 'IntersectionObserver' in window) {
    var map = {};
    tocLinks.forEach(function (a) {
      var id = (a.getAttribute('href') || '').replace('#', '');
      var el = id && document.getElementById(id);
      if (el) map[id] = a;
    });
    var obs = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) {
          tocLinks.forEach(function (a) { a.classList.remove('active'); });
          if (map[en.target.id]) map[en.target.id].classList.add('active');
        }
      });
    }, { rootMargin: '-15% 0px -75% 0px' });
    Object.keys(map).forEach(function (id) { var el = document.getElementById(id); if (el) obs.observe(el); });
  }

  // ---- library filter ----
  var chips = Array.prototype.slice.call(document.querySelectorAll('[data-filter]'));
  if (chips.length) {
    chips.forEach(function (chip) {
      chip.addEventListener('click', function () {
        var f = chip.getAttribute('data-filter');
        chips.forEach(function (c) { c.classList.remove('active'); });
        chip.classList.add('active');
        document.querySelectorAll('[data-cat]').forEach(function (item) {
          item.style.display = (f === 'all' || item.getAttribute('data-cat') === f) ? '' : 'none';
        });
      });
    });
  }

  // ---- reading progress bar + back-to-top (article pages) ----
  if (document.querySelector('.article-body')) {
    var bar = document.createElement('div'); bar.className = 'read-progress'; document.body.appendChild(bar);
    var top = document.createElement('button'); top.className = 'to-top'; top.setAttribute('aria-label', 'Back to top');
    top.innerHTML = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 19V5M5 12l7-7 7 7"/></svg>';
    document.body.appendChild(top);
    top.addEventListener('click', function () { window.scrollTo({ top: 0, behavior: 'smooth' }); });
    var onScroll = function () {
      var h = document.documentElement.scrollHeight - window.innerHeight;
      var pct = h > 0 ? (window.scrollY / h) * 100 : 0;
      bar.style.width = pct + '%';
      top.classList.toggle('show', window.scrollY > 600);
    };
    window.addEventListener('scroll', onScroll, { passive: true }); onScroll();
  }

  // ---- newsletter ----
  document.querySelectorAll('form[data-waitlist]').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var note = form.querySelector('[data-note]');
      if (note) { note.textContent = "Thanks — you're on the list. We'll be in touch."; note.style.color = 'var(--patina-deep)'; }
      form.reset();
    });
  });
})();
