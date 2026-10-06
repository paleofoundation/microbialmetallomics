#!/usr/bin/env python3
"""Build the pillar essay and reconcile its manually maintained discovery copy."""
from pathlib import Path
from html import unescape
from urllib.parse import quote
import json, re
from access_render import Citations, esc, render_blocks, claim_nodes
from author_identity import site_author, author_schema, author_byline
ROOT=Path(__file__).resolve().parents[1]
PATH='/blog/metal-microbiome-disease-axis'
URL='https://microbialmetallomics.com'+PATH
FILE=ROOT/(PATH.lstrip('/')+'.html')
data=json.loads((ROOT/'assets/data/pillar-essay.json').read_text())
author=site_author(data['authorSlug'])
original=FILE.read_text()
old_ld=json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>',original,re.S).group(1))
old_article=next(x for x in old_ld.get('@graph',[old_ld]) if x.get('@type')=='BlogPosting')
old_title=old_article['headline'];old_desc=old_article['description']
seen=set()
for s in data['sections']:
 for id in [s['id'],*s.get('aliases',[])]:
  assert re.fullmatch(r'[a-z][a-z0-9-]+',id) and id not in seen,id
  seen.add(id)
 for node in claim_nodes(s['blocks']):assert all(isinstance(n,int) and 0<n<=len(data['sources']) for n in node['refs'])
assert {n for s in data['sections'] for node in claim_nodes(s['blocks']) for n in node['refs']}==set(range(1,len(data['sources'])+1))
# Keep the site's shared header, footer and article controls.
prefix=original.split('<main')[0]
suffix=original[original.index('</main>')+7:]
share_start=re.search(r'<div\b(?=[^>]*class="share-row")[^>]*>',original).start()
share_end=re.search(r'<p\b(?=[^>]*data-reading-status)[^>]*>.*?</p>',original,re.S).end()
controls=original[share_start:share_end].replace(quote(old_title,safe=''),quote(data['title'],safe=''))
prefix=re.sub(r'<title>.*?</title>','<title>'+esc(data['title'])+' — Microbial Metallomics</title>',prefix,flags=re.S)
for attr,key,value in [('name','author',author['name']),('name','description',data['description']),('property','og:title',data['title']),('property','og:description',data['description']),('name','twitter:title',data['title']),('name','twitter:description',data['description'])]:
 prefix=re.sub(r'<meta\b(?=[^>]*\b'+attr+r'="'+re.escape(key)+r'")[^>]*>','<meta '+attr+'="'+key+'" content="'+esc(value)+'">',prefix)
prefix=re.sub(r'<script type="application/ld\+json">.*?</script>\s*','',prefix,flags=re.S)
# Old attribute ordering left duplicate discovery tags; emit one canonical copy.
prefix=re.sub(r'<meta\b[^>]*reading-catalogue[^>]*>\s*','',prefix)
prefix=re.sub(r'<link\b[^>]*href="/feeds/all.xml"[^>]*>\s*','',prefix)
prefix=re.sub(r'<link\b[^>]*href="/assets/(?:pillar|metal-access)\.css[^>]*>\s*','',prefix)
article={'@type':'BlogPosting','headline':data['title'],'description':data['description'],'datePublished':data['published'],'dateModified':data['updated'],'author':author_schema(author),'publisher':{'@type':'Organization','name':'Microbial Metallomics','logo':{'@type':'ImageObject','url':'https://microbialmetallomics.com/assets/favicon.svg'}},'mainEntityOfPage':URL,'inLanguage':'en-US','keywords':data['keywords']}
faq_ld={'@type':'FAQPage','mainEntity':[{'@type':'Question','name':f['question'],'acceptedAnswer':{'@type':'Answer','text':f['answer']}} for f in data['faqs']]}
crumbs={'@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':1,'name':'Home','item':'https://microbialmetallomics.com/'},{'@type':'ListItem','position':2,'name':'Essays','item':'https://microbialmetallomics.com/blog'},{'@type':'ListItem','position':3,'name':data['title'],'item':URL}]}
prefix=prefix.replace('</head>','<link rel="stylesheet" href="/assets/metal-access.css">\n<link rel="stylesheet" href="/assets/pillar.css">\n<script type="application/ld+json">'+json.dumps({'@context':'https://schema.org','@graph':[article,faq_ld,crumbs]},ensure_ascii=False)+'</script>\n</head>')
prefix=re.sub(r'<body[^>]*>','<body class="journal-article pillar-essay">',prefix,count=1)
hero='<section class="hero-band"><div class="wrap"><nav class="breadcrumb" aria-label="Breadcrumb"><a href="/">Home</a><span>/</span><a href="/blog">Essays</a><span>/</span><span>The metal–microbiome–disease axis</span></nav><p class="eyebrow">Pillar essay</p><h1>'+esc(data['title'])+'</h1><p class="article-lead">'+esc(data['deck'])+'</p><div class="article-meta"><span class="am-item">By <b>'+author_byline(author)+'</b></span></div>'+controls+'</div></section>'
book=Citations(data['sources'])
chapters=''
for s in data['sections']:
 aliases=''.join('<span id="'+esc(id)+'" class="pillar-legacy-anchor" aria-hidden="true"></span>' for id in s.get('aliases',[]))
 chapters+='<section class="pillar-chapter" id="'+esc(s['id'])+'">'+aliases+'<h2>'+esc(s['title'])+'</h2>'+render_blocks(s['blocks'],book.cite)+'</section>\n'
