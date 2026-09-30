(() => {
  if (document.body.dataset.articleType === 'commentary') {
    document.querySelectorAll('.nav-links a, .mega-col a').forEach(link => {
      link.classList.toggle('active', link.getAttribute('href') === '/commentary');
    });
  }
  document.querySelectorAll('.share-row').forEach(row => {
    const copy = row.querySelector('[data-copy-link]');
    if (!copy) return;
    const url = copy.dataset.copyLink;
    const status = row.querySelector('.share-status');
    const fallback = row.querySelector('.share-fallback');
    const manualCopy = () => {
      status.textContent = 'Select and copy the link below.';
      fallback.hidden = false;
      fallback.focus();
      fallback.select();
    };
    copy.addEventListener('click', async () => {
      try {
        if (!navigator.clipboard?.writeText) { manualCopy(); return; }
        await navigator.clipboard.writeText(url);
        fallback.hidden = true;
        status.textContent = 'Link copied.';
      } catch { manualCopy(); }
    });
    const share = row.querySelector('[data-native-share]');
    if (share && typeof navigator.share === 'function') {
      share.hidden = false;
      share.addEventListener('click', async () => {
        try {
          await navigator.share({title: document.querySelector('h1')?.textContent || document.title, url});
        } catch (error) {
          if (error.name !== 'AbortError') status.textContent = 'Use one of the sharing links or copy the article link.';
        }
      });
    }
  });
  document.querySelectorAll('[data-filter]').forEach(button => {
    button.setAttribute('aria-pressed',button.classList.contains('active')?'true':'false');
    button.addEventListener('click', () => {
      document.querySelectorAll('[data-filter]').forEach(item => item.setAttribute('aria-pressed',item===button?'true':'false'));
    });
  });
})();
