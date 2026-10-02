#!/usr/bin/env python3
"""Build the static metals atlas from assets/data/metals.json, then run refresh_site.py."""
from pathlib import Path
import json,re,html
from datetime import date
from collections import defaultdict
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
 for v in [r['summary'],*r['mechanisms'],r['microbiome'],r['exposure'],r['limits'],*r.get('researchQuestions',[]),*r.get('studies',[])]:
  assert v['refs'] and all(isinstance(n,int) and 0<n<=len(r['sources']) for n in v['refs']),r['symbol']
 for study in r.get('studies',[]):
  assert all(isinstance(study.get(k),str) and study[k].strip() for k in ['title','system','design','finding','interpretation']),r['symbol']
 used={n for v in [r['summary'],*r['mechanisms'],r['microbiome'],r['exposure'],r['limits'],*r['researchQuestions'],*r['studies']] for n in v['refs']}
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
def page(title,desc,path,body,typ='WebPage',reviewed=REVIEW_DATE):
 head=prefix
 head=re.sub(r'<title>.*?</title>','<title>'+E(title)+' — Microbial Metallomics</title>',head,flags=re.S)
 head=re.sub(r'<script type="application/ld\+json">.*?</script>\s*','',head,flags=re.S)
 head=re.sub(r'<link rel="canonical"[^>]*>','<link rel="canonical" href="'+ORIGIN+path+'">',head)
 for attr,key,val in [('name','description',desc),('property','og:title',title),('property','og:description',desc),('property','og:url',ORIGIN+path),('name','twitter:title',title),('name','twitter:description',desc),('name','theme-color','#934b2d')]:
  head=re.sub(r'<meta '+attr+'="'+key+'"[^>]*>','<meta '+attr+'="'+key+'" content="'+E(val)+'">',head)
 head=re.sub(r'<link rel="stylesheet" href="/assets/metals.css[^>]*>\s*','',head)
 ld={'@context':'https://schema.org','@type':typ,'name':title,'description':desc,'url':ORIGIN+path,'inLanguage':'en-US','dateModified':reviewed,'publisher':{'@type':'Organization','name':'Microbial Metallomics'}}
 crumbs=[{'@type':'ListItem','position':1,'name':'Home','item':ORIGIN+'/'},{'@type':'ListItem','position':2,'name':'Metals atlas','item':ORIGIN+'/metals'}]
 if path!='/metals':crumbs.append({'@type':'ListItem','position':3,'name':title,'item':ORIGIN+path})
 head=head.replace('</head>','<link rel="stylesheet" href="/assets/metals.css">\n<script type="application/ld+json">'+json.dumps(ld,ensure_ascii=False)+'</script>\n<script type="application/ld+json">'+json.dumps({'@context':'https://schema.org','@type':'BreadcrumbList','itemListElement':crumbs},ensure_ascii=False)+'</script>\n</head>')
 return head+'<main id="main-content">\n'+body+'\n</main>'+suffix.replace('</body>','<script src="/assets/metals.js" defer></script>\n</body>')
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
 summary=cite(r['summary']);mechanisms=''.join('<li>'+cite(m)+'</li>' for m in r['mechanisms'])
 studies=''
 for study in r.get('studies',[]):
  finding=cite({'text':study['finding'],'refs':study['refs']})
  studies+='<div class="atlas-study"><p class="atlas-study-system">'+E(study['system'])+'</p><h3>'+E(study['title'])+'</h3><p><strong>Study design.</strong> '+E(study['design'])+'</p><p><strong>What they found.</strong> '+finding+'</p><p class="atlas-study-reading"><strong>How to read it.</strong> '+E(study['interpretation'])+'</p></div>'
 micro=cite(r['microbiome']);exposure=cite(r['exposure']);limits=cite(r['limits'])
 questions=''.join('<li>'+cite(q)+'</li>' for q in r.get('researchQuestions',[]))
 refs=[]
 for n,old in enumerate(order,1):
  s=r['sources'][old-1]
  back=''.join('<a href="#cite-'+str(n)+'-'+str(k)+'" role="doc-backlink" aria-label="Return to citation '+str(n)+', occurrence '+str(k)+'">↩</a>' for k in range(1,counts[n]+1))
  refs.append('<li id="ref-'+str(n)+'" tabindex="-1">'+E(s['authors'])+' ('+E(s['year'])+'). '+E(s['title'])+'. <a href="'+E(s['url'])+'" aria-label="View source for reference '+str(n)+'">View source</a><span class="reference-backlinks">'+back+'</span></li>')
 related=[x for x in DATA if x['group']==r['group'] and x!=r][:6]
 body='<section class="hero-band"><div class="wrap"><nav class="breadcrumb" aria-label="Breadcrumb"><a href="/">Home</a><span>/</span><a href="/metals">Metals atlas</a><span>/</span><span>'+E(r['name'])+'</span></nav><p class="eyebrow">'+E(GROUPS[r['group']][0])+'</p><div class="atlas-heading"><span class="atlas-symbol" aria-hidden="true">'+E(r['symbol'])+'</span><div><h1>'+E(r['name'])+' &amp; microbes</h1><p class="article-lead">'+E(r['role'])+'</p></div></div>'+tags(r)+'</div></section>'
 body+='<div class="wrap atlas-layout"><nav class="atlas-toc" aria-label="On this page"><h2>In this profile</h2>'+''.join('<a href="#'+a+'">'+b+'</a>' for a,b in [('overview','Overview'),('mechanisms','Microbial mechanisms'),('studies','Key experiments'),('evidence','Community & host evidence'),('exposure','Exposure & chemical form'),('limits','What remains uncertain'),('questions','Open questions'),('references','Selected research')])+'<a href="/metals">← All elements</a></nav><article class="article-body atlas-prose"><section id="overview"><h2>Why it belongs in microbial metallomics</h2><p>'+summary+'</p></section><section id="mechanisms"><h2>What microbes do with it</h2><ul>'+mechanisms+'</ul></section><section id="studies"><h2>Experiments worth knowing</h2>'+studies+'</section><section id="evidence"><h2>Community &amp; host evidence</h2><p>'+micro+'</p></section><section id="exposure"><h2>Exposure &amp; chemical form</h2><p>'+exposure+'</p></section><section id="limits" class="atlas-limit"><h2>What the evidence does not establish</h2><p>'+limits+'</p></section><section id="questions"><h2>Open research questions</h2><p class="atlas-section-note">Questions suggested by the evidence and its limits.</p><ul>'+questions+'</ul></section><section class="references" id="references" aria-labelledby="references-heading"><h2 id="references-heading">Selected research</h2><p>Sources supporting the numbered statements and study summaries above. Publication status is identified where a source reports trial results outside a peer-reviewed paper. This is a curated entry point, not a systematic review.</p><ol class="reference-list">'+''.join(refs)+'</ol></section><section class="atlas-related"><h2>Continue exploring</h2><div class="atlas-mini-grid">'+''.join(tile(x) for x in related)+'</div><p><a href="/evidence-guide">How to read different kinds of evidence</a> · <a href="/contribute">Suggest a source or correction</a></p></section></article></div>'
 (ROOT/'metals'/ (r['slug']+'.html')).write_text(page(r['name']+' & microbes',r['role']+'. Sourced microbial mechanisms, community evidence, chemical forms, and research limits.',r['url'],body,reviewed=r.get('reviewed',REVIEW_DATE)))
