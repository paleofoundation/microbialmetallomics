(() => {
  const form = document.getElementById('method-question-form');
  if (!form) return;
  const select = document.getElementById('method-question');
  const answers = document.getElementById('method-answers');
  const status = document.getElementById('method-status');
  const reset = form.querySelector('button[type="reset"]');
  const cards = [...answers.querySelectorAll('[data-method-question]')];
  const update = () => {
    const all = select.value === 'all';
    cards.forEach(card => { card.hidden = !all && card.dataset.methodQuestion !== select.value; });
    answers.dataset.filtered = String(!all);
    reset.disabled = all;
    status.textContent = all
      ? 'Compare all four research questions below.'
      : 'Showing methods for: ' + select.options[select.selectedIndex].textContent;
  };
  form.hidden = false;
  form.addEventListener('submit', event => event.preventDefault());
  select.addEventListener('change', update);
  form.addEventListener('reset', event => {
    event.preventDefault();
    select.value = 'all';
    update();
    select.focus();
  });
  update();
})();
