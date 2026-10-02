/* The complete research collection is crawlable and usable before enhancement. */
(() => {
  const filters = document.querySelector('[data-host-filters]');
  if (filters) {
    const cards = [...document.querySelectorAll('[data-metal-action]')];
    const buttons = [...filters.querySelectorAll('button')];
    const status = document.querySelector('[data-host-count]');
    filters.hidden = false;
    buttons.forEach(button => button.addEventListener('click', () => {
      const action = button.dataset.metalFilter;
      buttons.forEach(b => b.setAttribute('aria-pressed', String(b === button)));
      cards.forEach(card => { card.hidden = action !== 'all' && action !== card.dataset.metalAction; });
      status.textContent = `Showing ${cards.filter(c => !c.hidden).length} of ${cards.length} deep dives`;
    }));
  }
  const button = document.querySelector('[data-copy-field-note]');
  if (button) button.addEventListener('click', async () => {
    const field = document.querySelector('.host-copy-fallback');
    const status = document.querySelector('[data-field-note-status]');
    try { await navigator.clipboard.writeText(field.value); status.textContent = 'Copied with its evidence context and article link.'; }
    catch { field.hidden = false; field.focus(); field.select(); status.textContent = 'The complete note is selected. Copy it using your browser.'; }
  });
  // Deep links from the downloadable ledger open the containing disclosure.
  function revealClaim() {
    if (!location.hash.startsWith('#claim-')) return;
    const target = document.getElementById(location.hash.slice(1));
    const details = target && target.closest('details');
    if (details) { details.open = true; target.scrollIntoView({block:'start'}); }
  }
  addEventListener('hashchange', revealClaim);
  revealClaim();
})();
