import json
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def extract_version(relative_path: str, pattern: str) -> str:
    content = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
    match = re.search(pattern, content, re.MULTILINE)
    if not match:
        raise AssertionError(f"Could not find version in {relative_path}")
    return match.group(1)


class VersionMetadataTests(unittest.TestCase):
    def test_version_sources_are_consistent(self):
        expected = extract_version("Cargo.toml", r'^version\s*=\s*"([^"]+)"')
        self.assertEqual(
            expected,
            extract_version("ainbox/__init__.py", r'^__version__\s*=\s*"([^"]+)"'),
        )

    def test_plugin_versions_match_release_version(self):
        expected = extract_version("Cargo.toml", r'^version\s*=\s*"([^"]+)"')

        json_checks = [
            (".claude-plugin/plugin.json", lambda data: [data["version"]]),
            (".github/plugin/plugin.json", lambda data: [data["version"]]),
            (
                ".claude-plugin/marketplace.json",
                lambda data: [data["metadata"]["version"]]
                + [plugin["version"] for plugin in data["plugins"]],
            ),
            (
                ".github/plugin/marketplace.json",
                lambda data: [data["metadata"]["version"]]
                + [plugin["version"] for plugin in data["plugins"]],
            ),
        ]

        for relative_path, extract_versions in json_checks:
            with self.subTest(path=relative_path):
                data = json.loads((REPO_ROOT / relative_path).read_text(encoding="utf-8"))
                self.assertEqual({expected}, set(extract_versions(data)))

    def test_setup_reads_version_from_python_package(self):
        setup_py = (REPO_ROOT / "setup.py").read_text(encoding="utf-8")
        self.assertIn("version=read_version()", setup_py)
        self.assertNotIn('version="0.1.0"', setup_py)


if __name__ == "__main__":
    unittest.main()
