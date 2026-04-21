import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class PluginManifestTests(unittest.TestCase):
    def _load_json(self, relative_path: str):
        with open(REPO_ROOT / relative_path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def test_marketplace_manifests_consistent(self):
        """Test that both marketplace files describe the same plugins."""
        claude_marketplace = self._load_json(".claude-plugin/marketplace.json")
        copilot_marketplace = self._load_json(".github/plugin/marketplace.json")
        self.assertEqual(claude_marketplace["name"], copilot_marketplace["name"])
        self.assertEqual(claude_marketplace["owner"], copilot_marketplace["owner"])
        self.assertEqual(claude_marketplace["metadata"], copilot_marketplace["metadata"])

        claude_entries = {entry["name"]: entry for entry in claude_marketplace["plugins"]}
        copilot_entries = {entry["name"]: entry for entry in copilot_marketplace["plugins"]}

        self.assertEqual(set(claude_entries), set(copilot_entries))
        self.assertEqual(claude_entries["ainbox"], copilot_entries["ainbox"])

        for name in ["agent-poll", "elections"]:
            self.assertEqual(claude_entries[name]["name"], copilot_entries[name]["name"])
            self.assertEqual(claude_entries[name]["description"], copilot_entries[name]["description"])
            self.assertEqual(claude_entries[name]["version"], copilot_entries[name]["version"])
            self.assertEqual(claude_entries[name]["author"], copilot_entries[name]["author"])
            self.assertEqual(claude_entries[name]["homepage"], copilot_entries[name]["homepage"])
            self.assertEqual(claude_entries[name]["repository"], copilot_entries[name]["repository"])
            self.assertEqual(claude_entries[name]["keywords"], copilot_entries[name]["keywords"])
            self.assertEqual(claude_entries[name]["source"], f"./plugins/{name}")
            self.assertEqual(copilot_entries[name]["source"], name)

    def test_plugin_manifests_match(self):
        claude_plugin = self._load_json(".claude-plugin/plugin.json")
        copilot_plugin = self._load_json(".github/plugin/plugin.json")
        self.assertEqual(claude_plugin["name"], copilot_plugin["name"])
        self.assertEqual(claude_plugin["version"], copilot_plugin["version"])
        self.assertEqual(claude_plugin["description"], copilot_plugin["description"])
        self.assertEqual(claude_plugin["author"], copilot_plugin["author"])
        self.assertEqual(claude_plugin["homepage"], copilot_plugin["homepage"])
        self.assertEqual(claude_plugin["repository"], copilot_plugin["repository"])
        self.assertEqual(claude_plugin["keywords"], copilot_plugin["keywords"])
        self.assertEqual(claude_plugin["commands"], copilot_plugin["commands"])
        self.assertEqual(claude_plugin["skills"], copilot_plugin["skills"])
        self.assertNotIn("agents", claude_plugin)
        self.assertEqual(copilot_plugin["agents"], "./agents")

    def test_marketplace_entry_points_to_valid_plugin_root(self):
        marketplace = self._load_json(".claude-plugin/marketplace.json")
        plugin = self._load_json(".claude-plugin/plugin.json")

        self.assertEqual(marketplace["name"], "ainbox-marketplace")
        self.assertEqual(marketplace["metadata"]["pluginRoot"], "./plugins")
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
        
        entries = {entry["name"]: entry for entry in marketplace["plugins"]}
        self.assertIn("agent-poll", entries)
        self.assertIn("elections", entries)

        for name in ["agent-poll", "elections"]:
            plugin_root = (REPO_ROOT / entries[name]["source"]).resolve()
            self.assertTrue(plugin_root.is_dir(), entries[name]["source"])
            self.assertTrue((plugin_root / ".claude-plugin" / "plugin.json").is_file())

    def test_plugin_components_exist(self):
        for relative_path in [
            "agents/orchestrator.agent.md",
            "agents/project-manager.agent.md",
            ".claude/commands/mailbox-read.md",
            ".claude/commands/mailbox-send.md",
            ".claude/commands/mailbox-sync.md",
            "skills/mailbox-basics/SKILL.md",
            "skills/mailbox-communication/SKILL.md",
            "skills/mailbox-inbox-processing/SKILL.md",
            "plugins/agent-poll/commands/poll.md",
            "plugins/agent-poll/commands/vote-poll.md",
            "plugins/agent-poll/skills/agent-poll/SKILL.md",
            "plugins/elections/commands/election.md",
            "plugins/elections/commands/vote-election.md",
            "plugins/elections/skills/elections/SKILL.md",
        ]:
            self.assertTrue((REPO_ROOT / relative_path).is_file(), relative_path)

    def test_agent_files_have_required_frontmatter(self):
        for relative_path, expected_name in [
            ("agents/orchestrator.agent.md", "orchestrator"),
            ("agents/project-manager.agent.md", "project-manager"),
        ]:
            content = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
            self.assertIn(f"name: {expected_name}", content)
            self.assertIn("description:", content)


if __name__ == "__main__":
    unittest.main()
