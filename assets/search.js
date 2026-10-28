/* Shared, local search. Ranking describes relevance, never evidence strength. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.MMSearch = factory();
})(typeof window === 'undefined' ? this : window, function () {
  'use strict';
  var ignored = new Set('a an the and of in to for with how what does do is are can'.split(' '));
  var starts = ['/start-here', '/metals', '/evidence', '/methods', '/people', '/evidence-guide'];
  var groups = {
    elements: ['Element profile'], papers: ['Paper review', 'Original research', 'Research synthesis', 'Critical Commentary', 'Essay'],
    people: ['Researcher profile'], terms: ['Glossary'], guides: ['Guide', 'Section']
  };
  function normalize(value) {
    return String(value || '').normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
      .toLowerCase().replace(/['’‘ʼ]/g, '').replace(/[^a-z0-9]+/g, ' ').trim();
  }
  function safe(item) {
    return item && typeof item.title === 'string' && typeof item.kind === 'string' &&
      typeof item.desc === 'string' && typeof item.url === 'string' &&
      /^\/(?!\/)[a-z0-9/?#%&=._-]*$/i.test(item.url);
  }
  function words(query, symbols) {
    symbols = symbols || {};
    var tokens = normalize(query).split(/\s+/).filter(Boolean);
    // "As" is an element symbol only when it is the entire query; in prose it is a word.
    return [...new Set(tokens.filter(function (token) {
      return (tokens.length === 1 && symbols[token]) || (!ignored.has(token) && token !== 'as');
    }).flatMap(function (token) { return (symbols[token] || token).split(' '); }))];
  }
  function match(tokens, term) {
    return tokens.some(function (token) { return token === term || (term.length > 2 && token.indexOf(term) === 0); });
  }
  function search(items, query, group) {
    var symbols = {};
    items.filter(safe).forEach(function (item) {
      (item.elements || []).forEach(function (element) { symbols[normalize(element.symbol)] = normalize(element.name); });
    });
    var terms = words(query, symbols), phrase = terms.join(' ');
    var pool = items.filter(safe).filter(function (item) {
      return !groups[group] || groups[group].includes(item.kind);
    });
    if (!normalize(query)) {
      if (!groups[group]) return starts.map(function (url) { return pool.find(function (item) { return item.url === url; }); }).filter(Boolean);
      return pool.slice().sort(function (a, b) { return a.title.localeCompare(b.title, 'en'); });
    }
    if (!terms.length) return [];
    return pool.map(function (item) {
      var title = normalize(item.title), titleWords = title.split(' ');
      var bodyWords = normalize(item.desc + ' ' + item.kind + ' ' + (item.studyDesign || '')).split(' ');
      var score = 0;
      for (var term of terms) {
        if (match(titleWords, term)) score += titleWords.includes(term) ? 16 : 10;
        else if (match(bodyWords, term)) score += 2;
        else return null;
      }
      if (title === phrase) score += 80;
      else if (title.indexOf(phrase) === 0) score += 30;
      else if (title.includes(phrase)) score += 20;
      if (terms.length === 1 && item.url === '/metals/' + terms[0]) score += 60;
      else if (terms.length === 1 && (item.elements || []).some(function (element) { return normalize(element.name) === terms[0]; })) score += 60;
      if (item.url.includes('#')) score -= 1;
      return { item: item, score: score };
    }).filter(Boolean).sort(function (a, b) {
      return b.score - a.score || a.item.title.localeCompare(b.item.title, 'en') || a.item.url.localeCompare(b.item.url, 'en');
    }).map(function (result) { return result.item; });
  }
  function excerpt(item, query) {
    var text = String(item.summary || item.desc || '').replace(/\s+/g, ' ').trim();
    if (text.length <= 155) return text;
    // For long atlas descriptions, reveal the passage that matched the question.
    var term = words(query).find(function (word) { return !normalize(item.title).includes(word); });
    var at = term ? text.toLowerCase().indexOf(term) : -1;
    var start = at > 75 ? text.lastIndexOf(' ', at - 45) + 1 : 0;
    var end = text.lastIndexOf(' ', start + 150);
    if (end <= start) end = start + 150;
    return (start ? '…' : '') + text.slice(start, end).trim() + '…';
  }
  return { normalize: normalize, safe: safe, search: search, excerpt: excerpt };
});
