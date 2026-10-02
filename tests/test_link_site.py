"""Regression cases for site-wide linking that must preserve scientific prose."""
import sys,tempfile,unittest,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from link_site import render_links,refresh_links
ENTITIES=[{'terms':['nickel'],'url':'/metals/nickel'},{'terms':['zinc'],'url':'/metals/zinc'},{'terms':['metallostasis'],'url':'/glossary/metallostasis'},{'terms':['lead exposure'],'url':'/metals/lead'}]
LEGACY={'/metals#ni':'/metals/nickel','/people#test':'/people/test'}
class Links(unittest.TestCase):
 def render(self,s,route='/science'):return render_links(s,route,ENTITIES,LEGACY)[0]
 def test_body_links_preserve_entities_and_emphasis(self):
  src='<main><p>Nickel &amp; <em>zinc</em> &#8212; chemistry.</p></main>'
  out=self.render(src)
  self.assertIn('href="/metals/nickel"',out);self.assertIn('<em><a href="/metals/zinc"',out)
  self.assertIn('&amp;',out);self.assertIn('&#8212;',out);self.assertEqual(out,self.render(out))
 def test_reference_and_publication_titles_are_untouched(self):
  src='<main><h1>Nickel</h1><p><cite>Bacterial Metallostasis</cite></p><section id="references"><li>Nickel paper</li></section><script>nickel</script><p data-no-context-link>nickel</p></main>'
  self.assertEqual(src,self.render(src))
 def test_existing_links_not_nested_and_same_page_not_linked(self):
  src='<main><p><a href="/metals/zinc">Zinc</a> supports enzymes. More zinc and nickel.</p></main>'
  out=self.render(src,'/metals/nickel');self.assertEqual(src,out)
 def test_repeated_entities_link_once(self):
  out=self.render('<main><p>Nickel matters.</p><p>Nickel again.</p></main>')
  self.assertEqual(out.count('data-context-link'),1)
 def test_ambiguous_lead_verb_not_linked(self):
  out=self.render('<main><p>Findings lead to questions about lead exposure.</p></main>')
  self.assertIn('Findings lead to',out);self.assertIn('>lead exposure</a>',out)
 def test_legacy_quoted_unquoted_and_profile_return(self):
  out=self.render('<main><p><a href=/metals#ni>Nickel</a></p></main>')
  self.assertIn('href="/metals/nickel"',out)
  src='<main><a href="/people#test">Back to the directory</a></main>'
  self.assertEqual(src,self.render(src,'/people/test'))
 def test_exact_origin_only(self):
  src='<main><a href="https://microbialmetallomics.com.example.org/path">External</a></main>'
  self.assertEqual(src,self.render(src))
  self.assertIn('href="/metals/nickel"',self.render('<main><a href="https://microbialmetallomics.com/metals#ni">Nickel</a></main>'))
 def test_related_fallback_is_idempotent(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'assets/data').mkdir(parents=True);(root/'glossary').mkdir()
   (root/'assets/data/metals.json').write_text('[]');(root/'assets/data/people.json').write_text('[]')
   (root/'assets/data/internal-links.json').write_text(json.dumps({'concepts':[],'related':{'/hub':[{'url':'/topic','title':'Topic','description':'Context'}]}}))
   (root/'hub.html').write_text('<main><p>A hub.</p></main>');(root/'topic.html').write_text('<main><p>A topic.</p></main>')
   refresh_links(root);before=(root/'hub.html').read_text();refresh_links(root)
   self.assertEqual(before,(root/'hub.html').read_text());self.assertEqual(before.count('class="wrap"'),1)
if __name__=='__main__':unittest.main()
