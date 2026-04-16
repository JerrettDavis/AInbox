"""Command-line interface."""

import sys
import argparse
from pathlib import Path

from . import __version__
from .mailbox import Mailbox
from .util import get_local_mailbox, get_agent_id


def cmd_init(args):
    """Handle 'mailbox init' command."""
    mailbox = Mailbox()
    mailbox.init()


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
    p_init.set_defaults(func=cmd_init)
    
    # send
    p_send = subparsers.add_parser("send", help="Send a message")
    p_send.add_argument("--to", required=True, help="Recipient agent ID")
    p_send.add_argument("--subject", required=True, help="Message subject")
    p_send.add_argument("--body", help="Message body (reads from stdin if not provided)")
    p_send.add_argument("--correlation-id", help="Optional correlation ID for threading")
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
