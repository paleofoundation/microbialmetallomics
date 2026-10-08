/* Contents remain usable without JavaScript; collapse only on small screens. */
(() => {
  const compact = window.matchMedia('(max-width: 940px)');
  const contents = [...document.querySelectorAll('details.reading-toc')];
  const sync = () => contents.forEach(node => { node.open = !compact.matches; });
  sync();
  compact.addEventListener('change', sync);
  contents.forEach(node => node.addEventListener('click', event => {
    const link = event.target.closest('a[href^="#"]');
    if (!link || !compact.matches) return;
    const destination = document.getElementById(decodeURIComponent(link.hash.slice(1)));
    if (!destination) return;
    node.open = false;
    if (!destination.hasAttribute('tabindex')) destination.tabIndex = -1;
    destination.focus({ preventScroll: true });
  }));
})();
