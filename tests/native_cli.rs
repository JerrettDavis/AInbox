use serde_json::Value;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

fn mailbox_bin() -> &'static str {
    env!("CARGO_BIN_EXE_mailbox")
}

fn create_workspace(root: &Path, name: &str) -> PathBuf {
    let path = root.join(name);
    fs::create_dir_all(&path).expect("create workspace");
    path
}

fn run_ok(current_dir: &Path, agent_id: &str, shared: &Path, args: &[&str]) -> String {
    let output = Command::new(mailbox_bin())
        .current_dir(current_dir)
        .env("MAILBOX_AGENT_ID", agent_id)
        .env("MAILBOX_SHARED", shared)
        .args(args)
        .output()
        .expect("run mailbox");

    assert!(
        output.status.success(),
        "command failed: {:?}\nstdout:\n{}\nstderr:\n{}",
        args,
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr)
    );

    String::from_utf8(output.stdout).expect("stdout utf8")
}

fn run_err(current_dir: &Path, agent_id: &str, shared: &Path, args: &[&str]) -> (i32, String) {
    let output = Command::new(mailbox_bin())
        .current_dir(current_dir)
        .env("MAILBOX_AGENT_ID", agent_id)
        .env("MAILBOX_SHARED", shared)
        .args(args)
        .output()
        .expect("run mailbox");

    let code = output.status.code().unwrap_or(-1);
    assert_ne!(code, 0, "command unexpectedly succeeded: {:?}", args);
    (code, String::from_utf8(output.stderr).expect("stderr utf8"))
}

#[test]
fn native_cli_round_trip_sync_and_read() {
    let temp = tempfile::tempdir().expect("tempdir");
    let shared = temp.path().join("shared-root");
    let worker = create_workspace(temp.path(), "worker");
    let reviewer = create_workspace(temp.path(), "reviewer");

    run_ok(&worker, "worker-agent", &shared, &["init"]);
    run_ok(&reviewer, "reviewer-agent", &shared, &["init"]);

    run_ok(
        &worker,
        "worker-agent",
        &shared,
        &[
            "send",
            "--to",
            "reviewer-agent",
            "--subject",
            "Review request",
            "--body",
            "Please review this change.",
            "--correlation-id",
            "task-123",
        ],
    );
    run_ok(&worker, "worker-agent", &shared, &["sync", "--push-only"]);
    run_ok(
        &reviewer,
        "reviewer-agent",
        &shared,
        &["sync", "--pull-only"],
    );

    let inbox = run_ok(
        &reviewer,
        "reviewer-agent",
        &shared,
        &["list", "--format", "json"],
    );
    let messages: Value = serde_json::from_str(&inbox).expect("parse inbox");
    let id = messages[0]["id"].as_str().expect("message id");
    assert_eq!(messages[0]["subject"], "Review request");
    assert_eq!(messages[0]["correlation_id"], "task-123");

    let message = run_ok(&reviewer, "reviewer-agent", &shared, &["read", "--id", id]);
    assert!(message.contains("subject: Review request"));
    assert!(message.contains("Please review this change."));

    let archived = reviewer.join(".mailbox").join("archive");
    assert!(
        fs::read_dir(archived)
            .expect("archive listing")
            .next()
            .is_some(),
        "expected read message to be archived"
    );
}

#[test]
fn native_cli_ballots_notify_and_block_self_vote() {
    let temp = tempfile::tempdir().expect("tempdir");
    let shared = temp.path().join("shared-root");
    let leader = create_workspace(temp.path(), "leader");
    let reviewer = create_workspace(temp.path(), "reviewer");

    run_ok(&leader, "leader-agent", &shared, &["init"]);
    run_ok(&reviewer, "reviewer-agent", &shared, &["init"]);

    let created = run_ok(
        &leader,
        "leader-agent",
        &shared,
        &[
            "create-poll",
            "--question",
            "Which database should we use?",
            "--option",
            "PostgreSQL",
            "--option",
            "MySQL",
            "--participant",
            "reviewer-agent",
            "--format",
            "json",
        ],
    );
    let poll: Value = serde_json::from_str(&created).expect("parse poll");
    assert_eq!(poll["notifications_sent"], 1);
    let poll_id = poll["id"].as_str().expect("poll id");

    run_ok(
        &reviewer,
        "reviewer-agent",
        &shared,
        &["sync", "--pull-only"],
    );
    let inbox = run_ok(
        &reviewer,
        "reviewer-agent",
        &shared,
        &["list", "--format", "json"],
    );
    assert!(inbox.contains("poll:"));

    run_ok(
        &reviewer,
        "reviewer-agent",
        &shared,
        &["vote-poll", "--id", poll_id, "--option", "PostgreSQL"],
    );
    let poll_details = run_ok(
        &leader,
        "leader-agent",
        &shared,
        &["show-poll", "--id", poll_id, "--format", "json"],
    );
    let tally: Value = serde_json::from_str(&poll_details).expect("parse tally");
    assert_eq!(tally["votes"]["votes"]["PostgreSQL"], 1);

    let election_created = run_ok(
        &leader,
        "leader-agent",
        &shared,
        &[
            "create-election",
            "--role",
            "leader",
            "--candidate",
            "leader-agent",
            "--candidate",
            "reviewer-agent",
            "--participant",
            "leader-agent",
            "--participant",
            "reviewer-agent",
            "--format",
            "json",
        ],
    );
    let election: Value = serde_json::from_str(&election_created).expect("parse election");
    let election_id = election["id"].as_str().expect("election id");

    let (code, stderr) = run_err(
        &leader,
        "leader-agent",
        &shared,
        &[
            "vote-election",
            "--id",
            election_id,
            "--candidate",
            "leader-agent",
        ],
    );
    assert_eq!(code, 3);
    assert!(stderr.contains("Cannot vote for yourself"));
}
