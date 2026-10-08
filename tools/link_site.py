#!/usr/bin/env python3
"""Render restrained, crawlable contextual links from the site's entity registry.

Runs after content generators. Never edits citations, headings, existing links,
code, or shared navigation. Generated links are rebuilt deterministically.
"""
from pathlib import Path
from html.parser import HTMLParser
from html import escape
from urllib.parse import urlsplit
import json,re

ORIGIN='https://microbialmetallomics.com'
VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
SKIP_TAGS={'a','head','script','style','nav','header','footer','aside','button','code','pre','cite','h1','h2','h3','h4','h5','h6','sup'}
SKIP_CLASSES={'references','refs','ref-list','reference-list','impact-sources','citation-panel','citation','related-module','atlas-related','connected-reading','person-links','person-topics','atlas-tags','article-tools','share-row','breadcrumb','journal-latest','profile-editorial'}
SKIP_IDS={'references','sources','directory-notes'}
AUTO_LINK=re.compile(r'<a\b[^>]*\bdata-context-link="true"[^>]*>(.*?)</a>',re.S)
AUTO_RELATED=re.compile(r'<!-- connected-reading:start -->.*?<!-- connected-reading:end -->\s*',re.S)

class ContextLinks(HTMLParser):
 def __init__(self,route,entities,legacy,max_links=14):
  super().__init__(convert_charrefs=False)
  self.route=route;self.legacy=legacy;self.stack=[];self.out=[];self.used=set();self.added=[];self.upgraded=0;self.max_links=max_links;self.in_block=0
  self.targets={a.casefold():e['url'] for e in entities for a in e['terms']}
  terms=sorted(self.targets,key=len,reverse=True)
  self.pattern=re.compile(r'(?<![\w])(?:'+'|'.join(re.escape(a) for a in terms)+r')(?![\w])',re.I) if terms else None
 def eligible(self):
  return any(t=='main' for t,a in self.stack) and any(t in {'p','li','dd','td'} for t,a in self.stack) and not any(t in SKIP_TAGS or set(a.get('class','').split())&SKIP_CLASSES or 'data-no-context-link' in a or a.get('id','') in SKIP_IDS or a.get('id','').startswith('ref-') for t,a in self.stack)
 def normalize(self,href):
  parsed=urlsplit(href)
  if parsed.scheme=='https' and parsed.netloc=='microbialmetallomics.com':href=parsed.path or '/';href+=('?' + parsed.query if parsed.query else '')+('#' + parsed.fragment if parsed.fragment else '')
  if href in self.legacy:
   target=self.legacy[href]
   # A profile's Back to the directory link intentionally retains its anchor.
   if href.startswith('/people#') and self.route in ['/people',target]:return href
   self.upgraded+=1
   return target
  return href
 def handle_starttag(self,tag,attrs):
  a=dict(attrs);raw=self.get_starttag_text()
  if tag=='a' and 'href' in a:
   href=self.normalize(a['href'])
   if href!=a['href']:
    raw=re.sub(r'''\bhref\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+)''',lambda m:'href="'+escape(href,quote=True)+'"',raw,count=1,flags=re.S)
   if self.eligible() and href.startswith('/') and not href.startswith('//'):self.used.add(href.split('#')[0])
  if tag in {'p','li','dd','td'}:self.in_block=0
  self.out.append(raw)
  if tag not in VOID:self.stack.append((tag,a))
 def handle_startendtag(self,tag,attrs):self.out.append(self.get_starttag_text())
 def handle_endtag(self,tag):
  self.out.append('</'+tag+'>')
  for n in range(len(self.stack)-1,-1,-1):
   if self.stack[n][0]==tag:self.stack=self.stack[:n];break
 def handle_data(self,text):
  if not self.eligible() or not self.pattern or len(self.added)>=self.max_links or self.in_block>=3:self.out.append(text);return
  start=0;parts=[];last_end=-100
  for m in self.pattern.finditer(text):
   target=self.targets[m.group().casefold()];base=target.split('#')[0]
   if base==self.route or base in self.used or len(self.added)>=self.max_links or self.in_block>=3 or m.start()-last_end<18:continue
   parts.extend([text[start:m.start()],'<a href="'+escape(target,quote=True)+'" data-context-link="true">'+m.group()+'</a>'])
   start=m.end();last_end=m.end();self.in_block+=1;self.used.add(base);self.added.append({'target':target,'anchor':m.group()})
  parts.append(text[start:]);self.out.append(''.join(parts))
 def handle_entityref(self,name):self.out.append('&'+name+';')
 def handle_charref(self,name):self.out.append('&#'+name+';')
 def handle_comment(self,data):self.out.append('<!--'+data+'-->')
 def handle_decl(self,decl):self.out.append('<!'+decl+'>')
 def handle_pi(self,data):self.out.append('<?'+data+'>')

