mod ballot;
mod global_init;
mod mailbox;
mod message;
mod util;

use ballot::{BallotBox, MotionSpec};
use clap::{ArgAction, Args, CommandFactory, Parser, Subcommand, ValueEnum};
use mailbox::Mailbox;
use serde_json::json;
use std::env;
use std::io::{self, Read};

#[derive(Parser)]
#[command(
    name = "mailbox",
    version = env!("CARGO_PKG_VERSION"),
    about = "Filesystem-based async mailbox for coding agents"
)]
struct Cli {
    #[command(subcommand)]
    command: Option<Commands>,
}

#[derive(Subcommand)]
enum Commands {
    Init(InitArgs),
    Send(SendArgs),
    List(ListArgs),
    Read(ReadArgs),
    Archive(IdArgs),
    Sync(SyncArgs),
    Config(ConfigArgs),
    CreatePoll(CreatePollArgs),
    ListPolls(ListBallotsArgs),
    ShowPoll(ShowArgs),
    VotePoll(VotePollArgs),
    ClosePoll(IdArgs),
    CreateElection(CreateElectionArgs),
    ListElections(ListBallotsArgs),
    ShowElection(ShowArgs),
    VoteElection(VoteElectionArgs),
    CloseElection(IdArgs),
    CreateMotion(CreateMotionArgs),
    ListMotions(ListBallotsArgs),
    ShowMotion(ShowArgs),
    VoteMotion(VoteMotionArgs),
    WaitMotion(WaitMotionArgs),
    CloseMotion(CloseMotionArgs),
}

#[derive(Args)]
struct InitArgs {
    #[arg(short = 'g', long = "global", action = ArgAction::SetTrue)]
    global_install: bool,
}

#[derive(Args)]
struct SendArgs {
    #[arg(long)]
    to: String,
    #[arg(long)]
    subject: String,
    #[arg(long)]
    body: Option<String>,
    #[arg(long = "correlation-id")]
    correlation_id: Option<String>,
    #[arg(long = "expires-at")]
    expires_at: Option<String>,
}

#[derive(Args)]
struct ListArgs {
    #[arg(long, default_value_t = 10)]
    limit: usize,
    #[arg(long, value_enum, default_value_t = OutputFormat::Text)]
    format: OutputFormat,
}

#[derive(Args)]
struct ReadArgs {
    #[arg(long)]
    id: Option<String>,
    #[arg(long = "correlation-id")]
    correlation_id: Option<String>,
}

#[derive(Args)]
struct SyncArgs {
    #[arg(long = "push-only", action = ArgAction::SetTrue)]
    push_only: bool,
    #[arg(long = "pull-only", action = ArgAction::SetTrue)]
    pull_only: bool,
}

#[derive(Args)]
struct ConfigArgs {
    #[arg(long, action = ArgAction::SetTrue)]
    list: bool,
    #[arg(long, num_args = 2)]
    set: Vec<String>,
}

#[derive(Args)]
struct IdArgs {
    #[arg(long)]
    id: String,
}

#[derive(Args)]
struct ShowArgs {
    #[arg(long)]
    id: String,
    #[arg(long, value_enum, default_value_t = OutputFormat::Text)]
    format: OutputFormat,
}

#[derive(Args)]
struct VotePollArgs {
    #[arg(long)]
    id: String,
    #[arg(long)]
    option: String,
}

#[derive(Args)]
struct VoteElectionArgs {
    #[arg(long)]
    id: String,
    #[arg(long)]
    candidate: String,
}

#[derive(Args)]
struct VoteMotionArgs {
    #[arg(long)]
    id: String,
    #[arg(long, value_enum)]
    vote: MotionVoteChoice,
    #[arg(long)]
    reason: Option<String>,
}

#[derive(Args)]
struct CreatePollArgs {
    #[arg(long)]
    question: String,
    #[arg(long, action = ArgAction::Append)]
    option: Vec<String>,
    #[arg(long, action = ArgAction::Append)]
    participant: Vec<String>,
    #[arg(long)]
    description: Option<String>,
    #[arg(long, value_enum, default_value_t = OutputFormat::Text)]
    format: OutputFormat,
}

