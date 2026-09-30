(function () {
  'use strict';

  var form = document.getElementById('newsletter-form');
  if (!form) return;

  var fields = document.getElementById('newsletter-fields');
  var email = document.getElementById('newsletter-email');
  var consent = document.getElementById('newsletter-consent');
  var company = document.getElementById('newsletter-company');
  var submit = document.getElementById('newsletter-submit');
  var status = document.getElementById('newsletter-status');
  var confirmPanel = document.getElementById('newsletter-confirm');
  var confirmButton = document.getElementById('newsletter-confirm-button');
  var confirmStatus = document.getElementById('newsletter-confirm-status');

  function message(target, text, state) {
    target.textContent = text;
    target.dataset.state = state || '';
  }

  async function request(payload, target, fallback) {
    var controller = new AbortController();
    var timeout = window.setTimeout(function () { controller.abort(); }, 20000);
    try {
      var response = await fetch('/api/newsletter', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller.signal
      });
      var result = await response.json().catch(function () { return null; });
      var text = result && typeof result.message === 'string' && result.message.length <= 700 ? result.message : '';
      if (!response.ok || !result || result.ok !== true) {
        message(target, text || 'We couldn’t complete this request. Please try again shortly.', 'error');
        return false;
      }
      message(target, text || fallback, 'success');
      return true;
    } catch (_) {
      message(target, 'We couldn’t confirm that your request completed. Check your connection and try again shortly.', 'error');
      return false;
    } finally {
      window.clearTimeout(timeout);
    }
  }

  fields.disabled = false;
  form.addEventListener('submit', async function (event) {
    event.preventDefault();
    if (fields.disabled || !form.reportValidity()) return;
    var payload = {
      action: 'subscribe',
      email: email.value.trim(),
      consent: consent.checked,
      company: company.value
    };
    fields.disabled = true;
    form.setAttribute('aria-busy', 'true');
    submit.textContent = 'Sending…';
    message(status, 'Requesting your confirmation email…');
    await request(payload, status, 'Check your inbox for a confirmation link. You’ll join the newsletter after you confirm.');
    fields.disabled = false;
    form.removeAttribute('aria-busy');
    submit.textContent = 'Send confirmation email →';
  });

  var url = new URL(window.location.href);
  var hasConfirmation = url.searchParams.has('confirm');
  var token = url.searchParams.get('confirm');
  if (hasConfirmation) {
    url.searchParams.delete('confirm');
    window.history.replaceState(window.history.state, '', url.pathname + url.search + url.hash);
    confirmPanel.hidden = false;
    if (!token || token.length > 4096) {
      token = '';
      confirmButton.disabled = true;
      message(confirmStatus, 'This confirmation link is incomplete. Request a new link using the form below.', 'error');
    }
  }

  confirmButton.addEventListener('click', async function () {
    if (!token || confirmButton.disabled) return;
    confirmButton.disabled = true;
    confirmPanel.setAttribute('aria-busy', 'true');
    confirmButton.textContent = 'Confirming…';
    message(confirmStatus, 'Confirming your email…');
    var complete = await request({ action: 'confirm', token: token }, confirmStatus, 'Your subscription is confirmed. Thank you for following Microbial Metallomics.');
    confirmPanel.removeAttribute('aria-busy');
    if (complete) {
      token = '';
      confirmButton.textContent = 'Subscription confirmed';
    } else {
      confirmButton.disabled = false;
      confirmButton.textContent = 'Try confirmation again';
    }
  });
}());
