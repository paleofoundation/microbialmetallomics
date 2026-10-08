#!/usr/bin/env python3
"""Build the static metals atlas after build_access.py; run refresh_site.py last."""
from pathlib import Path
import json,re,html
from datetime import date
from collections import defaultdict
from access_render import render_deep_dive, claim_nodes
ROOT=Path(__file__).resolve().parents[1]
ORIGIN='https://microbialmetallomics.com'
E=lambda x:html.escape(str(x),quote=True)
DATA=json.loads((ROOT/'assets/data/metals.json').read_text())
GROUPS={
 'cofactors':('Microbial cofactors','Enzyme chemistry, acquisition, competition, and toxicity. Requirements differ among organisms.'),
 'contaminants':('Contaminants & metalloids','Chemical form, dose, microbial transformation, and exposure. Some elements also have specialized biological roles.'),
 'materials':('Antimicrobials & materials','Defined compounds, nanoparticles, and surfaces. Laboratory activity does not establish clinical benefit.'),
 'rare-earths':('Rare earths','Selective enzyme use, uptake, adaptation, and limits to what is known across the series.'),
 'environment':('Environmental transformation','Metal recovery, redox cycling, biosorption, and radionuclide mobility.'),
 'context':('Other ions & related elements','Light metals and selenium provide essential context; this group is not a list of heavy metals.')}
ASSIGN={
 'cofactors':'Fe Zn Cu Mn Ni Co Mo W V',
 'contaminants':'As Cd Hg Pb Cr Al Sn Sb Te Tl Ge Be',
 'materials':'Ag Ga Bi Ru Os Ir Rh Re Ti Zr Hf Nb Ta',
 'rare-earths':'La Ce Pr Nd Gd Ln Sc Y',
 'environment':'U Th Tc Np Pu Am In Au Pt Pd Cs Sr Ba',
 'context':'Mg Ca Na K Li Se Rb'}
MAP={s:k for k,v in ASSIGN.items() for s in v.split()}
for r in DATA:
 r['group']=MAP[r['symbol']]
 r['slug']=r.get('slug',r['name'].lower().replace(' ','-'))
 r['url']='/metals/'+r['slug']
 assert r['sources'] and r['summary']['text']
 assert r.get('studies') and r.get('researchQuestions') and r.get('reviewed'),r['symbol']
 date.fromisoformat(r['reviewed'])
 access_claims=[node for section in r.get('access',[]) for node in claim_nodes(section['blocks'])]
 spotlight=r.get('mechanismSpotlight')
 spotlight_claims=[]
 if spotlight:
  assert spotlight['title'] and 2<=len(spotlight['steps'])<=5,r['symbol']
  spotlight_claims=[*spotlight['steps'],spotlight['significance']]
  assert all(step['title'] for step in spotlight['steps']),r['symbol']
  for v in spotlight_claims:
   assert v['text'] and v['refs'] and all(isinstance(n,int) and 0<n<=len(r['sources']) for n in v['refs']),r['symbol']
 for v in [r['summary'],*r['mechanisms'],r['microbiome'],r['exposure'],r['limits'],*r.get('researchQuestions',[]),*r.get('studies',[])]:
  assert v['refs'] and all(isinstance(n,int) and 0<n<=len(r['sources']) for n in v['refs']),r['symbol']
 # Optional access blocks may mark editorial synthesis with an empty refs list.
 for v in access_claims:
  assert isinstance(v['refs'],list) and all(isinstance(n,int) and 0<n<=len(r['sources']) for n in v['refs']),r['symbol']
 for study in r.get('studies',[]):
  assert all(isinstance(study.get(k),str) and study[k].strip() for k in ['title','system','design','finding','interpretation']),r['symbol']
 used={n for v in [r['summary'],*r['mechanisms'],r['microbiome'],r['exposure'],r['limits'],*r['researchQuestions'],*r['studies'],*access_claims,*spotlight_claims] for n in v['refs']}
 assert used==set(range(1,len(r['sources'])+1)),('Uncited source',r['symbol'])
 assert all(s['url'].startswith('https://') for s in r['sources'])
