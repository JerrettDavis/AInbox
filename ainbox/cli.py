"""Command-line interface."""

import sys
import argparse
import json

from . import __version__
from .global_init import ensure_global_integrations
from .mailbox import Mailbox
from .ballot import BallotBox
from .util import get_local_mailbox, get_agent_id


def _expand_values(raw_values, label):
    """Expand repeated, JSON-list, or comma-separated values."""
    values = []
    for raw in raw_values or []:
        if raw is None:
            continue

        text = raw.strip()
        if not text:
            continue

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None

        if isinstance(parsed, list):
            for item in parsed:
                item_text = str(item).strip()
                if item_text:
                    values.append(item_text)
            continue

        if "," in text:
            parts = [part.strip() for part in text.split(",") if part.strip()]
            if len(parts) > 1:
                values.extend(parts)
                continue

        values.append(text)

    if not values:
        raise ValueError(f"Provide at least one {label}. Repeat the flag, pass a JSON list, or use a comma-separated value.")

    return values


def _notify_participants(kind, ballot_id, title, participants, description=""):
    """Send mailbox notifications to ballot participants and push them immediately."""
    if not participants:
        return 0

    mailbox = Mailbox()
    body = (
        f"A new {kind} is available.\n\n"
        f"ID: {ballot_id}\n"
        f"Title: {title}\n"
        f"{description.strip()}\n\n"
        f"Use `mailbox show-{kind} --id {ballot_id}` to inspect it and "
        f"`mailbox vote-{kind} --id {ballot_id}` to respond."
    ).strip()

    sent = 0
    for participant in participants:
        mailbox.send(
            to=participant,
            subject=f"{kind.capitalize()} open: {title}",
            body=body,
            correlation_id=f"{kind}:{ballot_id}",
        )
        sent += 1

    mailbox.sync(push_only=True)
    return sent


def _init_local_mailbox() -> None:
    mailbox_root = get_local_mailbox()
    for folder in ["inbox", "outbox", "sent", "archive", "draft"]:
        (mailbox_root / folder).mkdir(parents=True, exist_ok=True)
    print(f"Initialized mailbox at {mailbox_root}")


def cmd_init(args):
    """Handle 'mailbox init' command."""
    _init_local_mailbox()
    if args.global_install:
        summaries = ensure_global_integrations()
        print("Global agent integration:")
        for summary in summaries:
            print(f"- {summary}")


def cmd_send(args):
    """Handle 'mailbox send' command."""
    if not args.to or not args.subject:
        print("Error: --to and --subject are required", file=sys.stderr)
        sys.exit(2)
    
    # Read body from stdin if not provided
    body = args.body
    if body is None or body == "-":
        body = sys.stdin.read()
    
    mailbox = Mailbox()
    filepath = mailbox.send(
        to=args.to,
        subject=args.subject,
        body=body,
        correlation_id=args.correlation_id,
        expires_at=args.expires_at,
    )
    print(f"Message created: {filepath}")


def cmd_list(args):
    """Handle 'mailbox list' command."""
    mailbox = Mailbox()
    messages = mailbox.list_inbox(limit=args.limit)
    
    if not messages:
        print("No messages in inbox")
        return
    
    if args.format == "json":
        import json
        data = []
        for msg in messages:
            data.append({
                "id": msg.id,
                "from": msg.from_,
                "subject": msg.subject,
                "sent_at": msg.sent_at,
                "to": msg.to,
                "correlation_id": msg.correlation_id,
                "expires_at": msg.expires_at,
            })
        print(json.dumps(data, indent=2))
    else:
        print(f"Inbox: {len(messages)} message(s)")
        print()
        for i, msg in enumerate(messages, 1):
            print(f"{i}. From: {msg.from_}")
            print(f"   Subject: {msg.subject}")
            print(f"   ID: {msg.id}")
            print(f"   Sent: {msg.sent_at}")
            if msg.correlation_id:
                print(f"   Thread: {msg.correlation_id}")
            if msg.expires_at:
                print(f"   Expires: {msg.expires_at}")
            print()


def cmd_read(args):
    """Handle 'mailbox read' command."""
    mailbox = Mailbox()
    
    msg = mailbox.read_message(msg_id=args.id, correlation_id=args.correlation_id)
    
    if not msg:
        print("No message found", file=sys.stderr)
        sys.exit(1)
    
    print(msg.to_markdown())


def cmd_archive(args):
    """Handle 'mailbox archive' command."""
    if not args.id:
        print("Error: --id is required", file=sys.stderr)
        sys.exit(2)
    
    mailbox = Mailbox()
    if mailbox.archive_message(args.id):
        print(f"Message {args.id} archived")
    else:
        print(f"Message {args.id} not found", file=sys.stderr)
        sys.exit(1)