#[derive(Args)]
struct CreateElectionArgs {
    #[arg(long)]
    role: String,
    #[arg(long, action = ArgAction::Append)]
    candidate: Vec<String>,
    #[arg(long, action = ArgAction::Append)]
    participant: Vec<String>,
    #[arg(long)]
    description: Option<String>,
    #[arg(long, value_enum, default_value_t = OutputFormat::Text)]
    format: OutputFormat,
}

#[derive(Args)]
struct CreateMotionArgs {
    #[arg(long)]
    title: String,
    #[arg(long, action = ArgAction::Append)]
    participant: Vec<String>,
    #[arg(long)]
    description: Option<String>,
    #[arg(long)]
    scope: Option<String>,
    #[arg(long)]
    quorum: Option<usize>,
    #[arg(long = "required-yes")]
    required_yes: Option<usize>,
    #[arg(long, action = ArgAction::SetTrue)]
    advisory: bool,
    #[arg(long, value_enum, default_value_t = OutputFormat::Text)]
    format: OutputFormat,
}

#[derive(Args)]
struct ListBallotsArgs {
    #[arg(long)]
    status: Option<String>,
    #[arg(long)]
    participant: Option<String>,
    #[arg(long = "created-by")]
    created_by: Option<String>,
    #[arg(long, value_enum, default_value_t = OutputFormat::Text)]
    format: OutputFormat,
}

#[derive(Args)]
struct WaitMotionArgs {
    #[arg(long)]
    id: String,
    #[arg(long = "timeout-seconds")]
    timeout_seconds: Option<f64>,
    #[arg(long = "poll-interval-seconds", default_value_t = 2.0)]
    poll_interval_seconds: f64,
    #[arg(long, value_enum, default_value_t = OutputFormat::Text)]
    format: OutputFormat,
}

#[derive(Args)]
struct CloseMotionArgs {
    #[arg(long)]
    id: String,
    #[arg(long, value_enum, default_value_t = MotionTerminalStatus::Cancelled)]
    status: MotionTerminalStatus,
}

#[derive(Copy, Clone, PartialEq, Eq, ValueEnum)]
enum OutputFormat {
    Text,
    Json,
}

#[derive(Copy, Clone, PartialEq, Eq, ValueEnum)]
enum MotionVoteChoice {
    Yes,
    No,
}

#[derive(Copy, Clone, PartialEq, Eq, ValueEnum)]
enum MotionTerminalStatus {
    Accepted,
    Rejected,
    Cancelled,
}

fn main() {
    let cli = Cli::parse();
    let result = match cli.command {
        None => {
            print_help();
            Ok(())
        }
        Some(command) => run(command),
    };

    if let Err((code, message)) = result {
        eprintln!("Error: {message}");
        std::process::exit(code);
    }
}