assert len({r['symbol'] for r in DATA})==len(DATA)
assert len({r['slug'] for r in DATA})==len(DATA)
DATA.sort(key=lambda r:(list(GROUPS).index(r['group']),r['atomicNumber'] or 71))
REVIEW_DATE=max(r.get('reviewed','2026-09-30') for r in DATA)
(ROOT/'assets/data/metals.json').write_text(json.dumps(DATA,ensure_ascii=False,indent=2)+'\n')
base=(ROOT/'metals.html').read_text()
prefix=base.split('<main')[0]
suffix=base[base.index('</main>')+7:]
suffix=re.sub(r'<script src="/assets/metals.js[^>]*></script>\s*','',suffix)
def page(title,desc,path,body,typ='WebPage',reviewed=REVIEW_DATE,has_access=False):
 head=prefix
 head=re.sub(r'<title>.*?</title>','<title>'+E(title)+' — Microbial Metallomics</title>',head,flags=re.S)
 head=re.sub(r'<script type="application/ld\+json">.*?</script>\s*','',head,flags=re.S)
 head=re.sub(r'<link rel="canonical"[^>]*>','<link rel="canonical" href="'+ORIGIN+path+'">',head)
 for attr,key,val in [('name','description',desc),('property','og:title',title),('property','og:description',desc),('property','og:url',ORIGIN+path),('name','twitter:title',title),('name','twitter:description',desc),('name','theme-color','#934b2d')]:
  head=re.sub(r'<meta '+attr+'="'+key+'"[^>]*>','<meta '+attr+'="'+key+'" content="'+E(val)+'">',head)
 head=re.sub(r'<link rel="stylesheet" href="/assets/(?:metals|metal-access)\.css[^>]*>\s*','',head)
 ld={'@context':'https://schema.org','@type':typ,'name':title,'description':desc,'url':ORIGIN+path,'inLanguage':'en-US','dateModified':reviewed,'publisher':{'@type':'Organization','name':'Microbial Metallomics'}}
 crumbs=[{'@type':'ListItem','position':1,'name':'Home','item':ORIGIN+'/'},{'@type':'ListItem','position':2,'name':'Metals atlas','item':ORIGIN+'/metals'}]
 if path!='/metals':crumbs.append({'@type':'ListItem','position':3,'name':title,'item':ORIGIN+path})
 access_css='<link rel="stylesheet" href="/assets/metal-access.css">\n' if has_access else ''
 head=head.replace('</head>','<link rel="stylesheet" href="/assets/metals.css">\n'+access_css+'<script type="application/ld+json">'+json.dumps(ld,ensure_ascii=False)+'</script>\n<script type="application/ld+json">'+json.dumps({'@context':'https://schema.org','@type':'BreadcrumbList','itemListElement':crumbs},ensure_ascii=False)+'</script>\n</head>')
 return head+'<main id="main-content">\n'+body+'\n</main>'+suffix.replace('</body>','<script src="/assets/metals.js" defer></script>\n</body>')
def access_search_text(value):
 """Collect readable deep-dive text, including tables and uncited headings."""
 if isinstance(value,str):return value
 if isinstance(value,list):return ' '.join(access_search_text(item) for item in value)
 if isinstance(value,dict):return ' '.join(access_search_text(item) for key,item in value.items() if key not in {'id','type','url','refs'})
 return ''
def tags(r):return '<ul class="atlas-tags">'+''.join('<li>'+E(t)+'</li>' for t in r['tags'])+'</ul>'
def tile(r):
 return '<a class="atlas-element" href="'+r['url']+'"><span class="atlas-number">'+E(r['atomicNumber'] or '57–71')+'</span><strong>'+E(r['symbol'])+'</strong><span>'+E(r['name'])+'</span></a>'
def tiles(records):
 expanded=[]
 for r in records:
  if r.get('members'):
   expanded.extend({**m,'url':r['url']} for m in r['members'])
  else:expanded.append(r)
 return ''.join(tile(r) for r in sorted(expanded,key=lambda r:r['atomicNumber'] or 71))
