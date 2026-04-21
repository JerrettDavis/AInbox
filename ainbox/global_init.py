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
    summaries: list[str] = []

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