def cmd_sync(args):
    """Handle 'mailbox sync' command."""
    if args.push_only and args.pull_only:
        print("Error: --push-only and --pull-only are mutually exclusive", file=sys.stderr)
        sys.exit(2)
    
    mailbox = Mailbox()
    pushed, pulled = mailbox.sync(
        push_only=args.push_only,
        pull_only=args.pull_only,
    )
    print(f"Sync complete: {pushed} pushed, {pulled} pulled")


def cmd_config(args):
    """Handle 'mailbox config' command."""
    # TODO: Implement config management
    if args.list:
        print("Agent ID:", get_agent_id())
        print(f"Local mailbox: {get_local_mailbox()}")
    elif args.set:
        print("Config --set not yet implemented")


def cmd_create_poll(args):
    """Handle 'mailbox create-poll' command."""
    try:
        options = _expand_values(args.option, "option")
        participants = _expand_values(args.participant, "participant") if args.participant else None
        agent_id = get_agent_id()
        ballot_box = BallotBox()
        poll = ballot_box.create_poll(
            question=args.question,
            options=options,
            created_by=agent_id,
            participants=participants,
            description=args.description,
        )
        notifications = _notify_participants("poll", poll.id, poll.question, participants, poll.description)

        if args.format == "json":
            output = poll.to_dict()
            output["notifications_sent"] = notifications
            print(json.dumps(output, indent=2))
        else:
            print(f"Poll created: {poll.id}")
            if participants:
                print(f"Participants notified: {notifications}")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(3)


def cmd_list_polls(args):
    """Handle 'mailbox list-polls' command."""
    ballot_box = BallotBox()
    polls = ballot_box.list_polls(
        status=args.status,
        participant=args.participant,
        created_by=args.created_by,
    )
    
    if not polls:
        print("No polls found")
        return
    
    if args.format == "json":
        data = [p.to_dict() for p in polls]
        print(json.dumps(data, indent=2))
    else:
        print(f"Polls: {len(polls)} found")
        print()
        for i, poll in enumerate(polls, 1):
            print(f"{i}. {poll.question}")
            print(f"   ID: {poll.id}")
            print(f"   Created by: {poll.created_by}")
            print(f"   Status: {poll.status}")
            print(f"   Options: {', '.join(poll.options)}")
            if poll.description:
                print(f"   Description: {poll.description}")
            print()


def cmd_show_poll(args):
    """Handle 'mailbox show-poll' command."""
    if not args.id:
        print("Error: --id is required", file=sys.stderr)
        sys.exit(2)
    
    ballot_box = BallotBox()
    poll = ballot_box.get_poll(args.id)
    
    if not poll:
        print(f"Poll {args.id} not found", file=sys.stderr)
        sys.exit(1)
    
    votes = ballot_box.get_poll_votes(args.id)
    
    if args.format == "json":
        output = {
            "poll": poll.to_dict(),
            "votes": votes,
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"Poll: {poll.question}")
        print(f"ID: {poll.id}")
        print(f"Created by: {poll.created_by}")
        print(f"Status: {poll.status}")
        print(f"Options: {', '.join(poll.options)}")
        print()
        print("Votes:")
        for option in poll.options:
            count = votes["votes"].get(option, 0)
            print(f"  {option}: {count}")
        print(f"Total: {votes['total_votes']}")


def cmd_vote_poll(args):
    """Handle 'mailbox vote-poll' command."""
    if not args.id or not args.option:
        print("Error: --id and --option are required", file=sys.stderr)
        sys.exit(2)
    
    agent_id = get_agent_id()
    ballot_box = BallotBox()
    
    try:
        ballot_box.vote_poll(args.id, agent_id, args.option)
        print(f"Vote recorded: {agent_id} voted for '{args.option}'")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(3)


def cmd_close_poll(args):
    """Handle 'mailbox close-poll' command."""
    if not args.id:
        print("Error: --id is required", file=sys.stderr)
        sys.exit(2)
    
    ballot_box = BallotBox()
    
    try:
        ballot_box.close_poll(args.id)
        print(f"Poll {args.id} closed")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(3)


