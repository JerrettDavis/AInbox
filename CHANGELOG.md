# Changelog

All notable changes to this project will be documented in this file.

## v0.2.8 - 2026-06-23

### Other
- add CodeQL security scanning (#8) (e663fc7)

## v0.2.7 - 2026-06-22

### Other
- bump actions/checkout (#7) (b670648)

## v0.2.6 - 2026-06-16

### Other
- bump typescript in /channel in the npm-dependencies group (#6) (b52c7df)

## v0.2.5 - 2026-06-16

### Other
- harden grouped dependency updates (2f08588)

## v0.2.4 - 2026-06-15

### Other
- bump the all-dependencies group across 1 directory with 2 updates (#5) (3bc9cc3)

## v0.2.3 - 2026-06-02

### Other
- bump serde_json in the all-dependencies group (#3) (6288e9f)

## v0.2.2 - 2026-05-25

### Other
- bump the all-dependencies group with 6 updates (#2) (239e533)

## v0.2.1 - 2026-05-22

### Other
- configure dependabot grouping, conventional commits, and cooldown (c1060c4)

## v0.2.0 - 2026-04-30

### Features
- add MCP push channel for mailbox events (#1) (9422934)

## v0.1.14 - 2026-04-21

### Other
- Add motion-based consensus gates (b52b246)

## v0.1.13 - 2026-04-21

### Other
- Add message TTL and DLQ routing (0f2f6a7)

## v0.1.12 - 2026-04-21

### Other
- Use mailbox drafts as memory (aaea3f9)

## v0.1.11 - 2026-04-21

### Other
- Add headless mailbox workflow test (5fa2545)

## v0.1.10 - 2026-04-21

### Other
- Document AInbox subagent usage (d142783)

## v0.1.9 - 2026-04-21

### Other
- Consolidate repo documentation (9672499)

## v0.1.8 - 2026-04-21

### Other
- Audit AInbox documentation (a1c6a92)

## v0.1.7 - 2026-04-21

### Other
- Refresh mailbox init docs (06525c1)

## v0.1.5 - 2026-04-21

### Other
- Add `mailbox init -g` global bootstrap for supported agent integrations (991f998)
- Auto-bootstrap mailbox with hooks (4a512c5)

## v0.1.4 - 2026-04-21

### Other
- Add safe mailbox ensure helpers (b0b50ff)

## v0.1.3 - 2026-04-21

### Other
- Prefer native mailbox binaries in prompts (682a6dc)

## v0.1.2 - 2026-04-21

### Other
- Disambiguate release pushes to main branch (baa6174)
- Publish releases from SemVer tags (5f2ca84)

## v0.1.1 - 2026-04-21

### Other
- Keep plugin versions aligned with SemVer releases (f27a65b)
- Enforce SemVer alignment for release and plugin versions (58df6c0)

## v0.1.0 - 2026-04-21

### Features
- Add first-class poll and election support (9a47944)

### Other
- Fix release prep parsing for empty commit bodies (82b8cf7)
- Switch releases to direct main-based tagging (3dfd2c5)
- Show Python and Rust command variants (157feeb)
- Add GitHub release and validation pipelines (4ed55dd)
- Tighten skill progressive disclosure (68fd480)
- Split marketplace sources by client (ab88a51)
- Split Claude and Copilot manifests (f0a5ec3)
- Fix marketplace plugin root (577712e)
- Use supported Intel macOS runners (824a1a6)
- Fix Unix installer line endings (2870cd5)
- Ship release artifacts and installers (b5baa18)
- Add native Rust mailbox runtime (c0a5fbf)
- Add orchestrator and project manager agents (3ab33ca)
- Add poll and election plugins (0547269)
- Update Claude marketplace commands (c2d52de)
- Add CI validation workflows (401e9e8)
- Add plugin marketplace manifests (3732e39)
- Initial commit: AInbox project implementation (87ecb50)
