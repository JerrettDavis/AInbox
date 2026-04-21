use crate::mailbox::Mailbox;
use crate::util::{generate_id, generate_timestamp, get_agent_id, get_shared_mailbox, CliResult};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::{Path, PathBuf};
use std::thread;
use std::time::{Duration, Instant};

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

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct Motion {
    pub id: String,
    pub title: String,
    pub created_by: String,
    pub created_at: String,
    pub status: String,
    pub participants: Vec<String>,
    pub description: String,
    pub scope: String,
    pub quorum: usize,
    pub required_yes: usize,
    pub blocking: bool,
}

#[derive(Clone, Debug)]
pub struct MotionSpec {
    pub title: String,
    pub created_by: String,
    pub participants: Vec<String>,
    pub description: Option<String>,
    pub scope: Option<String>,
    pub quorum: Option<usize>,
    pub required_yes: Option<usize>,
    pub blocking: bool,
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

#[derive(Clone, Debug, Serialize, Deserialize)]
struct MotionVote {
    voter: String,
    vote: String,
    reason: String,
    voted_at: String,
}

pub struct BallotBox {
    polls_root: PathBuf,
    elections_root: PathBuf,
    motions_root: PathBuf,
}

impl BallotBox {
    pub fn new() -> Self {
        let shared_mailbox = get_shared_mailbox();
        Self {
            polls_root: shared_mailbox.join("shared").join("polls"),
            elections_root: shared_mailbox.join("shared").join("elections"),
            motions_root: shared_mailbox.join("shared").join("motions"),
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

    pub fn get_poll_votes(&self, poll_id: &str) -> CliResult<Value> {
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

    pub fn get_election_votes(&self, election_id: &str) -> CliResult<Value> {
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

    pub fn create_motion(&self, spec: MotionSpec) -> CliResult<Motion> {
        if spec.participants.is_empty() {
            return Err("Motion must have at least one participant".to_string());
        }
        ensure_unique(&spec.participants, "Duplicate participants not allowed")?;
        let (quorum, required_yes) =
            validate_motion_thresholds(&spec.participants, spec.quorum, spec.required_yes)?;
        self.ensure_dirs()?;

        let motion = Motion {
            id: generate_id(),
            title: spec.title,
            created_by: spec.created_by,
            created_at: generate_timestamp(),
            status: "open".to_string(),
            participants: spec.participants,
            description: spec.description.unwrap_or_default(),
            scope: spec.scope.unwrap_or_default(),
            quorum,
            required_yes,
            blocking: spec.blocking,
        };

        let motion_dir = self.motions_root.join(&motion.id);
        fs::create_dir_all(&motion_dir).map_err(|err| err.to_string())?;
        write_json(&motion_dir.join("definition.json"), &motion)?;

        Ok(motion)
    }

    pub fn get_motion(&self, motion_id: &str) -> CliResult<Option<Motion>> {
        let definition = self.motions_root.join(motion_id).join("definition.json");
        if !definition.exists() {
            return Ok(None);
        }
        let motion: Motion = read_json(&definition)?;
        self.refresh_motion_status(motion).map(Some)
    }

    pub fn list_motions(
        &self,
        status: Option<&str>,
        participant: Option<&str>,
        created_by: Option<&str>,
    ) -> CliResult<Vec<Motion>> {
        self.ensure_dirs()?;
        let mut motions = Vec::new();
        for dir in read_dirs(&self.motions_root)? {
            let definition = dir.join("definition.json");
            if !definition.exists() {
                continue;
            }
            let motion: Motion = match read_json(&definition) {
                Ok(motion) => motion,
                Err(_) => continue,
            };
            let motion = self.refresh_motion_status(motion)?;
            if status.is_some_and(|value| value != "all" && motion.status != value) {
                continue;
            }
            if participant
                .is_some_and(|value| !motion.participants.iter().any(|item| item == value))
            {
                continue;
            }
            if created_by.is_some_and(|value| motion.created_by != value) {
                continue;
            }
            motions.push(motion);
        }
        motions.sort_by(|a, b| b.created_at.cmp(&a.created_at));
        Ok(motions)
    }

    pub fn vote_motion(
        &self,
        motion_id: &str,
        voter: &str,
        vote: &str,
        reason: Option<String>,
    ) -> CliResult<Value> {
        let motion = self
            .get_motion(motion_id)?
            .ok_or_else(|| format!("Motion {motion_id} not found"))?;
        if motion.status != "open" {
            return Err(format!("Motion is {}", motion.status));
        }
        if !motion.participants.iter().any(|item| item == voter) {
            return Err(format!("Voter {voter} not in motion participants"));
        }

        let normalized_vote = vote.trim().to_ascii_lowercase();
        if normalized_vote != "yes" && normalized_vote != "no" {
            return Err("Motion vote must be 'yes' or 'no'".to_string());
        }

        let response = MotionVote {
            voter: voter.to_string(),
            vote: normalized_vote,
            reason: reason.unwrap_or_default(),
            voted_at: generate_timestamp(),
        };
        write_json(
            &self
                .motions_root
                .join(motion_id)
                .join(format!("{voter}.json")),
            &response,
        )?;
        self.get_motion_state(motion_id)
    }

    pub fn get_motion_state(&self, motion_id: &str) -> CliResult<Value> {
        let motion = self
            .get_motion(motion_id)?
            .ok_or_else(|| format!("Motion {motion_id} not found"))?;
        let votes = self.get_motion_votes(motion_id)?;
        Ok(json!({
            "motion": motion,
            "votes": votes,
        }))
    }

    pub fn get_motion_votes(&self, motion_id: &str) -> CliResult<Value> {
        let motion = self
            .get_motion(motion_id)?
            .ok_or_else(|| format!("Motion {motion_id} not found"))?;
        let mut responses = Vec::new();
        for entry in read_vote_files(&self.motions_root.join(motion_id))? {
            let response: MotionVote = match read_json(&entry) {
                Ok(response) => response,
                Err(_) => continue,
            };
            responses.push(response);
        }
        responses.sort_by(|a, b| a.voted_at.cmp(&b.voted_at));

        let yes_votes = responses.iter().filter(|vote| vote.vote == "yes").count();
        let no_votes = responses.iter().filter(|vote| vote.vote == "no").count();
        let voters: Vec<String> = responses.iter().map(|vote| vote.voter.clone()).collect();
        let voter_set: BTreeSet<String> = voters.iter().cloned().collect();
        let remaining_voters: Vec<String> = motion
            .participants
            .iter()
            .filter(|participant| !voter_set.contains(*participant))
            .cloned()
            .collect();

        Ok(json!({
            "motion_id": motion_id,
            "title": motion.title,
            "status": motion.status,
            "scope": motion.scope,
            "blocking": motion.blocking,
            "participants": motion.participants,
            "quorum": motion.quorum,
            "required_yes": motion.required_yes,
            "votes": {
                "yes": yes_votes,
                "no": no_votes,
            },
            "total_votes": yes_votes + no_votes,
            "quorum_met": yes_votes + no_votes >= motion.quorum,
            "voters": voters,
            "remaining_voters": remaining_voters,
            "responses": responses,
        }))
    }

    pub fn close_motion(&self, motion_id: &str, status: &str) -> CliResult<()> {
        let mut motion = self
            .get_motion(motion_id)?
            .ok_or_else(|| format!("Motion {motion_id} not found"))?;
        if !matches!(status, "accepted" | "rejected" | "cancelled") {
            return Err("Motion close status must be accepted, rejected, or cancelled".to_string());
        }
        motion.status = status.to_string();
        write_json(
            &self.motions_root.join(motion_id).join("definition.json"),
            &motion,
        )
    }

    pub fn wait_for_motion(
        &self,
        motion_id: &str,
        timeout_seconds: Option<f64>,
        poll_interval_seconds: f64,
    ) -> CliResult<Value> {
        let started = Instant::now();
        loop {
            let state = self.get_motion_state(motion_id)?;
            let status = state["motion"]["status"].as_str().unwrap_or("open");
            if status != "open" {
                return Ok(state);
            }
            if timeout_seconds.is_some_and(|timeout| started.elapsed().as_secs_f64() >= timeout) {
                return Err(format!("Timed out waiting for motion {motion_id}"));
            }
            let sleep_seconds = poll_interval_seconds.max(0.1);
            thread::sleep(Duration::from_secs_f64(sleep_seconds));
        }
    }

    pub fn notify_participants(
        kind: &str,
        ballot_id: &str,
        title: &str,
        participants: &[String],
        description: &str,
        vote_hint: Option<String>,
        metadata_lines: &[String],
    ) -> CliResult<usize> {
        if participants.is_empty() {
            return Ok(0);
        }
        let mailbox = Mailbox::new()?;
        let mut lines = vec![
            format!("A new {kind} is available."),
            String::new(),
            format!("ID: {ballot_id}"),
            format!("Title: {title}"),
        ];
        for line in metadata_lines {
            if !line.trim().is_empty() {
                lines.push(line.clone());
            }
        }
        if !description.trim().is_empty() {
            lines.push(String::new());
            lines.push(description.trim().to_string());
        }
        let response_hint =
            vote_hint.unwrap_or_else(|| format!("`mailbox vote-{kind} --id {ballot_id}`"));
        lines.push(String::new());
        lines.push(format!(
            "Use `mailbox show-{kind} --id {ballot_id}` to inspect it and {response_hint} to respond."
        ));
        let body = lines.join("\n");

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
        fs::create_dir_all(&self.motions_root).map_err(|err| err.to_string())?;
        Ok(())
    }

    fn refresh_motion_status(&self, mut motion: Motion) -> CliResult<Motion> {
        if motion.status != "open" {
            return Ok(motion);
        }

        let mut yes_votes = 0usize;
        let mut total_votes = 0usize;
        for entry in read_vote_files(&self.motions_root.join(&motion.id))? {
            let vote: MotionVote = match read_json(&entry) {
                Ok(vote) => vote,
                Err(_) => continue,
            };
            total_votes += 1;
            if vote.vote == "yes" {
                yes_votes += 1;
            }
        }
        let remaining_votes = motion.participants.len().saturating_sub(total_votes);
        if yes_votes >= motion.required_yes && total_votes >= motion.quorum {
            motion.status = "accepted".to_string();
        } else if yes_votes + remaining_votes < motion.required_yes
            || total_votes >= motion.participants.len()
        {
            motion.status = "rejected".to_string();
        }

        if motion.status != "open" {
            write_json(
                &self.motions_root.join(&motion.id).join("definition.json"),
                &motion,
            )?;
        }

        Ok(motion)
    }
}

fn ensure_unique(values: &[String], message: &str) -> CliResult<()> {
    let mut seen = BTreeSet::new();
    for value in values {
        if !seen.insert(value) {
            return Err(message.to_string());
        }
    }
    Ok(())
}

fn validate_motion_thresholds(
    participants: &[String],
    quorum: Option<usize>,
    required_yes: Option<usize>,
) -> CliResult<(usize, usize)> {
    let participant_count = participants.len();
    let quorum_value = quorum.unwrap_or(participant_count);
    let required_yes_value = required_yes.unwrap_or(quorum_value);

    if quorum_value < 1 {
        return Err("Motion quorum must be at least 1".to_string());
    }
    if quorum_value > participant_count {
        return Err("Motion quorum cannot exceed participant count".to_string());
    }
    if required_yes_value < 1 {
        return Err("Motion required yes votes must be at least 1".to_string());
    }
    if required_yes_value > participant_count {
        return Err("Motion required yes votes cannot exceed participant count".to_string());
    }

    Ok((quorum_value, required_yes_value))
}

fn read_dirs(root: &Path) -> CliResult<Vec<PathBuf>> {
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

fn read_vote_files(dir: &Path) -> CliResult<Vec<PathBuf>> {
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
    use super::{BallotBox, MotionSpec};
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

    #[test]
    fn motion_accepts_when_quorum_and_yes_threshold_met() {
        let root = TempDir::new().expect("temp");
        env::set_var("MAILBOX_SHARED", root.path().join("shared-root"));
        let ballot_box = BallotBox::new();
        let motion = ballot_box
            .create_motion(MotionSpec {
                title: "Pause deploy".into(),
                created_by: "orchestrator".into(),
                participants: vec!["agent1".into(), "agent2".into(), "agent3".into()],
                description: Some("Stop work and report status".into()),
                scope: Some("cluster".into()),
                quorum: Some(2),
                required_yes: Some(2),
                blocking: true,
            })
            .expect("create motion");
        ballot_box
            .vote_motion(&motion.id, "agent1", "yes", Some("Acknowledged".into()))
            .expect("vote one");
        let state = ballot_box
            .vote_motion(&motion.id, "agent2", "yes", Some("Ready".into()))
            .expect("vote two");
        assert_eq!(state["motion"]["status"], "accepted");
    }
}
