import importlib.util
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "release_prepare.py"
SPEC = importlib.util.spec_from_file_location("release_prepare", MODULE_PATH)
release_prepare = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = release_prepare
SPEC.loader.exec_module(release_prepare)


class ReleasePrepareTests(unittest.TestCase):
    def test_classify_commit(self):
        self.assertEqual(
            "minor",
            release_prepare.classify_commit("feat(cli): add release command", ""),
        )
        self.assertEqual(
            "patch",
            release_prepare.classify_commit("fix: handle missing config", ""),
        )
        self.assertEqual(
            "major",
            release_prepare.classify_commit("feat!: change protocol", ""),
        )
        self.assertEqual(
            "major",
            release_prepare.classify_commit("refactor: update API", "BREAKING CHANGE: old clients fail"),
        )
        self.assertIsNone(
            release_prepare.classify_commit("docs: update README", ""),
        )

    def test_calculate_next_version(self):
        self.assertEqual(
            "0.1.0",
            release_prepare.calculate_next_version("0.1.0", "minor", None),
        )
        self.assertEqual(
            "1.3.0",
            release_prepare.calculate_next_version("1.2.3", "minor", "v1.2.3"),
        )
        self.assertEqual(
            "1.2.4",
            release_prepare.calculate_next_version("1.2.3", "patch", "v1.2.3"),
        )
        self.assertEqual(
            "2.0.0",
            release_prepare.calculate_next_version("1.2.3", "major", "v1.2.3"),
        )

    def test_parse_log_records_handles_empty_commit_body(self):
        raw = "abc123\x1ffix: handle empty bodies\x1f\x1e"
        commits = release_prepare.parse_log_records(raw)

        self.assertEqual(1, len(commits))
        self.assertEqual("abc123", commits[0].sha)
        self.assertEqual("fix: handle empty bodies", commits[0].subject)
        self.assertEqual("", commits[0].body)
        self.assertEqual("patch", commits[0].release_type)


if __name__ == "__main__":
    unittest.main()
