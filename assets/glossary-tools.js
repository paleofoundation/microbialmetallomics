(() => {
  const form = document.getElementById('glossary-search');
  if (!form) return;
  const input = document.getElementById('glossary-query');
  const scope = document.getElementById('glossary-scope');
  const status = document.getElementById('glossary-count');
  const empty = document.getElementById('glossary-empty');
  const reset = form.querySelector('button[type="reset"]');
  const normalize = value => value.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').replace(/[–—-]/g, ' ').toLowerCase();
  const groups = [...document.querySelectorAll('.gloss-group')];
  const rows = [...document.querySelectorAll('.gloss-row')].map(element => ({
    element,
    term: normalize(element.querySelector('.gr-term').textContent),
    definition: normalize(element.querySelector('.gr-def').textContent)
  }));
  const letters = [...document.querySelectorAll('.gloss-az a[href]')];
  const letterNavigation = document.querySelector('.gloss-az');
  const update = () => {
    const words = normalize(input.value.trim()).split(/\s+/).filter(Boolean);
    let count = 0;
    rows.forEach(row => {
      const haystack = scope.value === 'term' ? row.term : scope.value === 'definition' ? row.definition : row.term + ' ' + row.definition;
      const matches = words.every(word => haystack.includes(word));
      row.element.hidden = !matches;
      if (matches) count += 1;
    });
    groups.forEach(group => { group.hidden = ![...group.querySelectorAll('.gloss-row')].some(row => !row.hidden); });
    letters.forEach(link => { link.hidden = document.getElementById(link.hash.slice(1)).hidden; });
    letterNavigation.hidden = count === 0;
    status.textContent = count + ' of ' + rows.length + ' terms' + (words.length ? ' match your search.' : ' shown.');
    empty.hidden = count !== 0;
    reset.disabled = !input.value && scope.value === 'all';
  };
  form.hidden = false;
  input.addEventListener('input', update);
  scope.addEventListener('change', update);
  form.addEventListener('submit', event => event.preventDefault());
  form.addEventListener('reset', event => {
    event.preventDefault();
    input.value = '';
    scope.value = 'all';
    update();
    input.focus();
  });
  update();
})();
