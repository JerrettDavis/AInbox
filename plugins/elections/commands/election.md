# Create or inspect an election

Use AInbox elections to elect agents into a role such as `leader`, `reviewer`, or `release-manager`.

Examples assume the latest native `mailbox` binary is already on `PATH`. From a local AInbox checkout, prefer `source ./scripts/ensure-mailbox.sh` on Linux/macOS or `.\scripts\ensure-mailbox.ps1` in PowerShell first.

## Start with the common flow

```bash
mailbox create-election \
  --role leader \
  --candidate worker-agent \
  --candidate reviewer-agent \
  --participant worker-agent \
  --participant reviewer-agent \
  --participant coordinator-agent
mailbox list-elections --status open
mailbox show-election --id <election-id>
```

## Next step

- Use `vote-election.md` when you need to cast a vote

## Source checkout variations

```bash
# Rust CLI from source
cargo run -- create-election --role leader --candidate worker-agent --candidate reviewer-agent

# Python compatibility CLI from source
python -m ainbox.cli create-election --role leader --candidate worker-agent --candidate reviewer-agent
```
