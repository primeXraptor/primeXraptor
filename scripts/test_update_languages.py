import unittest
from collections import Counter
from xml.etree import ElementTree

from update_languages import collect, render


class LanguageCardTests(unittest.TestCase):
    def test_pagination_private_totals_and_fork_exclusion(self):
        def repo(name, private=False, fork=False):
            return {"owner": {"login": "primeXraptor"}, "full_name": name,
                    "private": private, "fork": fork}

        responses = {
            "/user": {"login": "primeXraptor"},
            "/user/repos?affiliation=owner&visibility=all&per_page=100&page=1": [repo("primeXraptor/public"), repo("primeXraptor/fork", fork=True)],
            "/user/repos?affiliation=owner&visibility=all&per_page=100&page=2": [repo("primeXraptor/private", private=True)],
            "/user/repos?affiliation=owner&visibility=all&per_page=100&page=3": [],
            "/repos/primeXraptor/public/languages": {"Python": 100},
            "/repos/primeXraptor/private/languages": {"Python": 200, "JavaScript": 100},
        }
        self.assertEqual(collect("primeXraptor", "test", lambda path, token: responses[path]),
                         Counter({"Python": 300, "JavaScript": 100}))

    def test_rejects_public_only_access(self):
        with self.assertRaisesRegex(RuntimeError, "No owned private"):
            collect("primeXraptor", "test", lambda path, token: {"login": "primeXraptor"} if path == "/user" else [])

    def test_rejects_wrong_account(self):
        with self.assertRaisesRegex(RuntimeError, "profile owner"):
            collect("primeXraptor", "test", lambda path, token: {"login": "someone-else"})

    def test_svg_percentages_escaping_and_other(self):
        totals = Counter({"A&B": 70, "B": 10, "C": 5, "D": 5, "E": 4, "F": 3, "G": 2, "H": 1})
        svg = render(totals, "2026-11-01 18:00")
        ElementTree.fromstring(svg)
        self.assertIn("A&amp;B 70.00%", svg)
        self.assertIn("Other 3.00%", svg)
        self.assertIn("2026-11-01 18:00", svg)


if __name__ == "__main__":
    unittest.main()
