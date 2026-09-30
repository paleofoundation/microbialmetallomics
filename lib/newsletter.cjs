const { createHmac, randomBytes, timingSafeEqual } = require('node:crypto');

const ORIGIN = 'https://microbialmetallomics.com';
const DAY = 86400;
const NOTICE = 'Check your inbox for a confirmation link. You will join the newsletter only after confirming your email address.';
const EXPIRED = 'This confirmation link has expired or has already been used. Please request a new link using the signup form.';

async function claimConfirmation(path) {
  const { put } = require('@vercel/blob');
  try {
    await put(path, '1', { access: 'private', addRandomSuffix: false, allowOverwrite: false, abortSignal: AbortSignal.timeout(8000) });
    return true;
  } catch (error) {
    if (error.message?.startsWith('Vercel Blob: This blob already exists,')) return false;
    throw error;
  }
}

async function wasClaimed(path) {
  const { head, BlobNotFoundError } = require('@vercel/blob');
  try { await head(path); return true; }
  catch (error) { if (error instanceof BlobNotFoundError) return false; throw error; }
}

function createHandler({ env = process.env, fetchImpl = globalThis.fetch, now = () => Date.now(), random = randomBytes, claimImpl = claimConfirmation, wasClaimedImpl = wasClaimed, pause = ms => new Promise(resolve => setTimeout(resolve, ms)) } = {}) {
  const traffic = new Map();
  const sign = value => createHmac('sha256', env.NEWSLETTER_SECRET).update(value).digest('base64url');
  const claimPath = (id, nonce, exp) => 'newsletter/confirm/' + exp + '/' + sign(id + ':' + nonce);
  function tokenFor(contact) {
    const p = contact.properties;
    const payload = Buffer.from(JSON.stringify({ id: contact.id, nonce: p.mm_nonce, exp: p.mm_requested + DAY })).toString('base64url');
    return payload + '.' + sign(payload);
  }
  function parseToken(token) {
    if (typeof token !== 'string' || token.length > 1500) return null;
    const parts = token.split('.');
    if (parts.length !== 2 || !/^[\w-]+$/.test(parts[0]) || !/^[\w-]+$/.test(parts[1])) return null;
    const signature = Buffer.from(parts[1]);
    const expected = Buffer.from(sign(parts[0]));
    if (signature.length !== expected.length || !timingSafeEqual(signature, expected)) return null;
    try {
      const value = JSON.parse(Buffer.from(parts[0], 'base64url').toString());
      if (!/^[a-f0-9-]{36}$/.test(value.id) || !/^[a-f0-9]{48}$/.test(value.nonce) || !Number.isInteger(value.exp)) return null;
      if (value.exp <= now() / 1000 || value.exp > now() / 1000 + DAY + 60) return null;
      return value;
    } catch { return null; }
  }
  async function provider(path, method = 'GET', body, idempotencyKey) {
    for (let attempt = 0; attempt < 3; attempt++) {
      const response = await fetchImpl('https://api.resend.com' + path, {
        method,
        headers: { Authorization: 'Bearer ' + env.RESEND_API_KEY, 'Content-Type': 'application/json', ...(idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {}) },
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: AbortSignal.timeout(8000),
      });
      if (response.status === 429 && attempt < 2) {
        await pause(1000 * (attempt + 1));
        continue;
      }
      const result = await response.json();
      if (!response.ok) {
        const error = new Error('Newsletter provider request failed');
        error.status = response.status;
        throw error;
      }
      return result;
    }
  }
  async function contactFor(email) {
    try {
      const contact = await provider('/contacts/' + encodeURIComponent(email));
      contact.properties = Object.fromEntries(Object.entries(contact.properties || {}).map(([key, value]) => [key, value && typeof value === 'object' && 'value' in value ? value.value : value]));
      return contact;
    }
    catch (error) { if (error.status === 404) return null; throw error; }
  }
  function allowRequest(req) {
    const origin = req.headers.origin;
    if (origin === ORIGIN || origin === 'https://www.microbialmetallomics.com') return true;
    if (env.VERCEL_ENV === 'preview' && env.VERCEL_URL && origin === 'https://' + env.VERCEL_URL) return true;
    return env.VERCEL_ENV !== 'production' && origin === 'http://127.0.0.1:4173';
  }
  function withinLimit(req) {
    // Best-effort per-instance protection supplements persistent per-email deduplication.
    const ip = String(req.headers['x-vercel-forwarded-for'] || req.headers['x-forwarded-for'] || req.socket?.remoteAddress || 'unknown').split(',')[0];
    const key = sign(ip);
    const at = now();
    for (const [id, value] of traffic) if (value.until <= at) traffic.delete(id);
    if (traffic.size > 10000) return false;
    const value = traffic.get(key) || { count: 0, until: at + 600000 };
    value.count++;
    traffic.set(key, value);
    return value.count <= 10;
  }
  function reply(res, status, message) {
    res.statusCode = status;
    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    res.setHeader('Cache-Control', 'no-store');
    res.setHeader('X-Content-Type-Options', 'nosniff');
    res.end(JSON.stringify({ ok: status < 400, message }));
  }
  async function subscribe(data) {
    const email = typeof data.email === 'string' ? data.email.trim().toLowerCase() : '';
    if (data.consent !== true || email.length > 254 || !/^[a-z0-9.!#$%&'*+\/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+$/i.test(email)) {
      return [400, 'Enter a valid email address and confirm that you want to receive the research digest.'];
    }
    if (data.company) return [200, NOTICE];
    let contact = await contactFor(email);
    const seconds = Math.floor(now() / 1000);
    if (contact) {
      const topics = await provider('/contacts/' + contact.id + '/topics');
      if (!contact.unsubscribed && topics.data?.some(t => t.id === env.NEWSLETTER_TOPIC_ID && t.subscription === 'opt_in')) {
        const segments = await provider('/contacts/' + contact.id + '/segments');
        if (segments.data?.some(s => s.id === env.NEWSLETTER_SEGMENT_ID)) return [200, 'If this address is already confirmed, it remains subscribed. Otherwise, check your inbox for your confirmation link.'];
      }
    }
    const old = contact?.properties || {};
    const reuse = typeof old.mm_nonce === 'string' && old.mm_nonce.length === 48 && old.mm_requested > seconds - DAY && old.mm_requested <= seconds && !await wasClaimedImpl(claimPath(contact.id, old.mm_nonce, old.mm_requested + DAY));
    const properties = reuse ? old : { mm_nonce: random(24).toString('hex'), mm_requested: seconds };
    if (!contact) {
      const created = await provider('/contacts', 'POST', { email, unsubscribed: true, properties: { ...properties, mm_created: 1 } });
      contact = { id: created.id, email, unsubscribed: true, properties };
    } else if (!reuse) {
      await provider('/contacts/' + contact.id, 'PATCH', { properties });
      contact.properties = { ...old, ...properties };
    }
    const url = ORIGIN + '/newsletter?confirm=' + tokenFor(contact);
    const text = `Confirm your Microbial Metallomics subscription\n\nFollow new research, critical commentary, and useful methods at the intersection of metals and microbial life.\n\nConfirm your email address: ${url}\n\nThis link expires in 24 hours. If you did not request this, ignore the email; you will not be subscribed. You can unsubscribe from any future digest.\n\nMicrobial Metallomics\n${ORIGIN}\nQuestions: ${ORIGIN}/contribute`;
    const html = `<div style="font-family:Georgia,serif;color:#18302e;max-width:580px;margin:32px auto;padding:24px"><p style="font:12px Arial,sans-serif;letter-spacing:2px">MICROBIAL METALLOMICS</p><h1 style="font-size:30px">Confirm your subscription.</h1><p style="font:16px/1.8 Arial,sans-serif">New research, critical commentary, and useful methods at the intersection of metals and microbial life.</p><p style="margin:30px 0"><a href="${url}" style="background:#235c55;color:#fff;padding:14px 20px;text-decoration:none;font:16px Arial,sans-serif">Confirm my email address</a></p><p style="font:14px/1.8 Arial,sans-serif">This link expires in 24 hours. If you did not request this, ignore the email; you will not be subscribed. You can unsubscribe from any future digest.</p><hr style="border:0;border-top:1px solid #ddd"><p style="font:13px/1.8 Arial,sans-serif"><a href="${ORIGIN}">Microbial Metallomics</a> · <a href="${ORIGIN}/contribute">Contact</a></p></div>`;
    await provider('/emails', 'POST', {
      from: 'Microbial Metallomics <hello@' + env.RESEND_EMAIL_DOMAIN + '>', to: [email],
      subject: 'Confirm your Microbial Metallomics subscription', html, text,
    }, 'mm-confirm-' + contact.id + '-' + contact.properties.mm_nonce);
    return [200, NOTICE];
  }
  async function confirm(data) {
    const token = parseToken(data.token);
    if (!token) return [400, EXPIRED];
    const contact = await contactFor(token.id);
    const p = contact?.properties || {};
    if (!contact || p.mm_nonce !== token.nonce || p.mm_requested + DAY !== token.exp) return [400, EXPIRED];
    if (contact.unsubscribed) {
      const segments = await provider('/contacts/' + contact.id + '/segments');
      // Do not undo account-wide opt-outs for unrelated mailing lists in the shared account.
      if (!p.mm_created || segments.has_more || segments.data?.some(x => x.id !== env.NEWSLETTER_SEGMENT_ID)) {
        return [409, 'This address has an account-wide unsubscribe covering another mailing list. Please contact us through the contribution page before reactivating it.'];
      }
    }
    // A conditional create is the cross-instance, atomic claim. Store no email or raw token.
    if (!await claimImpl(claimPath(token.id, token.nonce, token.exp))) return [400, EXPIRED];
    // Consume the nonce before activation. Recovery from a partial failure needs a fresh link.
    try {
      await provider('/contacts/' + contact.id, 'PATCH', { properties: { mm_nonce: '' } });
      // Activate before saving the newsletter-specific preference.
      await provider('/contacts/' + contact.id, 'PATCH', { unsubscribed: false });
      await provider('/contacts/' + contact.id + '/topics', 'PATCH', [{ id: env.NEWSLETTER_TOPIC_ID, subscription: 'opt_in' }]);
      // Provider reads can briefly lag writes. Retry reads, never the consent mutation.
      let retained = false;
      for (let attempt = 0; attempt < 5; attempt++) {
        if (attempt) await pause(attempt * 300);
        const topics = await provider('/contacts/' + contact.id + '/topics');
        if (topics.data?.some(t => t.id === env.NEWSLETTER_TOPIC_ID && t.subscription === 'opt_in')) { retained = true; break; }
      }
      if (!retained) throw new Error('Topic preference was not retained');
      await provider('/contacts/' + contact.id + '/segments/' + env.NEWSLETTER_SEGMENT_ID, 'POST');
      await provider('/contacts/' + contact.id, 'PATCH', { properties: { mm_confirmed: Math.floor(now() / 1000) } });
    } catch (error) {
      console.error('Newsletter confirmation incomplete', { status: error.status || 0, type: error.name });
      return [503, 'We could not finish confirming your subscription. Please request a new confirmation email using the signup form below.'];
    }
    return [200, 'Your subscription is confirmed. You are on the Microbial Metallomics research digest list, and can unsubscribe from any digest.'];
  }
  return async (req, res) => {
    if (req.method !== 'POST') { res.setHeader('Allow', 'POST'); return reply(res, 405, 'Use the signup form to request or confirm a subscription.'); }
    if (!allowRequest(req)) return reply(res, 403, 'Please use the newsletter form on microbialmetallomics.com.');
    if (!String(req.headers['content-type'] || '').startsWith('application/json')) return reply(res, 415, 'The signup form could not be read. Please reload the page.');
    if (!env.RESEND_API_KEY || !env.RESEND_EMAIL_DOMAIN || !env.NEWSLETTER_SEGMENT_ID || !env.NEWSLETTER_TOPIC_ID || (env.NEWSLETTER_SECRET || '').length < 32) return reply(res, 503, 'Email signup is temporarily unavailable. Please try again later or follow our RSS feed.');
    if (!withinLimit(req)) { res.setHeader('Retry-After', '600'); return reply(res, 429, 'Too many requests. Please wait ten minutes before trying again.'); }
    try {
      if (Number(req.headers['content-length']) > 8192 || (typeof req.body === 'string' && req.body.length > 8192)) return reply(res, 413, 'The form is too large. Please reload the page.');
      let data;
      try { data = typeof req.body === 'string' ? JSON.parse(req.body) : req.body; } catch { return reply(res, 400, 'The form could not be read. Please reload the page.'); }
      if (!data || typeof data !== 'object' || Array.isArray(data)) return reply(res, 400, 'The form could not be read. Please reload the page.');
      const result = data.action === 'subscribe' ? await subscribe(data) : data.action === 'confirm' ? await confirm(data) : [400, 'Choose signup or confirmation from the newsletter page.'];
      return reply(res, ...result);
    } catch (error) {
      // Keep email addresses, tokens and upstream response bodies out of logs and responses.
      console.error('Newsletter provider unavailable', { status: error.status || 0, type: error.name });
      return reply(res, 503, 'We could not complete that request. Please try again shortly. Your subscription has not been reported as confirmed.');
    }
  };
}

module.exports = { createHandler, claimConfirmation };