summary='<section class="journal-summary" id="article-summary"><h2>The argument</h2><p class="article-lead">'+esc(data['summary'])+'</p></section><div class="takeaways"><h2>Four ideas to carry through the essay</h2><ul>'+''.join('<li>'+esc(t)+'</li>' for t in data['takeaways'])+'</ul></div>'
faq='<section class="faq-block" id="faq"><h2>Questions the framework raises</h2><div class="faq">'+''.join('<details><summary>'+esc(f['question'])+'</summary><p>'+esc(f['answer'])+'</p></details>' for f in data['faqs'])+'</div></section>'
title_end='' if data['title'].endswith(('.', '?', '!')) else '.'
citation=author['name']+'. ('+data['published']+'). '+data['title']+title_end+' Microbial Metallomics. '+URL
cite_panel='<details class="citation-panel" data-citation id="cite-this-page"><summary>Cite this page</summary><p data-citation-text>'+esc(citation)+'</p><p>This citation identifies this website essay; the references identify the primary research.</p><div class="citation-actions"><button class="text-action" data-citation-copy type="button">Copy citation</button><button class="text-action" data-citation-bibtex type="button">Download BibTeX</button><button class="text-action" data-citation-ris type="button">Download RIS</button></div><p class="tool-status" data-citation-status role="status"></p></details><script id="page-citation-data" type="application/json">'+json.dumps({'title':data['title'],'date':data['published'],'authors':[author['name']],'url':URL},ensure_ascii=False)+'</script><p class="print-source">Published at '+URL+'</p>'
refs=book.references().replace('The framework and proposed experiments are editorial synthesis, not a clinical guideline or a systematic review.','This essay synthesizes primary research and distinguishes demonstrated findings from proposed connections.')
related='<div class="related-module"><h2>Work through the evidence</h2><div class="related-grid"><a href="/start-here"><span class="rk">Start here</span><span class="rt">Enough metal. Available to whom?</span></a><a href="/metals/zinc"><span class="rk">Worked example</span><span class="rt">Zinc access, formulations, and MS</span></a><a href="/metals/iron"><span class="rk">Worked example</span><span class="rt">Iron stores, restriction, and microbial exposure</span></a></div></div>'
nav='<nav aria-label="On this page"><a href="#article-summary">The argument</a>'+''.join('<a href="#'+esc(s['id'])+'">'+esc(s.get('nav',s['title']))+'</a>' for s in data['sections'])+'<a href="#faq">Questions</a><a href="#references">References</a></nav>'
history='<details class="pillar-history"><summary>Editorial history</summary><p><strong>Current revision.</strong> Rebuilt around metal access, microbial functions, and three distinct causal relationships. Reconciled the summary, examples, and FAQs with the limits of the cited evidence.</p><p><strong>Earlier correction · September 30, 2026.</strong> Addressed universal exposure and disease claims, the Parkinson’s comparison, and limits on causal inference.</p></details>'
aside='<aside class="pillar-sidebar"><div class="toc-label">In this essay</div>'+nav+'<div class="pillar-reading"><a href="/metal-access">Follow the metal →</a><a href="/evidence-guide">How to read the evidence →</a></div>'+history+'</aside>'
body='<main id="main-content">'+hero+'<div class="wrap pillar-layout"><article class="article-body pillar-prose">'+summary+chapters+faq+refs+cite_panel+related+'</article>'+aside+'</div></main>'
FILE.write_text(prefix+body+suffix)
# Keep existing manually authored card and related-link text consistent.
legacy_title='The Metal-Microbiome-Disease Axis: How Heavy Metals May Drive Disease Through the Gut'
legacy_desc='The metal-microbiome-disease axis: heavy-metal exposure reshapes the gut microbiome, and that dysbiosis may drive metabolic, neurological and gut disease.'
for path in ROOT.rglob('*.html'):
 if path==FILE or 'node_modules' in path.parts or any(x.startswith('.') for x in path.relative_to(ROOT).parts):continue
 text=path.read_text();new=text
 for previous in {old_title,legacy_title}:
  if previous!=data['title']:new=new.replace(previous,data['title'])
 for previous in {old_desc,legacy_desc}:
  if previous!=data['description']:new=new.replace(previous,data['description'])
 if path.name=='index.html':new=re.sub(r'<p class="journal-type">Pillar essay(?: <span>.*?</span>)?</p>','<p class="journal-type">Pillar essay</p>',new)
 if new!=text:path.write_text(new)
# Legacy blog feed remains available alongside generated catalog feeds.
rss=ROOT/'blog/rss.xml';text=rss.read_text()
def update_item(match):
 item=match.group(0)
 if '<link>'+URL+'</link>' not in item:return item
 item=re.sub(r'<title>.*?</title>','<title>'+esc(data['title'])+'</title>',item,flags=re.S)
 return re.sub(r'<description>.*?</description>','<description>'+esc(data['description'])+'</description>',item,flags=re.S)
text=re.sub(r'<item>.*?</item>',update_item,text,flags=re.S)
text=re.sub(r'(<channel>.*?<description>).*?(</description>)',lambda m:m.group(1)+'Essays on metal chemistry, microbial functions, host regulation, and disease.'+m.group(2),text,count=1,flags=re.S)
rss.write_text(text)
print('Built pillar essay:',len(data['sections']),'sections,',len(data['sources']),'primary sources, and synchronized discovery copy.')
