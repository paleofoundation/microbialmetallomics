"""Refresh shared navigation, asset versions, search and sitemap after content generators."""
from pathlib import Path
import re,json,html,hashlib
from urllib.parse import urlsplit
from html.parser import HTMLParser
from datetime import date,datetime,timezone
from xml.sax.saxutils import escape
from link_site import refresh_links,registry
from search_metadata import refresh_search_metadata
ROOT=Path(__file__).resolve().parents[1]
ORIGIN='https://microbialmetallomics.com'
class PageMetadata(HTMLParser):
 """Read metadata regardless of attribute order, quoting, or extra attributes."""
 def __init__(self,source):
  super().__init__(convert_charrefs=True)
  self.meta={};self.canonical='';self.heading=[];self.structured=[]
  self._heading=False;self._script=None
  self.feed(source)
 def handle_starttag(self,tag,attributes):
  attrs=dict(attributes)
  if tag=='meta':
   key=(attrs.get('name') or attrs.get('property') or '').lower()
   if key:self.meta.setdefault(key,[]).append(attrs.get('content',''))
  elif tag=='link' and 'canonical' in (attrs.get('rel') or '').lower().split():
   self.canonical=attrs.get('href','')
  elif tag=='h1':self._heading=True
  elif tag=='script' and (attrs.get('type') or '').lower()=='application/ld+json':self._script=[]
 def handle_endtag(self,tag):
  if tag=='h1':self._heading=False
  elif tag=='script' and self._script is not None:
   try:self.structured.append(json.loads(''.join(self._script)))
   except (TypeError,ValueError):pass # The whole-site linter reports malformed JSON.
   self._script=None
 def handle_data(self,data):
  if self._heading:self.heading.append(data)
  if self._script is not None:self._script.append(data)
 @property
 def description(self):return next(iter(self.meta.get('description',[])),'')
 @property
 def title(self):return ' '.join(''.join(self.heading).split())
 @property
 def indexable(self):
  directives=','.join(value.lower() for key in ['robots','googlebot','bingbot'] for value in self.meta.get(key,[]))
  return not {'noindex','none'}.intersection(re.split(r'[\s,]+',directives))
 def last_modified(self):
  # Use page-level dates, never dates on cited publications or the build clock.
  page_types={'WebPage','Article','BlogPosting','ScholarlyArticle','NewsArticle','CollectionPage','AboutPage','ProfilePage','FAQPage'}
  nodes=[]
  for data in self.structured:
   candidates=data if isinstance(data,list) else [data]
   for candidate in candidates:
    if isinstance(candidate,dict):nodes.extend(candidate.get('@graph',[candidate]))
  page_nodes=[]
  for node in nodes:
   if not isinstance(node,dict):continue
   types=node.get('@type',[]);types=[types] if isinstance(types,str) else types
   if not page_types.intersection(types):continue
   identity=node.get('url') or node.get('mainEntityOfPage') or node.get('@id')
   if isinstance(identity,dict):identity=identity.get('@id') or identity.get('url')
   if identity and str(identity).split('#')[0].rstrip('/')!=self.canonical.rstrip('/'):continue
   page_nodes.append(node)
  for field,meta_name in [('dateModified','article:modified_time'),('datePublished','article:published_time')]:
   dates=[]
   for value in [*[node.get(field) for node in page_nodes],*self.meta.get(meta_name,[])]:
    if not isinstance(value,str):continue
    try:
     parsed=datetime.fromisoformat(value.replace('Z','+00:00')) if 'T' in value else date.fromisoformat(value)
     day=parsed.date() if isinstance(parsed,datetime) else parsed
     if day<=datetime.now(timezone.utc).date():dates.append(day.isoformat())
    except ValueError:continue
   if dates:return max(dates)
  return None

def public_html():
 return sorted(p for p in ROOT.rglob('*.html') if 'node_modules' not in p.parts and not any(part.startswith('.') for part in p.relative_to(ROOT).parts))