count=len(DATA);element_count=sum(len(r.get('members',[])) or 1 for r in DATA)
intro='<section class="hero-band"><div class="wrap"><p class="eyebrow">The metals atlas</p><h1>A wider view of the microbial periodic table.</h1><p class="article-lead">From nickel enzymes to arsenic transformation, rare-earth metabolism, and metal-based materials: '+str(count)+' profiles covering '+str(element_count)+' elements, with microbial mechanisms, close readings of key experiments, and open research questions.</p></div></section>'
intro+='<section class="wrap atlas-intro"><h2>One element can play more than one role.</h2><p>Microbes can acquire, exclude, transform, store, or precipitate metals. A cofactor can become toxic in excess; a contaminant can support a specialized microbial process. These groups are reading pathways, not mutually exclusive chemical or safety classifications.</p><p>“Heavy metal” has no single boundary used consistently across the literature. We include relevant metalloids, light metals, and selenium and identify their context. The atlas covers selected documented interactions; it does not claim to contain every online paper or establish a disease pathway for every element.</p><p><a href="#coverage">Coverage &amp; evidence gaps</a> · <a href="/evidence-guide">Read the evidence guide</a> · <a href="/assets/data/metals.json" download>Download the sourced atlas (JSON)</a></p></section>'
controls='<form class="atlas-filters wrap" role="search" aria-label="Filter element profiles" hidden><div><label for="metal-query">Find an element, organism, enzyme, or process</label><input id="metal-query" type="search" placeholder="Try nickel, urease, biofilm, or soil" autocomplete="off"></div><div><label for="metal-group">Research area</label><select id="metal-group"><option value="all">All research areas</option>'+''.join('<option value="'+k+'">'+E(v[0])+'</option>' for k,v in GROUPS.items())+'</select></div><button type="reset">Clear filters</button><p id="metal-count" role="status" aria-live="polite">'+str(count)+' profiles</p></form><p class="wrap atlas-empty" hidden>No matching profiles. Try an element symbol or a broader process, or clear the filters.</p>'
groups=''
for k,(title,desc) in GROUPS.items():
 rows=[r for r in DATA if r['group']==k];cards=''
 for r in rows:
  search=' '.join([r['symbol'],r['name'],r['role'],*r['tags'],r['summary']['text'],r['microbiome']['text'],r['exposure']['text'],r['limits']['text'],*[m['text'] for m in r['mechanisms']],*[study[k] for study in r.get('studies',[]) for k in ['title','system','design','finding','interpretation']],*[q['text'] for q in r.get('researchQuestions',[])],*[m['name']+' '+m['symbol'] for m in r.get('members',[])]])
  cards+='<article class="atlas-card" id="'+r['symbol'].lower()+'" data-metal-group="'+k+'" data-metal-symbols="'+E(' '.join([r['symbol'],*[m['symbol'] for m in r.get('members',[])]]).lower())+'" data-metal-search="'+E(search.lower())+'"><div class="atlas-card-top"><span class="atlas-card-symbol" aria-hidden="true">'+E(r['symbol'])+'</span><div><h3><a href="'+r['url']+'">'+E(r['name'])+'</a></h3><span class="atlas-atomic">'+('Atomic number '+str(r['atomicNumber']) if r['atomicNumber'] else 'Related lanthanides')+'</span></div></div><p class="atlas-role">'+E(r['role'])+'</p><p>'+E(r['summary']['text'])+'</p><a class="atlas-read" href="'+r['url']+'">Mechanisms, evidence &amp; sources <span aria-hidden="true">→</span><span class="sr-only"> for '+E(r['name'])+'</span></a></article>'
 groups+='<section class="wrap atlas-group" id="'+('toxic' if k=='contaminants' else k)+'" data-atlas-group="'+k+'"><h2>'+E(title)+'</h2><p class="atlas-group-note">'+E(desc)+'</p><div class="atlas-card-grid">'+cards+'</div></section>'