for r in DATA:
 counts=defaultdict(int);order=[]
 def cite(v):
  out=E(v['text'])+' '
  for old in v['refs']:
   if old not in order:order.append(old)
   n=order.index(old)+1;counts[n]+=1
   out+='<sup class="citation"><a id="cite-'+str(n)+'-'+str(counts[n])+'" href="#ref-'+str(n)+'" role="doc-noteref" aria-label="Reference '+str(n)+'" title="'+E(r['sources'][old-1]['title'])+'">['+str(n)+']</a></sup>'
  return out
 # Explain the chemistry and its consequence before the study inventory.
 spotlight=r.get('mechanismSpotlight')
 mechanism_intro=''
 if spotlight:
  mechanism_intro='<ol class="atlas-mechanism-steps">'+''.join('<li><h3>'+E(step['title'])+'</h3><p>'+cite(step)+'</p></li>' for step in spotlight['steps'])+'</ol><div class="atlas-mechanism-significance"><h3>Why this matters</h3><p>'+cite(spotlight['significance'])+'</p></div><h3 class="atlas-mechanism-evidence">What the experiments show</h3>'
 mechanisms=''.join('<li>'+cite(m)+'</li>' for m in r['mechanisms'])
 mechanism_heading=spotlight['title'] if spotlight else 'What changes in the microbe, and why'
 summary=cite(r['summary'])
 studies=''
 for study in r.get('studies',[]):
  finding=cite({'text':study['finding'],'refs':study['refs']})
  studies+='<div class="atlas-study"><p class="atlas-study-system">'+E(study['system'])+'</p><h3>'+E(study['title'])+'</h3><p><strong>Study design.</strong> '+E(study['design'])+'</p><p><strong>What they found.</strong> '+finding+'</p><p class="atlas-study-reading"><strong>How to read it.</strong> '+E(study['interpretation'])+'</p></div>'
 micro=cite(r['microbiome']);exposure=cite(r['exposure'])
 access_sections=r.get('access',[])
 access=render_deep_dive(access_sections,cite)
 toc=[('mechanisms','Mechanism & significance'),('overview','The broader picture'),('studies','Key experiments'),('evidence','Community & host evidence'),('exposure','Exposure & chemical form')]
 toc.extend((section['id'],section.get('nav',section['title'])) for section in access_sections)
 toc.extend([('limits','What remains uncertain'),('questions','Open questions'),('references','Selected research')])
 assert len({item[0] for item in toc})==len(toc),('Duplicate profile section',r['symbol'])
 assert all(re.fullmatch(r'[a-z][a-z0-9-]+',item[0]) for item in toc),('Invalid profile section',r['symbol'])
 limits=cite(r['limits'])
 questions=''.join('<li>'+cite(q)+'</li>' for q in r.get('researchQuestions',[]))
 refs=[]
 for n,old in enumerate(order,1):
  s=r['sources'][old-1]
  back=''.join('<a href="#cite-'+str(n)+'-'+str(k)+'" role="doc-backlink" aria-label="Return to citation '+str(n)+', occurrence '+str(k)+'">↩</a>' for k in range(1,counts[n]+1))
  refs.append('<li id="ref-'+str(n)+'" tabindex="-1">'+E(s['authors'])+' ('+E(s['year'])+'). '+E(s['title'])+'. <a href="'+E(s['url'])+'" aria-label="View source for reference '+str(n)+'">View source</a><span class="reference-backlinks">'+back+'</span></li>')
 related=[x for x in DATA if x['group']==r['group'] and x!=r][:6]
 body='<section class="hero-band"><div class="wrap"><nav class="breadcrumb" aria-label="Breadcrumb"><a href="/">Home</a><span>/</span><a href="/metals">Metals atlas</a><span>/</span><span>'+E(r['name'])+'</span></nav><p class="eyebrow">'+E(GROUPS[r['group']][0])+'</p><div class="atlas-heading"><span class="atlas-symbol" aria-hidden="true">'+E(r['symbol'])+'</span><div><h1>'+E(r['name'])+' &amp; microbes</h1><p class="article-lead">'+E(r['role'])+'</p></div></div>'+tags(r)+'</div></section>'
 body+='<div class="wrap atlas-layout"><nav class="atlas-toc" aria-label="On this page"><h2>In this profile</h2>'+''.join('<a href="#'+E(a)+'">'+E(b)+'</a>' for a,b in toc)+'<a href="/metals">← All elements</a></nav><article class="article-body atlas-prose"><section id="mechanisms" class="atlas-mechanism"><p class="atlas-kicker">Mechanism &amp; significance</p><h2>'+E(mechanism_heading)+'</h2>'+mechanism_intro+'<ul>'+mechanisms+'</ul></section><section id="overview"><h2>The broader picture</h2><p>'+summary+'</p></section><section id="studies"><h2>Experiments worth knowing</h2>'+studies+'</section><section id="evidence"><h2>Community &amp; host evidence</h2><p>'+micro+'</p></section><section id="exposure"><h2>Exposure &amp; chemical form</h2><p>'+exposure+'</p></section>'+access+'<section id="limits" class="atlas-limit"><h2>What the evidence does not establish</h2><p>'+limits+'</p></section><section id="questions"><h2>Open research questions</h2><p class="atlas-section-note">Questions suggested by the evidence and its limits.</p><ul>'+questions+'</ul></section><section class="references" id="references" aria-labelledby="references-heading"><h2 id="references-heading">Selected research</h2><p>Sources supporting the numbered statements and study summaries above. Publication status is identified where a source reports trial results outside a peer-reviewed paper. This is a curated entry point, not a systematic review.</p><ol class="reference-list">'+''.join(refs)+'</ol></section><section class="atlas-related"><h2>Continue exploring</h2><div class="atlas-mini-grid">'+''.join(tile(x) for x in related)+'</div><p><a href="/start-here">Read the organizing thesis</a> · <a href="/metal-access">Follow the metal</a> · <a href="/evidence-guide">How to read different kinds of evidence</a> · <a href="/contribute">Suggest a source or correction</a></p></section></article></div>'
 (ROOT/'metals'/ (r['slug']+'.html')).write_text(page(r['name']+' & microbes',r['role']+'. Sourced microbial mechanisms, community evidence, chemical forms, and research limits.',r['url'],body,reviewed=r.get('reviewed',REVIEW_DATE),has_access=bool(access_sections)))
