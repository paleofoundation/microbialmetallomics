const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const search = require('../assets/search.js');
const index = JSON.parse(fs.readFileSync(path.join(__dirname, '../search-index.json'), 'utf8'));

test('matches separated concepts and ignores common connecting words', () => {
  const plain = search.search(index, 'iron gut');
  assert.ok(plain.length > 0);
  assert.ok(plain.some(item => item.url === '/library/iron-fortification-kenyan-infant-microbiome'));
  assert.deepEqual(search.search(index, 'iron and the gut'), plain);
});

test('recognizes element symbols without matching fragments of unrelated words', () => {
  for (const [symbol, name] of [['Fe', 'iron'], ['Ni', 'nickel'], ['Cu', 'copper'], ['As', 'arsenic'], ['W', 'tungsten']]) {
    assert.equal(search.search(index, symbol)[0].url, '/metals/' + name);
  }
  const records = [{ kind: 'Guide', title: 'Amino acids', desc: 'Organic chemistry', url: '/guide' }];
  assert.deepEqual(search.search(records, 'Ni'), []);
});

test('every cataloged element symbol leads to its source profile, including grouped lanthanides', () => {
  const elements = index.filter(item => item.kind === 'Element profile');
  for (const item of elements) {
    assert.ok(item.elements.length > 0);
    for (const element of item.elements) {
      assert.equal(search.search(index, element.symbol)[0].url, item.url, element.symbol);
    }
  }
});

test('normalizes curly apostrophes, accents, and scientific punctuation', () => {
  assert.deepEqual(search.search(index, 'Párkinson’s'), search.search(index, "Parkinson's"));
  assert.deepEqual(search.search(index, 'NiFe-hydrogenase'), search.search(index, '[NiFe] hydrogenase'));
});

test('scope filters restrict result kinds, including when query is empty', () => {
  const results = search.search(index, 'iron', 'elements');
  assert.ok(results.length > 0);
  assert.ok(results.every(item => item.kind === 'Element profile'));
  assert.ok(search.search(index, '', 'people').every(item => item.kind === 'Researcher profile'));
  assert.deepEqual(search.search(index, 'zzzzunfindable', 'papers'), []);
});

test('exact title matches outrank incidental description matches regardless of source order', () => {
  const records = [
    { kind: 'Guide', title: 'Other question', desc: 'Nutritional immunity', url: '/other' },
    { kind: 'Glossary', title: 'Nutritional immunity', desc: 'Definition', url: '/glossary/nutritional-immunity' }
  ];
  assert.equal(search.search(records, 'nutritional immunity')[0].url, '/glossary/nutritional-immunity');
  assert.deepEqual(search.search(records, 'immunity'), search.search([...records].reverse(), 'immunity'));
});

test('suggested starting points exist and do not depend on index ordering', () => {
  const expected = ['/start-here', '/metals', '/evidence', '/methods', '/people', '/evidence-guide'];
  assert.deepEqual(search.search(index, '').map(item => item.url), expected);
  assert.deepEqual(search.search([...index].reverse(), '').map(item => item.url), expected);
});

test('rejects external, protocol-relative, and executable result URLs', () => {
  const record = { kind: 'Guide', title: 'Iron', desc: 'Iron' };
  for (const url of ['https://example.com', '//example.com', 'javascript:alert(1)', '/\\example.com', '/test"onclick=']) {
    assert.equal(search.safe({ ...record, url }), false);
  }
  assert.deepEqual(search.search([{ ...record, url: '//example.com' }], 'iron'), []);
});

test('article results retain curated source status and study design', () => {
  const article = search.search(index, 'fertilizer').find(item => item.url === '/research/heavy-metals-in-fertilizers-contamination-trends');
  assert.ok(article);
  assert.equal(article.status, 'Preprint');
  assert.ok(search.excerpt(article, 'fertilizer').length <= 155);
});
