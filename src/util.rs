use chrono::{DateTime, Utc};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use uuid::Uuid;

pub type CliResult<T> = Result<T, String>;

pub fn get_home_mailbox() -> PathBuf {
    home_dir().join(".mailbox")
}

pub fn get_local_mailbox() -> PathBuf {
    env::current_dir()
        .unwrap_or_else(|_| PathBuf::from("."))
        .join(".mailbox")
}

pub fn get_shared_mailbox() -> PathBuf {
    if let Ok(path) = env::var("MAILBOX_SHARED") {
        let trimmed = path.trim();
        if !trimmed.is_empty() {
            return normalize_path(trimmed);
        }
    }

    let local_config = get_local_mailbox().join("config.yaml");
    if let Some(value) = load_config_value(&local_config, "shared_mailbox_path") {
        return normalize_path(&value);
    }

    let global_config = get_home_mailbox().join("config.yaml");
    if let Some(value) = load_config_value(&global_config, "shared_mailbox_path") {
        return normalize_path(&value);
    }

    get_home_mailbox()
}

pub fn get_shared_outbox() -> PathBuf {
    get_shared_mailbox().join("shared").join("outbox")
}

pub fn get_agent_id() -> CliResult<String> {
    if let Ok(value) = env::var("MAILBOX_AGENT_ID") {
        let trimmed = value.trim();
        if !trimmed.is_empty() {
            return Ok(trimmed.to_string());
        }
    }

    let local_config = get_local_mailbox().join("config.yaml");
    if let Some(value) = load_config_value(&local_config, "agent_id") {
        return Ok(value);
    }

    let global_config = get_home_mailbox().join("config.yaml");
    if let Some(value) = load_config_value(&global_config, "agent_id") {
        return Ok(value);
    }

    if let Ok(current_dir) = env::current_dir() {
        if let Some(name) = current_dir.file_name().and_then(|name| name.to_str()) {
            if !name.trim().is_empty() && name != "." {
                return Ok(name.to_string());
            }
        }
    }

    Err("Agent ID not found. Set MAILBOX_AGENT_ID env var, add 'agent_id' to .mailbox/config.yaml or ~/.mailbox/config.yaml, or use a named directory.".to_string())
}

pub fn generate_id() -> String {
    Uuid::new_v4().to_string().chars().take(13).collect()
}

pub fn generate_timestamp() -> String {
    Utc::now().format("%Y-%m-%dT%H:%M:%SZ").to_string()
}

pub fn parse_utc_timestamp(value: &str) -> CliResult<DateTime<Utc>> {
    if !value.ends_with('Z') {
        return Err("Timestamp must use ISO 8601 UTC format like 2026-04-21T04:00:00Z".to_string());
    }
    DateTime::parse_from_rfc3339(value)
        .map(|dt| dt.with_timezone(&Utc))
        .map_err(|_| "Timestamp must use ISO 8601 UTC format like 2026-04-21T04:00:00Z".to_string())
}

pub fn generate_filename_timestamp() -> String {
    Utc::now().format("%Y%m%dT%H%M%SZ").to_string()
}

pub fn make_message_filename(msg_id: &str) -> String {
    format!("{}_{}.md", generate_filename_timestamp(), msg_id)
}

pub fn extract_id_from_filename(filename: &str) -> Option<String> {
    filename
        .strip_suffix(".md")
        .and_then(|name| name.split_once('_'))
        .map(|(_, msg_id)| msg_id.to_string())
}

pub fn write_string_atomic(path: &Path, content: &str) -> CliResult<()> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|err| err.to_string())?;
        let temp = tempfile::NamedTempFile::new_in(parent).map_err(|err| err.to_string())?;
        fs::write(temp.path(), content).map_err(|err| err.to_string())?;
        if path.exists() {
            fs::remove_file(path).map_err(|err| err.to_string())?;
        }
        fs::rename(temp.path(), path).map_err(|err| err.to_string())?;
        Ok(())
    } else {
        Err(format!(
            "Cannot determine parent directory for {}",
            path.display()
        ))
    }
}

pub fn normalize_path(raw_path: &str) -> PathBuf {
    let expanded = if let Some(stripped) = raw_path.strip_prefix("~/") {
        home_dir().join(stripped)
    } else {
        PathBuf::from(raw_path)
    };

    expanded
}

fn home_dir() -> PathBuf {
    if let Ok(userprofile) = env::var("USERPROFILE") {
        if !userprofile.trim().is_empty() {
            return PathBuf::from(userprofile);
        }
    }
    if let Ok(home) = env::var("HOME") {
        if !home.trim().is_empty() {
            return PathBuf::from(home);
        }
    }
    env::current_dir().unwrap_or_else(|_| PathBuf::from("."))
}

fn load_config_value(config_path: &Path, key: &str) -> Option<String> {
    let content = fs::read_to_string(config_path).ok()?;
    for line in content.lines() {
        let trimmed = line.trim();
        if let Some(value) = trimmed.strip_prefix(&format!("{key}:")) {
            let clean = value
                .trim()
                .trim_matches('"')
                .trim_matches('\'')
                .to_string();
            if !clean.is_empty() {
                return Some(clean);
            }
        }
    }
    None
}
