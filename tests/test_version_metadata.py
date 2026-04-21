import json
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SEMVER_PATTERN = r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$"


def extract_version(relative_path: str, pattern: str) -> str:
    content = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
    match = re.search(pattern, content, re.MULTILINE)
    if not match:
        raise AssertionError(f"Could not find version in {relative_path}")
    return match.group(1)


class VersionMetadataTests(unittest.TestCase):
    def _all_versioned_plugin_json_files(self):
        files = {
            REPO_ROOT / ".claude-plugin" / "plugin.json",
            REPO_ROOT / ".claude-plugin" / "marketplace.json",
            REPO_ROOT / ".github" / "plugin" / "plugin.json",
            REPO_ROOT / ".github" / "plugin" / "marketplace.json",
        }
        files.update(REPO_ROOT.glob("plugins/*/.claude-plugin/plugin.json"))
        return sorted(files)

    def _extract_json_versions(self, path: Path):
        data = json.loads(path.read_text(encoding="utf-8"))
        versions = []
        if isinstance(data, dict) and "version" in data:
            versions.append(data["version"])
        if isinstance(data, dict) and "metadata" in data and "version" in data["metadata"]:
            versions.append(data["metadata"]["version"])
        if isinstance(data, dict):
            for plugin in data.get("plugins", []):
                if "version" in plugin:
                    versions.append(plugin["version"])
        return versions

    def test_version_sources_are_consistent(self):
        expected = extract_version("Cargo.toml", r'^version\s*=\s*"([^"]+)"')
        self.assertRegex(expected, SEMVER_PATTERN)
        self.assertEqual(
            expected,
            extract_version("ainbox/__init__.py", r'^__version__\s*=\s*"([^"]+)"'),
        )
        self.assertEqual(
            expected,
            extract_version("Cargo.lock", r'\[\[package\]\]\s+name = "ainbox"\s+version = "([^"]+)"'),
        )

    def test_plugin_versions_match_release_version(self):
        expected = extract_version("Cargo.toml", r'^version\s*=\s*"([^"]+)"')

        for path in self._all_versioned_plugin_json_files():
            with self.subTest(path=path.relative_to(REPO_ROOT)):
                versions = self._extract_json_versions(path)
                self.assertTrue(versions, f"No versions found in {path}")
                self.assertEqual({expected}, set(versions))
                for version in versions:
                    self.assertRegex(version, SEMVER_PATTERN)

    def test_setup_reads_version_from_python_package(self):
        setup_py = (REPO_ROOT / "setup.py").read_text(encoding="utf-8")
        self.assertIn("version=read_version()", setup_py)
        self.assertNotIn('version="0.1.0"', setup_py)


if __name__ == "__main__":
    unittest.main()
