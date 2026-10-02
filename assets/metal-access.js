/* Progressive enhancement: every case and citation remains readable without JS. */
(() => {
  const controls = document.querySelector('[data-scenario-controls]');
  if (!controls) return;
  const buttons = Array.from(controls.querySelectorAll('button[data-case]'));
  const panels = Array.from(document.querySelectorAll('[data-scenario]'));
  const status = document.querySelector('[data-scenario-status]');
  const valid = new Set(buttons.map(button => button.dataset.case));
  const allIds = new Map();
  panels.forEach(panel => panel.querySelectorAll('[id]').forEach(node => allIds.set(node.id, panel.id)));
  function select(id, announce = true) {
    if (!valid.has(id)) return;
    panels.forEach(panel => { panel.hidden = id !== 'all' && panel.id !== id; });
    buttons.forEach(button => { button.setAttribute('aria-pressed', String(button.dataset.case === id)); });
    if (announce) status.textContent = id === 'all' ? 'Showing all cases.' : 'Showing: ' + buttons.find(button => button.dataset.case === id).textContent.trim() + '.';
  }
  function revealHash() {
    const id = location.hash.slice(1);
    const panelId = allIds.get(id) || (panels.some(panel => panel.id === id) ? id : null);
    if (panelId) select(panelId);
    return panelId;
  }
  controls.hidden = false;
  status.hidden = false;
  select('all');
  buttons.forEach(button => button.addEventListener('click', () => select(button.dataset.case)));
  // A reference backlink can target a citation in a currently hidden case.
  document.addEventListener('click', event => {
    const link = event.target.closest('a[href^="#"]');
    if (!link) return;
    const id = link.getAttribute('href').slice(1);
    const panelId = allIds.get(id);
    if (panelId) select(panelId);
  });
  window.addEventListener('hashchange', revealHash);
  revealHash();
  document.querySelector('[data-print-cases]')?.addEventListener('click', () => window.print());
})();
