"""Refresh shared navigation, asset versions, search index and sitemap. Run after build_catalog.py."""
from pathlib import Path
import re,json,html,hashlib
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]
ORIGIN='https://microbialmetallomics.com'
links=[('/start-here','Start here'),('/research','Research'),('/library','Paper Reviews'),('/topics','Topics'),('/people',"Who’s Who"),('/commentary','Commentary')]
nav='<nav class="nav-links" aria-label="Primary">'+''.join('<a href="'+url+'">'+title+'</a>' for url,title in links)+'</nav>'
mega='''<div class="mega-menu" id="mega-menu"><div class="wrap"><div class="mega-grid"><div class="mega-col"><h5>Read the field</h5><a href="/start-here"><b>Start here</b><span>Three reading pathways</span></a><a href="/science"><b>The Science</b><span>How microbes use and compete for metals</span></a><a href="/metals"><b>The Metals</b><span>Element-by-element profiles</span></a><a href="/glossary"><b>Glossary</b><span>Find a term and its meaning</span></a><a href="/blog"><b>Essays</b><span>The metal–microbiome–disease axis</span></a></div><div class="mega-col"><h5>Work with the evidence</h5><a href="/evidence"><b>Evidence explorer</b><span>Search, filter, and export the catalog</span></a><a href="/library"><b>Paper Reviews</b><span>Studies, read in context</span></a><a href="/commentary"><b>Critical Commentary</b><span>Close readings and open questions</span></a><a href="/methods"><b>Methods comparison</b><span>Match a tool to a question</span></a><a href="/evidence-guide"><b>Evidence guide</b><span>Design, inference, and publication status</span></a></div><div class="mega-col"><h5>People &amp; participation</h5><a href="/people"><b>Who’s Who</b><span>Researchers, expertise, and public contacts</span></a><a href="/projects"><b>Research questions</b><span>Proposed directions and missing measurements</span></a><a href="/contribute"><b>Contribute or correct</b><span>Prepare a sourced suggestion</span></a><a href="/reading-list"><b>Saved reading</b><span>Your list on this browser</span></a><a href="/about"><b>About this resource</b><span>Purpose and affiliations</span></a></div><div class="mega-col"><h5>Follow &amp; understand</h5><a href="/newsletter"><b>Follow the field</b><span>Ways to keep up with new writing</span></a><a href="/feeds"><b>RSS feeds</b><span>All writing or a selected section</span></a><a href="/updates"><b>Latest &amp; changes</b><span>New articles and site revisions</span></a><a href="/editorial"><b>Editorial standards</b><span>Sources, disclosures, and corrections</span></a><a href="/landscape"><b>Research Landscape</b><span>Journals, facilities, and milestones</span></a></div></div></div></div>'''
footerlinks='<p class="utility-links"><a href="/about">About</a><a href="/editorial">Editorial standards</a><a href="/editorial#privacy">Privacy</a><a href="/contribute">Contribute / correct</a><a href="/feeds">RSS</a><a href="/updates">Updates</a><a href="/reading-list">Saved reading</a></p>'
footercredit='<p class="project-credit">© 2026 Microbial Metallomics. A project associated with <a href="https://microbiomemedicine.com/">Microbiome Medicine</a> and <a href="https://www.wikibiome.com/">Wikibiome.com</a>.</p>'
cat_hash=hashlib.sha256((ROOT/'assets/data/articles.json').read_bytes()).hexdigest()[:12]
for p in ROOT.rglob('*.html'):
 if 'node_modules' in p.parts or any(part.startswith('.') for part in p.relative_to(ROOT).parts):continue
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
# Preserve the original search records; update their author/category context and append new pages.
p=ROOT/'search-index.json';index=json.loads(p.read_text());byurl={r['url']:r for r in index}
articles=json.loads((ROOT/'assets/data/articles.json').read_text())
for r in articles:
 if r['url'] in byurl:byurl[r['url']].update({'kind':r['kind'],'title':r['title'],'desc':r['description']+' '+' '.join(r['authors'])+' '+' '.join(r['topics'])})
for p in [*ROOT.glob('*.html'), *(ROOT/'metals').glob('*.html')]:
 if p.name in ['404.html','index.html']:continue
 route='/'+p.relative_to(ROOT).with_suffix('').as_posix();s=p.read_text();title=re.search(r'<h1[^>]*>(.*?)</h1>',s,re.S);desc=re.search(r'<meta name="description" content="([^"]*)"',s)
 if not title:continue
 record={'kind':'Element profile' if route.startswith('/metals/') else ('Guide' if p.stem in ['start-here','evidence-guide','methods','editorial','about','projects'] else 'Section'),'title':html.unescape(re.sub('<[^>]+>','',title.group(1))),'url':route,'desc':html.unescape(desc.group(1)) if desc else ''}
 if route in byurl:byurl[route].update(record)
 else:index.append(record);byurl[route]=record
# Search includes element symbols, enzymes, organisms, and grouped lanthanide names.
metals_path=ROOT/'assets/data/metals.json'
if metals_path.exists():
 for r in json.loads(metals_path.read_text()):
  if r['url'] in byurl:
   byurl[r['url']]['desc']=' '.join([r['symbol'],r['role'],r['summary']['text'],*r['tags'],*[m['name']+' '+m['symbol'] for m in r.get('members',[])]])
(ROOT/'search-index.json').write_text(json.dumps(index,ensure_ascii=False)+'\n')
# Sitemap: all public pages with stable canonical URLs, excluding device-local reading list.
from xml.sax.saxutils import escape
urls=[]
for p in ROOT.rglob('*.html'):
 if 'node_modules' in p.parts or any(part.startswith('.') for part in p.relative_to(ROOT).parts) or p.name in ['404.html','reading-list.html']:continue
 s=p.read_text();match=re.search(r'<link rel="canonical" href="([^"]+)"',s)
 if match and match.group(1).startswith(ORIGIN):urls.append(html.unescape(match.group(1)))
(ROOT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join('<url><loc>'+escape(u)+'</loc></url>\n' for u in sorted(set(urls)))+'</urlset>\n')
p=ROOT/'reading-list.html';s=p.read_text();s=re.sub(r'<meta name="robots" content="[^"]*">','<meta name="robots" content="noindex,follow">',s);p.write_text(s)
print('Integrated navigation, profiles, tool assets, content feeds, metadata, and',len(index),'search entries.')
