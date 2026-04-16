use crate::util::{CliResult, write_string_atomic};
use std::collections::BTreeMap;
use std::fs;
use std::path::Path;

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Message {
    pub id: String,
    pub to: String,
    pub from_: String,
    pub subject: String,
    pub sent_at: String,
    pub received_at: Option<String>,
    pub read_at: Option<String>,
    pub correlation_id: Option<String>,
    pub body: String,
    pub extra_fields: BTreeMap<String, String>,
}

impl Message {
    pub fn to_markdown(&self) -> CliResult<String> {
        let frontmatter = self.build_frontmatter()?;
        Ok(format!("{frontmatter}\n\n{}\n", self.body))
    }

    pub fn from_markdown(content: &str) -> CliResult<Self> {
        let normalized = content.replace("\r\n", "\n");
        let lines: Vec<&str> = normalized.split('\n').collect();
        if lines.len() < 3 || lines.first().copied() != Some("---") {
            return Err("Invalid message format: missing frontmatter markers".to_string());
        }

        let closing_idx = lines
            .iter()
            .enumerate()
            .skip(1)
            .find_map(|(idx, line)| if line.trim() == "---" { Some(idx) } else { None })
            .ok_or_else(|| "Invalid message format: missing closing --- delimiter".to_string())?;

        let frontmatter_lines = &lines[1..closing_idx];
        let mut body_lines = lines[(closing_idx + 1)..].to_vec();
        if body_lines.first().is_some_and(|line| line.trim().is_empty()) {
            body_lines.remove(0);
        }
        while body_lines.last().is_some_and(|line| line.is_empty()) {
            body_lines.pop();
        }
        let body = body_lines.join("\n");

        let mut fields = BTreeMap::new();
        let optional_nullable = ["received_at", "read_at", "correlation_id"];
        let required = ["id", "to", "from", "subject", "sent_at"];

        for line in frontmatter_lines {
            let trimmed = line.trim();
            if trimmed.is_empty() || trimmed.starts_with('#') {
                continue;
            }
            let Some((key, value)) = trimmed.split_once(':') else {
                continue;
            };
            let key = key.trim().to_string();
            let value = value.trim().to_string();
            if value.eq_ignore_ascii_case("null") && optional_nullable.contains(&key.as_str()) {
                fields.insert(key, String::new());
            } else {
                fields.insert(key, value);
            }
        }

        let missing: Vec<&str> = required
            .iter()
            .copied()
            .filter(|key| !fields.contains_key(*key))
            .collect();
        if !missing.is_empty() {
            return Err(format!("Missing required fields: {:?}", missing));
        }

        let mut extra_fields = BTreeMap::new();
        for (key, value) in &fields {
            if !required.contains(&key.as_str()) && !optional_nullable.contains(&key.as_str()) {
                extra_fields.insert(key.clone(), value.clone());
            }
        }

        Ok(Self {
            id: fields["id"].clone(),
            to: fields["to"].clone(),
            from_: fields["from"].clone(),
            subject: fields["subject"].clone(),
            sent_at: fields["sent_at"].clone(),
            received_at: option_from_nullable(fields.get("received_at")),
            read_at: option_from_nullable(fields.get("read_at")),
            correlation_id: option_from_nullable(fields.get("correlation_id")),
            body,
            extra_fields,
        })
    }

    pub fn from_file(path: &Path) -> CliResult<Self> {
        let content = fs::read_to_string(path).map_err(|err| err.to_string())?;
        Self::from_markdown(&content)
    }

    pub fn to_file(&self, path: &Path) -> CliResult<()> {
        let content = self.to_markdown()?;
        write_string_atomic(path, &content)
    }

    fn build_frontmatter(&self) -> CliResult<String> {
        let mut lines = vec!["---".to_string()];
        lines.push(format!("id: {}", sanitize_field(&self.id)?));
        lines.push(format!("to: {}", sanitize_field(&self.to)?));
        lines.push(format!("from: {}", sanitize_field(&self.from_)?));
        lines.push(format!("subject: {}", sanitize_field(&self.subject)?));
        lines.push(format!("sent_at: {}", sanitize_field(&self.sent_at)?));
        lines.push(format!(
            "received_at: {}",
            sanitize_field(self.received_at.as_deref().unwrap_or("null"))?
        ));
        lines.push(format!(
            "read_at: {}",
            sanitize_field(self.read_at.as_deref().unwrap_or("null"))?
        ));
        if let Some(correlation_id) = &self.correlation_id {
            lines.push(format!("correlation_id: {}", sanitize_field(correlation_id)?));
        }
        for (key, value) in &self.extra_fields {
            lines.push(format!("{key}: {}", sanitize_field(value)?));
        }
        lines.push("---".to_string());
        Ok(lines.join("\n"))
    }
}

fn sanitize_field(value: &str) -> CliResult<String> {
    if value.contains('\n') || value.contains('\r') {
        return Err(format!(
            "Field values cannot contain newlines: {:?}",
            value.chars().take(50).collect::<String>()
        ));
    }
    Ok(value.to_string())
}

fn option_from_nullable(value: Option<&String>) -> Option<String> {
    value.and_then(|raw| if raw.is_empty() { None } else { Some(raw.clone()) })
}

#[cfg(test)]
mod tests {
    use super::Message;
    use std::collections::BTreeMap;

    #[test]
    fn round_trip_preserves_body_and_null_string() {
        let message = Message {
            id: "abc123".into(),
            to: "null".into(),
            from_: "sender".into(),
            subject: "Hello".into(),
            sent_at: "2026-01-01T00:00:00Z".into(),
            received_at: None,
            read_at: None,
            correlation_id: Some("thread-1".into()),
            body: "\nLeading blank line".into(),
            extra_fields: BTreeMap::new(),
        };

        let markdown = message.to_markdown().expect("markdown");
        let parsed = Message::from_markdown(&markdown).expect("parse");
        assert_eq!(parsed.to, "null");
        assert_eq!(parsed.body, "\nLeading blank line");
    }
}