fn run(command: Commands) -> Result<(), (i32, String)> {
    match command {
        Commands::Init(args) => {
            Mailbox::init_local().map_err(error3)?;
            let current_dir = env::current_dir().map_err(|err| error1(err.to_string()))?;
            let project_memory =
                global_init::ensure_project_memory_files(&current_dir).map_err(error1)?;
            println!("Mailbox memory:");
            for summary in project_memory {
                println!("- {summary}");
            }
            if args.global_install {
                let summaries = global_init::ensure_global_integrations().map_err(error1)?;
                println!("Global agent integration:");
                for summary in summaries {
                    println!("- {summary}");
                }
            }
            Ok(())
        }
        Commands::Send(args) => {
            let body = read_body(args.body).map_err(error1)?;
            let mailbox = Mailbox::new().map_err(error3)?;
            let path = mailbox
                .send(
                    &args.to,
                    &args.subject,
                    &body,
                    args.correlation_id,
                    args.expires_at,
                )
                .map_err(error3)?;
            println!("Message created: {path}");
            Ok(())
        }
        Commands::List(args) => {
            let mailbox = Mailbox::new().map_err(error3)?;
            let messages = mailbox.list_inbox(args.limit).map_err(error3)?;
            if messages.is_empty() {
                println!("No messages in inbox");
                return Ok(());
            }
            match args.format {
                OutputFormat::Json => {
                    let data: Vec<_> = messages
                        .into_iter()
                        .map(|msg| {
                            json!({
                                "id": msg.id,
                                "from": msg.from_,
                                "subject": msg.subject,
                                "sent_at": msg.sent_at,
                                "to": msg.to,
                                "correlation_id": msg.correlation_id,
                                "expires_at": msg.expires_at,
                            })
                        })
                        .collect();
                    println!(
                        "{}",
                        serde_json::to_string_pretty(&data)
                            .map_err(|err| error1(err.to_string()))?
                    );
                }
                OutputFormat::Text => {
                    println!("Inbox: {} message(s)\n", messages.len());
                    for (idx, msg) in messages.iter().enumerate() {
                        println!("{}. From: {}", idx + 1, msg.from_);
                        println!("   Subject: {}", msg.subject);
                        println!("   ID: {}", msg.id);
                        println!("   Sent: {}", msg.sent_at);
                        if let Some(thread) = &msg.correlation_id {
                            println!("   Thread: {thread}");
                        }
                        if let Some(expires_at) = &msg.expires_at {
                            println!("   Expires: {expires_at}");
                        }
                        println!();
                    }
                }
            }
            Ok(())
        }
        Commands::Read(args) => {
            let mailbox = Mailbox::new().map_err(error3)?;
            let message = mailbox
                .read_message(args.id.as_deref(), args.correlation_id.as_deref())
                .map_err(error3)?;
            if let Some(message) = message {
                print!("{}", message.to_markdown().map_err(error3)?);
                Ok(())
            } else {
                Err((1, "No message found".to_string()))
            }
        }
        Commands::Archive(args) => {
            let mailbox = Mailbox::new().map_err(error3)?;
            match mailbox.archive_message(&args.id).map_err(error3)? {
                true => {
                    println!("Message {} archived", args.id);
                    Ok(())
                }
                false => Err((1, format!("Message {} not found", args.id))),
            }
        }
        Commands::Sync(args) => {
            let mailbox = Mailbox::new().map_err(error3)?;
            let (pushed, pulled) = mailbox
                .sync(args.push_only, args.pull_only)
                .map_err(error2_or3)?;
            println!("Sync complete: {pushed} pushed, {pulled} pulled");
            Ok(())
        }
        Commands::Config(args) => {
            if args.list {
                println!("Agent ID: {}", util::get_agent_id().map_err(error3)?);
                println!("Local mailbox: {}", util::get_local_mailbox().display());
            } else if !args.set.is_empty() {
                println!("Config --set not yet implemented");
            }
            Ok(())
        }
        Commands::CreatePoll(args) => {
            let ballot_box = BallotBox::new();
            let options = expand_values_required(&args.option, "option").map_err(error3)?;
            let participants = expand_values_optional(&args.participant)?;
            let agent_id = BallotBox::current_agent_id().map_err(error3)?;
            let poll = ballot_box
                .create_poll(
                    &args.question,
                    options,
                    &agent_id,
                    participants.clone().unwrap_or_default(),
                    args.description.clone(),
                )
                .map_err(error3)?;
            let notifications = BallotBox::notify_participants(
                "poll",
                &poll.id,
                &poll.question,
                &participants.clone().unwrap_or_default(),
                poll.description.as_str(),
                None,
                &[],
            )
            .map_err(error3)?;
            output_create_result(args.format, "Poll", &poll.id, notifications, &poll)
                .map_err(error1)
        }
        Commands::ListPolls(args) => {
            let polls = BallotBox::new()
                .list_polls(
                    args.status.as_deref(),
                    args.participant.as_deref(),
                    args.created_by.as_deref(),
                )
                .map_err(error3)?;
            if polls.is_empty() {
                println!("No polls found");
                return Ok(());
            }
            match args.format {
                OutputFormat::Json => println!(
                    "{}",
                    serde_json::to_string_pretty(&polls).map_err(|err| error1(err.to_string()))?
                ),
                OutputFormat::Text => {
                    println!("Polls: {} found\n", polls.len());
                    for (idx, poll) in polls.iter().enumerate() {
                        println!("{}. {}", idx + 1, poll.question);
                        println!("   ID: {}", poll.id);
                        println!("   Created by: {}", poll.created_by);
                        println!("   Status: {}", poll.status);
                        println!("   Options: {}", poll.options.join(", "));
                        if !poll.description.is_empty() {
                            println!("   Description: {}", poll.description);
                        }
                        println!();
                    }
                }
            }
            Ok(())
        }
        Commands::ShowPoll(args) => {
            let ballot_box = BallotBox::new();
            let poll = ballot_box
                .get_poll(&args.id)
                .map_err(error3)?
                .ok_or_else(|| (1, format!("Poll {} not found", args.id)))?;
            let votes = ballot_box.get_poll_votes(&args.id).map_err(error3)?;
            match args.format {
                OutputFormat::Json => {
                    println!(
                        "{}",
                        serde_json::to_string_pretty(&json!({"poll": poll, "votes": votes}))
                            .map_err(|err| error1(err.to_string()))?
                    );
                }
                OutputFormat::Text => {
                    println!("Poll: {}", poll.question);
                    println!("ID: {}", poll.id);
                    println!("Created by: {}", poll.created_by);
                    println!("Status: {}", poll.status);
                    println!("Options: {}\n", poll.options.join(", "));
                    println!("Votes:");
                    let tallies = votes["votes"]
                        .as_object()
                        .ok_or_else(|| error1("Invalid vote data".to_string()))?;
                    for option in &poll.options {
                        let count = tallies
                            .get(option)
                            .and_then(|value| value.as_u64())
                            .unwrap_or(0);
                        println!("  {option}: {count}");
                    }
                    println!("Total: {}", votes["total_votes"].as_u64().unwrap_or(0));
                }
            }
            Ok(())
        }
        Commands::VotePoll(args) => {
            let agent_id = BallotBox::current_agent_id().map_err(error3)?;
            BallotBox::new()
                .vote_poll(&args.id, &agent_id, &args.option)
                .map_err(error3)?;
            println!("Vote recorded: {agent_id} voted for '{}'", args.option);
            Ok(())
        }
        Commands::ClosePoll(args) => {
            BallotBox::new().close_poll(&args.id).map_err(error3)?;
            println!("Poll {} closed", args.id);
            Ok(())
        }
        Commands::CreateElection(args) => {
            let ballot_box = BallotBox::new();
            let candidates =
                expand_values_required(&args.candidate, "candidate").map_err(error3)?;
            let participants = expand_values_optional(&args.participant)?;
            let agent_id = BallotBox::current_agent_id().map_err(error3)?;
            let election = ballot_box
                .create_election(
                    &args.role,
                    candidates,
                    &agent_id,
                    participants.clone().unwrap_or_default(),
                    args.description.clone(),
                )
                .map_err(error3)?;
            let notifications = BallotBox::notify_participants(
                "election",
                &election.id,
                &election.role,
                &participants.clone().unwrap_or_default(),
                election.description.as_str(),
                None,
                &[],
            )
            .map_err(error3)?;
            output_create_result(
                args.format,
                "Election",
                &election.id,
                notifications,
                &election,
            )
            .map_err(error1)
        }
        Commands::ListElections(args) => {
            let elections = BallotBox::new()
                .list_elections(
                    args.status.as_deref(),
                    args.participant.as_deref(),
                    args.created_by.as_deref(),
                )
                .map_err(error3)?;
            if elections.is_empty() {
                println!("No elections found");
                return Ok(());
            }
            match args.format {
                OutputFormat::Json => println!(
                    "{}",
                    serde_json::to_string_pretty(&elections)
                        .map_err(|err| error1(err.to_string()))?
                ),
                OutputFormat::Text => {
                    println!("Elections: {} found\n", elections.len());
                    for (idx, election) in elections.iter().enumerate() {
                        println!("{}. Role: {}", idx + 1, election.role);
                        println!("   ID: {}", election.id);
                        println!("   Created by: {}", election.created_by);
                        println!("   Status: {}", election.status);
                        println!("   Candidates: {}", election.candidates.join(", "));
                        if !election.description.is_empty() {
                            println!("   Description: {}", election.description);
                        }
                        println!();
                    }
                }
            }
            Ok(())
        }
        Commands::ShowElection(args) => {
            let ballot_box = BallotBox::new();
            let election = ballot_box
                .get_election(&args.id)
                .map_err(error3)?
                .ok_or_else(|| (1, format!("Election {} not found", args.id)))?;
            let votes = ballot_box.get_election_votes(&args.id).map_err(error3)?;
            match args.format {
                OutputFormat::Json => {
                    println!(
                        "{}",
                        serde_json::to_string_pretty(
                            &json!({"election": election, "votes": votes})
                        )
                        .map_err(|err| error1(err.to_string()))?
                    );
                }
                OutputFormat::Text => {
                    println!("Election: {}", election.role);
                    println!("ID: {}", election.id);
                    println!("Created by: {}", election.created_by);
                    println!("Status: {}", election.status);
                    println!("Candidates: {}\n", election.candidates.join(", "));
                    println!("Votes:");
                    let tallies = votes["votes"]
                        .as_object()
                        .ok_or_else(|| error1("Invalid vote data".to_string()))?;
                    for candidate in &election.candidates {
                        let count = tallies
                            .get(candidate)
                            .and_then(|value| value.as_u64())
                            .unwrap_or(0);
                        println!("  {candidate}: {count}");
                    }
                    println!("Total: {}", votes["total_votes"].as_u64().unwrap_or(0));
                }
            }
            Ok(())
        }
        Commands::VoteElection(args) => {
            let agent_id = BallotBox::current_agent_id().map_err(error3)?;
            BallotBox::new()
                .vote_election(&args.id, &agent_id, &args.candidate)
                .map_err(error3)?;
            println!("Vote recorded: {agent_id} voted for {}", args.candidate);
            Ok(())
        }
        Commands::CloseElection(args) => {
            BallotBox::new().close_election(&args.id).map_err(error3)?;
            println!("Election {} closed", args.id);
            Ok(())
        }
        Commands::CreateMotion(args) => {
            let ballot_box = BallotBox::new();
            let participants =
                expand_values_required(&args.participant, "participant").map_err(error3)?;
            let agent_id = BallotBox::current_agent_id().map_err(error3)?;
            let motion = ballot_box
                .create_motion(MotionSpec {
                    title: args.title.clone(),
                    created_by: agent_id.clone(),
                    participants: participants.clone(),
                    description: args.description.clone(),
                    scope: args.scope.clone(),
                    quorum: args.quorum,
                    required_yes: args.required_yes,
                    blocking: !args.advisory,
                })
                .map_err(error3)?;
            let metadata = vec![
                format!(
                    "Scope: {}",
                    if motion.scope.is_empty() {
                        "cluster"
                    } else {
                        motion.scope.as_str()
                    }
                ),
                format!("Blocking: {}", if motion.blocking { "yes" } else { "no" }),
                format!("Quorum: {}", motion.quorum),
                format!("Required yes: {}", motion.required_yes),
            ];
            let notifications = BallotBox::notify_participants(
                "motion",
                &motion.id,
                &motion.title,
                &participants,
                motion.description.as_str(),
                Some(format!(
                    "`mailbox vote-motion --id {} --vote yes|no`",
                    motion.id
                )),
                &metadata,
            )
            .map_err(error3)?;
            output_create_result(args.format, "Motion", &motion.id, notifications, &motion)
                .map_err(error1)
        }
        Commands::ListMotions(args) => {
            let motions = BallotBox::new()
                .list_motions(
                    args.status.as_deref(),
                    args.participant.as_deref(),
                    args.created_by.as_deref(),
                )
                .map_err(error3)?;
            if motions.is_empty() {
                println!("No motions found");
                return Ok(());
            }
            match args.format {
                OutputFormat::Json => println!(
                    "{}",
                    serde_json::to_string_pretty(&motions)
                        .map_err(|err| error1(err.to_string()))?
                ),
                OutputFormat::Text => {
                    println!("Motions: {} found\n", motions.len());
                    for (idx, motion) in motions.iter().enumerate() {
                        println!("{}. {}", idx + 1, motion.title);
                        println!("   ID: {}", motion.id);
                        println!("   Created by: {}", motion.created_by);
                        println!("   Status: {}", motion.status);
                        println!(
                            "   Blocking: {}",
                            if motion.blocking { "yes" } else { "no" }
                        );
                        println!(
                            "   Scope: {}",
                            if motion.scope.is_empty() {
                                "cluster"
                            } else {
                                motion.scope.as_str()
                            }
                        );
                        println!("   Quorum: {}", motion.quorum);
                        println!("   Required yes: {}", motion.required_yes);
                        if !motion.description.is_empty() {
                            println!("   Description: {}", motion.description);
                        }
                        println!();
                    }
                }
            }
            Ok(())
        }
        Commands::ShowMotion(args) => {
            let state = BallotBox::new()
                .get_motion_state(&args.id)
                .map_err(|message| {
                    if message.contains("not found") {
                        (1, message)
                    } else {
                        error3(message)
                    }
                })?;
            match args.format {
                OutputFormat::Json => println!(
                    "{}",
                    serde_json::to_string_pretty(&state).map_err(|err| error1(err.to_string()))?
                ),
                OutputFormat::Text => print_motion_state_text(&state)?,
            }
            Ok(())
        }
        Commands::VoteMotion(args) => {
            let agent_id = BallotBox::current_agent_id().map_err(error3)?;
            let state = BallotBox::new()
                .vote_motion(
                    &args.id,
                    &agent_id,
                    match args.vote {
                        MotionVoteChoice::Yes => "yes",
                        MotionVoteChoice::No => "no",
                    },
                    args.reason,
                )
                .map_err(error3)?;
            println!(
                "Vote recorded: {agent_id} voted {}",
                match args.vote {
                    MotionVoteChoice::Yes => "yes",
                    MotionVoteChoice::No => "no",
                }
            );
            println!(
                "Motion status: {}",
                state["motion"]["status"].as_str().unwrap_or("open")
            );
            Ok(())
        }
        Commands::WaitMotion(args) => {
            let state = BallotBox::new()
                .wait_for_motion(&args.id, args.timeout_seconds, args.poll_interval_seconds)
                .map_err(|message| {
                    if message.contains("Timed out waiting for motion") {
                        (5, message)
                    } else {
                        error3(message)
                    }
                })?;
            match args.format {
                OutputFormat::Json => println!(
                    "{}",
                    serde_json::to_string_pretty(&state).map_err(|err| error1(err.to_string()))?
                ),
                OutputFormat::Text => {
                    println!(
                        "Motion {} resolved: {}",
                        state["motion"]["id"].as_str().unwrap_or(""),
                        state["motion"]["status"].as_str().unwrap_or("open")
                    );
                    println!(
                        "Votes yes/no: {}/{}",
                        state["votes"]["votes"]["yes"].as_u64().unwrap_or(0),
                        state["votes"]["votes"]["no"].as_u64().unwrap_or(0)
                    );
                }
            }
            if state["motion"]["status"].as_str() != Some("accepted") {
                return Err((4, format!("Motion {} did not reach acceptance", args.id)));
            }
            Ok(())
        }
        Commands::CloseMotion(args) => {
            let status = match args.status {
                MotionTerminalStatus::Accepted => "accepted",
                MotionTerminalStatus::Rejected => "rejected",
                MotionTerminalStatus::Cancelled => "cancelled",
            };
            BallotBox::new()
                .close_motion(&args.id, status)
                .map_err(error3)?;
            println!("Motion {} marked {}", args.id, status);
            Ok(())
        }
    }
}