coverage='<section class="wrap atlas-coverage" id="coverage"><h2>Coverage &amp; evidence gaps</h2><p>The atlas spans microbial biochemistry, environmental communities, host-associated microbiomes, and experimental materials. The depth of each profile follows the available sources: a biochemical assay, a soil experiment, an animal model, and a human trial answer different questions.</p><p>Rare lanthanides are grouped when evidence is limited or shared across a series. Elements without a separately sourced interaction here are not presumed biologically irrelevant. Newly published studies, unindexed work, contradictory findings, and additional chemical species may change these summaries.</p><p>To propose an addition, send the element, chemical form, organism or community, study design, and a DOI or other primary-source link through <a href="/contribute">Contribute or correct</a>. A paper showing metal binding alone is not proof of a nutritional requirement; a taxonomic association alone is not proof of disease causation.</p></section>'
(ROOT/'metals.html').write_text(page('Metals atlas: elements & microbial interactions',str(count)+' sourced profiles spanning microbial cofactors, contaminants, rare earths, antimicrobials, and environmental metal transformations.','/metals',intro+controls+groups+coverage,'CollectionPage'))
# Homepage keeps every tile as a real, indexable link, including without JavaScript.
home=(ROOT/'index.html').read_text()
homegroups=''
for k,(title,_) in GROUPS.items():
 homegroups+='<div class="atlas-home-group"><h3>'+E(title)+'</h3><div class="atlas-mini-grid">'+tiles([r for r in DATA if r['group']==k])+'</div></div>'
section='<section data-section="metals-section" class="section-line"><div class="wrap"><div class="section-head"><p class="eyebrow">The metals atlas</p><h2>Every metal has a microbial story. The evidence varies.</h2><p>Explore '+str(count)+' sourced profiles covering '+str(element_count)+' elements: enzyme cofactors, contaminants, metalloids, rare earths, and emerging materials. Each profile connects microbial mechanisms to primary research and explains what remains uncertain.</p></div>'+homegroups+'<p class="atlas-home-note">Groups are research pathways, not safety ratings. Light metals and the nonmetal selenium are included for context; some lanthanides share a profile.</p><p><a class="btn btn-primary" href="/metals">Search the complete atlas →</a></p></div></section>'
home,n=re.subn(r'<section[^>]*data-section="metals-section"[^>]*>.*?</section>',section,home,flags=re.S);assert n==1
if '/assets/metals.css' not in home:home=home.replace('</head>','<link rel="stylesheet" href="/assets/metals.css">\n</head>')
(ROOT/'index.html').write_text(home)
print('Built',count,'profiles covering',element_count,'elements, hub, and homepage tiles.')
