use crate::message::Message;
use crate::util::{
    CliResult, extract_id_from_filename, generate_id, generate_timestamp, get_agent_id,
    get_local_mailbox, get_shared_outbox, make_message_filename,
};
use std::fs;
use std::path::{Path, PathBuf};

pub struct Mailbox {
    pub local_mailbox: PathBuf,
    pub shared_outbox: PathBuf,
    pub agent_id: String,
}

impl Mailbox {
    pub fn new() -> CliResult<Self> {
        Ok(Self {
            local_mailbox: get_local_mailbox(),
            shared_outbox: get_shared_outbox(),
            agent_id: get_agent_id()?,
        })
    }

    pub fn init(&self) -> CliResult<()> {
        for folder in ["inbox", "outbox", "sent", "archive", "draft"] {
            fs::create_dir_all(self.local_mailbox.join(folder)).map_err(|err| err.to_string())?;
        }
        println!("Initialized mailbox at {}", self.local_mailbox.display());
        Ok(())
    }

    pub fn send(
        &self,
        to: &str,
        subject: &str,
        body: &str,
        correlation_id: Option<String>,
    ) -> CliResult<String> {
        let message = Message {
            id: generate_id(),
            to: to.to_string(),
            from_: self.agent_id.clone(),
            subject: subject.to_string(),
            sent_at: generate_timestamp(),
            received_at: None,
            read_at: None,
            correlation_id,
            body: body.to_string(),
            extra_fields: Default::default(),
        };

        let outbox = self.local_mailbox.join("outbox");
        fs::create_dir_all(&outbox).map_err(|err| err.to_string())?;
        let file_path = outbox.join(make_message_filename(&message.id));
        message.to_file(&file_path)?;
        Ok(file_path.display().to_string())
    }

    pub fn list_inbox(&self, limit: usize) -> CliResult<Vec<Message>> {
        let inbox = self.local_mailbox.join("inbox");
        if !inbox.exists() {
            return Ok(vec![]);
        }

        let mut files = markdown_files(&inbox)?;
        files.sort();
        files.reverse();

        let mut messages = Vec::new();
        for file in files.into_iter().take(limit) {
            if let Ok(message) = Message::from_file(&file) {
                messages.push(message);
            }
        }
        Ok(messages)
    }

    pub fn read_message(
        &self,
        message_id: Option<&str>,
        correlation_id: Option<&str>,
    ) -> CliResult<Option<Message>> {
        let inbox = self.local_mailbox.join("inbox");
        if !inbox.exists() {
            return Ok(None);
        }

        if let Some(target_id) = message_id {
            for file in markdown_files(&inbox)? {
                if extract_id_from_filename(file.file_name().and_then(|x| x.to_str()).unwrap_or_default())
                    .as_deref()
                    == Some(target_id)
                {
                    return self.mark_and_read(&file).map(Some);
                }
            }
            return Ok(None);
        }

        if let Some(thread_id) = correlation_id {
            let mut files = markdown_files(&inbox)?;
            files.sort();
            for file in files {
                let message = Message::from_file(&file)?;
                if message.correlation_id.as_deref() == Some(thread_id) {
                    return self.mark_and_read(&file).map(Some);
                }
            }
            return Ok(None);
        }

        let mut files = markdown_files(&inbox)?;
        files.sort();
        if let Some(file) = files.first() {
            return self.mark_and_read(file).map(Some);
        }
        Ok(None)
    }

    pub fn archive_message(&self, message_id: &str) -> CliResult<bool> {
        let inbox = self.local_mailbox.join("inbox");
        if !inbox.exists() {
            return Ok(false);
        }

        for file in markdown_files(&inbox)? {
            if extract_id_from_filename(file.file_name().and_then(|x| x.to_str()).unwrap_or_default())
                .as_deref()
                == Some(message_id)
            {
                self.mark_and_read(&file)?;
                return Ok(true);
            }
        }
        Ok(false)
    }

    pub fn sync(&self, push_only: bool, pull_only: bool) -> CliResult<(usize, usize)> {
        if push_only && pull_only {
            return Err("--push-only and --pull-only are mutually exclusive".to_string());
        }

        let pushed = if !pull_only { self.sync_push()? } else { 0 };
        let pulled = if !push_only { self.sync_pull()? } else { 0 };
        Ok((pushed, pulled))
    }

    fn mark_and_read(&self, path: &Path) -> CliResult<Message> {
        let mut message = Message::from_file(path)?;
        message.read_at = Some(generate_timestamp());
        let archive = self.local_mailbox.join("archive");
        fs::create_dir_all(&archive).map_err(|err| err.to_string())?;
        let archive_path = archive.join(path.file_name().ok_or_else(|| "Invalid message path".to_string())?);
        message.to_file(&archive_path)?;
        fs::remove_file(path).map_err(|err| err.to_string())?;
        Ok(message)
    }

    fn sync_push(&self) -> CliResult<usize> {
        let outbox = self.local_mailbox.join("outbox");
        if !outbox.exists() {
            return Ok(0);
        }
        fs::create_dir_all(&self.shared_outbox).map_err(|err| err.to_string())?;
        let sent = self.local_mailbox.join("sent");
        fs::create_dir_all(&sent).map_err(|err| err.to_string())?;

        let mut count = 0;
        for file in markdown_files(&outbox)? {
            let message = Message::from_file(&file)?;
            let filename = file.file_name().ok_or_else(|| "Invalid message filename".to_string())?;
            message.to_file(&self.shared_outbox.join(filename))?;
            message.to_file(&sent.join(filename))?;
            fs::remove_file(&file).map_err(|err| err.to_string())?;
            count += 1;
        }
        Ok(count)
    }

    fn sync_pull(&self) -> CliResult<usize> {
        if !self.shared_outbox.exists() {
            return Ok(0);
        }

        let inbox = self.local_mailbox.join("inbox");
        fs::create_dir_all(&inbox).map_err(|err| err.to_string())?;

        let mut existing_ids = std::collections::BTreeSet::new();
        for folder in ["inbox", "archive", "sent"] {
            let path = self.local_mailbox.join(folder);
            if path.exists() {
                for file in markdown_files(&path)? {
                    if let Some(id) =
                        extract_id_from_filename(file.file_name().and_then(|x| x.to_str()).unwrap_or_default())
                    {
                        existing_ids.insert(id);
                    }
                }
            }
        }

        let mut count = 0;
        for file in markdown_files(&self.shared_outbox)? {
            let mut message = match Message::from_file(&file) {
                Ok(message) => message,
                Err(_) => continue,
            };
            if message.to == self.agent_id && !existing_ids.contains(&message.id) {
                if message.received_at.is_none() {
                    message.received_at = Some(generate_timestamp());
                }
                let filename = file.file_name().ok_or_else(|| "Invalid message filename".to_string())?;
                message.to_file(&inbox.join(filename))?;
                existing_ids.insert(message.id.clone());
                fs::remove_file(&file).map_err(|err| err.to_string())?;
                count += 1;
            }
        }
        Ok(count)
    }
}

fn markdown_files(dir: &Path) -> CliResult<Vec<PathBuf>> {
    let entries = fs::read_dir(dir).map_err(|err| err.to_string())?;
    let mut files = Vec::new();
    for entry in entries {
        let path = entry.map_err(|err| err.to_string())?.path();
        if path.extension().and_then(|ext| ext.to_str()) == Some("md") {
            files.push(path);
        }
    }
    Ok(files)
}
