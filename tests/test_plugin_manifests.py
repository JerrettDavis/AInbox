import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class PluginManifestTests(unittest.TestCase):
    def _load_json(self, relative_path: str):
        with open(REPO_ROOT / relative_path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def test_marketplace_manifests_consistent(self):
        """Test that both marketplace files have the same plugin structure."""
        claude_marketplace = self._load_json(".claude-plugin/marketplace.json")
        copilot_marketplace = self._load_json(".github/plugin/marketplace.json")
        
        # Both should have 3 plugins with same names
        self.assertEqual(len(claude_marketplace["plugins"]), 3)
        self.assertEqual(len(copilot_marketplace["plugins"]), 3)
        
        claude_names = sorted([p["name"] for p in claude_marketplace["plugins"]])
        copilot_names = sorted([p["name"] for p in copilot_marketplace["plugins"]])
        self.assertEqual(claude_names, copilot_names)

    def test_plugin_manifests_match(self):
        claude_plugin = self._load_json(".claude-plugin/plugin.json")
        copilot_plugin = self._load_json(".github/plugin/plugin.json")
        self.assertEqual(claude_plugin, copilot_plugin)

    def test_marketplace_entry_points_to_valid_plugin_root(self):
        marketplace = self._load_json(".claude-plugin/marketplace.json")
        plugin = self._load_json(".claude-plugin/plugin.json")

        self.assertEqual(marketplace["name"], "ainbox-marketplace")
        # Now we expect 3 plugins: ainbox, agent-poll, elections
        self.assertEqual(len(marketplace["plugins"]), 3)

        # Verify ainbox plugin
        ainbox_entry = next((p for p in marketplace["plugins"] if p["name"] == "ainbox"), None)
        self.assertIsNotNone(ainbox_entry)
        self.assertEqual(ainbox_entry["name"], plugin["name"])
        self.assertEqual(ainbox_entry["source"], "./")

        commands_path = (REPO_ROOT / plugin["commands"]).resolve()
        skills_path = (REPO_ROOT / plugin["skills"]).resolve()
        self.assertTrue(commands_path.is_dir(), plugin["commands"])
        self.assertTrue(skills_path.is_dir(), plugin["skills"])
        
        # Verify new plugins exist in marketplace
        plugin_names = {p["name"] for p in marketplace["plugins"]}
        self.assertIn("agent-poll", plugin_names)
        self.assertIn("elections", plugin_names)

    def test_plugin_components_exist(self):
        for relative_path in [
            ".claude/commands/mailbox-read.md",
            ".claude/commands/mailbox-send.md",
            ".claude/commands/mailbox-sync.md",
            "skills/mailbox-basics/SKILL.md",
            "skills/mailbox-communication/SKILL.md",
            "skills/mailbox-inbox-processing/SKILL.md",
        ]:
            self.assertTrue((REPO_ROOT / relative_path).is_file(), relative_path)


if __name__ == "__main__":
    unittest.main()