count=len(DATA);element_count=sum(len(r.get('members',[])) or 1 for r in DATA)
entry_specs=[('gallium','Iron mimicry','Gallium enters iron-handling pathways but cannot do iron’s redox work.'),('nickel','A cofactor for survival','Nickel-loaded urease helps H. pylori buffer its acidic surroundings.'),('mercury','Microbes change the metal','Methylation and demethylation change mercury’s chemical form and fate.')]
by_slug={r['slug']:r for r in DATA}
mechanism_entries='<section class="wrap atlas-mechanism-entries" aria-labelledby="atlas-entry-heading"><p class="atlas-kicker">Start with a mechanism</p><h2 id="atlas-entry-heading">The chemistry is the story.</h2><div class="atlas-entry-grid">'+''.join('<a href="'+by_slug[slug]['url']+'#mechanisms"><span class="atlas-entry-symbol" aria-hidden="true">'+E(by_slug[slug]['symbol'])+'</span><span class="atlas-entry-copy"><span class="atlas-entry-element">'+E(by_slug[slug]['name'])+'</span><strong>'+E(title)+'</strong><span>'+E(deck)+'</span><span class="atlas-entry-link">Follow the mechanism <span aria-hidden="true">→</span></span></span></a>' for slug,title,deck in entry_specs)+'</div></section>'

