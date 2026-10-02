#!/usr/bin/env python3
"""Validate crawl inventory and the internal link graph without network calls."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit
from collections import Counter,deque
from datetime import date
import xml.etree.ElementTree as ET
import json
ROOT=Path(__file__).resolve().parents[1]
ORIGIN='https://microbialmetallomics.com'
class Page(HTMLParser):
 def __init__(self,s):
  super().__init__();self.canonical='';self.noindex=False;self.links=[];self.h1=0;self.title='';self.description='';self.in_title=False;self.feed(s)
 def handle_starttag(self,t,a):
  a=dict(a)
  if t=='link' and 'canonical' in a.get('rel','').split():self.canonical=a.get('href','')
  if t=='meta':
   name=a.get('name','').lower();value=a.get('content','')
   if name in ['robots','googlebot','bingbot'] and any(x in value.lower().replace(',',' ').split() for x in ['noindex','none']):self.noindex=True
   if name=='description':self.description=value
  if t=='title':self.in_title=True
  if t=='h1':self.h1+=1
  if t=='a':self.links.append(a.get('href',''))
 def handle_endtag(self,t):
  if t=='title':self.in_title=False
 def handle_data(self,d):
  if self.in_title:self.title+=d
pages={};errors=[]
for path in ROOT.rglob('*.html'):
 if any(x.startswith('.') or x=='node_modules' for x in path.relative_to(ROOT).parts):continue
 p=Page(path.read_text())
 if p.noindex:continue
 route='/' if path.name=='index.html' else '/'+path.relative_to(ROOT).with_suffix('').as_posix()
 pages[route]=p
 if p.canonical!=ORIGIN+route:errors.append('Unexpected canonical: '+route)
 if p.h1!=1:errors.append('Expected exactly one main heading: '+route)
for field in ['title','description','canonical']:
 counts=Counter(getattr(p,field) for p in pages.values())
 for value,count in counts.items():
  if not value or count>1:errors.append('Missing/duplicate '+field+': '+value)
search_urls=[r['url'] for r in json.loads((ROOT/'search-index.json').read_text())]
if set(pages)-set(search_urls):errors.append('Public pages missing from local search')
if len(search_urls)!=len(set(search_urls)):errors.append('Duplicate local search URLs')
if '/metals#ni' in search_urls:errors.append('Local search still targets legacy nickel card')
ns={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'};tree=ET.parse(ROOT/'sitemap.xml')
urls=[x.text for x in tree.findall('.//s:loc',ns)]
expected={p.canonical for p in pages.values()}
if set(urls)!=expected:errors.append('Sitemap mismatch: missing '+str(sorted(expected-set(urls)))+' extra '+str(sorted(set(urls)-expected)))
if len(urls)!=len(set(urls)):errors.append('Duplicate sitemap URLs')
for el in tree.findall('.//s:lastmod',ns):
 try:
  if date.fromisoformat(el.text)>date.today():errors.append('Future sitemap date')
 except ValueError:errors.append('Invalid sitemap date')
graph={}
for route,p in pages.items():
 targets=set()
 for link in p.links:
  u=urlsplit(link)
  if u.netloc and u.netloc!='microbialmetallomics.com':continue
  path=u.path
  if path in pages and path!=route:targets.add(path)
 graph[route]=targets
seen={'/'};queue=deque(['/'])
while queue:
 for target in graph.get(queue.popleft(),set()):
  if target not in seen:seen.add(target);queue.append(target)
if set(pages)-seen:errors.append('Not reachable from homepage: '+str(sorted(set(pages)-seen)))
critical=pages['/blog/tampon-metals-vaginal-microbiome-blind-spot']
if '/metals/nickel' not in critical.links:errors.append('Nickel criticism lacks dedicated nickel link')
print(f'Search integrity: {len(pages)} indexable pages, {len(urls)} sitemap URLs, {len(seen)} reachable pages.')
for error in errors:print('ERROR:',error)
raise SystemExit(bool(errors))
