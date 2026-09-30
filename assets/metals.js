/* Progressive enhancement: all profiles and source links work without JavaScript. */
(() => {
  const form = document.querySelector('.atlas-filters');
  if (!form) return;
  const query = document.getElementById('metal-query');
  const group = document.getElementById('metal-group');
  const count = document.getElementById('metal-count');
  const cards = Array.from(document.querySelectorAll('[data-metal-search]'));
  const sections = Array.from(document.querySelectorAll('[data-atlas-group]'));
  const empty = document.querySelector('.atlas-empty');
  function filter() {
    const terms = query.value.trim().toLocaleLowerCase('en-US').split(/\s+/).filter(Boolean);
    const symbolQuery = terms.length === 1 && cards.some(card => card.dataset.metalSymbols.split(' ').includes(terms[0]));
    let visible = 0;
    cards.forEach(card => {
      const textMatches = symbolQuery ? card.dataset.metalSymbols.split(' ').includes(terms[0]) : terms.every(term => card.dataset.metalSearch.includes(term));
      const matches = (group.value === 'all' || card.dataset.metalGroup === group.value) && textMatches;
      card.hidden = !matches;
      if (matches) visible += 1;
    });
    sections.forEach(section => { section.hidden = !section.querySelector('.atlas-card:not([hidden])'); });
    count.textContent = `${visible} of ${cards.length} profiles`;
    empty.hidden = visible !== 0;
  }
  form.hidden = false;
  form.addEventListener('submit', event => event.preventDefault());
  query.addEventListener('input', filter);
  group.addEventListener('change', filter);
  form.addEventListener('reset', () => { query.value = ''; group.value = 'all'; filter(); });
})();
