"""Parity tests: channel server's mailbox-CLI integration assumptions.

These don't run the channel server itself (that requires Bun and is covered
by the bun:test suites). Instead they verify the Python `mailbox` CLI's
contract that the channel relies on:

- `mailbox send --to ... --subject ... --body ...` writes a parseable .md
  file under `.mailbox/outbox/`.
- `mailbox list --format json` emits a JSON array with the fields the
  channel surfaces in tool output.
- The channel/server.ts file references the expected flag set.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_mailbox(args, *, cwd, env_overrides=None):
    env = os.environ.copy()
    env["MAILBOX_AGENT_ID"] = env.get("MAILBOX_AGENT_ID", "channel-parity-agent")
    env["MAILBOX_SHARED"] = env.get("MAILBOX_SHARED", str(Path(cwd) / "_shared"))
    existing_pythonpath = env.get("PYTHONPATH", "")
    parts = [str(REPO_ROOT)]
    if existing_pythonpath:
        parts.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(parts)
    if env_overrides:
        env.update(env_overrides)
    cmd = [sys.executable, "-m", "ainbox.cli", *args]
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


class ChannelParityTests(unittest.TestCase):
    def test_send_produces_parseable_outbox_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = _run_mailbox(
                [
                    "send",
                    "--to",
                    "reviewer-agent",
                    "--subject",
                    "Channel parity test",
                    "--body",
                    "hello from parity",
                    "--correlation-id",
                    "thread-parity",
                ],
                cwd=tmp,
            )
            self.assertEqual(
                result.returncode,
                0,
                f"send failed: stdout={result.stdout!r} stderr={result.stderr!r}",
            )
            outbox = Path(tmp) / ".mailbox" / "outbox"
            self.assertTrue(outbox.is_dir(), "outbox folder created")
            md_files = list(outbox.glob("*.md"))
            self.assertEqual(len(md_files), 1)
            content = md_files[0].read_text(encoding="utf-8")
            # Frontmatter delimiters and required fields
            self.assertTrue(content.startswith("---"))
            for field in ("id:", "to: reviewer-agent", "subject: Channel parity test", "sent_at:"):
                self.assertIn(field, content, field)
            self.assertIn("correlation_id: thread-parity", content)
            self.assertIn("hello from parity", content)

    def test_list_json_returns_expected_shape(self):
        """Verify `mailbox list --format json` returns the field shape the channel surfaces."""
        with tempfile.TemporaryDirectory() as tmp:
            inbox = Path(tmp) / ".mailbox" / "inbox"
            inbox.mkdir(parents=True, exist_ok=True)
            msg = (inbox / "20260430T120000Z_paritymsg.md")
            msg.write_text(
                "---\n"
                "id: paritymsg\n"
                "to: channel-parity-agent\n"
                "from: peer-agent\n"
                "subject: shape check\n"
                "sent_at: 2026-04-30T12:00:00Z\n"
                "received_at: 2026-04-30T12:00:01Z\n"
                "read_at: null\n"
                "correlation_id: thread-shape\n"
                "---\n"
                "\n"
                "body content\n",
                encoding="utf-8",
            )
            listed = _run_mailbox(["list", "--limit", "5", "--format", "json"], cwd=tmp)
            self.assertEqual(listed.returncode, 0, listed.stderr)
            stdout = listed.stdout.strip()
            self.assertNotEqual(stdout, "No messages in inbox", listed.stdout)
            data = json.loads(stdout)
            self.assertIsInstance(data, list)
            self.assertGreaterEqual(len(data), 1)
            entry = data[0]
            for key in ("id", "from", "subject", "sent_at", "to", "correlation_id"):
                self.assertIn(key, entry, key)
            self.assertEqual(entry["id"], "paritymsg")
            self.assertEqual(entry["from"], "peer-agent")
            self.assertEqual(entry["correlation_id"], "thread-shape")

    def test_channel_server_uses_known_mailbox_flags(self):
        """Sanity-check that channel/server.ts only emits flags the CLI supports."""
        server_ts = (REPO_ROOT / "channel" / "server.ts").read_text(encoding="utf-8")
        # The flag set we expect to see emitted somewhere:
        expected = [
            "send",
            "--to",
            "--subject",
            "--body",
            "--correlation-id",
            "sync",
            "--push-only",
            "read",
            "--id",
            "list",
            "--limit",
            "--format",
            "json",
        ]
        for token in expected:
            self.assertIn(token, server_ts, f"server.ts should reference: {token!r}")

    def test_mcp_json_protected_from_drift(self):
        """The .mcp.json shape should match the documented contract."""
        with open(REPO_ROOT / ".mcp.json", "r", encoding="utf-8") as f:
            mcp = json.load(f)
        self.assertEqual(list(mcp["mcpServers"].keys()), ["ainbox"])
        ainbox = mcp["mcpServers"]["ainbox"]
        self.assertEqual(ainbox["command"], "bun")
        # Must be a bare relative path so it works in both dev mode (cwd = repo
        # root) and after plugin install (claude sets cwd to plugin root).
        self.assertEqual(ainbox["args"], ["channel/server.ts"])
        self.assertFalse(
            any("${" in arg for arg in ainbox["args"]),
            "args must not contain shell variable expansions like ${CLAUDE_PLUGIN_ROOT}",
        )


if __name__ == "__main__":
    unittest.main()