links=[('/metals','Metals atlas'),('/research','Research'),('/library','Paper Reviews'),('/disease-signatures','Disease signatures'),('/people',"Who’s Who"),('/commentary','Commentary')]
nav='<nav class="nav-links" aria-label="Primary">'+''.join('<a href="'+url+'">'+title+'</a>' for url,title in links)+'</nav>'
mega='''<div class="mega-menu" id="mega-menu"><div class="wrap"><div class="mega-grid"><div class="mega-col"><h5>Read the field</h5><a href="/topics"><b>Topics</b><span>Explore the guide by subject</span></a><a href="/start-here"><b>Start here</b><span>The organizing thesis</span></a><a href="/metal-access"><b>Follow the metal</b><span>Form, compartment, and microbial access</span></a><a href="/science"><b>The Science</b><span>How microbes use and compete for metals</span></a><a href="/metals"><b>Metals atlas</b><span>Elements, mechanisms, and biological consequences</span></a><a href="/glossary"><b>Glossary</b><span>Find a term and its meaning</span></a><a href="/faq"><b>Frequently asked questions</b><span>Answers about microbes and metals</span></a><a href="/blog"><b>Essays</b><span>The metal–microbiome–disease axis</span></a></div><div class="mega-col"><h5>Work with the evidence</h5><a href="/disease-signatures"><b>Disease signatures</b><span>Metal patterns, microbial mechanisms, next experiments</span></a><a href="/evidence"><b>Evidence explorer</b><span>Search, filter, and export the catalog</span></a><a href="/library"><b>Paper Reviews</b><span>Studies, read in context</span></a><a href="/commentary"><b>Critical Commentary</b><span>Close readings and open questions</span></a><a href="/methods"><b>Methods comparison</b><span>Match a tool to a question</span></a><a href="/evidence-guide"><b>Evidence guide</b><span>Design, inference, and publication status</span></a></div><div class="mega-col"><h5>People &amp; participation</h5><a href="/people"><b>Who’s Who</b><span>Researchers, expertise, and public contacts</span></a><a href="/projects"><b>Research questions</b><span>Proposed directions and missing measurements</span></a><a href="/contribute"><b>Contribute or correct</b><span>Prepare a sourced suggestion</span></a><a href="/reading-list"><b>Saved reading</b><span>Your list on this browser</span></a><a href="/about"><b>About this resource</b><span>Purpose and affiliations</span></a></div><div class="mega-col"><h5>Follow &amp; understand</h5><a href="/newsletter"><b>Follow the field</b><span>Ways to keep up with new writing</span></a><a href="/feeds"><b>RSS feeds</b><span>All writing or a selected section</span></a><a href="/updates"><b>Latest &amp; changes</b><span>New articles and site revisions</span></a><a href="/editorial"><b>Editorial standards</b><span>Sources, disclosures, and corrections</span></a><a href="/landscape"><b>Research Landscape</b><span>Journals, facilities, and milestones</span></a></div></div></div></div>'''
footerlinks='<p class="utility-links"><a href="/about">About</a><a href="/editorial">Editorial standards</a><a href="/editorial#privacy">Privacy</a><a href="/contribute">Contribute / correct</a><a href="/feeds">RSS</a><a href="/updates">Updates</a><a href="/reading-list">Saved reading</a></p>'
footercredit='<p class="project-credit">© 2026 Microbial Metallomics. A project associated with <a href="https://microbiomemedicine.com/">Microbiome Medicine</a> and <a href="https://www.wikibiome.com/">Wikibiome.com</a>.</p>'
cat_hash=hashlib.sha256((ROOT/'assets/data/articles.json').read_bytes()).hexdigest()[:12]
for p in public_html():
 s=p.read_text()
 s=s.replace('<html lang="en">','<html lang="en-US">').replace('"inLanguage": "en"','"inLanguage": "en-US"')
 s=re.sub(r'<nav class="nav-links" aria-label="Primary">.*?</nav>',nav,s,flags=re.S)
 # The existing mega menu is the last block before the site header closes.
 s=re.sub(r'<div class="mega-menu" id="mega-menu">.*?(?=</header>)',mega+'\n',s,flags=re.S)
 if 'field-tools.css' not in s:s=s.replace('</head>','<link rel="stylesheet" href="/assets/field-tools.css">\n</head>')
 if 'field-tools.js' not in s:s=s.replace('</body>','<script src="/assets/field-tools.js" defer></script>\n</body>')
 s=re.sub(r'<meta name="reading-catalogue"[^>]*>\n?','',s)
 s=s.replace('</head>','<meta name="reading-catalogue" content="/assets/data/articles.json?v='+cat_hash+'">\n</head>')
 if 'rel="alternate" type="application/rss+xml"' not in s:s=s.replace('</head>','<link rel="alternate" type="application/rss+xml" title="Microbial Metallomics — all writing" href="/feeds/all.xml">\n</head>')
 s=s.replace('<a href="/#newsletter">Newsletter</a>','<a href="/newsletter">Follow the field</a>')
 if 'class="utility-links"' not in s:s=s.replace('<div class="foot-bottom">','<div class="foot-bottom">'+footerlinks)
 s=re.sub(r'<p(?: class="project-credit")?>© \d{4} Microbial Metallomics\..*?</p>',footercredit,s,flags=re.S)
 s=s.replace('An independent, open field guide to the science of metals','An open field guide to the science of metals')
 # Every changed asset gets a content-based URL, matching immutable hosting cache.
 def bust(match):
  attr,url=match.group(1),html.unescape(match.group(2));u=urlsplit(url)
  asset=ROOT/u.path.lstrip('/')
  if asset.is_file():
   digest=hashlib.sha256(asset.read_bytes()).hexdigest()[:12]
   return attr+'="'+u.path+'?v='+digest+'"'
  return match.group(0)
 s=re.sub(r'(href|src)="(/assets/[^\"]+\.(?:css|js|json|csv)(?:\?[^\"]*)?)"',bust,s)
 s='\n'.join(line.rstrip() for line in s.splitlines())+'\n'
 p.write_text(s)
