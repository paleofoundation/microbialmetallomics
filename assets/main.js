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
      if (clean !== '/' && (path === clean || path.indexOf(clean + '/') === 0)) a.classList.add('active');
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
  function closeMenu(restoreFocus) {
    var m = document.getElementById('mega-menu');
    var wasOpen = m && m.classList.contains('open');
    if (m) m.classList.remove('open');
    document.querySelectorAll('[data-menu-toggle]').forEach(function (b) { b.setAttribute('aria-expanded', 'false'); });
    if (wasOpen && restoreFocus) document.querySelector('[data-menu-toggle]')?.focus();
  }

  document.addEventListener('click', async function (e) {
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
        await navigator.clipboard.writeText(copy.getAttribute('data-copy'));
        var orig = copy.textContent; copy.textContent = '✓';
        setTimeout(function () { copy.textContent = orig; }, 1200);
      } catch (x) {
        var label = copy.textContent;
        copy.textContent = 'Copy unavailable';
        setTimeout(function () { copy.textContent = label; }, 1600);
      }
      return;
    }
    if (e.target.closest('[data-search-toggle]')) { openSearch(e.target.closest('[data-search-toggle]')); return; }
    if (e.target.closest('.search-close')) { closeSearch(); return; }
    // click a mega-menu link closes it; click outside closes it
    if (e.target.closest('.mega-col a')) { closeMenu(); return; }
    if (!e.target.closest('.mega-menu') && !e.target.closest('[data-menu-toggle]')) closeMenu();
  });

  // ---- search overlay ----
  var index = null, indexRequest = null, results = [], sel = -1;
  var overlay = document.getElementById('search-overlay');
  var input = document.getElementById('search-input');
  var resBox = document.getElementById('search-results');
  var searchTrigger = null, inertElements = [];
  var searchScope = null, searchStatus = null;
  var searchEngine = window.MMSearch;

  if (overlay && input && resBox && searchEngine) {
    var modal = overlay.querySelector('.search-modal');
    var searchTitle = document.createElement('h2');
    searchTitle.className = 'search-heading'; searchTitle.textContent = 'Search the field';
    searchTitle.id = 'search-heading'; modal.prepend(searchTitle);
    modal.setAttribute('aria-labelledby', searchTitle.id); modal.removeAttribute('aria-label');
    input.type = 'search'; input.placeholder = 'Try “iron gut” or “nickel urease”';
    var toolbar = document.createElement('div'); toolbar.className = 'search-toolbar';
    var scopeLabel = document.createElement('label'); scopeLabel.textContent = 'Look in';
    searchScope = document.createElement('select'); searchScope.id = 'search-scope';
    scopeLabel.htmlFor = searchScope.id;
    [['all', 'Everything'], ['elements', 'Elements'], ['papers', 'Writing & papers'], ['people', 'Researchers'], ['terms', 'Glossary'], ['guides', 'Guides']].forEach(function (choice) {
      var option = document.createElement('option'); option.value = choice[0]; option.textContent = choice[1]; searchScope.append(option);
    });
    searchStatus = document.createElement('span'); searchStatus.className = 'search-count';
    searchStatus.setAttribute('role', 'status'); searchStatus.setAttribute('aria-live', 'polite'); searchStatus.setAttribute('aria-atomic', 'true');
    toolbar.append(scopeLabel, searchScope, searchStatus); input.after(toolbar);
    var examples = document.createElement('div'); examples.className = 'search-examples';
    var exampleLabel = document.createElement('span'); exampleLabel.textContent = 'Try'; examples.append(exampleLabel);
    ['iron gut', 'nickel urease', 'copper brain'].forEach(function (query) {
      var button = document.createElement('button'); button.type = 'button'; button.textContent = query;
      button.addEventListener('click', function () { input.value = query; searchScope.value = 'all'; render(query); input.focus(); });
      examples.append(button);
    });
    toolbar.after(examples);
    searchScope.addEventListener('change', function () { render(input.value); });
  }

  function announce(text) {
    if (searchStatus) searchStatus.textContent = text;
  }

  function loadIndex() {
    if (index) return Promise.resolve(index);
    if (indexRequest) return indexRequest;
    indexRequest = fetch(document.querySelector('meta[name="site-search"]')?.content || '/search-index.json').then(function (r) {
      if (!r.ok) throw new Error('Search index unavailable');
      return r.json();
    }).then(function (d) {
      if (!Array.isArray(d)) throw new Error('Invalid search index');
      index = d.filter(searchEngine.safe);
      return index;
    }).finally(function () { indexRequest = null; });
    return indexRequest;
  }
  function searchMessage(text) {
    if (!resBox) return;
    results = []; sel = -1;
    var message = document.createElement('div');
    message.className = 'sr-empty'; message.textContent = text;
    resBox.replaceChildren(message);
    announce(text);
  }
  function searchFailure() {
    searchMessage('Search could not load. Browse the metals atlas or evidence explorer, or try again.');
    var retry = document.createElement('button'); retry.type = 'button'; retry.className = 'search-retry'; retry.textContent = 'Try again';
    retry.addEventListener('click', function () {
      searchMessage('Loading search…');
      loadIndex().then(function () { if (overlay.classList.contains('open')) render(input.value); }).catch(searchFailure);
    });
    resBox.append(retry);
    browseLinks();
  }
  function browseLinks() {
    var links = document.createElement('div'); links.className = 'search-browse';
    [['/metals', 'Metals atlas'], ['/evidence', 'Evidence explorer'], ['/glossary', 'Glossary']].forEach(function (entry) {
      var link = document.createElement('a'); link.href = entry[0]; link.textContent = entry[1] + ' →'; links.append(link);
    });
    resBox.append(links);
  }
  function openSearch(trigger) {
    if (!overlay || !searchEngine) return;
    if (overlay.classList.contains('open')) { input?.focus(); return; }
    searchTrigger = trigger || document.activeElement;
    closeMenu();
    overlay.classList.add('open');
    document.body.classList.add('search-open');
    overlay.setAttribute('aria-hidden', 'false');
    inertElements = Array.prototype.filter.call(document.body.children, function (element) {
      return element !== overlay && !element.contains(overlay) && !element.inert && !['SCRIPT', 'STYLE', 'LINK'].includes(element.tagName);
    });
    inertElements.forEach(function (element) { element.inert = true; });
    if (searchScope) searchScope.value = 'all';
    if (input) { input.value = ''; input.focus(); }
    searchMessage('Loading search…');
    loadIndex().then(function () {
      if (overlay.classList.contains('open')) render(input ? input.value : '');
    }).catch(function () {
      if (overlay.classList.contains('open')) searchFailure();
    });
  }
  function closeSearch() {
    if (!overlay || !overlay.classList.contains('open')) return;
    overlay.classList.remove('open'); overlay.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('search-open');
    inertElements.forEach(function (element) { element.inert = false; });
    inertElements = [];
    if (searchTrigger && searchTrigger.isConnected) searchTrigger.focus();
    searchTrigger = null;
  }
  function render(q) {
    if (!resBox || !searchEngine || !index) return;
    q = (q || '').trim();
    var all = searchEngine.search(index, q, searchScope ? searchScope.value : 'all');
    results = all.slice(0, 18); sel = -1;
    if (!results.length) {
      searchMessage('No matches. Try fewer words or choose Everything in “Look in.”');
      browseLinks(); return;
    }
    announce(!q && (!searchScope || searchScope.value === 'all') ? 'Suggested starting points' : all.length + (all.length === 1 ? ' result' : ' results') + (all.length > results.length ? ' · showing first ' + results.length : ''));
    resBox.scrollTop = 0;
    resBox.replaceChildren.apply(resBox, results.map(function (r, i) {
      var link = document.createElement('a'); link.href = r.url;
      link.dataset.searchResult = String(i);
      var kind = document.createElement('div'); kind.className = 'sr-kind'; kind.textContent = [r.kind, r.status, r.studyDesign].filter(Boolean).join(' · ');
      var title = document.createElement('div'); title.className = 'sr-title'; title.textContent = r.title;
      var desc = document.createElement('p'); desc.className = 'sr-description'; desc.textContent = searchEngine.excerpt(r, q);
      link.append(kind, title, desc);
      link.addEventListener('focus', function () { sel = i; });
      return link;
    }));
  }
  function move(d) {
    if (!results.length) return;
    if (sel === 0 && d < 0) { sel = -1; input.focus(); return; }
    sel = sel < 0 ? (d > 0 ? 0 : results.length - 1) : (sel + d + results.length) % results.length;
    var links = resBox.querySelectorAll('[data-search-result]');
    if (links[sel]) { links[sel].focus(); links[sel].scrollIntoView({ block: 'nearest' }); }
  }
  if (input) {
    input.addEventListener('input', function () { render(input.value); });
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && results.length) { e.preventDefault(); location.href = results[0].url; }
    });
    input.addEventListener('focus', function () { sel = -1; });
  }
  if (overlay) {
    overlay.addEventListener('click', function (e) { if (e.target === overlay) closeSearch(); });
    overlay.addEventListener('keydown', function (e) {
      if (e.target !== input && !e.target.closest('[data-search-result]')) return;
      if (e.key === 'ArrowDown') { e.preventDefault(); move(1); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); move(-1); }
    });
  }

  document.addEventListener('keydown', function (e) {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); openSearch(); }
    else if (e.key === 'Escape') { closeSearch(); closeMenu(true); }
    else if (e.key === 'Tab' && overlay?.classList.contains('open')) {
      var focusable = Array.prototype.filter.call(overlay.querySelectorAll('input,button,a[href],[tabindex="0"]'), function (element) { return !element.disabled && element.getClientRects().length; });
      var first = focusable[0], last = focusable[focusable.length - 1];
      if (!first) return;
      if (e.shiftKey && (document.activeElement === first || !overlay.contains(document.activeElement))) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && (document.activeElement === last || !overlay.contains(document.activeElement))) { e.preventDefault(); first.focus(); }
    }
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


})();
