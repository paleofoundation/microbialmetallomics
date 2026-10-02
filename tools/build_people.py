#!/usr/bin/env python3
"""Build the researcher directory and contribution profiles from one source."""
from pathlib import Path
from html import escape as esc
import json,re
from author_identity import orcid_link
ROOT=Path(__file__).resolve().parents[1]
ORIGIN='https://microbialmetallomics.com'
people=json.loads((ROOT/'assets/data/people.json').read_text())
articles=json.loads((ROOT/'assets/data/articles.json').read_text())
context=json.loads((ROOT/'assets/data/people-context.json').read_text())
assert len({r['slug'] for r in people})==len(people)
for r in people:
 assert re.fullmatch('[a-z0-9-]+',r['slug'])
 assert all(r['impact'].get(k) for k in ['headline','discovery','significance','frontier','sources']),r['name']
 for link in [*r['impact']['sources'],*r.get('profileLinks',[])]:assert link['url'].startswith(('https://','mailto:','/')),link
old=(ROOT/'people.html').read_text()
prefix=old.split('<main')[0];suffix=old[old.index('</main>')+7:]
prefix=re.sub(r'<script type="application/ld\+json">.*?</script>\s*','',prefix,flags=re.S)
def head(title,description,url,ld,bodyclass,profile=None):
 full_title=profile.get('searchTitle') if profile else None
 s=re.sub(r'<title>.*?</title>','<title>'+esc(full_title or title+' — Microbial Metallomics')+'</title>',prefix,flags=re.S)
 for attr,key,value in [('name','description',description),('property','og:title',title),('property','og:description',description),('property','og:url',ORIGIN+url),('name','twitter:title',title),('name','twitter:description',description)]:
  s=re.sub(r'<meta\b(?=[^>]*\b'+attr+'="'+re.escape(key)+'")[^>]*>','<meta '+attr+'="'+key+'" content="'+esc(value,quote=True)+'">',s)
 s=re.sub(r'<link rel="canonical" href="[^"]+">','<link rel="canonical" href="'+ORIGIN+url+'">',s)
 s=re.sub(r'<body[^>]*>','<body class="'+bodyclass+'">',s)
 if profile and profile.get('searchTitle'):
  portrait=ORIGIN+profile['portrait'];alt=profile.get('portraitAlt',profile['name'])
  for attr,key,value in [('property','og:type','profile'),('property','og:title',full_title),('name','twitter:title',full_title),('property','og:image',portrait),('name','twitter:image',portrait),('name','twitter:card','summary')]:
   s=re.sub(r'<meta\b(?=[^>]*\b'+attr+'="'+re.escape(key)+'")[^>]*>','<meta '+attr+'="'+key+'" content="'+esc(value,quote=True)+'">',s)
  s=s.replace('</head>','<meta property="og:image:alt" content="'+esc(alt,quote=True)+'">\n<meta name="twitter:image:alt" content="'+esc(alt,quote=True)+'">\n<meta property="og:image:type" content="image/avif">\n<meta property="og:image:width" content="'+str(profile['portraitWidth'])+'">\n<meta property="og:image:height" content="'+str(profile['portraitHeight'])+'">\n</head>')
 return s.replace('</head>','<script type="application/ld+json">'+json.dumps(ld,ensure_ascii=False)+'</script>\n</head>')
def source_links(sources):return '<ul class="impact-sources">'+''.join('<li><a href="'+esc(s['url'],quote=True)+'">'+esc(s['label'])+' ↗</a></li>' for s in sources)+'</ul>'
def visual(r):
 if r.get('portrait'):return '<figure class="person-visual"><img src="'+esc(r['portrait'],quote=True)+'" alt="'+esc(r.get('portraitAlt',r['name']),quote=True)+'" width="'+str(r.get('portraitWidth',180))+'" height="'+str(r.get('portraitHeight',220))+'" loading="lazy" decoding="async"><figcaption>'+ (esc(r['portraitCaption'])+'<br>' if r.get('portraitCaption') else '')+'<a href="'+esc(r['portraitSource'],quote=True)+'">Portrait source ↗</a></figcaption></figure>'
 initials=''.join(w[0] for w in r['name'].split() if len(w)>2)[:2]
 return '<div class="person-monogram" aria-hidden="true">'+esc(initials)+'<span>FIELD GUIDE</span></div>'
