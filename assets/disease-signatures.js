/* Progressive enhancement: every review remains readable without JavaScript. */
(() => {
  const controls = document.querySelector('.signature-filters');
  if (!controls) return;
  const cards = [...document.querySelectorAll('[data-signature-group]')];
  const buttons = [...controls.querySelectorAll('button')];
  const status = document.querySelector('[data-signature-count]');
  controls.hidden = false;
  buttons.forEach(button => button.addEventListener('click', () => {
    const group = button.dataset.signatureFilter;
    buttons.forEach(item => item.setAttribute('aria-pressed', String(item === button)));
    cards.forEach(card => { card.hidden = group !== 'all' && card.dataset.signatureGroup !== group; });
    const visible = cards.filter(card => !card.hidden).length;
    status.textContent = `Showing ${visible} of ${cards.length} papers`;
  }));
})();
