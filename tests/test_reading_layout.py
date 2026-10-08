"""Reading changes must preserve evidence, deep links and repeatable builds."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from html_blocks import Blocks
from reading_layout import (article_layout, contents_disclosures, profile_layout,
                            remove_routine_review_dates, shared_navigation)


class ReadingLayout(unittest.TestCase):
    def test_summary_movement_preserves_citations_and_all_findings(self):
        summary = '<section id="article-summary"><p>Observed <em>in mice</em>.</p></section>'
        findings = ['<li>Finding ' + str(n) + '<sup><a id="cite-' + str(n) +
                    '" href="#ref-' + str(n) + '">[' + str(n) + ']</a></sup></li>'
                    for n in range(1, 6)]
        correction = '<p class="editorial-correction">Correction: units changed.</p>'
        source = ('<body><main><div class="hero-band"><div class="wrap"><h1>Title</h1>'
                  '<div class="share-row">Share</div></div></div><article>' + summary +
                  '<div class="takeaways"><h2>Takeaways</h2><ul>' + ''.join(findings) +
                  '</ul></div>' + correction + '<h2 id="mechanism">Mechanism</h2>'
                  '<p>The mechanism remains an inference.</p></article></main></body>')
        result = article_layout(source)
        doc = Blocks(result)
        self.assertTrue(doc.one(id='article-summary').within(doc.one(cls='hero-band')))
        self.assertLess(result.index(summary), result.index('class="share-row"'))
        self.assertEqual(result.count(correction), 1)
        for finding in findings:
            self.assertEqual(result.count(finding), 1)
        self.assertEqual(len(doc.find(tag='li', within=doc.one(cls='reading-takeaways'))), 3)
        self.assertEqual(len(doc.find(tag='li', within=doc.one(cls='reading-further-findings'))), 2)
        self.assertIn('<h2 id="mechanism">Mechanism</h2><p>The mechanism remains an inference.</p>', result)
        self.assertEqual(article_layout(result), result)

    def test_native_contents_preserve_labels_and_fragments(self):
        source = '<aside class="toc-sidebar"><h2 id="contents-heading">Contents</h2><nav aria-labelledby="contents-heading"><a href="#sources">Sources</a></nav></aside>'
        result = contents_disclosures(source)
        self.assertIn('<details class="reading-toc" open>', result)
        self.assertIn('<summary id="contents-heading">Contents</summary>', result)
        self.assertIn('<a href="#sources">Sources</a>', result)
        self.assertEqual(contents_disclosures(result), result)

    def test_navigation_ignores_attribute_order_and_keeps_following_header_content(self):
        source = '<header><nav aria-label="Primary" class="nav-links"><a href="/old">Old</a></nav><div id="mega-menu" class="mega-menu"><div>Old menu</div></div><p>Keep this</p></header>'
        nav = '<nav class="nav-links" aria-label="Primary"><a href="/metals">Metals atlas</a></nav>'
        menu = '<div class="mega-menu" id="mega-menu"><div>New menu</div></div>'
        result = shared_navigation(source, nav, menu)
        self.assertEqual(result, '<header>' + nav + menu + '<p>Keep this</p></header>')
        self.assertEqual(shared_navigation(result, nav, menu), result)

    def test_review_strip_removal_keeps_corrections_and_machine_dates(self):
        source = '<meta name="article:modified_time" content="2026-10-01"><div class="article-meta"><span class="am-item">By Author</span><span class="am-sep">·</span><span class="am-item">Updated October 1, 2026</span></div><p class="editorial-correction">Correction — October 1, 2026.</p>'
        result = remove_routine_review_dates(source)
        self.assertNotIn('Updated', result)
        self.assertIn('By Author', result)
        self.assertIn('Correction — October 1, 2026.', result)
        self.assertIn('content="2026-10-01"', result)

    def test_selected_work_follows_contribution_before_long_background(self):
        source = '<body><section id="contribution">Contribution</section><section id="significance">Significance</section><section id="frontier">Frontier</section><section id="background">Background</section><section class="person-works" id="selected-works">Sources</section></body>'
        result = profile_layout(source)
        self.assertLess(result.index('id="selected-works"'), result.index('id="frontier"'))
        self.assertEqual(profile_layout(result), result)

    def test_all_pages_share_navigation_and_crawlable_content(self):
        for path in ROOT.rglob('*.html'):
            if any(part.startswith('.') or part == 'node_modules' for part in path.relative_to(ROOT).parts):
                continue
            with self.subTest(page=str(path.relative_to(ROOT))):
                doc = Blocks(path.read_text())
                nav = doc.one(cls='nav-links')
                self.assertIsNotNone(nav)
                self.assertEqual([n.attrs.get('href') for n in doc.find(tag='a', within=nav)],
                                 ['/science', '/metals', '/topics', '/evidence', '/people'])
                self.assertEqual(len(doc.find(tag='h1')), 1)
                self.assertIsNotNone(doc.one(id='main-content'))


if __name__ == '__main__':
    unittest.main()
