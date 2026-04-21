use crate::util::CliResult;
use std::env;
use std::fs;
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

const MAILBOX_MEMORY_TEXT: &str = r#"# MAILBOX.md

Use AInbox as the durable coordination layer.

- Preserve or set `MAILBOX_AGENT_ID` explicitly.
- Use `.mailbox/draft/` as living memory for active threads.
- Sync before reading and after sending important updates.
- Use `mailbox send`, `list`, `read`, and `sync` for durable coordination.
- Reuse `--correlation-id` for related conversations.
- Use polls or elections when the group needs a durable decision or role assignment.
"#;

pub fn ensure_project_memory_files(root: &Path) -> CliResult<Vec<String>> {
    Ok(vec![
        ensure_memory_install(
            root,
            Path::new(".claude/MAILBOX.md"),
            Path::new("CLAUDE.md"),
            "@.claude/MAILBOX.md",
            "Claude Code project memory",
        )?,
        ensure_memory_install(
            root,
            Path::new(".agents/MAILBOX.md"),
            Path::new("AGENTS.md"),
            "@.agents/MAILBOX.md",
            "AGENTS project memory",
        )?,
    ])
}

pub fn ensure_global_integrations() -> CliResult<Vec<String>> {
    let mut summaries = ensure_user_memory_files()?;

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

fn ensure_user_memory_files() -> CliResult<Vec<String>> {
    let home_root = user_home_dir()?;
    Ok(vec![
        ensure_memory_install(
            &home_root,
            Path::new(".claude/MAILBOX.md"),
            Path::new(".claude/CLAUDE.md"),
            "@MAILBOX.md",
            "Claude Code user memory",
        )?,
        ensure_memory_install(
            &home_root,
            Path::new(".agents/MAILBOX.md"),
            Path::new(".agents/AGENTS.md"),
            "@MAILBOX.md",
            "AGENTS user memory",
        )?,
    ])
}

fn ensure_memory_install(
    root: &Path,
    mailbox_rel: &Path,
    include_target: &Path,
    include_line: &str,
    label: &str,
) -> CliResult<String> {
    let mailbox_created = ensure_mailbox_file(&root.join(mailbox_rel))?;
    let include_updated = ensure_include_file(&root.join(include_target), include_line)?;
    let mut actions = Vec::new();
    if mailbox_created {
        actions.push(format!("created {}", mailbox_rel.display()));
    }
    if include_updated {
        actions.push(format!("updated {}", include_target.display()));
    }
    if actions.is_empty() {
        actions.push("already configured".to_string());
    }
    Ok(format!("{label}: {}", actions.join(", ")))
}

fn ensure_mailbox_file(path: &Path) -> CliResult<bool> {
    if path.exists() {
        return Ok(false);
    }
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|err| err.to_string())?;
    }
    fs::write(path, format!("{MAILBOX_MEMORY_TEXT}\n")).map_err(|err| err.to_string())?;
    Ok(true)
}

fn ensure_include_file(path: &Path, include_line: &str) -> CliResult<bool> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|err| err.to_string())?;
    }

    if !path.exists() {
        fs::write(path, format!("{include_line}\n")).map_err(|err| err.to_string())?;
        return Ok(true);
    }

    let content = fs::read_to_string(path).map_err(|err| err.to_string())?;
    if content.contains(include_line) {
        return Ok(false);
    }

    fs::write(path, format!("{include_line}\n\n{content}")).map_err(|err| err.to_string())?;
    Ok(true)
}

fn user_home_dir() -> CliResult<PathBuf> {
    env::var_os("USERPROFILE")
        .or_else(|| env::var_os("HOME"))
        .map(PathBuf::from)
        .filter(|path| !path.as_os_str().is_empty())
        .ok_or_else(|| "Could not determine user home directory".to_string())
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

fn executable_candidates(program: &str, dir: &Path) -> bool {
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