def links(r):
 items=list(r.get('profileLinks',[]))
 items.extend(x for x in r.get('identityLinks',[]) if x['url'] not in {item['url'] for item in items})
 rendered=''.join('<a href="'+esc(x['url'],quote=True)+'">'+esc(x['label'])+'</a>' for x in items)
 if r.get('orcid'):rendered+=orcid_link(r['orcid'],r['name'])
 items=[]
 if r.get('orcidSource'):items.append({'label':'ORCID source: institutional CV','url':r['orcidSource']})
 if r.get('emailSource'):items.append({'label':'Professional email: institutional source','url':r['emailSource']})
 return '<div class="person-links">'+rendered+''.join('<a href="'+esc(x['url'],quote=True)+'">'+esc(x['label'])+'</a>' for x in items)+'</div>'
def works(r):
 if not r.get('works'):return ''
 return '<section class="person-works"><h2>'+esc(r.get('worksTitle','Selected research & writing'))+'</h2>'+''.join('<div class="person-work"><a href="'+esc(w['url'],quote=True)+'">'+esc(w['title'])+' →</a>'+('<p class="person-work-type">'+esc(w['type'])+'</p>' if w.get('type') else '')+('<p class="person-work-note">'+esc(w['note'])+'</p>' if w.get('note') else '')+'</div>' for w in r['works'])+'</section>'
def identity(r):
 person={'@type':'Person','name':r['name'],'url':ORIGIN+'/people/'+r['slug'],'description':r['impact']['significance'],'sameAs':list(dict.fromkeys([r['source'],*[x['url'] for x in r.get('identityLinks',[])]]+(['https://orcid.org/'+r['orcid']] if r.get('orcid') else []))),**({'image':ORIGIN+r['portrait']} if r.get('portrait') else {})}
 if r.get('siteAuthor'):
  person['@id']=person['url']+'#person'
 if r.get('affiliations'):
  person.update({'description':r['bio'],'jobTitle':r['role'],'knowsAbout':r['topics'],'affiliation':[{'@type':'Organization','name':a['name'],'url':a['url']} for a in r['affiliations']]})
 if r.get('portraitCaption'):
  person['image']={'@type':'ImageObject','@id':person['url']+'#portrait','contentUrl':ORIGIN+r['portrait'],'url':ORIGIN+r['portrait'],'name':r['portraitAlt'],'caption':r['portraitCaption'],'width':r['portraitWidth'],'height':r['portraitHeight'],'encodingFormat':'image/avif','about':{'@id':person['@id']}}
 return person
def affiliations(r):
 if not r.get('affiliations'):return ''
 return '<section id="affiliations"><h2>Affiliations and projects</h2>'+''.join('<h3><a href="'+esc(a['url'],quote=True)+'">'+esc(a['name'])+'</a></h3><p><strong>'+esc(a['role'])+'.</strong> '+esc(a['description'])+'</p>' for a in r['affiliations'])+'</section>'
def author_archive(r):
 if not r.get('showAuthorArchive'):return ''
 selected={w['url'] for w in r.get('works',[])}
 authored=[a for a in articles if r['name'] in a['authors'] and a['url'] not in selected]
 return '<section class="person-works" id="author-archive"><h2>More writing by '+esc(r['name'])+'</h2><p>Research frameworks and commentary published on this site. Follow each page to its original source and publication status.</p>'+''.join('<div class="person-work"><a href="'+esc(a['url'],quote=True)+'">'+esc(a['title'])+' →</a><p class="person-work-type">'+esc(a['status'] or a['kind'])+'</p></div>' for a in authored)+'</section>'
