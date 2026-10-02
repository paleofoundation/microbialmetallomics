#!/usr/bin/env python3
"""Notify IndexNow of published canonical URLs; default is a local dry run.

Run with --submit only after verifying the production deployment. A received
submission is not a guarantee of crawling, indexing, ranking, or traffic.
"""
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlsplit
import argparse,json,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
HOST='microbialmetallomics.com';ORIGIN='https://'+HOST
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--submit',action='store_true');parser.add_argument('urls',nargs='*',help='Canonical URLs; omit to submit the current sitemap.')
args=parser.parse_args()
urls=args.urls or [el.text for el in ET.parse(ROOT/'sitemap.xml').findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
assert urls and len(urls)<=10000 and len(urls)==len(set(urls))
assert all(urlsplit(u).scheme=='https' and urlsplit(u).netloc==HOST and not urlsplit(u).fragment for u in urls)
key=(ROOT/'indexnow-verification.txt').read_text().strip();location=ORIGIN+'/indexnow-verification.txt'
if not args.submit:print(json.dumps({'mode':'dry-run','urls':len(urls),'host':HOST}));raise SystemExit()
with urlopen(location,timeout=30) as response:assert response.read().decode().strip()==key,'Published verification key differs from local file'
body=json.dumps({'host':HOST,'key':key,'keyLocation':location,'urlList':urls}).encode()
request=Request('https://api.indexnow.org/indexnow',data=body,headers={'Content-Type':'application/json; charset=utf-8'},method='POST')
with urlopen(request,timeout=40) as response:
 print(json.dumps({'status':response.status,'submitted':len(urls),'meaning':'URLs received; key validation pending' if response.status==202 else 'URLs submitted; indexing and ranking are separate'}))