def render_links(text,route,entities,legacy):
 parser=ContextLinks(route,entities,legacy);parser.feed(AUTO_LINK.sub(r'\1',text));parser.close()
 return ''.join(parser.out),parser

def registry(root):
 data=json.loads((root/'assets/data/internal-links.json').read_text())
 entities=list(data['concepts']);legacy={}
 for metal in json.loads((root/'assets/data/metals.json').read_text()):
  url=metal['url'];name=metal['name'];terms=[name]
  if name=='Lead':terms=['lead exposure','lead contamination','lead toxicity','lead concentrations','lead concentration','blood lead','lead levels','lead poisoning','lead (Pb)','lead-containing']
  if name=='Aluminum':terms+=['aluminium']
  entities.append({'url':url,'terms':terms})
  legacy['/metals#'+metal['symbol'].lower()]=url
  for member in metal.get('members',[]):entities.append({'url':url,'terms':[member['name']]})
 for person in json.loads((root/'assets/data/people.json').read_text()):
  url='/people/'+person['slug'];legacy['/people#'+person['slug']]=url
  entities.append({'url':url,'terms':[person['name']]})
 for p in (root/'glossary').glob('*.html'):legacy['/glossary#'+p.stem]='/glossary/'+p.stem
 for e in entities:
  assert e['terms'] and (root/(e['url'].split('#')[0].lstrip('/')+'.html')).is_file(),e
 return data,entities,legacy

def reading_block(items):
 def cards(rows):
  return '<div class="connected-reading-grid">'+''.join('<a href="'+escape(r['url'],quote=True)+'"><strong>'+escape(r['title'])+'</strong><span>'+escape(r['description'])+'</span></a>' for r in rows)+'</div>'
 more='<details class="reading-more"><summary>More related reading</summary>'+cards(items[3:])+'</details>' if len(items)>3 else ''
 return '<!-- connected-reading:start --><section class="connected-reading" aria-label="Related reading"><h2>Follow the connections</h2>'+cards(items[:3])+more+'</section><!-- connected-reading:end -->\n'

def refresh_links(root):
 data,entities,legacy=registry(root);report=[]
 for p in sorted(root.rglob('*.html')):
  if any(x.startswith('.') or x=='node_modules' for x in p.relative_to(root).parts) or p.name in ['404.html','reading-list.html']:continue
  route='/' if p.name=='index.html' else '/'+p.relative_to(root).with_suffix('').as_posix()
  old=p.read_text();source=AUTO_RELATED.sub('',old)
  result,parser=render_links(source,route,entities,legacy)
  related=data['related'].get(route,[])
  if related:
   for item in related:assert (root/(item['url'].split('#')[0].lstrip('/')+'.html')).is_file(),item
   block=reading_block(related)
   match=re.search(r'<section\b(?=[^>]*\bid="references")[^>]*>',result)
   if match:result=result[:match.start()]+block+result[match.start():]
   else:result=result.replace('</main>',block.replace('<!-- connected-reading:start -->','<!-- connected-reading:start --><div class="wrap">').replace('<!-- connected-reading:end -->','</div><!-- connected-reading:end -->')+'</main>',1)
  if result!=old:p.write_text(result)
  report.append({'url':route,'contextualLinks':parser.added,'upgradedLinks':parser.upgraded,'relatedLinks':len(related)})
 summary={'pages':len(report),'contextualLinks':sum(len(x['contextualLinks']) for x in report),'pagesWithContextualLinks':sum(bool(x['contextualLinks']) for x in report),'legacyLinksUpgraded':sum(x['upgradedLinks'] for x in report),'curatedRelatedLinks':sum(x['relatedLinks'] for x in report)}
 print('Internal links:',json.dumps(summary))
 return summary,report

if __name__=='__main__':refresh_links(Path(__file__).resolve().parents[1])
