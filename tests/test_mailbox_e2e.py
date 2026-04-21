import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class MailboxCliE2ETests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.home = self.root / "home"
        self.agent_a = self.root / "agent-a"
        self.agent_b = self.root / "agent-b"
        self.home.mkdir(parents=True, exist_ok=True)
        self.agent_a.mkdir(parents=True, exist_ok=True)
        self.agent_b.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _env(self, agent_id: str) -> dict:
        env = os.environ.copy()
        env["MAILBOX_AGENT_ID"] = agent_id
        env["MAILBOX_SHARED"] = str(self.home / "shared-root")
        env["PYTHONUTF8"] = "1"
        existing_pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(REPO_ROOT) if not existing_pythonpath else f"{REPO_ROOT}{os.pathsep}{existing_pythonpath}"
        if os.name == "nt":
            env["USERPROFILE"] = str(self.home)
        else:
            env["HOME"] = str(self.home)
        return env

    def _run(self, cwd: Path, agent_id: str, *args: str, input_text: str | None = None, extra_env: dict | None = None) -> subprocess.CompletedProcess:
        env = self._env(agent_id)
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [sys.executable, "-m", "ainbox.cli", *args],
            cwd=cwd,
            env=env,
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
        )

    def _create_fake_agent_cli(self, name: str, bin_dir: Path) -> Path:
        if os.name == "nt":
            wrapper = bin_dir / f"{name}-fake.cmd"
            wrapper.write_text(
                (
                    "@echo off\r\n"
                    "setlocal\r\n"
                    f'>> "%MAILBOX_GLOBAL_INIT_LOG%" echo {name} %*\r\n'
                    'if /I "%1 %2 %3 %4"=="plugin marketplace update ainbox-marketplace" exit /b 1\r\n'
                    'if /I "%1 %2"=="plugin update" exit /b 1\r\n'
                    "exit /b 0\r\n"
                ),
                encoding="utf-8",
            )
        else:
            wrapper = bin_dir / f"{name}-fake"
            wrapper.write_text(
                (
                    "#!/bin/sh\n"
                    f'printf "%s %s\\n" "{name}" "$*" >> "$MAILBOX_GLOBAL_INIT_LOG"\n'
                    'if [ "$1 $2 $3 $4" = "plugin marketplace update ainbox-marketplace" ]; then exit 1; fi\n'
                    'if [ "$1 $2" = "plugin update" ]; then exit 1; fi\n'
                    "exit 0\n"
                ),
                encoding="utf-8",
            )
            wrapper.chmod(0o755)
        return wrapper

    def test_send_sync_read_round_trip(self):
        init_a = self._run(self.agent_a, "worker-agent", "init")
        init_b = self._run(self.agent_b, "reviewer-agent", "init")
        self.assertEqual(init_a.returncode, 0, init_a.stderr)
        self.assertEqual(init_b.returncode, 0, init_b.stderr)

        send = self._run(
            self.agent_a,
            "worker-agent",
            "send",
            "--to",
            "reviewer-agent",
            "--subject",
            "PR ready",
            input_text="Please review the parser hardening.\n\nThanks.\n",
        )
        self.assertEqual(send.returncode, 0, send.stderr)
        self.assertIn("Message created:", send.stdout)

        push = self._run(self.agent_a, "worker-agent", "sync", "--push-only")
        self.assertEqual(push.returncode, 0, push.stderr)
        self.assertIn("1 pushed", push.stdout)

        shared_outbox = self.home / "shared-root" / "shared" / "outbox"
        self.assertEqual(len(list(shared_outbox.glob("*.md"))), 1)

        pull = self._run(self.agent_b, "reviewer-agent", "sync", "--pull-only")
        self.assertEqual(pull.returncode, 0, pull.stderr)
        self.assertIn("1 pulled", pull.stdout)
        self.assertEqual(len(list(shared_outbox.glob("*.md"))), 0)

        listing = self._run(self.agent_b, "reviewer-agent", "list")
        self.assertEqual(listing.returncode, 0, listing.stderr)
        self.assertIn("PR ready", listing.stdout)
        self.assertIn("worker-agent", listing.stdout)

        read = self._run(self.agent_b, "reviewer-agent", "read")
        self.assertEqual(read.returncode, 0, read.stderr)
        self.assertIn("subject: PR ready", read.stdout)
        self.assertIn("Please review the parser hardening.", read.stdout)

        inbox = self.agent_b / ".mailbox" / "inbox"
        archive = self.agent_b / ".mailbox" / "archive"
        self.assertEqual(len(list(inbox.glob("*.md"))), 0)
        self.assertEqual(len(list(archive.glob("*.md"))), 1)

    def test_init_installs_project_mailbox_memory_once(self):
        first = self._run(self.agent_a, "worker-agent", "init")
        second = self._run(self.agent_a, "worker-agent", "init")
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)

        claude_mailbox = self.agent_a / ".claude" / "MAILBOX.md"
        agents_mailbox = self.agent_a / ".agents" / "MAILBOX.md"
        self.assertTrue(claude_mailbox.is_file())
        self.assertTrue(agents_mailbox.is_file())
        self.assertIn("Use AInbox as the durable coordination layer.", claude_mailbox.read_text(encoding="utf-8"))
        self.assertIn("Use `.mailbox/draft/` as living memory", agents_mailbox.read_text(encoding="utf-8"))

        claude_instructions = (self.agent_a / "CLAUDE.md").read_text(encoding="utf-8")
        agents_instructions = (self.agent_a / "AGENTS.md").read_text(encoding="utf-8")
        self.assertTrue(claude_instructions.startswith("@.claude/MAILBOX.md"))
        self.assertTrue(agents_instructions.startswith("@.agents/MAILBOX.md"))
        self.assertEqual(claude_instructions.count("@.claude/MAILBOX.md"), 1)
        self.assertEqual(agents_instructions.count("@.agents/MAILBOX.md"), 1)

    def test_read_by_correlation_id(self):
        self._run(self.agent_a, "worker-agent", "init")
        self._run(self.agent_b, "reviewer-agent", "init")

        send = self._run(
            self.agent_a,
            "worker-agent",
            "send",
            "--to",
            "reviewer-agent",
            "--subject",
            "Threaded update",
            "--correlation-id",
            "task-123",
            "--body",
            "Status update in thread",
        )
        self.assertEqual(send.returncode, 0, send.stderr)

        self.assertEqual(self._run(self.agent_a, "worker-agent", "sync").returncode, 0)
        self.assertEqual(self._run(self.agent_b, "reviewer-agent", "sync", "--pull-only").returncode, 0)

        read = self._run(self.agent_b, "reviewer-agent", "read", "--correlation-id", "task-123")
        self.assertEqual(read.returncode, 0, read.stderr)
        self.assertIn("correlation_id: task-123", read.stdout)
        self.assertIn("Threaded update", read.stdout)

    def test_expired_message_routes_to_dlq_on_push(self):
        dlq_agent = self.root / "dlq-agent"
        dlq_agent.mkdir(parents=True, exist_ok=True)
        self.assertEqual(self._run(self.agent_a, "worker-agent", "init").returncode, 0)
        self.assertEqual(self._run(self.agent_b, "reviewer-agent", "init").returncode, 0)
        self.assertEqual(self._run(dlq_agent, "dlq", "init").returncode, 0)

        send = self._run(
            self.agent_a,
            "worker-agent",
            "send",
            "--to",
            "reviewer-agent",
            "--subject",
            "Expiring task",
            "--body",
            "This should go to the dlq.",
            "--expires-at",
            "2000-01-01T00:00:00Z",
        )
        self.assertEqual(send.returncode, 0, send.stderr)

        push = self._run(self.agent_a, "worker-agent", "sync", "--push-only")
        self.assertEqual(push.returncode, 0, push.stderr)
        self.assertIn("0 pushed", push.stdout)

        review_pull = self._run(self.agent_b, "reviewer-agent", "sync", "--pull-only")
        self.assertEqual(review_pull.returncode, 0, review_pull.stderr)
        self.assertIn("0 pulled", review_pull.stdout)

        dlq_pull = self._run(dlq_agent, "dlq", "sync", "--pull-only")
        self.assertEqual(dlq_pull.returncode, 0, dlq_pull.stderr)
        self.assertIn("1 pulled", dlq_pull.stdout)

        dlq_read = self._run(dlq_agent, "dlq", "read")
        self.assertEqual(dlq_read.returncode, 0, dlq_read.stderr)
        self.assertIn("message_type: expired", dlq_read.stdout)
        self.assertIn("original_subject: Expiring task", dlq_read.stdout)
        self.assertIn("This should go to the dlq.", dlq_read.stdout)

    def test_expired_inbox_message_routes_to_dlq_before_listing(self):
        dlq_agent = self.root / "dlq-agent"
        dlq_agent.mkdir(parents=True, exist_ok=True)
        self.assertEqual(self._run(self.agent_a, "worker-agent", "init").returncode, 0)
        self.assertEqual(self._run(self.agent_b, "reviewer-agent", "init").returncode, 0)
        self.assertEqual(self._run(dlq_agent, "dlq", "init").returncode, 0)

        send = self._run(
            self.agent_a,
            "worker-agent",
            "send",
            "--to",
            "reviewer-agent",
            "--subject",
            "Soon stale",
            "--body",
            "This expires after delivery.",
            "--expires-at",
            "2099-01-01T00:00:00Z",
        )
        self.assertEqual(send.returncode, 0, send.stderr)
        self.assertEqual(self._run(self.agent_a, "worker-agent", "sync", "--push-only").returncode, 0)
        self.assertEqual(self._run(self.agent_b, "reviewer-agent", "sync", "--pull-only").returncode, 0)

        inbox_file = next((self.agent_b / ".mailbox" / "inbox").glob("*.md"))
        content = inbox_file.read_text(encoding="utf-8")
        inbox_file.write_text(
            content.replace("2099-01-01T00:00:00Z", "2000-01-01T00:00:00Z"),
            encoding="utf-8",
        )

        listing = self._run(self.agent_b, "reviewer-agent", "list")
        self.assertEqual(listing.returncode, 0, listing.stderr)
        self.assertIn("No messages in inbox", listing.stdout)

        dlq_pull = self._run(dlq_agent, "dlq", "sync", "--pull-only")
        self.assertEqual(dlq_pull.returncode, 0, dlq_pull.stderr)
        self.assertIn("1 pulled", dlq_pull.stdout)

    def test_conflicting_sync_flags_fail(self):
        self._run(self.agent_a, "worker-agent", "init")
        result = self._run(self.agent_a, "worker-agent", "sync", "--push-only", "--pull-only")
        self.assertEqual(result.returncode, 2)
        self.assertIn("mutually exclusive", result.stderr)

    def test_create_poll_notifies_participants(self):
        self.assertEqual(self._run(self.agent_a, "worker-agent", "init").returncode, 0)
        self.assertEqual(self._run(self.agent_b, "reviewer-agent", "init").returncode, 0)

        create = self._run(
            self.agent_a,
            "worker-agent",
            "create-poll",
            "--question",
            "What database should we use?",
            "--option",
            '["MSSQL","PostgreSQL","MySQL"]',
            "--participant",
            "reviewer-agent",
        )
        self.assertEqual(create.returncode, 0, create.stderr)
        self.assertIn("Participants notified: 1", create.stdout)

        pull = self._run(self.agent_b, "reviewer-agent", "sync", "--pull-only")
        self.assertEqual(pull.returncode, 0, pull.stderr)
        self.assertIn("1 pulled", pull.stdout)

        listing = self._run(self.agent_b, "reviewer-agent", "list")
        self.assertEqual(listing.returncode, 0, listing.stderr)
        self.assertIn("Poll open:", listing.stdout)
        self.assertIn("What database should we use?", listing.stdout)

    def test_motion_gate_notifies_and_waits_for_acceptance(self):
        self.assertEqual(self._run(self.agent_a, "worker-agent", "init").returncode, 0)
        self.assertEqual(self._run(self.agent_b, "reviewer-agent", "init").returncode, 0)

        created = self._run(
            self.agent_a,
            "worker-agent",
            "create-motion",
            "--title",
            "Pause and report",
            "--participant",
            "worker-agent",
            "--participant",
            "reviewer-agent",
            "--description",
            "Stop current work and report status before proceeding.",
            "--scope",
            "cluster",
            "--format",
            "json",
        )
        self.assertEqual(created.returncode, 0, created.stderr)
        motion = json.loads(created.stdout)
        motion_id = motion["id"]

        pull = self._run(self.agent_b, "reviewer-agent", "sync", "--pull-only")
        self.assertEqual(pull.returncode, 0, pull.stderr)
        listing = self._run(self.agent_b, "reviewer-agent", "list")
        self.assertIn("Motion open: Pause and report", listing.stdout)

        first_vote = self._run(self.agent_a, "worker-agent", "vote-motion", "--id", motion_id, "--vote", "yes")
        self.assertEqual(first_vote.returncode, 0, first_vote.stderr)
        wait_open = self._run(
            self.agent_a,
            "worker-agent",
            "wait-motion",
            "--id",
            motion_id,
            "--timeout-seconds",
            "0.2",
            "--poll-interval-seconds",
            "0.1",
        )
        self.assertEqual(wait_open.returncode, 5)

        second_vote = self._run(
            self.agent_b,
            "reviewer-agent",
            "vote-motion",
            "--id",
            motion_id,
            "--vote",
            "yes",
            "--reason",
            "Status collected",
        )
        self.assertEqual(second_vote.returncode, 0, second_vote.stderr)

        wait_done = self._run(self.agent_a, "worker-agent", "wait-motion", "--id", motion_id, "--format", "json")
        self.assertEqual(wait_done.returncode, 0, wait_done.stderr)
        resolved = json.loads(wait_done.stdout)
        self.assertEqual(resolved["motion"]["status"], "accepted")
        self.assertEqual(resolved["votes"]["votes"]["yes"], 2)

    def test_init_global_bootstraps_supported_agent_integrations(self):
        bin_dir = self.root / "fake-bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        log_path = self.root / "global-init.log"
        log_path.write_text("", encoding="utf-8")
        claude_bin = self._create_fake_agent_cli("claude", bin_dir)
        copilot_bin = self._create_fake_agent_cli("copilot", bin_dir)

        extra_env = {
            "MAILBOX_GLOBAL_INIT_LOG": str(log_path),
            "MAILBOX_CLAUDE_BIN": str(claude_bin),
            "MAILBOX_COPILOT_BIN": str(copilot_bin),
        }
        result = self._run(self.agent_a, "worker-agent", "init", "-g", extra_env=extra_env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Initialized mailbox at", result.stdout)
        self.assertIn("Global agent integration:", result.stdout)
        self.assertIn("Claude Code: marketplace added;", result.stdout)
        self.assertIn("GitHub Copilot CLI: marketplace added;", result.stdout)

        calls = log_path.read_text(encoding="utf-8").splitlines()
        self.assertIn("claude plugin marketplace update ainbox-marketplace", calls)
        self.assertIn("claude plugin marketplace add JerrettDavis/AInbox", calls)
        self.assertIn("claude plugin install ainbox@ainbox-marketplace", calls)
        self.assertIn("copilot plugin marketplace update ainbox-marketplace", calls)
        self.assertIn("copilot plugin install elections@ainbox-marketplace", calls)

        mailbox_root = self.agent_a / ".mailbox"
        self.assertTrue((mailbox_root / "inbox").is_dir())
        self.assertTrue((self.agent_a / ".claude" / "MAILBOX.md").is_file())
        self.assertTrue((self.agent_a / ".agents" / "MAILBOX.md").is_file())
        self.assertEqual((self.agent_a / "CLAUDE.md").read_text(encoding="utf-8").count("@.claude/MAILBOX.md"), 1)
        self.assertEqual((self.agent_a / "AGENTS.md").read_text(encoding="utf-8").count("@.agents/MAILBOX.md"), 1)
        self.assertTrue((self.home / ".claude" / "MAILBOX.md").is_file())
        self.assertTrue((self.home / ".agents" / "MAILBOX.md").is_file())
        self.assertEqual((self.home / ".claude" / "CLAUDE.md").read_text(encoding="utf-8").count("@MAILBOX.md"), 1)
        self.assertEqual((self.home / ".agents" / "AGENTS.md").read_text(encoding="utf-8").count("@MAILBOX.md"), 1)


if __name__ == "__main__":
    unittest.main()
