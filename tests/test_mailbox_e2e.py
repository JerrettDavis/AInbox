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

    def _run(self, cwd: Path, agent_id: str, *args: str, input_text: str | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "ainbox.cli", *args],
            cwd=cwd,
            env=self._env(agent_id),
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
        )

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


if __name__ == "__main__":
    unittest.main()
