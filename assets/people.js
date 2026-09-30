(() => {
  const form = document.querySelector('.people-tools');
  if (!form) return;
  const query = document.getElementById('people-query');
  const area = document.getElementById('people-area');
  const records = [...document.querySelectorAll('[data-person]')];
  const sections = [...document.querySelectorAll('[data-people-area]')];
  const count = document.getElementById('people-count');
  const empty = document.getElementById('people-empty');
  const normalize = text => text.replace(/[łŁ]/g, 'l').normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  const searchText = new Map(records.map(record => [record, normalize(record.textContent)]));
  function filter(updateUrl = true) {
    const terms = normalize(query.value.trim()).split(/\s+/).filter(Boolean);
    let visible = 0;
    records.forEach(record => {
      const match = (!area.value || record.dataset.area === area.value) && terms.every(term => searchText.get(record).includes(term));
      record.hidden = !match;
      if (match) visible++;
    });
    sections.forEach(section => { section.hidden = ![...section.querySelectorAll('[data-person]')].some(record => !record.hidden); });
    count.textContent = visible === records.length ? `Showing all ${records.length} profiles` : `Showing ${visible} of ${records.length} profiles`;
    empty.hidden = visible !== 0;
    if (updateUrl) {
      const url = new URL(location.href);
      if (query.value.trim()) url.searchParams.set('q', query.value.trim()); else url.searchParams.delete('q');
      if (area.value) url.searchParams.set('area', area.value); else url.searchParams.delete('area');
      history.replaceState(null, '', url);
    }
  }
  const params = new URLSearchParams(location.search);
  query.value = params.get('q') || '';
  if ([...area.options].some(option => option.value === params.get('area'))) area.value = params.get('area');
  form.addEventListener('submit', event => { event.preventDefault(); filter(); });
  query.addEventListener('input', () => filter());
  area.addEventListener('change', () => filter());
  form.addEventListener('reset', () => {
    query.value = '';
    area.value = '';
    filter();
  });
  function revealLinkedProfile() {
    let id;
    try { id = decodeURIComponent(location.hash.slice(1)); } catch { return; }
    const target = document.getElementById(id);
    if (target?.matches('[data-person]')) {
      if (target.hidden) {
        query.value = '';
        area.value = '';
        filter();
      }
      requestAnimationFrame(() => target.scrollIntoView({ block: 'start' }));
    }
  }
  window.addEventListener('hashchange', revealLinkedProfile);
  filter(false);
  revealLinkedProfile();
})();
