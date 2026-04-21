#!/usr/bin/env python3
"""Prepare a direct-on-main release from conventional commits."""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
CHANGELOG_PATH = REPO_ROOT / "CHANGELOG.md"
JSON_VERSION_TARGETS = [
    (REPO_ROOT / ".claude-plugin" / "plugin.json", False),
    (REPO_ROOT / ".claude-plugin" / "marketplace.json", True),
    (REPO_ROOT / ".github" / "plugin" / "plugin.json", False),
    (REPO_ROOT / ".github" / "plugin" / "marketplace.json", True),
]
RELEASE_TYPES = ("major", "minor", "patch")
CONVENTIONAL_RE = re.compile(
    r"^(?P<type>[a-z]+)(?:\([^)]+\))?(?P<breaking>!)?:\s+(?P<description>.+)$"
)


@dataclass
class CommitEntry:
    sha: str
    subject: str
    body: str
    release_type: str | None
    display: str


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        encoding="utf-8",
    ).strip()


def try_git(*args: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", *args],
            cwd=REPO_ROOT,
            text=True,
            encoding="utf-8",
            stderr=subprocess.DEVNULL,
        ).strip()
    except subprocess.CalledProcessError:
        return None


def read_current_version() -> str:
    cargo_toml = (REPO_ROOT / "Cargo.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', cargo_toml, re.MULTILINE)
    if not match:
        raise RuntimeError("Could not find version in Cargo.toml")
    return match.group(1)


def last_release_tag() -> str | None:
    return try_git("describe", "--tags", "--match", "v*", "--abbrev=0")


def commit_range(last_tag: str | None) -> str:
    return f"{last_tag}..HEAD" if last_tag else "HEAD"


def collect_commits(last_tag: str | None) -> list[CommitEntry]:
    raw = git("log", "--format=%H%x1f%s%x1f%b%x1e", commit_range(last_tag))
    return parse_log_records(raw)


def parse_log_records(raw: str) -> list[CommitEntry]:
    commits: list[CommitEntry] = []
    for entry in raw.split("\x1e"):
        entry = entry.lstrip("\n")
        if not entry:
            continue
        parts = entry.split("\x1f", 2)
        if len(parts) == 2:
            sha, subject = parts
            body = ""
        elif len(parts) == 3:
            sha, subject, body = parts
        else:
            raise RuntimeError(f"Could not parse git log record: {entry!r}")
        release_type = classify_commit(subject, body)
        display = clean_display_line(subject, sha)
        commits.append(
            CommitEntry(
                sha=sha,
                subject=subject.strip(),
                body=body.strip(),
                release_type=release_type,
                display=display,
            )
        )
    return commits


def classify_commit(subject: str, body: str) -> str | None:
    body_upper = body.upper()
    if "BREAKING CHANGE:" in body_upper or "BREAKING-CHANGE:" in body_upper:
        return "major"

    match = CONVENTIONAL_RE.match(subject)
    if not match:
        return None

    commit_type = match.group("type")
    if match.group("breaking"):
        return "major"
    if commit_type == "feat":
        return "minor"
    if commit_type in {"fix", "perf", "refactor", "deps", "revert"}:
        return "patch"
    return None


def clean_display_line(subject: str, sha: str) -> str:
    match = CONVENTIONAL_RE.match(subject)
    description = match.group("description").strip() if match else subject.strip()
    short_sha = sha[:7]
    return f"- {description} ({short_sha})"


def calculate_next_version(current_version: str, release_type: str | None, last_tag: str | None) -> str | None:
    if release_type is None:
        return None
    if last_tag is None:
        return current_version

    major, minor, patch = (int(part) for part in current_version.split("."))
    if release_type == "major":
        return f"{major + 1}.0.0"
    if release_type == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def highest_release_type(commits: Iterable[CommitEntry]) -> str | None:
    found = {commit.release_type for commit in commits if commit.release_type}
    for release_type in RELEASE_TYPES:
        if release_type in found:
            return release_type
    return None


def update_text_versions(path: Path, current_version: str, next_version: str) -> None:
    content = path.read_text(encoding="utf-8")
    if path.name == "Cargo.toml":
        updated, count = re.subn(
            r'(^version\s*=\s*")' + re.escape(current_version) + r'(")',
            r"\g<1>" + next_version + r"\g<2>",
            content,
            count=1,
            flags=re.MULTILINE,
        )
    elif path.name == "Cargo.lock":
        updated, count = re.subn(
            r'(\[\[package\]\]\s+name = "ainbox"\s+version = ")'
            + re.escape(current_version)
            + r'(")',
            r"\g<1>" + next_version + r"\g<2>",
            content,
            count=1,
            flags=re.MULTILINE,
        )
    else:
        updated, count = re.subn(
            r'(^__version__\s*=\s*")' + re.escape(current_version) + r'(")',
            r"\g<1>" + next_version + r"\g<2>",
            content,
            count=1,
            flags=re.MULTILINE,
        )
    if count == 0:
        raise RuntimeError(f"Version {current_version} not found in {path}")
    path.write_text(updated, encoding="utf-8", newline="\n")


def update_json_versions(path: Path, next_version: str, is_marketplace: bool) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    if is_marketplace:
        data["metadata"]["version"] = next_version
        for plugin in data["plugins"]:
            plugin["version"] = next_version
    else:
        data["version"] = next_version
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")


def update_changelog(version: str, commits: list[CommitEntry]) -> str:
    existing = CHANGELOG_PATH.read_text(encoding="utf-8")
    if re.search(rf"^## v{re.escape(version)}\b", existing, re.MULTILINE):
        return f"CHANGELOG.md already contains v{version}."

    categories = {
        "Breaking Changes": [c.display for c in commits if c.release_type == "major"],
        "Features": [c.display for c in commits if c.release_type == "minor"],
        "Fixes": [c.display for c in commits if c.release_type == "patch"],
        "Other": [c.display for c in commits if c.release_type is None],
    }

    lines = [f"## v{version} - {date.today().isoformat()}", ""]
    for title, items in categories.items():
        if not items:
            continue
        lines.append(f"### {title}")
        lines.extend(items)
        lines.append("")
    section = "\n".join(lines).rstrip() + "\n\n"

    header = "# Changelog\n\nAll notable changes to this project will be documented in this file.\n\n"
    if existing.startswith(header):
        updated = header + section + existing[len(header):].lstrip()
    else:
        updated = existing.rstrip() + "\n\n" + section
    CHANGELOG_PATH.write_text(updated, encoding="utf-8", newline="\n")
    return section.strip()


def write_output(name: str, value: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(f"{name}={value}\n")


def main() -> int:
    current_version = read_current_version()
    last_tag = last_release_tag()
    commits = collect_commits(last_tag)
    release_type = highest_release_type(commits)
    next_version = calculate_next_version(current_version, release_type, last_tag)

    if not next_version:
        write_output("released", "false")
        print("No releasable commits found since the last release.")
        return 0

    if next_version != current_version:
        for path in [
            REPO_ROOT / "Cargo.toml",
            REPO_ROOT / "Cargo.lock",
            REPO_ROOT / "ainbox" / "__init__.py",
        ]:
            update_text_versions(path, current_version, next_version)
        for path, is_marketplace in JSON_VERSION_TARGETS:
            update_json_versions(path, next_version, is_marketplace)

    changelog_excerpt = update_changelog(next_version, commits)
    write_output("released", "true")
    write_output("version", next_version)
    write_output("tag", f"v{next_version}")
    print(f"Prepared release v{next_version}")
    print(changelog_excerpt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