def topics(r):return '<ul class="person-topics" aria-label="Research interests">'+''.join('<li>'+esc(t)+'</li>' for t in r['topics'])+'</ul>'
def spotlight(spot):
 rows=''.join('<tr><th scope="row">'+esc(row['setting'])+'</th><td>'+esc(row['finding'])+'</td><td>'+esc(row['meaning'])+'</td></tr>' for row in spot['rows'])
 return '<section class="profile-spotlight" id="dmg-evidence"><h2>'+esc(spot['title'])+'</h2><div class="profile-table-wrap" role="region" aria-label="DMG evidence by study setting" tabindex="0"><table><caption>What the DMG studies establish</caption><thead><tr><th scope="col">Study setting</th><th scope="col">Observed result</th><th scope="col">Why it matters</th></tr></thead><tbody>'+rows+'</tbody></table></div><h3>'+esc(spot['contextTitle'])+'</h3><p>'+esc(spot['context'])+'</p>'+source_links(spot['sources'])+'</section>'
def mechanistic_case(case):
 rows=''.join('<tr><th scope="row"><i>'+esc(row['organism'])+'</i><p>'+esc(row['priority'])+'</p></th><td>'+esc(row['finding'])+source_links(row['sources'])+'</td><td>'+esc(row['question'])+'</td></tr>' for row in case['rows'])
 sections=''.join('<section><h3>'+esc(s['title'])+'</h3>'+''.join('<p>'+esc(p)+'</p>' for p in s['paragraphs'])+(source_links(s['sources']) if s.get('sources') else '')+'</section>' for s in case['sections'])
 return '<section class="profile-spotlight" id="nickel-research-directions"><h2>'+esc(case['title'])+'</h2><p>'+esc(case['intro'])+'</p><div class="profile-table-wrap" role="region" aria-label="Published nickel-enzyme research and WHO priorities" tabindex="0"><table><caption>'+esc(case['caption'])+'</caption><thead><tr><th scope="col">Organism and WHO category</th><th scope="col">Established finding</th><th scope="col">Research significance</th></tr></thead><tbody>'+rows+'</tbody></table></div>'+sections+'</section>'
