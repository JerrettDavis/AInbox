"""Global agent integration bootstrap."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess


@dataclass(frozen=True)
class AgentIntegration:
    name: str
    executable: str
    marketplace_source: str
    marketplace_name: str
    plugins: tuple[str, ...]


SUPPORTED_INTEGRATIONS = (
    AgentIntegration(
        name="Claude Code",
        executable="claude",
        marketplace_source="JerrettDavis/AInbox",
        marketplace_name="ainbox-marketplace",
        plugins=(
            "ainbox@ainbox-marketplace",
            "agent-poll@ainbox-marketplace",
            "elections@ainbox-marketplace",
        ),
    ),
    AgentIntegration(
        name="GitHub Copilot CLI",
        executable="copilot",
        marketplace_source="JerrettDavis/AInbox",
        marketplace_name="ainbox-marketplace",
        plugins=(
            "ainbox@ainbox-marketplace",
            "agent-poll@ainbox-marketplace",
            "elections@ainbox-marketplace",
        ),
    ),
)

MAILBOX_MEMORY_TEXT = """# MAILBOX.md

Use AInbox as the durable coordination layer.

- Preserve or set `MAILBOX_AGENT_ID` explicitly.
- Use `.mailbox/draft/` as living memory for active threads.
- Sync before reading and after sending important updates.
- Use `mailbox send`, `list`, `read`, and `sync` for durable coordination.
- Reuse `--correlation-id` for related conversations.
- Use polls or elections when the group needs a durable decision or role assignment.
"""


def _run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        text=True,
        capture_output=True,
        check=False,
    )


def _resolved_executable(agent: AgentIntegration) -> str:
    override_name = f"MAILBOX_{agent.executable.upper()}_BIN"
    return os.environ.get(override_name, agent.executable)


def _command_exists(command: str) -> bool:
    path = Path(command)
    if path.is_absolute() or path.parent != Path():
        return path.is_file()
    return shutil.which(command) is not None


def _ensure_include_file(path: Path, include_line: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(f"{include_line}\n", encoding="utf-8")
        return True

    content = path.read_text(encoding="utf-8")
    if include_line in content:
        return False

    path.write_text(f"{include_line}\n\n{content}", encoding="utf-8")
    return True


def _ensure_mailbox_file(path: Path) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return False
    path.write_text(MAILBOX_MEMORY_TEXT.rstrip() + "\n", encoding="utf-8")
    return True


def _ensure_memory_install(root: Path, mailbox_rel: Path, include_target: Path, include_line: str, label: str) -> str:
    mailbox_created = _ensure_mailbox_file(root / mailbox_rel)
    include_updated = _ensure_include_file(root / include_target, include_line)
    actions = []
    if mailbox_created:
        actions.append(f"created {mailbox_rel}")
    if include_updated:
        actions.append(f"updated {include_target}")
    if not actions:
        actions.append("already configured")
    return f"{label}: " + ", ".join(actions)


def ensure_project_memory_files(root: Path | None = None) -> list[str]:
    project_root = (root or Path.cwd()).resolve()
    return [
        _ensure_memory_install(
            project_root,
            Path(".claude/MAILBOX.md"),
            Path("CLAUDE.md"),
            "@.claude/MAILBOX.md",
            "Claude Code project memory",
        ),
        _ensure_memory_install(
            project_root,
            Path(".agents/MAILBOX.md"),
            Path("AGENTS.md"),
            "@.agents/MAILBOX.md",
            "AGENTS project memory",
        ),
    ]


def ensure_user_memory_files() -> list[str]:
    home_root = Path.home()
    return [
        _ensure_memory_install(
            home_root,
            Path(".claude/MAILBOX.md"),
            Path(".claude/CLAUDE.md"),
            "@MAILBOX.md",
            "Claude Code user memory",
        ),
        _ensure_memory_install(
            home_root,
            Path(".agents/MAILBOX.md"),
            Path(".agents/AGENTS.md"),
            "@MAILBOX.md",
            "AGENTS user memory",
        ),
    ]


def _ensure_marketplace(agent: AgentIntegration) -> str:
    executable = _resolved_executable(agent)
    update = _run_command(
        [executable, "plugin", "marketplace", "update", agent.marketplace_name]
    )
    if update.returncode == 0:
        return "updated"

    add = _run_command(
        [executable, "plugin", "marketplace", "add", agent.marketplace_source]
    )
    if add.returncode == 0:
        return "added"

    raise RuntimeError(
        f"{agent.name}: failed to update or add marketplace {agent.marketplace_name}\n"
        f"update stderr: {update.stderr.strip()}\n"
        f"add stderr: {add.stderr.strip()}"
    )


def _ensure_plugin(agent: AgentIntegration, plugin: str) -> str:
    executable = _resolved_executable(agent)
    update = _run_command([executable, "plugin", "update", plugin])
    if update.returncode == 0:
        return "updated"

    install = _run_command([executable, "plugin", "install", plugin])
    if install.returncode == 0:
        return "installed"

    raise RuntimeError(
        f"{agent.name}: failed to update or install plugin {plugin}\n"
        f"update stderr: {update.stderr.strip()}\n"
        f"install stderr: {install.stderr.strip()}"
    )


def ensure_global_integrations() -> list[str]:
    """Install or update supported agent integrations."""
    summaries: list[str] = ensure_user_memory_files()

    for agent in SUPPORTED_INTEGRATIONS:
        executable = _resolved_executable(agent)
        if not _command_exists(executable):
            summaries.append(f"{agent.name}: skipped ({agent.executable} not found)")
            continue

        marketplace_status = _ensure_marketplace(agent)
        plugin_summaries = []
        for plugin in agent.plugins:
            plugin_summaries.append(f"{plugin} { _ensure_plugin(agent, plugin) }")

        summaries.append(
            f"{agent.name}: marketplace {marketplace_status}; "
            + ", ".join(plugin_summaries)
        )

    return summaries
