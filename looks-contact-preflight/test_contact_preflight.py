import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from contact_preflight import audit


class ContactPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def page(self, route, body):
        path = self.root / route.strip('/') / 'index.html'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('<html><main>' + body + '</main></html>', encoding='utf-8')

    def test_policy_cycle_has_no_reachable_mailbox(self):
        self.page('/en/about/', '<a href="/en/legal/terms/">Contact</a>')
        self.page('/en/legal/terms/', '<a href="/en/about/">Contact</a>')
        report = audit(self.root, ['/en/about/', '/en/legal/terms/'])
        self.assertFalse(report['ok'])
        self.assertEqual(report['pages'][0]['visited'], ['/en/about/', '/en/legal/terms/'])
        self.assertIsNone(report['pages'][0]['contact'])

    def test_internal_relative_link_reaches_mailbox(self):
        self.page('/en/about/', '<a href="../contact/?via=about#email">Contact</a>')
        self.page('/en/contact/', '<a href="mailto:editor@example.org?subject=Correction">Email</a>')
        report = audit(self.root, ['/en/about/', '/en/contact/'])
        self.assertTrue(report['ok'])
        self.assertEqual(report['pages'][0]['path'], ['/en/about/', '/en/contact/'])
        self.assertEqual(report['pages'][0]['contact'], 'editor@example.org')

    def test_external_lookalike_is_not_followed(self):
        self.page('/en/about/', '<a href="https://looksmaxxing.guide.evil.test/en/contact/">Contact</a>')
        self.page('/en/contact/', '<a href="mailto:editor@example.org">Email</a>')
        self.assertFalse(audit(self.root, ['/en/about/', '/en/contact/'])['ok'])

    def test_footer_and_hidden_addresses_cannot_satisfy_contact_path(self):
        self.page('/en/about/', '<footer><a href="mailto:footer@example.org">Footer</a></footer><div hidden><a href="mailto:hidden@example.org">Hidden</a></div><template><a href="mailto:template@example.org">Template</a></template>')
        self.assertFalse(audit(self.root, ['/en/about/'])['ok'])

    def test_hidden_void_element_does_not_hide_following_visible_link(self):
        self.page('/en/about/', '<input hidden><a href="MAILTO:editor@example.org">Email</a>')
        self.assertTrue(audit(self.root, ['/en/about/'])['ok'])

    def test_fragment_only_links_and_invalid_email_fail(self):
        self.page('/en/about/', '<a href="#contact">Contact</a><a href="mailto:not-an-email">Email</a>')
        self.assertFalse(audit(self.root, ['/en/about/'])['ok'])

    def test_form_is_manual_review_not_claimed_working(self):
        self.page('/en/about/', '<form action="/contact"><input name="message"></form>')
        report = audit(self.root, ['/en/about/'])
        self.assertFalse(report['ok'])
        self.assertTrue(report['pages'][0]['form_present'])

    def test_missing_file_is_input_error(self):
        with self.assertRaises(ValueError):
            audit(self.root, ['/en/missing/'])

    def test_traversal_route_is_rejected(self):
        with self.assertRaises(ValueError):
            audit(self.root, ['/../outside/'])

    def test_symlink_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as external:
            Path(external, 'index.html').write_text('<main>outside</main>')
            (self.root / 'outside').symlink_to(external, target_is_directory=True)
            with self.assertRaises(ValueError):
                audit(self.root, ['/outside/'])

    def test_missing_main_is_input_error(self):
        path = self.root / 'index.html'
        path.write_text('<footer><a href="mailto:editor@example.org">Email</a></footer>')
        with self.assertRaises(ValueError):
            audit(self.root, ['/'])

    def test_cli_exit_codes_and_json(self):
        script = Path(__file__).with_name('contact_preflight.py')
        self.page('/en/about/', '<a href="/en/about/">Contact</a>')
        args = [sys.executable, str(script), str(self.root), '--page', '/en/about/']
        bad = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(bad.returncode, 1)
        self.assertFalse(json.loads(bad.stdout)['ok'])
        self.page('/en/about/', '<a href="mailto:editor@example.org">Email</a>')
        good = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(good.returncode, 0)
        self.assertTrue(json.loads(good.stdout)['ok'])
        missing = subprocess.run(args[:-1] + ['/missing/'], capture_output=True, text=True)
        self.assertEqual(missing.returncode, 2)
        self.assertIn('error', json.loads(missing.stdout))


if __name__ == '__main__':
    unittest.main()