def cmd_create_election(args):
    """Handle 'mailbox create-election' command."""
    try:
        candidates = _expand_values(args.candidate, "candidate")
        participants = _expand_values(args.participant, "participant") if args.participant else None
        agent_id = get_agent_id()
        ballot_box = BallotBox()
        election = ballot_box.create_election(
            role=args.role,
            candidates=candidates,
            created_by=agent_id,
            participants=participants,
            description=args.description,
        )
        notifications = _notify_participants("election", election.id, election.role, participants, election.description)

        if args.format == "json":
            output = election.to_dict()
            output["notifications_sent"] = notifications
            print(json.dumps(output, indent=2))
        else:
            print(f"Election created: {election.id}")
            if participants:
                print(f"Participants notified: {notifications}")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(3)


def cmd_list_elections(args):
    """Handle 'mailbox list-elections' command."""
    ballot_box = BallotBox()
    elections = ballot_box.list_elections(
        status=args.status,
        participant=args.participant,
        created_by=args.created_by,
    )
    
    if not elections:
        print("No elections found")
        return
    
    if args.format == "json":
        data = [e.to_dict() for e in elections]
        print(json.dumps(data, indent=2))
    else:
        print(f"Elections: {len(elections)} found")
        print()
        for i, election in enumerate(elections, 1):
            print(f"{i}. Role: {election.role}")
            print(f"   ID: {election.id}")
            print(f"   Created by: {election.created_by}")
            print(f"   Status: {election.status}")
            print(f"   Candidates: {', '.join(election.candidates)}")
            if election.description:
                print(f"   Description: {election.description}")
            print()


def cmd_show_election(args):
    """Handle 'mailbox show-election' command."""
    if not args.id:
        print("Error: --id is required", file=sys.stderr)
        sys.exit(2)
    
    ballot_box = BallotBox()
    election = ballot_box.get_election(args.id)
    
    if not election:
        print(f"Election {args.id} not found", file=sys.stderr)
        sys.exit(1)
    
    votes = ballot_box.get_election_votes(args.id)
    
    if args.format == "json":
        output = {
            "election": election.to_dict(),
            "votes": votes,
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"Election: {election.role}")
        print(f"ID: {election.id}")
        print(f"Created by: {election.created_by}")
        print(f"Status: {election.status}")
        print(f"Candidates: {', '.join(election.candidates)}")
        print()
        print("Votes:")
        for candidate in election.candidates:
            count = votes["votes"].get(candidate, 0)
            print(f"  {candidate}: {count}")
        print(f"Total: {votes['total_votes']}")


def cmd_vote_election(args):
    """Handle 'mailbox vote-election' command."""
    if not args.id or not args.candidate:
        print("Error: --id and --candidate are required", file=sys.stderr)
        sys.exit(2)
    
    agent_id = get_agent_id()
    ballot_box = BallotBox()
    
    try:
        ballot_box.vote_election(args.id, agent_id, args.candidate)
        print(f"Vote recorded: {agent_id} voted for {args.candidate}")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(3)


def cmd_close_election(args):
    """Handle 'mailbox close-election' command."""
    if not args.id:
        print("Error: --id is required", file=sys.stderr)
        sys.exit(2)
    
    ballot_box = BallotBox()
    
    try:
        ballot_box.close_election(args.id)
        print(f"Election {args.id} closed")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(3)


