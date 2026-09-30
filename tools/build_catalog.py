"""Generate a site reading catalogue and feeds from published article metadata.

This catalogue describes this site's coverage; it is not a systematic evidence dataset.
Run after adding or updating an article: python3 tools/build_catalog.py
"""
from pathlib import Path
from html import unescape
from urllib.parse import urlsplit
from datetime import datetime, timezone
from email.utils import format_datetime
import re, json, csv, io
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = 'https://microbialmetallomics.com'
# These descriptions are explicitly stated in the existing cited reviews.
DESIGNS = {
 'iron-fortification-kenyan-infant-microbiome': ('Randomized trial','Human'),
 'iron-supplements-microbiome-reproductive-women': ('Randomized trial','Human'),
 'lactobacillus-plantarum-299v-oral-iron': ('Randomized trial','Human'),
 'prebiotic-iron-cereal-kenyan-infants': ('Randomized trial','Human'),
 'prenatal-lead-childhood-gut-microbiome': ('Observational study','Human'),
 'prenatal-metals-microbiome-child-inflammation': ('Observational study','Human'),
 'prenatal-metals-microbiome-childhood-depression': ('Observational study','Human'),
 'childhood-blood-metals-microbiome-geste': ('Observational study','Human'),
 'prenatal-acetaminophen-microbiome-cognition': ('Observational study','Human'),
 'perinatal-tobacco-child-gut-microbiota': ('Observational study','Human'),
 'arsenic-gut-ecoli-children-bangladesh': ('Observational study','Human'),
 'parkinsons-intestinal-biomarkers-nonmotor': ('Observational study','Human'),
 'crohns-multiomics-mre-bowel-damage': ('Observational study','Human'),
 'heavy-metals-obesity-pregnancy-upbeat': ('Observational study','Human'),
 'heavy-metals-gut-microbiota-systematic-review': ('Systematic review','Human studies'),
 'pediatric-gut-microbiome-health-review': ('Systematic review','Human studies'),
 'gut-microbiome-childhood-stunting-lmic': ('Systematic review','Human studies'),
 'iron-zinc-biofortified-foods-gut-microbiota': ('Systematic review','Animal studies'),
 'gallium-cystic-fibrosis-pseudomonas': ('Early-phase clinical trial','Human'),
 'wheat-iron-binding-proteome': ('Computational analysis','Plant'),
 'iron-metalloproteome-pseudomonas': ('Laboratory study','Microbial culture'),
 'arnr-4fe4s-nitric-oxide-sensing': ('Laboratory study','Molecular mechanism'),
 'spatial-metallomics-colorectal-cancer': ('Methods / proof of concept','Human tissue'),
}
METALS = ['Iron','Zinc','Copper','Nickel','Manganese','Arsenic','Cadmium','Lead','Mercury','Gallium','Cobalt','Molybdenum','Tungsten']
THEMES = {'Nutritional immunity':r'nutritional immunity|infection|immune|pathogen', 'Early life':r'infant|child|prenatal|pediatric|pregnan|baby|neonatal', 'Neurobiology':r'parkinson|neuro|brain|cognition|depression', 'Metabolic health':r'obesity|metabolic|diabetes|fatty liver', 'Environmental exposure':r'fertilizer|soil|arsenic|cadmium|lead|mercury|tobacco|exposure', 'Methods & measurement':r'spectro|metalloproteom|proteome|spatial|cofactor|biosynthesis', 'Vaginal microbiome':r'vaginal|tampon'}

def plain(value):
 return ' '.join(unescape(re.sub('<[^>]+>',' ',value or '')).split())

