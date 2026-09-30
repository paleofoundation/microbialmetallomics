const test = require('node:test');
const assert = require('node:assert/strict');
const { createHandler } = require('../lib/newsletter.cjs');

function setup({ existing, fail, ignoreTopicWrite = false } = {}) {
  let at = Date.now();
  const env = { RESEND_API_KEY: 'test-only', RESEND_EMAIL_DOMAIN: 'newsletter.example.test', NEWSLETTER_SECRET: 'test-only-secret-which-is-at-least-32-characters', NEWSLETTER_SEGMENT_ID: 'our-segment', NEWSLETTER_TOPIC_ID: 'our-topic', VERCEL_ENV: 'production' };
  const id = '11111111-2222-3333-4444-555555555555';
  let contact = existing ? { id, email: 'reader@example.test', unsubscribed: true, properties: {}, segments: [], topics: [], ...existing } : null;
  const sends = new Map();
  const calls = [];
  const response = (data, status = 200) => ({ ok: status < 400, status, json: async () => structuredClone(data) });
  const fetchImpl = async (url, options) => {
    const path = url.replace('https://api.resend.com', '');
    const method = options.method;
    const body = options.body === undefined ? undefined : JSON.parse(options.body);
    calls.push({ path, method, body });
    if (fail?.(path, method, body)) return response({}, 500);
    if (path === '/emails') {
      const key = options.headers['Idempotency-Key'];
      if (sends.has(key)) assert.deepEqual(body, sends.get(key));
      sends.set(key, body);
      return response({ id: 'email-id' });
    }
    if (path === '/contacts' && method === 'POST') {
      contact = { id, ...body, segments: [], topics: [] };
      return response({ id });
    }
    if (path.startsWith('/contacts/')) {
      if (!contact) return response({}, 404);
      if (path.endsWith('/topics')) {
        if (method === 'GET') return response({ data: contact.topics });
        assert.ok(Array.isArray(body));
        if (!contact.unsubscribed && !ignoreTopicWrite) contact.topics = body;
        return response({ id });
      }
      if (path.endsWith('/segments')) return response({ data: contact.segments });
      if (path.includes('/segments/')) { contact.segments.push({ id: env.NEWSLETTER_SEGMENT_ID }); return response({ id }); }
      if (method === 'GET') {
        // Resend wraps each custom property's value and type in the GET response.
        return response({ ...contact, properties: Object.fromEntries(Object.entries(contact.properties).map(([key, value]) => [key, { value, type: typeof value }])) });
      }
      if (method === 'PATCH') {
        if ('unsubscribed' in body) contact.unsubscribed = body.unsubscribed;
        Object.assign(contact.properties, body.properties);
        return response({ id });
      }
    }
    throw new Error('Unexpected mocked API path: ' + path);
  };
  const claims = new Set();
  const claimImpl = async path => { if (claims.has(path)) return false; claims.add(path); return true; };
  const handler = createHandler({ env, fetchImpl, now: () => at, claimImpl, wasClaimedImpl: async path => claims.has(path), pause: async () => {} });
  async function request(body, { method = 'POST', origin = 'https://microbialmetallomics.com', type = 'application/json' } = {}) {
    let result;
    const res = { statusCode: 200, setHeader() {}, end(value) { result = { status: this.statusCode, ...JSON.parse(value) }; } };
    await handler({ method, body, headers: { origin, 'content-type': type } }, res);
    return result;
  }
  return { request, calls, sends, get contact() { return contact; }, expire() { at += 86401000; }, token() { return new URL([...sends.values()].at(-1).text.match(/https:\/\/[^\s]+\?confirm=[^\s]+/)[0]).searchParams.get('confirm'); } };
}

test('signup remains pending, repeat is deduplicated, explicit confirmation opts into only the newsletter', async () => {
  const s = setup();
  const data = { action: 'subscribe', email: 'Reader@example.test', consent: true };
  assert.equal((await s.request(data)).status, 200);
  assert.equal(s.contact.unsubscribed, true);
  assert.deepEqual(s.contact.segments, []);
  const token = s.token();
  assert.equal((await s.request(data)).status, 200);
  assert.equal(s.sends.size, 1);
  assert.equal(s.token(), token);
  assert.equal((await s.request({ action: 'confirm', token })).status, 200);
  assert.equal(s.contact.unsubscribed, false);
  assert.equal(s.contact.properties.mm_nonce, '');
  assert.deepEqual(s.contact.topics, [{ id: 'our-topic', subscription: 'opt_in' }]);
  s.contact.unsubscribed = true;
  assert.equal((await s.request({ action: 'confirm', token })).status, 400);
  assert.equal(s.contact.unsubscribed, true);
});