fn expand_values(values: &[String]) -> Result<Vec<String>, String> {
    let mut expanded = Vec::new();
    for raw in values {
        let text = raw.trim();
        if text.is_empty() {
            continue;
        }

        if let Ok(parsed) = serde_json::from_str::<Vec<String>>(text) {
            expanded.extend(parsed.into_iter().filter(|value| !value.trim().is_empty()));
            continue;
        }

        if text.contains(',') {
            let parts: Vec<String> = text
                .split(',')
                .map(|part| part.trim().to_string())
                .filter(|part| !part.is_empty())
                .collect();
            if parts.len() > 1 {
                expanded.extend(parts);
                continue;
            }
        }

        expanded.push(text.to_string());
    }

    if expanded.is_empty() {
        return Ok(vec![]);
    }

    Ok(expanded)
}

fn expand_values_required(values: &[String], label: &str) -> Result<Vec<String>, String> {
    let expanded = expand_values(values)?;
    if expanded.is_empty() {
        Err(format!(
            "Provide at least one {label}. Repeat the flag, pass a JSON list, or use a comma-separated value."
        ))
    } else {
        Ok(expanded)
    }
}

fn expand_values_optional(values: &[String]) -> Result<Option<Vec<String>>, (i32, String)> {
    let expanded = expand_values(values).map_err(error3)?;
    if expanded.is_empty() {
        Ok(None)
    } else {
        Ok(Some(expanded))
    }
}