# Individual pages make the contribution shareable and allow detailed evidence without an unwieldy directory.
(ROOT/'people').mkdir(exist_ok=True)
for r in people:
 i=r['impact'];url='/people/'+r['slug'];person=identity(r)
 description=r.get('searchDescription',r['name']+': '+i['headline'].rstrip('.')+'. Explore the evidence and research directions.')
 ld={'@context':'https://schema.org','@graph':[{'@type':'WebPage','name':r['name']+' — Why this work matters','url':ORIGIN+url,'description':description,'about':person,'isPartOf':{'@type':'WebSite','name':'Microbial Metallomics','url':ORIGIN}}, {'@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':1,'name':'Home','item':ORIGIN+'/'},{'@type':'ListItem','position':2,'name':'Who’s Who','item':ORIGIN+'/people'},{'@type':'ListItem','position':3,'name':r['name'],'item':ORIGIN+url}]}]}
 main='<main id="main-content"><section class="hero-band"><div class="wrap"><nav class="breadcrumb" aria-label="Breadcrumb"><a href="/">Home</a><span>/</span><a href="/people">Who’s Who</a><span>/</span><span>'+esc(r['name'])+'</span></nav><p class="eyebrow">'+esc(r['category'])+'</p><h1>'+esc(r['name'])+(' †' if r.get('deceased') else '')+'</h1><p class="article-lead">'+esc(i['headline'])+'</p></div></section><div class="wrap profile-layout"><article class="profile-argument"><section id="contribution"><p class="eyebrow">The contribution</p><h2>What this work established</h2><p>'+esc(i['discovery'])+'</p>'+source_links(i['sources'])+'</section><section id="significance"><h2>Why this matters to microbial metallomics</h2><p>'+esc(i['significance'])+'</p></section>'+ (spotlight(r['spotlight']) if r.get('spotlight') else '')+(mechanistic_case(r['mechanisticCase']) if r.get('mechanisticCase') else '')+'<section id="frontier"><h2>The next scientific question</h2><p>'+esc(i['frontier'])+'</p></section><section id="background"><h2>Research background</h2>'+''.join('<p>'+esc(b)+'</p>' for b in r.get('bioParagraphs',[r['bio']]))+'</section>'+works(r)+'<p class="profile-editorial">The contribution is grounded in the linked sources. Its significance and future directions are this guide’s editorial synthesis. Inclusion does not imply endorsement of this website.</p><div class="related-module"><h2>Connect the work</h2><div class="related-grid"><a href="/people#'+r['slug']+'"><span class="rk">Who’s Who</span><span class="rt">Back to the directory</span></a><a href="/metal-access"><span class="rk">The framework</span><span class="rt">Follow the metal</span></a><a href="/metals"><span class="rk">The atlas</span><span class="rt">Explore the elements</span></a></div></div></article><aside class="profile-identity" aria-label="Profile and public links">'+visual(r)+'<p class="person-kind">'+esc(r['profileKind'])+'</p><p class="person-position">'+esc(r['role'])+'</p><p class="person-affiliation">'+esc(r['affiliation'])+'</p>'+topics(r)+links(r)+'</aside></div></main>'
 page=ld['@graph'][0]
 if r.get('siteAuthor'):
  page.update({'@type':'ProfilePage','@id':ORIGIN+url+'#profile','mainEntity':page.pop('about')})
  main=main.replace(' Inclusion does not imply endorsement of this website.','')
 if r.get('searchTitle'):page['name']=r['searchTitle']
 if r.get('portraitCaption'):page['primaryImageOfPage']=person['image']
 if r.get('profileIntro'):
  page['dateModified']=r['revisedAt']
  intro=''.join('<p class="profile-intro">'+esc(p)+'</p>' for p in r['profileIntro'])
  main=main.replace('<article class="profile-argument">','<article class="profile-argument">'+intro,1)
 if r.get('showAuthorArchive'):
  page['hasPart']=[{'@type':'Article','headline':a['title'],'url':ORIGIN+a['url'],'author':{'@id':person['@id']}} for a in articles if r['name'] in a['authors']]
 main=main.replace(works(r),affiliations(r)+works(r)+author_archive(r),1) if r.get('works') else main
 tail=re.sub(r'<script src="/assets/people.js[^>]*></script>\s*','',suffix)
 (ROOT/'people'/(r['slug']+'.html')).write_text(head(r['name']+' — Why this work matters',description,url,ld,'people-page person-profile'+(' author-profile' if r.get('siteAuthor') else ''),r)+main+tail)