test('expired, tampered, and GET confirmation links never activate a contact', async () => {
  const s = setup();
  await s.request({ action: 'subscribe', email: 'reader@example.test', consent: true });
  const token = s.token();
  assert.equal((await s.request({ action: 'confirm', token }, { method: 'GET' })).status, 405);
  assert.equal((await s.request({ action: 'confirm', token: token.slice(0, -2) + 'xx' })).status, 400);
  s.expire();
  assert.equal((await s.request({ action: 'confirm', token })).status, 400);
  assert.equal(s.contact.unsubscribed, true);
});

test('invalid input, honeypot and cross-origin requests make no provider writes', async () => {
  const s = setup();
  assert.equal((await s.request({ action: 'subscribe', email: 'bad', consent: true })).status, 400);
  assert.equal((await s.request({ action: 'subscribe', email: 'reader@example.test' })).status, 400);
  assert.equal((await s.request({ action: 'subscribe', email: 'reader@example.test', consent: true, company: 'bot' })).status, 200);
  assert.equal((await s.request({}, { origin: 'https://another-site.test' })).status, 403);
  assert.equal((await s.request({}, { type: 'text/plain' })).status, 415);
  assert.equal(s.calls.length, 0);
});

test('repeat signup preserves an existing active subscriber', async () => {
  const s = setup({ existing: { unsubscribed: false, segments: [{ id: 'our-segment' }], topics: [{ id: 'our-topic', subscription: 'opt_in' }] } });
  assert.equal((await s.request({ action: 'subscribe', email: 'reader@example.test', consent: true })).status, 200);
  assert.equal(s.sends.size, 0);
  assert.equal(s.contact.unsubscribed, false);
  assert.ok(s.calls.every(x => x.method === 'GET'));
});

test('confirmation does not override an unrelated account-wide unsubscribe', async () => {
  const s = setup({ existing: { segments: [{ id: 'other-list' }] } });
  await s.request({ action: 'subscribe', email: 'reader@example.test', consent: true });
  assert.equal((await s.request({ action: 'confirm', token: s.token() })).status, 409);
  assert.equal(s.contact.unsubscribed, true);
  assert.deepEqual(s.contact.segments, [{ id: 'other-list' }]);
});

test('provider failure directs the reader to request a fresh link and does not add them to the segment', async () => {
  const s = setup({ fail: (path, method) => path.endsWith('/topics') && method === 'PATCH' });
  await s.request({ action: 'subscribe', email: 'reader@example.test', consent: true });
  const r = await s.request({ action: 'confirm', token: s.token() });
  assert.equal(r.status, 503);
  assert.equal(r.ok, false);
  assert.match(r.message, /request a new confirmation email/);
  assert.deepEqual(s.contact.segments, []);
});

test('simultaneous confirmation requests can only activate once', async () => {
  const s = setup();
  await s.request({ action: 'subscribe', email: 'reader@example.test', consent: true });
  const data = { action: 'confirm', token: s.token() };
  const results = await Promise.all([s.request(data), s.request(data)]);
  assert.deepEqual(results.map(r => r.status).sort(), [200, 400]);
  assert.equal(s.calls.filter(c => c.method === 'PATCH' && c.body?.unsubscribed === false).length, 1);
});

test('a provider success response without a saved topic preference cannot report confirmation', async () => {
  const s = setup({ ignoreTopicWrite: true });
  await s.request({ action: 'subscribe', email: 'reader@example.test', consent: true });
  assert.equal((await s.request({ action: 'confirm', token: s.token() })).status, 503);
  assert.deepEqual(s.contact.segments, []);
});

test('a claim followed by a failed nonce write can recover through a fresh signup', async () => {
  let failOnce = true;
  const s = setup({ fail: (path, method, body) => {
    if (failOnce && method === 'PATCH' && body?.properties?.mm_nonce === '') { failOnce = false; return true; }
    return false;
  } });
  const signup = { action: 'subscribe', email: 'reader@example.test', consent: true };
  await s.request(signup);
  const first = s.token();
  assert.equal((await s.request({ action: 'confirm', token: first })).status, 503);
  assert.equal((await s.request(signup)).status, 200);
  const second = s.token();
  assert.notEqual(second, first);
  assert.equal((await s.request({ action: 'confirm', token: second })).status, 200);
});