fn output_create_result<T: serde::Serialize>(
    format: OutputFormat,
    label: &str,
    id: &str,
    notifications: usize,
    value: &T,
) -> Result<(), String> {
    match format {
        OutputFormat::Json => {
            let mut object = serde_json::to_value(value).map_err(|err| err.to_string())?;
            if let Some(map) = object.as_object_mut() {
                map.insert("notifications_sent".to_string(), json!(notifications));
            }
            println!(
                "{}",
                serde_json::to_string_pretty(&object).map_err(|err| err.to_string())?
            );
        }
        OutputFormat::Text => {
            println!("{label} created: {id}");
            if notifications > 0 {
                println!("Participants notified: {notifications}");
            }
        }
    }
    Ok(())
}

fn print_motion_state_text(state: &serde_json::Value) -> Result<(), (i32, String)> {
    let motion = state["motion"]
        .as_object()
        .ok_or_else(|| error1("Invalid motion state".to_string()))?;
    let votes = state["votes"]
        .as_object()
        .ok_or_else(|| error1("Invalid motion votes".to_string()))?;

    println!(
        "Motion: {}",
        motion
            .get("title")
            .and_then(|value| value.as_str())
            .unwrap_or("")
    );
    println!(
        "ID: {}",
        motion
            .get("id")
            .and_then(|value| value.as_str())
            .unwrap_or("")
    );
    println!(
        "Created by: {}",
        motion
            .get("created_by")
            .and_then(|value| value.as_str())
            .unwrap_or("")
    );
    println!(
        "Status: {}",
        motion
            .get("status")
            .and_then(|value| value.as_str())
            .unwrap_or("")
    );
    println!(
        "Blocking: {}",
        if motion
            .get("blocking")
            .and_then(|value| value.as_bool())
            .unwrap_or(true)
        {
            "yes"
        } else {
            "no"
        }
    );
    println!(
        "Scope: {}",
        motion
            .get("scope")
            .and_then(|value| value.as_str())
            .filter(|value| !value.is_empty())
            .unwrap_or("cluster")
    );
    println!(
        "Quorum: {}",
        motion
            .get("quorum")
            .and_then(|value| value.as_u64())
            .unwrap_or(0)
    );
    println!(
        "Required yes: {}",
        motion
            .get("required_yes")
            .and_then(|value| value.as_u64())
            .unwrap_or(0)
    );
    let participants = motion
        .get("participants")
        .and_then(|value| value.as_array())
        .map(|items| {
            items
                .iter()
                .filter_map(|value| value.as_str())
                .collect::<Vec<_>>()
                .join(", ")
        })
        .unwrap_or_default();
    println!("Participants: {participants}");
    if let Some(description) = motion.get("description").and_then(|value| value.as_str()) {
        if !description.is_empty() {
            println!("Description: {description}");
        }
    }
    println!();
    println!(
        "Votes yes/no: {}/{}",
        votes["votes"]["yes"].as_u64().unwrap_or(0),
        votes["votes"]["no"].as_u64().unwrap_or(0)
    );
    println!(
        "Total votes: {}",
        votes["total_votes"].as_u64().unwrap_or(0)
    );
    let remaining = votes
        .get("remaining_voters")
        .and_then(|value| value.as_array())
        .map(|items| {
            items
                .iter()
                .filter_map(|value| value.as_str())
                .collect::<Vec<_>>()
                .join(", ")
        })
        .unwrap_or_default();
    println!(
        "Remaining voters: {}",
        if remaining.is_empty() {
            "none"
        } else {
            &remaining
        }
    );
    if let Some(responses) = votes.get("responses").and_then(|value| value.as_array()) {
        if !responses.is_empty() {
            println!("Responses:");
            for response in responses {
                let voter = response["voter"].as_str().unwrap_or("");
                let vote = response["vote"].as_str().unwrap_or("");
                let reason = response["reason"].as_str().unwrap_or("").trim();
                if reason.is_empty() {
                    println!("  {voter}: {vote}");
                } else {
                    println!("  {voter}: {vote} - {reason}");
                }
            }
        }
    }
    Ok(())
}

fn read_body(body: Option<String>) -> Result<String, String> {
    match body {
        Some(value) if value != "-" => Ok(value),
        _ => {
            let mut buffer = String::new();
            io::stdin()
                .read_to_string(&mut buffer)
                .map_err(|err| err.to_string())?;
            Ok(buffer)
        }
    }
}

fn print_help() {
    Cli::command().print_help().expect("help");
    println!();
}

fn error1(message: String) -> (i32, String) {
    (1, message)
}

fn error3(message: String) -> (i32, String) {
    (3, message)
}

fn error2_or3(message: String) -> (i32, String) {
    if message.contains("mutually exclusive") {
        (2, message)
    } else {
        (3, message)
    }
}