refresh_links(ROOT)
refresh_search_metadata(ROOT)
# Normalize the device-local page before building discovery records.
p=ROOT/'reading-list.html';s=p.read_text();s=re.sub(r'<meta name="robots" content="[^"]*">','<meta name="robots" content="noindex,follow">',s);p.write_text(s)
# One attribute-order-independent inventory drives both search and the sitemap.
pages={}
for p in public_html():
 metadata=PageMetadata(p.read_text());canonical=urlsplit(metadata.canonical)
 if not metadata.indexable or canonical.scheme!='https' or canonical.netloc!=urlsplit(ORIGIN).netloc:continue
 pages[canonical.path or '/']=(p,metadata)
# Preserve useful section-anchor records and refresh every indexable page.
_,_,legacy_destinations=registry(ROOT)
p=ROOT/'search-index.json';index=[r for r in json.loads(p.read_text()) if urlsplit(r['url']).path in pages and r['url'] not in legacy_destinations]
byurl={r['url']:r for r in index}
for route,(p,metadata) in pages.items():
 if not metadata.title:continue
 existing=byurl.get(route,{})
 kind='Researcher profile' if route.startswith('/people/') else ('Element profile' if route.startswith('/metals/') else ('Glossary' if route.startswith('/glossary/') else ('Guide' if p.stem in ['start-here','metal-access','evidence-guide','methods','editorial','about','projects'] else existing.get('kind','Section'))))
 record={'kind':kind,'title':metadata.title,'url':route,'desc':metadata.description}
 if route in byurl:byurl[route].update(record)
 else:index.append(record);byurl[route]=record
# Article author and topic context is richer than the search-result description.
articles=json.loads((ROOT/'assets/data/articles.json').read_text())
for r in articles:
 if r['url'] in byurl:byurl[r['url']].update({'kind':r['kind'],'title':r['title'],'desc':r['description']+' '+' '.join(r['authors'])+' '+' '.join(r['topics'])})
# Search includes element symbols, enzymes, organisms, and grouped lanthanide names.
def readable_access(value):
 if isinstance(value,str):return value
 if isinstance(value,list):return ' '.join(readable_access(item) for item in value)
 if isinstance(value,dict):return ' '.join(readable_access(item) for key,item in value.items() if key not in {'id','type','url','refs','layout'})
 return ''
metals_path=ROOT/'assets/data/metals.json'
if metals_path.exists():
 for r in json.loads(metals_path.read_text()):
  if r['url'] in byurl:
   byurl[r['url']]['desc']=' '.join([r['symbol'],r['role'],r['summary']['text'],*r['tags'],*[study['system'] for study in r.get('studies',[])],*[m['name']+' '+m['symbol'] for m in r.get('members',[])]])
   if r.get('access'):byurl[r['url']]['desc']+=' '+readable_access(r['access'])
   if r.get('mechanismSpotlight'):byurl[r['url']]['desc']+=' '+readable_access(r['mechanismSpotlight'])
access_path=ROOT/'assets/data/metal-access.json'
if access_path.exists():
 access_data=json.loads(access_path.read_text())
 for route,key in [('/start-here','thesis'),('/metal-access','explorer')]:
  if route in byurl:byurl[route]['desc']=readable_access(access_data[key])
people_path=ROOT/'assets/data/people.json'
profile_portraits={}
if people_path.exists():
 for r in json.loads(people_path.read_text()):
  route='/people/'+r['slug']
  if route in byurl:byurl[route]['desc']=' '.join([r['bio'],*r['topics'],readable_access(r.get('impact',{})),readable_access(r.get('spotlight',{})),readable_access(r.get('mechanisticCase',{}))])
  if route in pages and r.get('portrait'):
   portrait=urlsplit(r['portrait']);asset=(ROOT/portrait.path.lstrip('/')).resolve()
   # Only publish real, local portrait assets; omit cache parameters from image URLs.
   if portrait.scheme or portrait.netloc or not portrait.path.startswith('/assets/') or not asset.is_relative_to((ROOT/'assets').resolve()) or not asset.is_file():
    raise ValueError('Invalid profile portrait for '+r['slug']+': '+r['portrait'])
   profile_portraits[pages[route][1].canonical]=ORIGIN+portrait.path
(ROOT/'search-index.json').write_text(json.dumps(index,ensure_ascii=False)+'\n')
# Sitemap: every indexable canonical page, with reliable page-level freshness only.
entries={metadata.canonical:metadata.last_modified() for _,metadata in pages.values()}
(ROOT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'+''.join('<url><loc>'+escape(url)+'</loc>'+('<lastmod>'+modified+'</lastmod>' if modified else '')+('<image:image><image:loc>'+escape(profile_portraits[url])+'</image:loc></image:image>' if url in profile_portraits else '')+'</url>\n' for url,modified in sorted(entries.items()))+'</urlset>\n')
print('Integrated navigation, profiles, tool assets, content feeds, metadata,',len(index),'search entries and',len(entries),'sitemap URLs.')