def _create_parser():
    """Create and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="mailbox",
        description="Filesystem-based async mailbox for coding agents",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # init
    p_init = subparsers.add_parser("init", help="Initialize mailbox")
    p_init.add_argument("-g", "--global", dest="global_install", action="store_true", help="Install or update supported agent integrations globally")
    p_init.set_defaults(func=cmd_init)
    
    # send
    p_send = subparsers.add_parser("send", help="Send a message")
    p_send.add_argument("--to", required=True, help="Recipient agent ID")
    p_send.add_argument("--subject", required=True, help="Message subject")
    p_send.add_argument("--body", help="Message body (reads from stdin if not provided)")
    p_send.add_argument("--correlation-id", help="Optional correlation ID for threading")
    p_send.add_argument("--expires-at", help="Optional ISO 8601 UTC expiry like 2026-04-21T04:00:00Z")
    p_send.set_defaults(func=cmd_send)
    
    # list
    p_list = subparsers.add_parser("list", help="List inbox messages")
    p_list.add_argument("--limit", type=int, default=10, help="Limit results (default: 10)")
    p_list.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    p_list.set_defaults(func=cmd_list)
    
    # read
    p_read = subparsers.add_parser("read", help="Read a message")
    p_read.add_argument("--id", help="Message ID (reads first if not provided)")
    p_read.add_argument("--correlation-id", help="Filter by correlation ID")
    p_read.set_defaults(func=cmd_read)
    
    # archive
    p_archive = subparsers.add_parser("archive", help="Archive a message")
    p_archive.add_argument("--id", required=True, help="Message ID")
    p_archive.set_defaults(func=cmd_archive)
    
    # sync
    p_sync = subparsers.add_parser("sync", help="Sync mailbox (push and/or pull)")
    p_sync.add_argument("--push-only", action="store_true", help="Only push, don't pull (mutually exclusive with --pull-only)")
    p_sync.add_argument("--pull-only", action="store_true", help="Only pull, don't push (mutually exclusive with --push-only)")
    p_sync.set_defaults(func=cmd_sync)
    
    # config
    p_config = subparsers.add_parser("config", help="Manage configuration")
    p_config.add_argument("--list", action="store_true", help="List current config")
    p_config.add_argument("--set", nargs=2, metavar=("KEY", "VALUE"), help="Set config value")
    p_config.set_defaults(func=cmd_config)
    
    # help
    p_help = subparsers.add_parser("help", help="Show help")
    p_help.set_defaults(func=cmd_help)
    
    # create-poll
    p_create_poll = subparsers.add_parser("create-poll", help="Create a poll")
    p_create_poll.add_argument("--question", required=True, help="Poll question")
    p_create_poll.add_argument("--option", action="append", required=True, help="Poll option (can be repeated)")
    p_create_poll.add_argument("--participant", action="append", help="Participant (can be repeated)")
    p_create_poll.add_argument("--description", help="Poll description")
    p_create_poll.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    p_create_poll.set_defaults(func=cmd_create_poll)
    
    # list-polls
    p_list_polls = subparsers.add_parser("list-polls", help="List polls")
    p_list_polls.add_argument("--status", choices=["open", "closed", "all"], help="Filter by status")
    p_list_polls.add_argument("--participant", help="Filter by participant")
    p_list_polls.add_argument("--created-by", help="Filter by creator")
    p_list_polls.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    p_list_polls.set_defaults(func=cmd_list_polls)
    
    # show-poll
    p_show_poll = subparsers.add_parser("show-poll", help="Show poll details and votes")
    p_show_poll.add_argument("--id", required=True, help="Poll ID")
    p_show_poll.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    p_show_poll.set_defaults(func=cmd_show_poll)
    
    # vote-poll
    p_vote_poll = subparsers.add_parser("vote-poll", help="Vote in a poll")
    p_vote_poll.add_argument("--id", required=True, help="Poll ID")
    p_vote_poll.add_argument("--option", required=True, help="Option to vote for")
    p_vote_poll.set_defaults(func=cmd_vote_poll)
    
    # close-poll
    p_close_poll = subparsers.add_parser("close-poll", help="Close a poll")
    p_close_poll.add_argument("--id", required=True, help="Poll ID")
    p_close_poll.set_defaults(func=cmd_close_poll)
    
    # create-election
    p_create_election = subparsers.add_parser("create-election", help="Create an election")
    p_create_election.add_argument("--role", required=True, help="Role being elected")
    p_create_election.add_argument("--candidate", action="append", required=True, help="Candidate (can be repeated)")
    p_create_election.add_argument("--participant", action="append", help="Participant (can be repeated)")
    p_create_election.add_argument("--description", help="Election description")
    p_create_election.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    p_create_election.set_defaults(func=cmd_create_election)
    
    # list-elections
    p_list_elections = subparsers.add_parser("list-elections", help="List elections")
    p_list_elections.add_argument("--status", choices=["open", "closed", "all"], help="Filter by status")
    p_list_elections.add_argument("--participant", help="Filter by participant")
    p_list_elections.add_argument("--created-by", help="Filter by creator")
    p_list_elections.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    p_list_elections.set_defaults(func=cmd_list_elections)
    
    # show-election
    p_show_election = subparsers.add_parser("show-election", help="Show election details and votes")
    p_show_election.add_argument("--id", required=True, help="Election ID")
    p_show_election.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    p_show_election.set_defaults(func=cmd_show_election)
    
    # vote-election
    p_vote_election = subparsers.add_parser("vote-election", help="Vote in an election")
    p_vote_election.add_argument("--id", required=True, help="Election ID")
    p_vote_election.add_argument("--candidate", required=True, help="Candidate to vote for")
    p_vote_election.set_defaults(func=cmd_vote_election)
    
    # close-election
    p_close_election = subparsers.add_parser("close-election", help="Close an election")
    p_close_election.add_argument("--id", required=True, help="Election ID")
    p_close_election.set_defaults(func=cmd_close_election)
    
    return parser


def cmd_help(args):
    """Handle 'mailbox help' command."""
    # Print the argument parser's help
    parser = _create_parser()
    parser.print_help()


def main():
    """Main CLI entry point."""
    parser = _create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(0)
    
    try:
        args.func(args)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(3)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
