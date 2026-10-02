"""Release must remain closed when required work is missing or audits are stale."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import hashlib
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from check_host_series import run, audit_errors, release_scope, EXPECTED


class HostSeriesGateTests(unittest.TestCase):
    def test_missing_work_cannot_be_zero_fail_release(self):
        with tempfile.TemporaryDirectory() as folder:
            result = run(Path(folder), Path(folder))
        self.assertEqual(result['status'], 'blocked')
        self.assertGreater(result['pendingCount'], 0)
        self.assertEqual(result['gates']['independentAudit'], 'pending')
        self.assertEqual(result['gates']['deployment'], 'pending')

    def test_passing_audit_for_old_content_is_rejected(self):
        audit = dict(sourceHash='old', status='pass', openIssues=[], sourceChecks=['a', 'b', 'c'], checkedAreas=['chemistry', 'claim-source-match', 'model-to-human', 'counterevidence'], reviewer='Independent reviewer', summary='Sources checked')
        self.assertIn('Independent audit is stale or for different content', audit_errors(audit, 'new'))
        self.assertEqual(audit_errors(audit, 'old'), [])

    def test_self_reported_pass_without_evidence_is_rejected(self):
        self.assertGreater(len(audit_errors({'sourceHash': 'a', 'status': 'pass'}, 'a')), 0)

    def test_explicit_task_blocker_cannot_disappear_as_missing_work(self):
        slug = next(iter(EXPECTED))
        with tempfile.TemporaryDirectory() as folder:
            result = run(Path(folder), Path(folder), {'blockedArticles': {slug: 'Task could not complete'}})
        self.assertEqual(result['status'], 'blocked')
        self.assertEqual(result['articles'][0]['status'], 'blocked')
        self.assertEqual(result['failureCount'], 1)
        self.assertEqual(result['failures'][0]['detail'], 'Task could not complete')

    def test_site_changes_invalidate_old_verification(self):
        old = {'status': 'pass', 'contentHash': hashlib.sha256(b'').hexdigest(), 'buildHash': 'old'}
        with tempfile.TemporaryDirectory() as folder, patch('check_host_series.build_digest', return_value='changed'):
            result = run(Path(folder), Path(folder), {'siteChecks': old})
        self.assertEqual(result['gates']['siteChecks'], 'failed')
        self.assertTrue(any('stale for this site build' in f['detail'] for f in result['failures']))

    def test_release_scope_must_account_for_every_campaign_article(self):
        slugs = list(EXPECTED)
        for manifest in [dict(id='release-one', articles=slugs[:8], excluded=[]),
                         dict(id='release-one', articles=slugs, excluded=slugs[:1]),
                         dict(id='release-one', articles=[], excluded=slugs)]:
            with self.assertRaises(ValueError): release_scope(manifest)

    def test_excluded_work_stays_visible_without_passing_or_blocking_selected_work(self):
        slugs = list(EXPECTED)
        manifest = dict(id='release-one', articles=slugs[:8], excluded=slugs[8:])
        with tempfile.TemporaryDirectory() as folder:
            report = run(Path(folder), Path(folder), {'blockedArticles': {slugs[8]: 'Task remains blocked'}}, release=manifest)
        self.assertEqual(len(report['articles']), 8)
        self.assertEqual(len(report['excluded']), 3)
        self.assertEqual(report['excluded'][0]['reason'], 'Task remains blocked')
        self.assertEqual(report['excluded'][0]['status'], 'outside-release')
        self.assertEqual(report['failureCount'], 0)
        self.assertEqual(report['status'], 'blocked')  # Missing selected work is still pending.
        self.assertEqual(report['releaseId'], 'release-one')

    def test_receipt_cannot_be_reused_for_different_release_scope(self):
        manifest = dict(id='release-one', articles=list(EXPECTED), excluded=[])
        receipt = dict(status='pass', contentHash=hashlib.sha256(b'').hexdigest(), buildHash='same', scopeHash='other-scope')
        with tempfile.TemporaryDirectory() as folder, patch('check_host_series.build_digest', return_value='same'):
            report = run(Path(folder), Path(folder), {'siteChecks': receipt}, release=manifest)
        self.assertTrue(any('different release scope' in f['detail'] for f in report['failures']))


if __name__ == '__main__': unittest.main()
