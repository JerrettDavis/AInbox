use crate::util::CliResult;
use std::env;
use std::path::{Path, PathBuf};
use std::process::Command;

struct AgentIntegration {
    name: &'static str,
    executable: &'static str,
    marketplace_source: &'static str,
    marketplace_name: &'static str,
    plugins: &'static [&'static str],
}

const SUPPORTED_INTEGRATIONS: &[AgentIntegration] = &[
    AgentIntegration {
        name: "Claude Code",
        executable: "claude",
        marketplace_source: "JerrettDavis/AInbox",
        marketplace_name: "ainbox-marketplace",
        plugins: &[
            "ainbox@ainbox-marketplace",
            "agent-poll@ainbox-marketplace",
            "elections@ainbox-marketplace",
        ],
    },
    AgentIntegration {
        name: "GitHub Copilot CLI",
        executable: "copilot",
        marketplace_source: "JerrettDavis/AInbox",
        marketplace_name: "ainbox-marketplace",
        plugins: &[
            "ainbox@ainbox-marketplace",
            "agent-poll@ainbox-marketplace",
            "elections@ainbox-marketplace",
        ],
    },
];

pub fn ensure_global_integrations() -> CliResult<Vec<String>> {
    let mut summaries = Vec::new();

    for agent in SUPPORTED_INTEGRATIONS {
        let executable = resolved_executable(agent);
        if !command_exists(&executable) {
            summaries.push(format!(
                "{}: skipped ({} not found)",
                agent.name, agent.executable
            ));
            continue;
        }

        let marketplace_status = ensure_marketplace(agent, &executable)?;
        let mut plugin_summaries = Vec::new();
        for plugin in agent.plugins {
            plugin_summaries.push(format!(
                "{plugin} {}",
                ensure_plugin(agent, &executable, plugin)?
            ));
        }

        summaries.push(format!(
            "{}: marketplace {}; {}",
            agent.name,
            marketplace_status,
            plugin_summaries.join(", ")
        ));
    }

    Ok(summaries)
}

fn resolved_executable(agent: &AgentIntegration) -> String {
    env::var(format!(
        "MAILBOX_{}_BIN",
        agent.executable.to_ascii_uppercase()
    ))
    .unwrap_or_else(|_| agent.executable.to_string())
}

fn ensure_marketplace(agent: &AgentIntegration, executable: &str) -> CliResult<&'static str> {
    let update = run_command(
        executable,
        &["plugin", "marketplace", "update", agent.marketplace_name],
    )?;
    if update.status.success() {
        return Ok("updated");
    }

    let add = run_command(
        executable,
        &["plugin", "marketplace", "add", agent.marketplace_source],
    )?;
    if add.status.success() {
        return Ok("added");
    }

    Err(format!(
        "{}: failed to update or add marketplace {}\nupdate stderr: {}\nadd stderr: {}",
        agent.name,
        agent.marketplace_name,
        String::from_utf8_lossy(&update.stderr).trim(),
        String::from_utf8_lossy(&add.stderr).trim()
    ))
}

fn ensure_plugin(
    agent: &AgentIntegration,
    executable: &str,
    plugin: &str,
) -> CliResult<&'static str> {
    let update = run_command(executable, &["plugin", "update", plugin])?;
    if update.status.success() {
        return Ok("updated");
    }

    let install = run_command(executable, &["plugin", "install", plugin])?;
    if install.status.success() {
        return Ok("installed");
    }

    Err(format!(
        "{}: failed to update or install plugin {}\nupdate stderr: {}\ninstall stderr: {}",
        agent.name,
        plugin,
        String::from_utf8_lossy(&update.stderr).trim(),
        String::from_utf8_lossy(&install.stderr).trim()
    ))
}

fn run_command(program: &str, args: &[&str]) -> CliResult<std::process::Output> {
    Command::new(program)
        .args(args)
        .output()
        .map_err(|err| err.to_string())
}

fn command_exists(program: &str) -> bool {
    let path = Path::new(program);
    if path.is_absolute()
        || path
            .parent()
            .is_some_and(|parent| !parent.as_os_str().is_empty())
    {
        return path.is_file();
    }

    env::var_os("PATH")
        .map(|paths| env::split_paths(&paths).any(|dir| executable_candidates(program, &dir)))
        .unwrap_or(false)
}

fn executable_candidates(program: &str, dir: &PathBuf) -> bool {
    let base = dir.join(program);
    if base.is_file() {
        return true;
    }

    if cfg!(windows) {
        for ext in [".exe", ".cmd", ".bat"] {
            if dir.join(format!("{program}{ext}")).is_file() {
                return true;
            }
        }
    }

    false
}
