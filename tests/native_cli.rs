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
    run_ok_with_env(current_dir, agent_id, shared, args, &[])
}

fn run_ok_with_env(
    current_dir: &Path,
    agent_id: &str,
    shared: &Path,
    args: &[&str],
    extra_env: &[(&str, &std::ffi::OsStr)],
) -> String {
    let output = Command::new(mailbox_bin())
        .current_dir(current_dir)
        .env("MAILBOX_AGENT_ID", agent_id)
        .env("MAILBOX_SHARED", shared)
        .envs(extra_env.iter().copied())
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

fn create_fake_agent_cli(bin_dir: &Path, name: &str) -> PathBuf {
    if cfg!(windows) {
        let wrapper = bin_dir.join(format!("{name}-fake.cmd"));
        fs::write(
            &wrapper,
            format!(
                "@echo off\r\nsetlocal\r\n>> \"%MAILBOX_GLOBAL_INIT_LOG%\" echo {name} %*\r\nif /I \"%1 %2 %3 %4\"==\"plugin marketplace update ainbox-marketplace\" exit /b 1\r\nif /I \"%1 %2\"==\"plugin update\" exit /b 1\r\nexit /b 0\r\n"
            ),
        )
        .expect("write windows wrapper");
        wrapper
    } else {
        let wrapper = bin_dir.join(format!("{name}-fake"));
        fs::write(
            &wrapper,
            format!(
                "#!/bin/sh\nprintf \"%s %s\\n\" \"{name}\" \"$*\" >> \"$MAILBOX_GLOBAL_INIT_LOG\"\nif [ \"$1 $2 $3 $4\" = \"plugin marketplace update ainbox-marketplace\" ]; then exit 1; fi\nif [ \"$1 $2\" = \"plugin update\" ]; then exit 1; fi\nexit 0\n"
            ),
        )
        .expect("write unix wrapper");
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let mut perms = fs::metadata(&wrapper)
                .expect("wrapper metadata")
                .permissions();
            perms.set_mode(0o755);
            fs::set_permissions(&wrapper, perms).expect("set wrapper perms");
        }
        wrapper
    }
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

#[test]
fn native_cli_routes_expired_messages_to_dlq() {
    let temp = tempfile::tempdir().expect("tempdir");
    let shared = temp.path().join("shared-root");
    let worker = create_workspace(temp.path(), "worker");
    let reviewer = create_workspace(temp.path(), "reviewer");
    let dlq = create_workspace(temp.path(), "dlq");

    run_ok(&worker, "worker-agent", &shared, &["init"]);
    run_ok(&reviewer, "reviewer-agent", &shared, &["init"]);
    run_ok(&dlq, "dlq", &shared, &["init"]);

    run_ok(
        &worker,
        "worker-agent",
        &shared,
        &[
            "send",
            "--to",
            "reviewer-agent",
            "--subject",
            "TTL test",
            "--body",
            "This should expire into dlq.",
            "--expires-at",
            "2099-01-01T00:00:00Z",
        ],
    );
    run_ok(&worker, "worker-agent", &shared, &["sync", "--push-only"]);

    let shared_outbox = shared.join("shared").join("outbox");
    let path = fs::read_dir(&shared_outbox)
        .expect("shared outbox")
        .next()
        .expect("message in shared outbox")
        .expect("entry")
        .path();
    let updated = fs::read_to_string(&path)
        .expect("read shared message")
        .replace("2099-01-01T00:00:00Z", "2000-01-01T00:00:00Z");
    fs::write(&path, updated).expect("rewrite shared message");

    let reviewer_pull = run_ok(&reviewer, "reviewer-agent", &shared, &["sync", "--pull-only"]);
    assert!(reviewer_pull.contains("0 pulled"));

    let dlq_pull = run_ok(&dlq, "dlq", &shared, &["sync", "--pull-only"]);
    assert!(dlq_pull.contains("1 pulled"));

    let listing = run_ok(&dlq, "dlq", &shared, &["list", "--format", "json"]);
    let messages: Value = serde_json::from_str(&listing).expect("parse dlq listing");
    let id = messages[0]["id"].as_str().expect("dlq message id");
    let message = run_ok(&dlq, "dlq", &shared, &["read", "--id", id]);
    assert!(message.contains("message_type: expired"));
    assert!(message.contains("original_subject: TTL test"));
    assert!(message.contains("This should expire into dlq."));
}

#[test]
fn native_cli_init_global_bootstraps_supported_agents() {
    let temp = tempfile::tempdir().expect("tempdir");
    let shared = temp.path().join("shared-root");
    let worker = create_workspace(temp.path(), "worker");
    let bin_dir = temp.path().join("fake-bin");
    fs::create_dir_all(&bin_dir).expect("create fake bin");
    let log_path = temp.path().join("global-init.log");
    fs::write(&log_path, "").expect("initialize global init log");
    let claude_bin = create_fake_agent_cli(&bin_dir, "claude");
    let copilot_bin = create_fake_agent_cli(&bin_dir, "copilot");

    let output = run_ok_with_env(
        &worker,
        "worker-agent",
        &shared,
        &["init", "-g"],
        &[
            ("MAILBOX_GLOBAL_INIT_LOG", log_path.as_os_str()),
            ("MAILBOX_CLAUDE_BIN", claude_bin.as_os_str()),
            ("MAILBOX_COPILOT_BIN", copilot_bin.as_os_str()),
        ],
    );
    assert!(output.contains("Initialized mailbox at"));
    assert!(output.contains("Global agent integration:"));
    assert!(output.contains("Claude Code: marketplace added;"));
    assert!(output.contains("GitHub Copilot CLI: marketplace added;"));

    let calls = fs::read_to_string(log_path).expect("read global init log");
    assert!(calls.contains("claude plugin marketplace update ainbox-marketplace"));
    assert!(calls.contains("claude plugin marketplace add JerrettDavis/AInbox"));
    assert!(calls.contains("claude plugin install ainbox@ainbox-marketplace"));
    assert!(calls.contains("copilot plugin marketplace update ainbox-marketplace"));
    assert!(calls.contains("copilot plugin install elections@ainbox-marketplace"));
}
