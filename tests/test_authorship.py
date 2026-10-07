"""Authorship must survive rebuilds without appropriating cited research."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from authorship import refresh_page, SCRIPT, attrs, nodes, types, ARTICLE_TYPES, Tags

AUTHORS = {p['name']: p for p in json.loads((ROOT / 'assets/data/people.json').read_text()) if p.get('siteAuthor')}


class Authorship(unittest.TestCase):
    def test_page_author_changes_but_cited_author_and_collection_survive(self):
        article = {'@type': 'Article', 'author': {'@type': 'Organization', 'name': 'Microbial Metallomics'},
                   'citation': {'@type': 'ScholarlyArticle', 'author': {'@type': 'Person', 'name': 'Source Researcher'}},
                   'isPartOf': {'@type': 'CollectionPage', '@id': 'https://microbialmetallomics.com/host-metal-defense'}}
        source = '<head><link href="https://microbialmetallomics.com/example" rel="canonical">' + \
                 '<meta content="Microbial Metallomics" name="author">' + \
                 '<script type="application/ld+json">' + json.dumps(article) + '</script></head>' + \
                 '<main><p>By <b>Microbial Metallomics</b></p><ol class="references"><li>Source Researcher. Results.</li></ol></main>'
        output = refresh_page(source, AUTHORS)
        result = json.loads(next(SCRIPT.finditer(output))[2])
        self.assertEqual(result['author']['name'], 'Karen Pendergrass')
        self.assertEqual(result['citation'], article['citation'])
        self.assertEqual(result['isPartOf']['@id'], article['isPartOf']['@id'])
        self.assertIn('<ol class="references"><li>Source Researcher. Results.</li></ol>', output)
        self.assertEqual(output, refresh_page(output, AUTHORS))

    def test_coauthor_order_agrees_across_schema_and_exports(self):
        source = (ROOT / 'research/melanin-metal-parkinsons-redheads.html').read_text()
        output = refresh_page(source, AUTHORS)
        scripts = {attrs(m[1]).get('id', attrs(m[1]).get('type')): json.loads(m[2])
                   for m in SCRIPT.finditer(output) if attrs(m[1]).get('type') in ['application/ld+json', 'application/json']}
        article = next(n for n in nodes(scripts['application/ld+json']) if 'ScholarlyArticle' in types(n))
        expected = ['Kimberly Eyer', 'Karen Pendergrass']
        self.assertEqual([a['name'] for a in article['author']], expected)
        self.assertEqual(scripts['page-citation-data']['authors'], expected)

    def test_profile_subject_is_distinct_from_page_author(self):
        source = (ROOT / 'people/amy-c-rosenzweig.html').read_text()
        output = refresh_page(source, AUTHORS)
        page = next(n for m in SCRIPT.finditer(output) if attrs(m[1]).get('type') == 'application/ld+json'
                    for n in nodes(json.loads(m[2])) if n.get('@type') == 'WebPage' and 'about' in n)
        self.assertEqual(page['about']['name'], 'Amy C. Rosenzweig')
        self.assertEqual(page['author']['name'], 'Karen Pendergrass')

    def test_every_published_page_has_verified_research_identity(self):
        for path in ROOT.rglob('*.html'):
            if any(p.startswith('.') or p == 'node_modules' for p in path.relative_to(ROOT).parts):
                continue
            with self.subTest(page=str(path.relative_to(ROOT))):
                source = path.read_text()
                tags = Tags(source.split('</head>')[0]).tags
                meta = {a.get('name', a.get('property')): a.get('content') for t, a in tags if t == 'meta'}
                self.assertIn('Karen Pendergrass', meta['author'])
                identity = [json.loads(m[2]) for m in SCRIPT.finditer(source) if attrs(m[1]).get('id') == 'site-identity']
                self.assertEqual(len(identity), 1)
                person = identity[0]['@graph'][0]
                self.assertEqual(person['identifier']['value'], '0000-0002-2348-7259')
                self.assertIn('https://orcid.org/0000-0002-2348-7259', person['sameAs'])
                self.assertTrue({'Microbial metallomics', 'Heavy metals', 'Microbiome'}.issubset(person['knowsAbout']))
                for match in SCRIPT.finditer(source):
                    if attrs(match[1]).get('type') != 'application/ld+json':
                        continue
                    for article in nodes(json.loads(match[2])):
                        if not ARTICLE_TYPES.intersection(types(article)):
                            continue
                        authors = article['author'] if isinstance(article['author'], list) else [article['author']]
                        self.assertTrue(all(a['@type'] == 'Person' for a in authors))
                        self.assertEqual(article['publisher']['name'], 'Microbial Metallomics')


if __name__ == '__main__':
    unittest.main()