# Directory and scientific overview.
categories=list(dict.fromkeys(r['category'] for r in people))
portraits=''.join('<a href="/people/'+r['slug']+'"><img src="'+r['portrait']+'" alt="" width="180" height="220"><span>'+esc(r['name'])+'</span></a>' for slug in ['stephane-benoit','amy-c-rosenzweig','michael-d-l-johnson','dianne-k-newman'] for r in people if r['slug']==slug)
intro='<section class="people-intro"><div class="wrap"><div class="people-intro-grid"><div><p class="eyebrow">Who’s Who · Discoveries and their significance</p><h1>The people changing what we can explain.</h1><p class="lede">'+esc(context['intro'])+'</p><p class="people-edition">'+str(len(people))+' profiles · '+str(len(categories))+' research areas</p><a class="person-profile-link" href="#directory">Find a researcher ↓</a></div><div class="people-portraits" aria-label="Explore contribution profiles">'+portraits+'</div></div><p class="people-scope">Directory inclusion describes contributions to the field. It does not imply authorship of, affiliation with, or endorsement of this guide. Site authors are labeled separately.</p></div></section>'
argument='<section class="people-argument"><div class="wrap"><p class="eyebrow">Why the field matters</p><h2>'+esc(context['title'])+'</h2><p class="people-argument-lead">'+esc(context['argument'])+'</p><div class="people-frontiers">'+''.join('<article><h3>'+esc(c['title'])+'</h3><p>'+esc(c['text'])+'</p><a href="'+esc(c['url'],quote=True)+'">'+esc(c['link'])+' →</a></article>' for c in context['frontiers'])+'</div><details class="people-context"><summary>'+esc(context['exposureTitle'])+'</summary>'+''.join('<p>'+esc(p)+'</p>' for p in context['exposureParagraphs'])+source_links(context['sources'])+'</details></div></section>'
filters='<form class="people-tools" role="search" aria-label="Filter researchers"><div><label for="people-query">Search people, discoveries, or metals</label><input id="people-query" type="search" placeholder="Try DMG, mismetallation, iron…" autocomplete="off"></div><div><label for="people-area">Research area</label><select id="people-area"><option value="">All research areas</option>'+''.join('<option>'+esc(c)+'</option>' for c in categories)+'</select></div><button type="reset" id="people-reset">Clear filters</button></form><div class="people-results"><p id="people-count" role="status" aria-live="polite">Showing all '+str(len(people))+' profiles</p><a href="#directory-notes">About this directory</a></div><p id="people-empty" hidden>No profiles match. Try a different name, metal, or research question.</p>'
areas=''
for number,cat in enumerate(categories,1):
 cards=''
 for r in people:
  if r['category']!=cat:continue
  i=r['impact'];search=' '.join([r['name'],r['bio'],*r['topics'],i['discovery'],i['frontier'],*[' '.join([row['organism'],row['priority'],row['finding']]) for row in r.get('mechanisticCase',{}).get('rows',[])]])
  cards+='<article class="person-record" id="'+r['slug']+'" data-person data-area="'+esc(cat,quote=True)+'" data-discovery="'+esc(search,quote=True)+'">'+visual(r)+'<div class="person-text"><p class="person-kind">'+esc(r['profileKind'])+'</p><h3><a href="/people/'+r['slug']+'">'+esc(r['name'])+(' †' if r.get('deceased') else '')+'</a></h3><p class="person-affiliation">'+esc(r['affiliation'])+'</p><div class="person-impact"><p class="impact-label">Why this work matters</p><h4>'+esc(i['headline'])+'</h4><p>'+esc(i['significance'])+'</p></div>'+topics(r)+'<a class="person-profile-link" href="/people/'+r['slug']+'">Read the contribution & evidence →</a></div></article>'
 areas+='<section class="people-area" id="area-'+str(number)+'" data-people-area><h2>'+esc(cat)+'</h2><div class="people-records">'+cards+'</div></section>'
notes='<aside class="people-notes" id="directory-notes"><div><p class="eyebrow">An open record</p><h2>Specific contributions. Traceable evidence.</h2></div><div><p>These profiles connect discoveries, methods, environmental research, evidence curation, and standards with the questions of microbial metallomics. Each person’s work has a different role in that scientific effort.</p><p>Contribution summaries link to primary studies or official research records. Sections explaining significance and future directions are editorial synthesis. They explain what a discovery makes possible and which observations would move the idea forward. Mechanistic hypotheses are a central part of this guide’s contribution.</p><p>Historical profiles preserve the affiliation associated with the cited work; † marks a deceased researcher. Portrait and public professional contact sources appear on the individual profiles. Roles can change; institutional records remain the reference.</p><a href="/contribute">Suggest a researcher or correction →</a></div></aside>'
main='<main id="main-content">'+intro+argument+'<section class="people-directory" id="directory"><div class="wrap">'+filters+areas+notes+'</div></section></main>'
ld={'@context':'https://schema.org','@type':'ItemList','name':'Who’s Who in Microbial Metallomics','numberOfItems':len(people),'itemListElement':[{'@type':'ListItem','position':n,'item':identity(r)} for n,r in enumerate(people,1)]}
(ROOT/'people.html').write_text(head('Who’s Who in Microbial Metallomics','Meet '+str(len(people))+' researchers and contributors through the discoveries, methods, and ideas that make microbial metallomics matter for medicine, biology, and environmental exposure.','/people',ld,'people-page')+main+suffix)
print('Built',len(people),'contribution profiles and the searchable directory.')
