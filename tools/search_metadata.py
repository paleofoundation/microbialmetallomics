"""Apply editorial search snippets and canonical researcher identities after builds."""
from html.parser import HTMLParser
from html import escape
from urllib.parse import urlsplit
import json,re

ORIGIN='https://microbialmetallomics.com'
class HeadTags(HTMLParser):
 def __init__(self,overrides):
  super().__init__(convert_charrefs=False);self.overrides=overrides;self.out=[]
 def handle_starttag(self,t,attrs):
  raw=self.get_starttag_text();a=dict(attrs);key=a.get('name',a.get('property',''))
  value=None
  if t=='meta' and key in ['description','og:description','twitter:description']:value=self.overrides.get('description')
  if t=='meta' and key in ['og:title','twitter:title']:value=self.overrides.get('title')
  if value is not None:
   raw=re.sub(r'''\bcontent\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+)''',lambda m:'content="'+escape(value,quote=True)+'"',raw,count=1)
  self.out.append(raw)
 def handle_startendtag(self,t,attrs):self.handle_starttag(t,attrs)
 def handle_endtag(self,t):self.out.append('</'+t+'>')
 def handle_data(self,t):self.out.append(t)
 def handle_entityref(self,t):self.out.append('&'+t+';')
 def handle_charref(self,t):self.out.append('&#'+t+';')
 def handle_comment(self,t):self.out.append('<!--'+t+'-->')
 def handle_decl(self,t):self.out.append('<!'+t+'>')

def refresh_search_metadata(root):
 overrides=json.loads((root/'assets/data/search-pages.json').read_text())
 authors={ORIGIN+'/people/'+r['slug']:r for r in json.loads((root/'assets/data/people.json').read_text()) if r.get('siteAuthor')}
 for p in root.rglob('*.html'):
  if any(x.startswith('.') or x=='node_modules' for x in p.relative_to(root).parts):continue
  route='/' if p.name=='index.html' else '/'+p.relative_to(root).with_suffix('').as_posix()
  config=overrides.get(route,{});old=p.read_text();s=old
  if config:
   head,body=s.split('</head>',1);parser=HeadTags(config);parser.feed(head);head=''.join(parser.out)
   head=re.sub(r'<title>.*?</title>','<title>'+escape(config['title'])+'</title>',head,flags=re.S)
   s=head+'</head>'+body
  def schema(match):
   data=json.loads(match.group(1));changed=False
   def visit(node):
    nonlocal changed
    if isinstance(node,dict):
     typ=node.get('@type');types=typ if isinstance(typ,list) else [typ]
     if 'Person' in types and isinstance(node.get('url'),str):
      u=urlsplit(node['url'])
      if u.netloc=='microbialmetallomics.com' and u.path=='/people' and u.fragment and (root/'people'/(u.fragment+'.html')).is_file():node['url']=ORIGIN+'/people/'+u.fragment;changed=True
      author=authors.get(node['url'])
      if author:
       person_id=node['url']+'#person'
       if node.get('@id')!=person_id:node['@id']=person_id;changed=True
       if author.get('identityLinks'):
        same_as=list(dict.fromkeys([author['source'],*[x['url'] for x in author['identityLinks']],*(['https://orcid.org/'+author['orcid']] if author.get('orcid') else [])]))
        if node.get('sameAs')!=same_as:node['sameAs']=same_as;changed=True
     if config and any(t in ['WebPage','CollectionPage','WebSite'] for t in types):
      identity=node.get('url',node.get('@id',ORIGIN+route))
      if isinstance(identity,str) and identity.split('#')[0].rstrip('/')==(ORIGIN+route).rstrip('/'):
       if node.get('description')!=config['description']:node['description']=config['description'];changed=True
       if node.get('name')!=config['title']:node['name']=config['title'];changed=True
     for val in node.values():visit(val)
    elif isinstance(node,list):
     for v in node:visit(v)
   visit(data)
   return '<script type="application/ld+json">'+json.dumps(data,ensure_ascii=False)+'</script>' if changed else match.group(0)
  s=re.sub(r'<script\b[^>]*\btype="application/ld\+json"[^>]*>(.*?)</script>',schema,s,flags=re.S)
  if s!=old:p.write_text(s)
