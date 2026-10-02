#!/usr/bin/env python3
"""Fail-closed editorial release gate. Pending checks are never counted as passes."""
from pathlib import Path
from urllib.parse import urlsplit
import argparse
import hashlib
import json
import re
from access_render import Citations, claim_nodes, render_blocks

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    'lactoferrin-iron-withholding-microbial-countermeasures': 'host-defense',
    'hepcidin-ferroportin-iron-redistribution': 'host-defense',
    'transferrin-ferritin-heme-recycling': 'host-defense',
    'calprotectin-multimetal-nutritional-immunity': 'host-defense',
    'phagosomal-copper-zinc-intoxication': 'host-defense',
    'metallothionein-metal-buffering-microbial-conflict': 'host-defense',
    'glutathione-metals-mitochondria-drug-metabolism': 'host-defense',
    'bile-acids-biliary-metal-excretion': 'host-defense',
    'vancomycin-zinc-binding-antimicrobial-mechanisms': 'hidden-mechanisms',
    'silymarin-metal-binding-liver-evidence': 'hidden-mechanisms',
    'saccharomyces-boulardii-metal-biosorption': 'hidden-mechanisms',
}
EVIDENCE = {'observed', 'model-causal', 'human-intervention', 'hypothesis', 'established-mechanism'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_digest():
    """Invalidate verification after changes to rendered pages, assets or checks."""
    files = list(ROOT.glob('*.html'))
    files += [ROOT / name for name in ['package.json', 'vercel.json', 'sitemap.xml', 'robots.txt', 'llms.txt'] if (ROOT / name).exists()]
    for folder in ['assets', 'tools', 'tests', 'api', 'library', 'blog', 'metals', 'people', 'glossary', 'research', 'feeds']:
        files += [p for p in (ROOT / folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and not p.name.startswith('.')]
    return hashlib.sha256('\n'.join(str(p.relative_to(ROOT)) + ':' + digest(p) for p in sorted(set(files))).encode()).hexdigest()


def words(data):
    """Count reader-facing prose, excluding repeated claims ledgers and references."""
    fields = {'text', 'title', 'caption', 'cells', 'headers', 'measures', 'decision', 'label', 'finding', 'claim', 'missing'}
    def strings(value, key=''):
        if isinstance(value, dict):
            return [s for k, v in value.items() for s in strings(v, k)]
        if isinstance(value, list):
            return [s for v in value for s in strings(v, key)]
        return [value] if isinstance(value, str) and key in fields else []
    return len(re.findall(r"\b[\w’'-]+\b", ' '.join(strings({'summary': data.get('summary', {}), 'sections': data.get('sections', [])}))))


def validate_article(data, slug):
    errors = []
    def require(condition, message):
        if not condition: errors.append(message)
    required = ['slug', 'title', 'shortTitle', 'series', 'description', 'deck', 'published', 'updated', 'keywords', 'summary', 'sections', 'faqs', 'sources', 'claims', 'share', 'related']
    for key in required:
        require(key in data and bool(data[key]), 'Missing field: ' + key)
    if errors: return errors
    require(data['slug'] == slug, 'Filename and slug disagree')
    require(data['series'] == EXPECTED[slug], 'Wrong series')
    require(110 <= len(data['description']) <= 185, 'Description must be concise and complete')
    require(words(data) >= 1100, 'Fewer than 1,100 body words')
    sources = data['sources']
    require(len(sources) >= 6, 'Fewer than six sources')
    require(sum(s.get('kind') == 'primary' for s in sources) >= 5, 'Fewer than five primary sources')
    for i, source in enumerate(sources, 1):
        for key in ['authors', 'year', 'title', 'url', 'kind', 'access', 'studyType', 'setting', 'note']:
            require(bool(source.get(key)), f'Source {i}: missing {key}')
        url = source.get('url', '')
        parsed = urlsplit(url)
        require(parsed.scheme == 'https' and bool(parsed.netloc) and not re.search(r'\s', url), f'Source {i}: invalid URL')
        require(source.get('kind') in ['primary', 'review', 'guidance'], f'Source {i}: invalid kind')
        require(source.get('access') in ['full-text', 'abstract'], f'Source {i}: access not stated')
    blocks = [b for s in data['sections'] for b in s['blocks']]
    ids = [s['id'] for s in data['sections']]
    require(len(ids) == len(set(ids)) and all(re.fullmatch(r'[a-z][a-z0-9-]+', i) for i in ids), 'Invalid or duplicate section IDs')
    require(any(b['type'] == 'table' for b in blocks), 'No comparison table')
    proposals = [b for b in blocks if b['type'] == 'proposal']
    require(bool(proposals) and all(b.get('decision') and b.get('measures') for b in proposals), 'Missing discriminating research proposal')
    links = [b for b in blocks if b['type'] == 'link']
    require(len(links) >= 3 and all(b.get('url', '').startswith('/') for b in links), 'Need three contextual internal links')
    require(len(data['faqs']) >= 3, 'Need at least three useful FAQs')
    require(len(data['claims']) >= 8, 'Need at least eight central claims in the evidence ledger')
    claim_ids = [c.get('id') for c in data['claims']]
    require(all(claim_ids) and len(claim_ids) == len(set(claim_ids)), 'Invalid or duplicate claim IDs')
    for c in data['claims']:
        require(c.get('evidence') in EVIDENCE, 'Invalid evidence classification for ' + str(c.get('id')))
        require(bool(c.get('claim')) and bool(c.get('setting')) and bool(c.get('boundary')), 'Claim lacks wording, setting or interpretation boundary')
    all_nodes = [data['summary'], data['share'], *claim_nodes(blocks), *data['claims']]
    for node in all_nodes:
        require(all(isinstance(n, int) and not isinstance(n, bool) and 0 < n <= len(sources) for n in node.get('refs', [])), 'Invalid reference index')
    for node in [data['summary'], data['share'], *data['claims']]:
        require(bool(node.get('refs')), 'Summary, share card and central claims must have sources')
    require(all(data['share'].get(k) for k in ['hook', 'explanation', 'qualification']), 'Share card missing context or qualification')
    if not errors:
        try:
            cite = Citations(sources)
            cite.cite(data['summary'])
            render_blocks(blocks, cite.cite)
            require(set(cite.order) == set(range(1, len(sources) + 1)), 'Not every declared source is cited in the main review')
        except (KeyError, AssertionError, TypeError, ValueError) as e:
            errors.append('Article cannot render: ' + str(e))
    return errors


def audit_errors(audit, source_hash):
    errors = []
    if audit.get('sourceHash') != source_hash: errors.append('Independent audit is stale or for different content')
    if audit.get('status') != 'pass': errors.append('Independent audit has not passed')
    if audit.get('openIssues'): errors.append('Independent audit contains unresolved issues')
    if len(audit.get('sourceChecks', [])) < 3: errors.append('Independent audit lacks three documented source checks')
    required = {'chemistry', 'claim-source-match', 'model-to-human', 'counterevidence'}
    if not required.issubset(set(audit.get('checkedAreas', []))): errors.append('Independent audit coverage incomplete')
    if not audit.get('reviewer') or not audit.get('summary'): errors.append('Independent audit lacks review provenance')
    return errors


def release_scope(manifest):
    """Require a named, explicit partition; omitted work cannot become a pass."""
    if not isinstance(manifest, dict) or not re.fullmatch(r'[a-z0-9][a-z0-9-]+', manifest.get('id', '')):
        raise ValueError('Release needs a stable ID')
    included, excluded = manifest.get('articles'), manifest.get('excluded')
    for name, values in [('articles', included), ('excluded', excluded)]:
        if not isinstance(values, list) or any(not isinstance(s, str) for s in values) or len(values) != len(set(values)):
            raise ValueError('Release ' + name + ' must be a unique slug list')
    if not included or set(included) & set(excluded) or set(included) | set(excluded) != set(EXPECTED):
        raise ValueError('Release must explicitly partition the complete campaign')
    selected = [slug for slug in EXPECTED if slug in included]
    scope_hash = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return selected, scope_hash


def run(review_dir, audit_dir, receipts=None, release=None):
    failures, pending, articles = [], [], []
    receipts = receipts or {}
    blocked = receipts.get('blockedArticles', {})
    selected, scope_hash = release_scope(release) if release is not None else (list(EXPECTED), None)
    def add(target, gate, article, detail): target.append(dict(gate=gate, article=article, detail=detail))
    package_hashes = []
    for slug in selected:
        if slug in blocked:
            add(failures, 'packages', slug, blocked[slug])
            add(pending, 'independentAudit', slug, 'Blocked task has not completed independent review')
            articles.append(dict(slug=slug, title=slug, wordCount=0, status='blocked'))
            continue
        path = review_dir / (slug + '.json')
        if not path.exists():
            add(pending, 'packages', slug, 'Review not delivered')
            articles.append(dict(slug=slug, title=slug, wordCount=0, status='pending'))
            continue
        package_hashes.append(digest(path))
        try:
            data = json.loads(path.read_text())
            errors = validate_article(data, slug)
        except (ValueError, KeyError, TypeError) as e:
            data, errors = {}, ['Invalid article package: ' + str(e)]
        for error in errors: add(failures, 'packages', slug, error)
        audit_path = audit_dir / (slug + '.json')
        state = 'failed' if errors else 'awaiting audit'
        if not audit_path.exists(): add(pending, 'independentAudit', slug, 'Independent review not delivered')
        else:
            try: audit = json.loads(audit_path.read_text()); errs = audit_errors(audit, digest(path))
            except (ValueError, TypeError) as e: errs = ['Invalid independent audit: ' + str(e)]
            for error in errs: add(failures, 'independentAudit', slug, error)
            if errs: state = 'failed'
            elif not errors: state = 'passed'
        articles.append(dict(slug=slug, title=data.get('title', slug), wordCount=words(data), status=state))
    content_hash = hashlib.sha256('\n'.join(package_hashes).encode()).hexdigest()
    build_hash = build_digest()
    for gate in ['siteChecks', 'browser', 'deployment']:
        record = receipts.get(gate, {})
        if not record: add(pending, gate, None, 'Check has not run')
        elif record.get('status') != 'pass': add(failures, gate, None, record.get('detail', 'Check did not pass'))
        elif record.get('contentHash') != content_hash: add(failures, gate, None, 'Verification receipt is stale for this article set')
        elif record.get('buildHash') != build_hash: add(failures, gate, None, 'Verification receipt is stale for this site build')
        elif scope_hash and record.get('scopeHash') != scope_hash: add(failures, gate, None, 'Verification receipt is for a different release scope')
    gates = {g: 'failed' if any(x['gate'] == g for x in failures) else 'pending' if any(x['gate'] == g for x in pending) else 'passed' for g in ['packages', 'independentAudit', 'siteChecks', 'browser', 'deployment']}
    # Even when packages are absent, independent review must remain pending.
    if gates['packages'] == 'pending' and gates['independentAudit'] == 'passed': gates['independentAudit'] = 'pending'
    return dict(status='pass' if not failures and not pending else 'blocked', failureCount=len(failures), pendingCount=len(pending), failures=failures, pending=pending, articles=articles, gates=gates, contentHash=content_hash, buildHash=build_hash,
                releaseId=release['id'] if release else 'complete-eleven-review-campaign', scopeHash=scope_hash,
                excluded=[dict(slug=slug, status='outside-release', reason=blocked.get(slug, 'Not included in this release')) for slug in EXPECTED if slug not in selected],
                meaning=('All implemented checks passed for this explicit release scope; excluded work is not certified' if release else 'All implemented checks passed') if not failures and not pending else 'Release gate remains closed; pending checks are not passes')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reviews', type=Path, default=ROOT / 'assets/data/host-defense/reviews')
    parser.add_argument('--audits', type=Path, required=True)
    parser.add_argument('--receipts', type=Path)
    parser.add_argument('--release', type=Path, help='Explicit release manifest; omitted means the complete eleven-review campaign')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = run(args.reviews, args.audits, json.loads(args.receipts.read_text()) if args.receipts and args.receipts.exists() else None, json.loads(args.release.read_text()) if args.release else None)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ['status', 'failureCount', 'pendingCount', 'gates', 'contentHash']}, indent=2))
    raise SystemExit(0 if report['status'] == 'pass' else 1)