intro='<section class="hero-band"><div class="wrap"><p class="eyebrow">Elements &amp; microbial mechanisms</p><h1>The metals atlas</h1><p class="article-lead">Explore '+str(count)+' profiles covering '+str(element_count)+' elements. Find how each metal affects microbes, the mechanisms involved, and the supporting evidence.</p><p class="atlas-hub-links"><a href="#element-profiles">Find an element <span aria-hidden="true">↓</span></a><a href="#reading-the-atlas">How to read the atlas</a></p></div></section>'
reading_intro='<section class="wrap atlas-intro" id="reading-the-atlas"><h2>Follow the form, the pool, and the competition.</h2><p>Interpreting a metal measurement starts with what chemical form is present, where it is, and which host cells or microbes can access it. The organizing thesis connects these questions to microbial functions and inflammatory feedback; the explorer follows specific cases and separates measured results from proposed links.</p><p><a href="/start-here">Read the organizing thesis</a> · <a href="/metal-access">Follow the metal through different compartments</a></p><h2>One element can play more than one role.</h2><p>Microbes can acquire, exclude, transform, store, or precipitate metals. A cofactor can become toxic in excess; a contaminant can support a specialized microbial process. These groups are reading pathways, not mutually exclusive chemical or safety classifications.</p><p>“Heavy metal” has no single boundary used consistently across the literature. We include relevant metalloids, light metals, and selenium and identify their context. The atlas covers selected documented interactions; it does not claim to contain every online paper or establish a disease pathway for every element.</p><p><a href="#coverage">Coverage &amp; evidence gaps</a> · <a href="/evidence-guide">Read the evidence guide</a> · <a href="/assets/data/metals.json" download>Download the sourced atlas (JSON)</a></p></section>'
controls='<div id="element-profiles" class="wrap atlas-browser-heading"><h2>Find an element or mechanism</h2><p>Search by element, organism, enzyme, or biological process.</p></div><form class="atlas-filters wrap" role="search" aria-label="Filter element profiles" hidden><div><label for="metal-query">Find an element, organism, enzyme, or process</label><input id="metal-query" type="search" placeholder="Try gallium, iron mimicry, urease, or biofilm" autocomplete="off"></div><div><label for="metal-group">Research area</label><select id="metal-group"><option value="all">All research areas</option>'+''.join('<option value="'+k+'">'+E(v[0])+'</option>' for k,v in GROUPS.items())+'</select></div><button type="reset">Clear filters</button><p id="metal-count" role="status" aria-live="polite">'+str(count)+' profiles</p></form><p class="wrap atlas-empty" hidden>No matching profiles. Try an element symbol or a broader process, or clear the filters.</p>'
groups=''
for k,(title,desc) in GROUPS.items():
 rows=[r for r in DATA if r['group']==k];cards=''
 for r in rows:
  search=' '.join([r['symbol'],r['name'],r['role'],*r['tags'],r['summary']['text'],r['microbiome']['text'],r['exposure']['text'],r['limits']['text'],access_search_text(r.get('access',[])),access_search_text(r.get('mechanismSpotlight',{})),*[m['text'] for m in r['mechanisms']],*[study[k] for study in r.get('studies',[]) for k in ['title','system','design','finding','interpretation']],*[q['text'] for q in r.get('researchQuestions',[])],*[m['name']+' '+m['symbol'] for m in r.get('members',[])]])
  cards+='<article class="atlas-card" id="'+r['symbol'].lower()+'" data-metal-group="'+k+'" data-metal-symbols="'+E(' '.join([r['symbol'],*[m['symbol'] for m in r.get('members',[])]]).lower())+'" data-metal-search="'+E(search.lower())+'"><div class="atlas-card-top"><span class="atlas-card-symbol" aria-hidden="true">'+E(r['symbol'])+'</span><div><h3><a href="'+r['url']+'">'+E(r['name'])+'</a></h3><span class="atlas-atomic">'+('Atomic number '+str(r['atomicNumber']) if r['atomicNumber'] else 'Related lanthanides')+'</span></div></div><p class="atlas-role">'+E(r['role'])+'</p><details class="card-context"><summary>Why this metal matters</summary><p>'+E(r['summary']['text'])+'</p></details><a class="atlas-read" href="'+r['url']+'">Mechanisms, evidence &amp; sources <span aria-hidden="true">→</span><span class="sr-only"> for '+E(r['name'])+'</span></a></article>'
 groups+='<section class="wrap atlas-group" id="'+('toxic' if k=='contaminants' else k)+'" data-atlas-group="'+k+'"><h2>'+E(title)+'</h2><p class="atlas-group-note">'+E(desc)+'</p><div class="atlas-card-grid">'+cards+'</div></section>'
coverage='<section class="wrap atlas-coverage" id="coverage"><h2>Coverage &amp; evidence gaps</h2><p>The atlas spans microbial biochemistry, environmental communities, host-associated microbiomes, and experimental materials. The depth of each profile follows the available sources: a biochemical assay, a soil experiment, an animal model, and a human trial answer different questions.</p><p>Rare lanthanides are grouped when evidence is limited or shared across a series. Elements without a separately sourced interaction here are not presumed biologically irrelevant. Newly published studies, unindexed work, contradictory findings, and additional chemical species may change these summaries.</p><p>To propose an addition, send the element, chemical form, organism or community, study design, and a DOI or other primary-source link through <a href="/contribute">Contribute or correct</a>. A paper showing metal binding alone is not proof of a nutritional requirement; a taxonomic association alone is not proof of disease causation.</p></section>'
(ROOT/'metals.html').write_text(page('Metals atlas: elements & microbial interactions',str(count)+' sourced profiles spanning microbial cofactors, contaminants, rare earths, antimicrobials, and environmental metal transformations.','/metals',intro+controls+groups+mechanism_entries+reading_intro+coverage,'CollectionPage'))
print('Built',count,'profiles covering',element_count,'elements and the searchable atlas.')