def build():
 records=[]
 for folder,kind in [('blog','Essay'),('library','Paper review'),('research','Original research')]:
  for file in sorted((ROOT/folder).glob('*.html')):
   source=file.read_text();match=re.search(r'<script type="application/ld\+json">(.*?)</script>',source,re.S)
   if not match:continue
   document=json.loads(match.group(1));nodes=document.get('@graph',[document])
   article=next((n for n in nodes if n.get('@type') in ['Article','BlogPosting','ScholarlyArticle']),None)
   if not article:continue
   url='/'+str(file.relative_to(ROOT).with_suffix(''));headline=article['headline'];description=article.get('description','')
   category='Critical Commentary' if 'data-article-type="commentary"' in source else kind
   names=article.get('author',{});names=names if isinstance(names,list) else [names]
   authors=[a.get('name','Microbial Metallomics') for a in names]
   status=''
   if folder=='research':
    meta=re.search(r'<div class="meta-row">(.*?)</div>',source,re.S)
    if meta:
     pills=re.findall(r'<span class="pill[^\"]*">(.*?)</span>',meta.group(1))
     status=next((plain(x) for x in pills if plain(x) in ['Preprint','Journal article','Standard','Journal']), '')
   source_url=article.get('citation') or (article.get('sameAs') if folder=='research' else '') or ''
   if not isinstance(source_url,str):source_url=''
   block=re.search(r'<div class="journal-source-link">(.*?)</div>',source,re.S)
   if block:
    href=re.search(r'href="(https?://[^"]+)"',block.group(1))
    if href:source_url=unescape(href.group(1))
   doi=article.get('identifier','') if folder=='research' else ''
   if not doi and 'doi.org/' in source_url:doi=source_url.split('doi.org/',1)[1]
   if not isinstance(doi,str):doi=''
   design,setting=DESIGNS.get(file.stem,('',''))
   topic_text=(headline+' '+description+' '+article.get('keywords','')).lower()
   topics=[m for m in METALS if re.search(r'\b'+m.lower()+r'\b',topic_text)]
   topics += [name for name,pattern in THEMES.items() if re.search(pattern,topic_text)]
   records.append(dict(title=headline,description=description,url=url,kind=category,date=article.get('datePublished',''),updated=article.get('dateModified',''),authors=authors,status=status,sourceUrl=source_url,sourceDoi=doi,studyDesign=design,setting=setting,topics=topics))
 records.sort(key=lambda x:(x['date'],x['title']),reverse=True)
 data=ROOT/'assets/data';data.mkdir(parents=True,exist_ok=True)
 (data/'articles.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
 output=io.StringIO();columns=['title','kind','date','authors','status','studyDesign','setting','topics','sourceUrl','sourceDoi','url'];writer=csv.DictWriter(output,fieldnames=columns,lineterminator="\n");writer.writeheader()
 for record in records:
  row={k:record[k] for k in columns};row['authors']='; '.join(row['authors']);row['topics']='; '.join(row['topics']);row['url']=ORIGIN+row['url'];writer.writerow(row)
 (data/'reading-catalogue.csv').write_text(output.getvalue())
 feed=ROOT/'feeds';feed.mkdir(exist_ok=True)
 for name,items in [('all',records),('commentary',[r for r in records if r['kind']=='Critical Commentary']),('reviews',[r for r in records if r['kind']=='Paper review']),('research',[r for r in records if r['kind']=='Original research'])]:
  pieces=['<?xml version="1.0" encoding="UTF-8"?><rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>', '<title>Microbial Metallomics — '+name.title()+'</title><link>'+ORIGIN+'</link><description>New writing, research summaries, and paper reviews from Microbial Metallomics.</description><language>en</language><atom:link href="'+ORIGIN+'/feeds/'+name+'.xml" rel="self" type="application/rss+xml"/>']
  for r in items:
   date=format_datetime(datetime.fromisoformat(r['date']).replace(tzinfo=timezone.utc)) if r['date'] else ''
   pieces.append('<item><title>'+escape(r['title'])+'</title><link>'+ORIGIN+r['url']+'</link><guid isPermaLink="true">'+ORIGIN+r['url']+'</guid><description>'+escape((r['status']+' — ' if r['status'] else '')+r['description'])+'</description><category>'+escape(r['kind'])+'</category>'+('<category>'+escape(r['status'])+'</category>' if r['status'] else '')+('<pubDate>'+date+'</pubDate>' if date else '')+'</item>')
  pieces.append('</channel></rss>');(feed/(name+'.xml')).write_text('\n'.join(pieces)+'\n')
 jsonfeed={'version':'https://jsonfeed.org/version/1.1','title':'Microbial Metallomics','home_page_url':ORIGIN,'feed_url':ORIGIN+'/feeds/all.json','items':[{'id':ORIGIN+r['url'],'url':ORIGIN+r['url'],'title':r['title'],'content_text':(r['status']+' — ' if r['status'] else '')+r['description'],'date_published':r['date']+'T00:00:00Z','authors':[{'name':n} for n in r['authors']],'tags':[r['kind'],*([r['status']] if r['status'] else []),*r['topics']]} for r in records]}
 (feed/'all.json').write_text(json.dumps(jsonfeed,ensure_ascii=False,indent=2)+'\n')
 print('Generated',len(records),'article records, CSV, and five feeds.')
 return records

if __name__=='__main__':build()
