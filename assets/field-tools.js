(() => {
  'use strict';
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const el = (tag, text, className) => {
    const node = document.createElement(tag);
    if (text != null) node.textContent = text;
    if (className) node.className = className;
    return node;
  };
  const normalize = value => String(value).toLowerCase().replace(/[‘’ʼ]/g, "'").replace(/[‐‑–—]/g, '-');
  window.addEventListener('storage', event => {if (event.key === 'mm-reading-v1' || event.key === null) document.dispatchEvent(new Event('readinglistchange'));});
  let catalogue;
  function articles() {
    return catalogue ||= fetch(document.querySelector('meta[name="reading-catalogue"]')?.content || '/assets/data/articles.json').then(response => {
      if (!response.ok) throw new Error('Catalogue unavailable');
      return response.json();
    });
  }
  function saved() {
    try {
      const value = JSON.parse(localStorage.getItem('mm-reading-v1') || '[]');
      return Array.isArray(value) ? value.filter(x => typeof x === 'string' && /^\/(blog|research|library)\/[a-z0-9-]+$/.test(x)) : [];
    } catch { return []; }
  }
  function saveList(value, status) {
    try {
      localStorage.setItem('mm-reading-v1', JSON.stringify(value));
      document.dispatchEvent(new Event('readinglistchange'));
      return true;
    } catch {
      if (status) status.textContent = 'This browser cannot save a reading list. You can still bookmark or export the article links.';
      return false;
    }
  }
  function download(name, text, mime) {
    const url = URL.createObjectURL(new Blob([text], {type: mime}));
    const link = el('a'); link.href = url; link.download = name; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function card(record) {
    const article = el('article', null, 'catalogue-entry');
    const meta = el('div', record.kind + (record.status ? ' · ' + record.status : ''), 'catalogue-meta');
    const date = el('time', record.date); date.dateTime = record.date; meta.append(date);
    const heading = el('h3');const link = el('a', record.title);link.href = record.url;heading.append(link);
    article.append(meta, heading, el('p', record.description), el('p', record.authors.join(' · '), 'catalogue-authors'));
    if (record.studyDesign) article.append(el('p', record.studyDesign + ' · ' + record.setting, 'catalogue-design'));
    return article;
  }
  function options(select, values) {
    values.filter(Boolean).sort().forEach(value => { const option = el('option', value); option.value = value; select.append(option); });
  }
  const explorer = $('[data-catalogue]');
  if (explorer) {
    articles().then(all => {
      const locked = explorer.dataset.kindLock;
      const records = locked ? all.filter(x => x.kind === locked) : all;
      const form = $('[data-catalogue-form]', explorer);
      const out = $('[data-catalogue-results]', explorer);
      const status = $('[data-catalogue-count]', explorer);
      const q = $('[name=q]', form), topic = $('[name=topic]', form), kind = $('[name=kind]', form), design = $('[name=design]', form), sort = $('[name=sort]', form);
      options(topic, [...new Set(records.flatMap(x => x.topics))]);
      if (kind) options(kind, [...new Set(records.map(x => x.kind))]);
      if (design) options(design, [...new Set(records.map(x => x.studyDesign))]);
      const params = new URLSearchParams(location.search);
      [q, topic, kind, design, sort].filter(Boolean).forEach(control => {
        const value = params.get(control.name);
        if (value && (control.tagName !== 'SELECT' || [...control.options].some(x => x.value === value))) control.value = value;
      });
      function render(updateURL = true) {
        const words = normalize(q.value.trim()).split(/\s+/).filter(Boolean);
        let results = records.filter(r => words.every(word => normalize([r.title,r.description,r.authors.join(' '),r.topics.join(' '),r.studyDesign].join(' ')).includes(word)) && (!topic.value || r.topics.includes(topic.value)) && (!kind?.value || r.kind === kind.value) && (!design?.value || r.studyDesign === design.value));
        results = [...results].sort(sort.value === 'title' ? (a,b) => a.title.localeCompare(b.title) : sort.value === 'oldest' ? (a,b) => a.date.localeCompare(b.date) : (a,b) => b.date.localeCompare(a.date));
        out.replaceChildren(...results.map(card));
        status.textContent = results.length + ' of ' + records.length + ' articles';
        if (!results.length) out.append(el('p', 'No articles match these filters. Try a broader term or reset the filters.', 'tool-empty'));
        if (updateURL) {
          const next = new URLSearchParams();
          [q, topic, kind, design, sort].filter(Boolean).forEach(control => {if (control.value && !(control.name === 'sort' && control.value === 'newest')) next.set(control.name,control.value);});
          history.replaceState(null, '', location.pathname + (next.size ? '?' + next : '') + location.hash);
        }
      }
      form.hidden = false;
      $('[data-catalogue-fallback]', explorer)?.setAttribute('hidden', '');
      form.addEventListener('input', () => render());
      form.addEventListener('change', () => render());
      form.addEventListener('submit', event => {event.preventDefault();render();});
      $('[data-reset]', form).addEventListener('click', () => {form.reset();render();q.focus();});
      $('[data-copy-filters]', form)?.addEventListener('click', async () => {
        try {await navigator.clipboard.writeText('https://microbialmetallomics.com' + location.pathname + location.search);status.textContent += ' · Filter link copied.';}
        catch {status.textContent += ' · Copy the page address from your browser to share these filters.';}
      });
      render(false);
    }).catch(() => { $('[data-catalogue-count]', explorer).textContent = 'The interactive catalogue could not load. The reading links below remain available.'; });
  }
  const topicRoot = $('[data-topic-explorer]');
  if (topicRoot) {
    articles().then(records => {
      const links = $$('[data-topic]', topicRoot), results = $('[data-topic-results]', topicRoot), status = $('[data-topic-count]', topicRoot);
      function select(topic, update) {
        links.forEach(link => link.setAttribute('aria-pressed', String(link.dataset.topic === topic)));
        const matching = records.filter(r => r.topics.includes(topic));
        $('[data-topic-title]',topicRoot).textContent = topic;
        status.textContent = matching.length + ' articles in this collection';
        results.replaceChildren(...matching.map(card));
        if (!matching.length) results.append(el('p','No articles are catalogued under this topic yet. Browse the research library.'));
        if (update) history.replaceState(null,'','/topics?topic='+encodeURIComponent(topic));
      }
      links.forEach(link => {
        link.addEventListener('click', event => {event.preventDefault();select(link.dataset.topic,true);});
        link.addEventListener('keydown', event => {if (event.key === ' ') {event.preventDefault();link.click();}});
      });
      const requested = new URLSearchParams(location.search).get('topic');
      select(links.some(x => x.dataset.topic === requested) ? requested : 'Iron', false);
    }).catch(() => {$('[data-topic-count]',topicRoot).textContent = 'Use the topic links to open the evidence library.';});
  }
  $$('[data-save-article]').forEach(button => {
    const path = button.dataset.saveArticle;
    const status = $('[data-reading-status]');
    const update = () => {const active = saved().includes(path);button.setAttribute('aria-pressed',String(active));$('.tool-label',button).textContent = active ? 'Saved' : 'Save to reading list';};
    button.addEventListener('click', () => {const list=saved();const active=list.includes(path);if(saveList(active?list.filter(x=>x!==path):[...list,path],status)){status.textContent=active?'Removed from your reading list.':'Saved on this browser. View your reading list from the menu.';}});
    document.addEventListener('readinglistchange',update);update();
  });
  const reading = $('[data-reading-list]');
  if (reading) {
    articles().then(records => {
      const status = $('[data-reading-status]',reading), out=$('[data-reading-items]',reading);
      function render() {
        const ids=saved();const list=ids.map(id=>records.find(x=>x.url===id)).filter(Boolean);
        out.replaceChildren();status.textContent=list.length+' saved articles';
        if (!list.length) out.append(el('p','Your reading list is empty. Use “Save to reading list” on an article to add it here.','tool-empty'));
        list.forEach(record => {const entry=card(record);const remove=el('button','Remove','text-action');remove.type='button';remove.setAttribute('aria-label','Remove '+record.title);remove.addEventListener('click',()=>saveList(saved().filter(x=>x!==record.url),status));entry.append(remove);out.append(entry);});
        $('[data-export-reading]',reading).disabled=!list.length;
        $('[data-clear-reading]',reading).disabled=!list.length;
      }
      $('[data-clear-reading]',reading).addEventListener('click',()=>saveList([],status));
      $('[data-export-reading]',reading).addEventListener('click',()=>{const ids=saved();download('microbial-metallomics-reading-list.txt',records.filter(r=>ids.includes(r.url)).map(r=>r.title+'\nhttps://microbialmetallomics.com'+r.url).join('\n\n'),'text/plain;charset=utf-8');});
      document.addEventListener('readinglistchange',render);render();
    }).catch(()=>{$('[data-reading-status]',reading).textContent='Your saved links are unchanged, but article details could not load. Please reload.';});
  }
  $$('[data-print-article]').forEach(button=>button.addEventListener('click',()=>window.print()));
  const citation=$('[data-citation]');
  if (citation) {
    $$('a[href="#cite-this-page"]').forEach(link=>link.addEventListener('click',()=>{citation.open=true;}));
    const data=JSON.parse($('#page-citation-data').textContent);
    const plain=$('[data-citation-text]',citation).textContent;
    const status=$('[data-citation-status]',citation);
    $('[data-citation-copy]',citation).addEventListener('click',async()=>{
      try{await navigator.clipboard.writeText(plain);status.textContent='Citation copied.';}
      catch {const range=document.createRange();range.selectNodeContents($('[data-citation-text]',citation));const selection=getSelection();selection.removeAllRanges();selection.addRange(range);status.textContent='Citation selected. Use your browser’s Copy command.';}
    });
    const clean=value=>String(value).replace(/[{}\\]/g,'').replace(/[\r\n]/g,' ');
    $('[data-citation-bibtex]',citation).addEventListener('click',()=>download('microbial-metallomics.bib','@misc{microbialmetallomics'+data.date.slice(0,4)+'-'+data.url.split('/').pop().replace(/[^a-z0-9-]/gi,'')+',\n  author = {'+data.authors.map(a=>a==='Microbial Metallomics'?'{'+clean(a)+'}':clean(a)).join(' and ')+'},\n  title = {'+clean(data.title)+'},\n  year = {'+data.date.slice(0,4)+'},\n  url = {'+data.url+'},\n  note = {Microbial Metallomics website article}\n}\n','application/x-bibtex'));
    $('[data-citation-ris]',citation).addEventListener('click',()=>download('microbial-metallomics.ris','TY  - ELEC\n'+data.authors.map(a=>'AU  - '+clean(a)).join('\n')+'\nTI  - '+clean(data.title)+'\nPY  - '+data.date.slice(0,4)+'\nDA  - '+data.date+'\nUR  - '+data.url+'\nPB  - Microbial Metallomics\nER  - \n','application/x-research-info-systems'));
  }
  const latest=$('[data-latest-writing]');
  if(latest) articles().then(records=>latest.replaceChildren(...records.slice(0,12).map(card))).catch(()=>latest.append(el('p','Browse the research library for recent writing.')));
})();
