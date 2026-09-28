#!/usr/bin/env node
// Serve this repo with the live site's clean URL rules, then compare every
// sitemap URL with https://microbialmetallomics.com. Fails if a status code
// or HTML body differs.

import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const LIVE = 'https://microbialmetallomics.com';
const SITEMAP = path.join(ROOT, 'sitemap.xml');

function sitemapUrls() {
  const xml = fs.readFileSync(SITEMAP, 'utf8');
  const urls = [...xml.matchAll(/<loc>\s*([^<\s]+)\s*<\/loc>/g)].map((match) => match[1]);
  if (!urls.length) throw new Error('No URLs found in sitemap.xml');
  return urls;
}

function safeJoin(rel) {
  const full = path.resolve(ROOT, rel);
  const rootWithSep = ROOT.endsWith(path.sep) ? ROOT : ROOT + path.sep;
  if (full !== ROOT && !full.startsWith(rootWithSep)) return null;
  return full;
}

function resolveRequest(pathname) {
  let decoded;
  try {
    decoded = decodeURIComponent(pathname);
  } catch {
    return { status: 400, body: Buffer.from('Bad request') };
  }
  if (decoded.includes('\0')) return { status: 400, body: Buffer.from('Bad request') };

  if (decoded.length > 1 && decoded.endsWith('/')) {
    return { redirect: decoded.replace(/\/+$/, '') || '/' };
  }

  const rel = decoded === '/' ? 'index.html' : decoded.replace(/^\/+/, '');
  const candidates = path.extname(rel)
    ? [rel]
    : [`${rel}.html`, path.join(rel, 'index.html')];

  for (const candidate of candidates) {
    const full = safeJoin(candidate);
    if (full && fs.existsSync(full) && fs.statSync(full).isFile()) {
      return { status: 200, file: full };
    }
  }

  const notFound = safeJoin('404.html');
  if (notFound && fs.existsSync(notFound)) return { status: 404, file: notFound };
  return { status: 404, body: Buffer.from('Not found') };
}

function contentType(file) {
  switch (path.extname(file).toLowerCase()) {
    case '.html':
      return 'text/html; charset=utf-8';
    case '.css':
      return 'text/css; charset=utf-8';
    case '.js':
    case '.mjs':
      return 'application/javascript; charset=utf-8';
    case '.svg':
      return 'image/svg+xml';
    case '.xml':
      return 'application/xml';
    case '.txt':
      return 'text/plain; charset=utf-8';
    case '.json':
      return 'application/json; charset=utf-8';
    default:
      return 'application/octet-stream';
  }
}

function startServer() {
  const server = http.createServer((req, res) => {
    const host = req.headers.host || '127.0.0.1';
    const url = new URL(req.url || '/', `http://${host}`);
    const resolved = resolveRequest(url.pathname);

    if (resolved.redirect) {
      const location = resolved.redirect + url.search;
      res.writeHead(308, {
        Location: location,
        'Content-Type': 'text/plain',
        Refresh: `0;url=${location}`,
        'Access-Control-Allow-Origin': '*',
        'Cache-Control': 'public, max-age=0, must-revalidate',
      });
      res.end('Redirecting');
      return;
    }

    const body = resolved.file ? fs.readFileSync(resolved.file) : resolved.body;
    const inAssets = resolved.file && resolved.file.includes(`${path.sep}assets${path.sep}`);
    res.writeHead(resolved.status, {
      'Content-Type': resolved.file ? contentType(resolved.file) : 'text/plain; charset=utf-8',
      'Content-Length': body.length,
      'Access-Control-Allow-Origin': '*',
      'Cache-Control': inAssets
        ? 'public, max-age=31536000, immutable'
        : 'public, max-age=0, must-revalidate',
    });
    res.end(body);
  });

  return new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const address = server.address();
      resolve({ server, port: address.port });
    });
  });
}

async function fetchBuf(url, attempt = 1) {
  try {
    const res = await fetch(url, {
      redirect: 'manual',
      headers: {
        'user-agent': 'microbialmetallomics-verify-mirror',
        accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      },
    });
    const buf = Buffer.from(await res.arrayBuffer());
    return { status: res.status, buf };
  } catch (err) {
    if (attempt < 3) {
      await new Promise((resolve) => setTimeout(resolve, 400 * attempt));
      return fetchBuf(url, attempt + 1);
    }
    throw err;
  }
}

function firstDiff(left, right) {
  const length = Math.min(left.length, right.length);
  for (let i = 0; i < length; i += 1) {
    if (left[i] !== right[i]) return i;
  }
  return left.length === right.length ? -1 : length;
}

function snippet(buf, index) {
  const start = Math.max(0, index - 48);
  const end = Math.min(buf.length, index + 48);
  return JSON.stringify(buf.subarray(start, end).toString('utf8'));
}

async function mapPool(items, limit, fn) {
  const results = new Array(items.length);
  let cursor = 0;
  async function worker() {
    while (cursor < items.length) {
      const index = cursor;
      cursor += 1;
      results[index] = await fn(items[index], index);
    }
  }
  const workers = Math.min(limit, items.length);
  await Promise.all(Array.from({ length: workers }, () => worker()));
  return results;
}

const urls = sitemapUrls();
const { server, port } = await startServer();
const failures = [];

try {
  await mapPool(urls, 6, async (liveUrl) => {
    let pathAndQuery = liveUrl.startsWith(LIVE) ? liveUrl.slice(LIVE.length) : new URL(liveUrl).pathname;
    if (!pathAndQuery.startsWith('/')) pathAndQuery = `/${pathAndQuery}`;
    const localUrl = `http://127.0.0.1:${port}${pathAndQuery}`;
    const [local, live] = await Promise.all([fetchBuf(localUrl), fetchBuf(liveUrl)]);
    const sameStatus = local.status === live.status;
    const sameBody = local.buf.equals(live.buf);
    if (sameStatus && sameBody) return;
    const at = firstDiff(local.buf, live.buf);
    failures.push({
      url: liveUrl,
      localStatus: local.status,
      liveStatus: live.status,
      localLength: local.buf.length,
      liveLength: live.buf.length,
      at,
      localSnippet: at >= 0 ? snippet(local.buf, at) : '',
      liveSnippet: at >= 0 ? snippet(live.buf, at) : '',
    });
  });
} finally {
  await new Promise((resolve) => server.close(resolve));
}

if (failures.length) {
  console.error(`FAIL: ${failures.length} of ${urls.length} sitemap URLs differ.`);
  for (const failure of failures) {
    console.error(`- ${failure.url}`);
    console.error(
      `  status local=${failure.localStatus} live=${failure.liveStatus} bytes local=${failure.localLength} live=${failure.liveLength} firstDiff=${failure.at}`,
    );
    if (failure.at >= 0) {
      console.error(`  local: ${failure.localSnippet}`);
      console.error(`  live:  ${failure.liveSnippet}`);
    }
  }
  process.exit(1);
}

console.log(`OK: ${urls.length} sitemap URLs matched the live site (status code and HTML body).`);
