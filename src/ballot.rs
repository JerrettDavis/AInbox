use crate::mailbox::Mailbox;
use crate::util::{generate_id, generate_timestamp, get_agent_id, get_shared_mailbox, CliResult};
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct Poll {
    pub id: String,
    pub question: String,
    pub options: Vec<String>,
    pub created_by: String,
    pub created_at: String,
    pub status: String,
    pub participants: Vec<String>,
    pub description: String,
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct Election {
    pub id: String,
    pub role: String,
    pub candidates: Vec<String>,
    pub created_by: String,
    pub created_at: String,
    pub status: String,
    pub participants: Vec<String>,
    pub description: String,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
struct PollVote {
    voter: String,
    option: String,
    voted_at: String,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
struct ElectionVote {
    voter: String,
    candidate: String,
    voted_at: String,
}

pub struct BallotBox {
    polls_root: PathBuf,
    elections_root: PathBuf,
}

impl BallotBox {
    pub fn new() -> Self {
        let shared_mailbox = get_shared_mailbox();
        Self {
            polls_root: shared_mailbox.join("shared").join("polls"),
            elections_root: shared_mailbox.join("shared").join("elections"),
        }
    }

    pub fn create_poll(
        &self,
        question: &str,
        options: Vec<String>,
        created_by: &str,
        participants: Vec<String>,
        description: Option<String>,
    ) -> CliResult<Poll> {
        if options.is_empty() {
            return Err("Poll must have at least one option".to_string());
        }
        ensure_unique(&options, "Duplicate options not allowed")?;
        self.ensure_dirs()?;

        let poll = Poll {
            id: generate_id(),
            question: question.to_string(),
            options,
            created_by: created_by.to_string(),
            created_at: generate_timestamp(),
            status: "open".to_string(),
            participants,
            description: description.unwrap_or_default(),
        };

        let poll_dir = self.polls_root.join(&poll.id);
        fs::create_dir_all(&poll_dir).map_err(|err| err.to_string())?;
        write_json(&poll_dir.join("definition.json"), &poll)?;

        Ok(poll)
    }

    pub fn list_polls(
        &self,
        status: Option<&str>,
        participant: Option<&str>,
        created_by: Option<&str>,
    ) -> CliResult<Vec<Poll>> {
        self.ensure_dirs()?;
        let mut polls = Vec::new();
        for dir in read_dirs(&self.polls_root)? {
            let definition = dir.join("definition.json");
            if !definition.exists() {
                continue;
            }
            let poll: Poll = match read_json(&definition) {
                Ok(poll) => poll,
                Err(_) => continue,
            };
            if status.is_some_and(|value| value != "all" && poll.status != value) {
                continue;
            }
            if participant.is_some_and(|value| {
                !poll.participants.is_empty() && !poll.participants.iter().any(|item| item == value)
            }) {
                continue;
            }
            if created_by.is_some_and(|value| poll.created_by != value) {
                continue;
            }
            polls.push(poll);
        }
        polls.sort_by(|a, b| b.created_at.cmp(&a.created_at));
        Ok(polls)
    }

    pub fn get_poll(&self, poll_id: &str) -> CliResult<Option<Poll>> {
        let definition = self.polls_root.join(poll_id).join("definition.json");
        if !definition.exists() {
            return Ok(None);
        }
        read_json(&definition).map(Some)
    }

    pub fn vote_poll(&self, poll_id: &str, voter: &str, option: &str) -> CliResult<()> {
        let poll = self
            .get_poll(poll_id)?
            .ok_or_else(|| format!("Poll {poll_id} not found"))?;
        if poll.status != "open" {
            return Err(format!("Poll is {}", poll.status));
        }
        if !poll.options.iter().any(|item| item == option) {
            return Err(format!("Invalid option: {option}"));
        }
        if !poll.participants.is_empty() && !poll.participants.iter().any(|item| item == voter) {
            return Err(format!("Voter {voter} not in poll participants"));
        }

        let vote = PollVote {
            voter: voter.to_string(),
            option: option.to_string(),
            voted_at: generate_timestamp(),
        };
        write_json(
            &self.polls_root.join(poll_id).join(format!("{voter}.json")),
            &vote,
        )
    }

    pub fn get_poll_votes(&self, poll_id: &str) -> CliResult<serde_json::Value> {
        let poll = self
            .get_poll(poll_id)?
            .ok_or_else(|| format!("Poll {poll_id} not found"))?;
        let mut votes = BTreeMap::new();
        for option in &poll.options {
            votes.insert(option.clone(), 0usize);
        }
        let mut voters = Vec::new();
        for entry in read_vote_files(&self.polls_root.join(poll_id))? {
            let vote: PollVote = match read_json(&entry) {
                Ok(vote) => vote,
                Err(_) => continue,
            };
            if let Some(count) = votes.get_mut(&vote.option) {
                *count += 1;
            }
            voters.push(vote.voter);
        }
        let total_votes = votes.values().sum::<usize>();
        Ok(json!({
            "poll_id": poll_id,
            "question": poll.question,
            "status": poll.status,
            "options": poll.options,
            "votes": votes,
            "total_votes": total_votes,
            "voters": voters
        }))
    }

    pub fn close_poll(&self, poll_id: &str) -> CliResult<()> {
        let mut poll = self
            .get_poll(poll_id)?
            .ok_or_else(|| format!("Poll {poll_id} not found"))?;
        poll.status = "closed".to_string();
        write_json(
            &self.polls_root.join(poll_id).join("definition.json"),
            &poll,
        )
    }

    pub fn create_election(
        &self,
        role: &str,
        candidates: Vec<String>,
        created_by: &str,
        participants: Vec<String>,
        description: Option<String>,
    ) -> CliResult<Election> {
        if candidates.is_empty() {
            return Err("Election must have at least one candidate".to_string());
        }
        ensure_unique(&candidates, "Duplicate candidates not allowed")?;
        self.ensure_dirs()?;

        let election = Election {
            id: generate_id(),
            role: role.to_string(),
            candidates,
            created_by: created_by.to_string(),
            created_at: generate_timestamp(),
            status: "open".to_string(),
            participants,
            description: description.unwrap_or_default(),
        };

        let election_dir = self.elections_root.join(&election.id);
        fs::create_dir_all(&election_dir).map_err(|err| err.to_string())?;
        write_json(&election_dir.join("definition.json"), &election)?;

        Ok(election)
    }

    pub fn list_elections(
        &self,
        status: Option<&str>,
        participant: Option<&str>,
        created_by: Option<&str>,
    ) -> CliResult<Vec<Election>> {
        self.ensure_dirs()?;
        let mut elections = Vec::new();
        for dir in read_dirs(&self.elections_root)? {
            let definition = dir.join("definition.json");
            if !definition.exists() {
                continue;
            }
            let election: Election = match read_json(&definition) {
                Ok(election) => election,
                Err(_) => continue,
            };
            if status.is_some_and(|value| value != "all" && election.status != value) {
                continue;
            }
            if participant.is_some_and(|value| {
                !election.participants.is_empty()
                    && !election.participants.iter().any(|item| item == value)
            }) {
                continue;
            }
            if created_by.is_some_and(|value| election.created_by != value) {
                continue;
            }
            elections.push(election);
        }
        elections.sort_by(|a, b| b.created_at.cmp(&a.created_at));
        Ok(elections)
    }

    pub fn get_election(&self, election_id: &str) -> CliResult<Option<Election>> {
        let definition = self
            .elections_root
            .join(election_id)
            .join("definition.json");
        if !definition.exists() {
            return Ok(None);
        }
        read_json(&definition).map(Some)
    }

    pub fn vote_election(&self, election_id: &str, voter: &str, candidate: &str) -> CliResult<()> {
        let election = self
            .get_election(election_id)?
            .ok_or_else(|| format!("Election {election_id} not found"))?;
        if election.status != "open" {
            return Err(format!("Election is {}", election.status));
        }
        if !election.candidates.iter().any(|item| item == candidate) {
            return Err(format!("Invalid candidate: {candidate}"));
        }
        if voter == candidate {
            return Err("Cannot vote for yourself".to_string());
        }
        if !election.participants.is_empty()
            && !election.participants.iter().any(|item| item == voter)
        {
            return Err(format!("Voter {voter} not in election participants"));
        }

        let vote = ElectionVote {
            voter: voter.to_string(),
            candidate: candidate.to_string(),
            voted_at: generate_timestamp(),
        };
        write_json(
            &self
                .elections_root
                .join(election_id)
                .join(format!("{voter}.json")),
            &vote,
        )
    }

    pub fn get_election_votes(&self, election_id: &str) -> CliResult<serde_json::Value> {
        let election = self
            .get_election(election_id)?
            .ok_or_else(|| format!("Election {election_id} not found"))?;
        let mut votes = BTreeMap::new();
        for candidate in &election.candidates {
            votes.insert(candidate.clone(), 0usize);
        }
        let mut voters = Vec::new();
        for entry in read_vote_files(&self.elections_root.join(election_id))? {
            let vote: ElectionVote = match read_json(&entry) {
                Ok(vote) => vote,
                Err(_) => continue,
            };
            if let Some(count) = votes.get_mut(&vote.candidate) {
                *count += 1;
            }
            voters.push(vote.voter);
        }
        let total_votes = votes.values().sum::<usize>();
        Ok(json!({
            "election_id": election_id,
            "role": election.role,
            "status": election.status,
            "candidates": election.candidates,
            "votes": votes,
            "total_votes": total_votes,
            "voters": voters
        }))
    }

    pub fn close_election(&self, election_id: &str) -> CliResult<()> {
        let mut election = self
            .get_election(election_id)?
            .ok_or_else(|| format!("Election {election_id} not found"))?;
        election.status = "closed".to_string();
        write_json(
            &self
                .elections_root
                .join(election_id)
                .join("definition.json"),
            &election,
        )
    }

    pub fn notify_participants(
        kind: &str,
        ballot_id: &str,
        title: &str,
        participants: &[String],
        description: &str,
    ) -> CliResult<usize> {
        if participants.is_empty() {
            return Ok(0);
        }
        let mailbox = Mailbox::new()?;
        let body = format!(
            "A new {kind} is available.\n\nID: {ballot_id}\nTitle: {title}\n{}\n\nUse `mailbox show-{kind} --id {ballot_id}` to inspect it and `mailbox vote-{kind} --id {ballot_id}` to respond.",
            description.trim()
        )
        .trim()
        .to_string();

        for participant in participants {
            mailbox.send(
                participant,
                &format!("{} open: {}", title_case(kind), title),
                &body,
                Some(format!("{kind}:{ballot_id}")),
                None,
            )?;
        }
        mailbox.sync(true, false)?;
        Ok(participants.len())
    }

    pub fn current_agent_id() -> CliResult<String> {
        get_agent_id()
    }

    fn ensure_dirs(&self) -> CliResult<()> {
        fs::create_dir_all(&self.polls_root).map_err(|err| err.to_string())?;
        fs::create_dir_all(&self.elections_root).map_err(|err| err.to_string())?;
        Ok(())
    }
}

fn ensure_unique(values: &[String], message: &str) -> CliResult<()> {
    let mut seen = std::collections::BTreeSet::new();
    for value in values {
        if !seen.insert(value) {
            return Err(message.to_string());
        }
    }
    Ok(())
}

fn read_dirs(root: &PathBuf) -> CliResult<Vec<PathBuf>> {
    if !root.exists() {
        return Ok(vec![]);
    }
    let mut result = Vec::new();
    for entry in fs::read_dir(root).map_err(|err| err.to_string())? {
        let path = entry.map_err(|err| err.to_string())?.path();
        if path.is_dir() {
            result.push(path);
        }
    }
    Ok(result)
}

fn read_vote_files(dir: &PathBuf) -> CliResult<Vec<PathBuf>> {
    if !dir.exists() {
        return Ok(vec![]);
    }
    let mut result = Vec::new();
    for entry in fs::read_dir(dir).map_err(|err| err.to_string())? {
        let path = entry.map_err(|err| err.to_string())?.path();
        if path.extension().and_then(|ext| ext.to_str()) == Some("json")
            && path.file_name().and_then(|name| name.to_str()) != Some("definition.json")
        {
            result.push(path);
        }
    }
    Ok(result)
}

fn write_json<T: Serialize>(path: &Path, value: &T) -> CliResult<()> {
    let content = serde_json::to_string_pretty(value).map_err(|err| err.to_string())?;
    crate::util::write_string_atomic(path, &content)
}

fn read_json<T: for<'de> Deserialize<'de>>(path: &Path) -> CliResult<T> {
    let content = fs::read_to_string(path).map_err(|err| err.to_string())?;
    serde_json::from_str(&content).map_err(|err| err.to_string())
}

fn title_case(value: &str) -> String {
    let mut chars = value.chars();
    match chars.next() {
        Some(first) => format!("{}{}", first.to_ascii_uppercase(), chars.as_str()),
        None => String::new(),
    }
}

#[cfg(test)]
mod tests {
    use super::BallotBox;
    use std::env;
    use tempfile::TempDir;

    #[test]
    fn election_rejects_self_vote() {
        let root = TempDir::new().expect("temp");
        env::set_var("MAILBOX_SHARED", root.path().join("shared-root"));
        let ballot_box = BallotBox::new();
        let election = ballot_box
            .create_election(
                "leader",
                vec!["alice".into(), "bob".into()],
                "coordinator",
                vec![],
                None,
            )
            .expect("create");
        let result = ballot_box.vote_election(&election.id, "alice", "alice");
        assert!(result.is_err());
    }
}
