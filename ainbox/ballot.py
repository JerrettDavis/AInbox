"""Core poll, election, and motion support using filesystem state."""

import json
import time
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .util import generate_id, generate_timestamp, get_shared_mailbox


class PollStatus(str, Enum):
    """Poll status."""

    OPEN = "open"
    CLOSED = "closed"


class ElectionStatus(str, Enum):
    """Election status."""

    OPEN = "open"
    CLOSED = "closed"


class MotionStatus(str, Enum):
    """Motion status."""

    OPEN = "open"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class MotionVoteDecision(str, Enum):
    """Valid motion vote values."""

    YES = "yes"
    NO = "no"


class Poll:
    """Represents a poll."""

    def __init__(
        self,
        poll_id: str,
        question: str,
        options: List[str],
        created_by: str,
        created_at: str,
        status: str = PollStatus.OPEN,
        participants: Optional[List[str]] = None,
        description: Optional[str] = None,
    ):
        self.id = poll_id
        self.question = question
        self.options = options
        self.created_by = created_by
        self.created_at = created_at
        self.status = status
        self.participants = participants or []
        self.description = description or ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "question": self.question,
            "options": self.options,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "status": self.status,
            "participants": self.participants,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Poll":
        return cls(
            poll_id=data["id"],
            question=data["question"],
            options=data["options"],
            created_by=data["created_by"],
            created_at=data["created_at"],
            status=data.get("status", PollStatus.OPEN),
            participants=data.get("participants", []),
            description=data.get("description", ""),
        )


class Election:
    """Represents an election."""

    def __init__(
        self,
        election_id: str,
        role: str,
        candidates: List[str],
        created_by: str,
        created_at: str,
        status: str = ElectionStatus.OPEN,
        participants: Optional[List[str]] = None,
        description: Optional[str] = None,
    ):
        self.id = election_id
        self.role = role
        self.candidates = candidates
        self.created_by = created_by
        self.created_at = created_at
        self.status = status
        self.participants = participants or []
        self.description = description or ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role,
            "candidates": self.candidates,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "status": self.status,
            "participants": self.participants,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Election":
        return cls(
            election_id=data["id"],
            role=data["role"],
            candidates=data["candidates"],
            created_by=data["created_by"],
            created_at=data["created_at"],
            status=data.get("status", ElectionStatus.OPEN),
            participants=data.get("participants", []),
            description=data.get("description", ""),
        )


class Motion:
    """Represents a distributed motion or coordination gate."""

    def __init__(
        self,
        motion_id: str,
        title: str,
        created_by: str,
        created_at: str,
        participants: List[str],
        status: str = MotionStatus.OPEN,
        description: Optional[str] = None,
        scope: Optional[str] = None,
        quorum: Optional[int] = None,
        required_yes: Optional[int] = None,
        blocking: bool = True,
    ):
        self.id = motion_id
        self.title = title
        self.created_by = created_by
        self.created_at = created_at
        self.participants = participants
        self.status = status
        self.description = description or ""
        self.scope = scope or ""
        self.quorum = quorum if quorum is not None else len(participants)
        self.required_yes = required_yes if required_yes is not None else self.quorum
        self.blocking = blocking

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "participants": self.participants,
            "status": self.status,
            "description": self.description,
            "scope": self.scope,
            "quorum": self.quorum,
            "required_yes": self.required_yes,
            "blocking": self.blocking,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Motion":
        return cls(
            motion_id=data["id"],
            title=data["title"],
            created_by=data["created_by"],
            created_at=data["created_at"],
            participants=data.get("participants", []),
            status=data.get("status", MotionStatus.OPEN),
            description=data.get("description", ""),
            scope=data.get("scope", ""),
            quorum=data.get("quorum"),
            required_yes=data.get("required_yes"),
            blocking=data.get("blocking", True),
        )


class BallotBox:
    """Manages polls, elections, and motions."""

    def __init__(self):
        self.shared_mailbox = get_shared_mailbox()
        self.polls_root = self.shared_mailbox / "shared" / "polls"
        self.elections_root = self.shared_mailbox / "shared" / "elections"
        self.motions_root = self.shared_mailbox / "shared" / "motions"

    def _ensure_dirs(self) -> None:
        self.polls_root.mkdir(parents=True, exist_ok=True)
        self.elections_root.mkdir(parents=True, exist_ok=True)
        self.motions_root.mkdir(parents=True, exist_ok=True)

    def create_poll(
        self,
        question: str,
        options: List[str],
        created_by: str,
        participants: Optional[List[str]] = None,
        description: Optional[str] = None,
    ) -> Poll:
        if not options:
            raise ValueError("Poll must have at least one option")
        _ensure_unique(options, "Duplicate options not allowed")
        self._ensure_dirs()

        poll = Poll(
            poll_id=generate_id(),
            question=question,
            options=options,
            created_by=created_by,
            created_at=generate_timestamp(),
            participants=participants,
            description=description,
        )
        poll_dir = self.polls_root / poll.id
        poll_dir.mkdir(parents=True, exist_ok=True)
        _write_json(poll_dir / "definition.json", poll.to_dict())
        return poll

    def get_poll(self, poll_id: str) -> Optional[Poll]:
        definition_file = self.polls_root / poll_id / "definition.json"
        if not definition_file.exists():
            return None
        return Poll.from_dict(_read_json(definition_file))

    def list_polls(
        self,
        status: Optional[str] = None,
        participant: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> List[Poll]:
        self._ensure_dirs()
        return _list_ballots(self.polls_root, Poll, status, participant, created_by)

    def vote_poll(self, poll_id: str, voter: str, option: str) -> bool:
        poll = self.get_poll(poll_id)
        if not poll:
            raise ValueError(f"Poll {poll_id} not found")
        if poll.status != PollStatus.OPEN:
            raise ValueError(f"Poll is {poll.status}")
        if option not in poll.options:
            raise ValueError(f"Invalid option: {option}")
        if poll.participants and voter not in poll.participants:
            raise ValueError(f"Voter {voter} not in poll participants")

        _write_json(
            self.polls_root / poll_id / f"{voter}.json",
            {"voter": voter, "option": option, "voted_at": generate_timestamp()},
        )
        return True

    def get_poll_votes(self, poll_id: str) -> Dict[str, Any]:
        poll = self.get_poll(poll_id)
        if not poll:
            raise ValueError(f"Poll {poll_id} not found")

        tallies = {option: 0 for option in poll.options}
        voters: List[str] = []
        for vote_data in _read_vote_files(self.polls_root / poll_id):
            option = vote_data.get("option")
            if option in tallies:
                tallies[option] += 1
            voter = vote_data.get("voter")
            if voter:
                voters.append(voter)

        return {
            "poll_id": poll_id,
            "question": poll.question,
            "status": poll.status,
            "options": poll.options,
            "votes": tallies,
            "total_votes": sum(tallies.values()),
            "voters": voters,
        }

    def close_poll(self, poll_id: str) -> bool:
        poll = self.get_poll(poll_id)
        if not poll:
            raise ValueError(f"Poll {poll_id} not found")
        poll.status = PollStatus.CLOSED
        _write_json(self.polls_root / poll_id / "definition.json", poll.to_dict())
        return True

    def create_election(
        self,
        role: str,
        candidates: List[str],
        created_by: str,
        participants: Optional[List[str]] = None,
        description: Optional[str] = None,
    ) -> Election:
        if not candidates:
            raise ValueError("Election must have at least one candidate")
        _ensure_unique(candidates, "Duplicate candidates not allowed")
        self._ensure_dirs()

        election = Election(
            election_id=generate_id(),
            role=role,
            candidates=candidates,
            created_by=created_by,
            created_at=generate_timestamp(),
            participants=participants,
            description=description,
        )
        election_dir = self.elections_root / election.id
        election_dir.mkdir(parents=True, exist_ok=True)
        _write_json(election_dir / "definition.json", election.to_dict())
        return election

    def get_election(self, election_id: str) -> Optional[Election]:
        definition_file = self.elections_root / election_id / "definition.json"
        if not definition_file.exists():
            return None
        return Election.from_dict(_read_json(definition_file))

    def list_elections(
        self,
        status: Optional[str] = None,
        participant: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> List[Election]:
        self._ensure_dirs()
        return _list_ballots(self.elections_root, Election, status, participant, created_by)

    def vote_election(self, election_id: str, voter: str, candidate: str) -> bool:
        election = self.get_election(election_id)
        if not election:
            raise ValueError(f"Election {election_id} not found")
        if election.status != ElectionStatus.OPEN:
            raise ValueError(f"Election is {election.status}")
        if candidate not in election.candidates:
            raise ValueError(f"Invalid candidate: {candidate}")
        if voter == candidate:
            raise ValueError("Cannot vote for yourself")
        if election.participants and voter not in election.participants:
            raise ValueError(f"Voter {voter} not in election participants")

        _write_json(
            self.elections_root / election_id / f"{voter}.json",
            {"voter": voter, "candidate": candidate, "voted_at": generate_timestamp()},
        )
        return True

    def get_election_votes(self, election_id: str) -> Dict[str, Any]:
        election = self.get_election(election_id)
        if not election:
            raise ValueError(f"Election {election_id} not found")

        tallies = {candidate: 0 for candidate in election.candidates}
        voters: List[str] = []
        for vote_data in _read_vote_files(self.elections_root / election_id):
            candidate = vote_data.get("candidate")
            if candidate in tallies:
                tallies[candidate] += 1
            voter = vote_data.get("voter")
            if voter:
                voters.append(voter)

        return {
            "election_id": election_id,
            "role": election.role,
            "status": election.status,
            "candidates": election.candidates,
            "votes": tallies,
            "total_votes": sum(tallies.values()),
            "voters": voters,
        }

    def close_election(self, election_id: str) -> bool:
        election = self.get_election(election_id)
        if not election:
            raise ValueError(f"Election {election_id} not found")
        election.status = ElectionStatus.CLOSED
        _write_json(self.elections_root / election_id / "definition.json", election.to_dict())
        return True

    def create_motion(
        self,
        title: str,
        created_by: str,
        participants: List[str],
        description: Optional[str] = None,
        scope: Optional[str] = None,
        quorum: Optional[int] = None,
        required_yes: Optional[int] = None,
        blocking: bool = True,
    ) -> Motion:
        if not participants:
            raise ValueError("Motion must have at least one participant")
        _ensure_unique(participants, "Duplicate participants not allowed")
        quorum_value, required_yes_value = _validate_motion_thresholds(
            participants,
            quorum,
            required_yes,
        )
        self._ensure_dirs()

        motion = Motion(
            motion_id=generate_id(),
            title=title,
            created_by=created_by,
            created_at=generate_timestamp(),
            participants=participants,
            description=description,
            scope=scope,
            quorum=quorum_value,
            required_yes=required_yes_value,
            blocking=blocking,
        )
        motion_dir = self.motions_root / motion.id
        motion_dir.mkdir(parents=True, exist_ok=True)
        _write_json(motion_dir / "definition.json", motion.to_dict())
        return motion

    def get_motion(self, motion_id: str) -> Optional[Motion]:
        definition_file = self.motions_root / motion_id / "definition.json"
        if not definition_file.exists():
            return None
        motion = Motion.from_dict(_read_json(definition_file))
        return self._refresh_motion_status(motion)

    def list_motions(
        self,
        status: Optional[str] = None,
        participant: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> List[Motion]:
        self._ensure_dirs()
        motions: List[Motion] = []
        for motion_dir in self.motions_root.iterdir() if self.motions_root.exists() else []:
            if not motion_dir.is_dir():
                continue
            definition_file = motion_dir / "definition.json"
            if not definition_file.exists():
                continue
            try:
                motion = self._refresh_motion_status(Motion.from_dict(_read_json(definition_file)))
            except Exception:
                continue
            if status and status != "all" and motion.status != status:
                continue
            if participant and participant not in motion.participants:
                continue
            if created_by and motion.created_by != created_by:
                continue
            motions.append(motion)
        return sorted(motions, key=lambda motion: motion.created_at, reverse=True)

    def vote_motion(
        self,
        motion_id: str,
        voter: str,
        vote: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        motion = self.get_motion(motion_id)
        if not motion:
            raise ValueError(f"Motion {motion_id} not found")
        if motion.status != MotionStatus.OPEN:
            raise ValueError(f"Motion is {motion.status}")
        if voter not in motion.participants:
            raise ValueError(f"Voter {voter} not in motion participants")

        normalized_vote = vote.strip().lower()
        if normalized_vote not in (MotionVoteDecision.YES, MotionVoteDecision.NO):
            raise ValueError("Motion vote must be 'yes' or 'no'")

        _write_json(
            self.motions_root / motion_id / f"{voter}.json",
            {
                "voter": voter,
                "vote": normalized_vote,
                "reason": reason or "",
                "voted_at": generate_timestamp(),
            },
        )
        return self.get_motion_state(motion_id)

    def get_motion_state(self, motion_id: str) -> Dict[str, Any]:
        motion = self.get_motion(motion_id)
        if not motion:
            raise ValueError(f"Motion {motion_id} not found")
        votes = self.get_motion_votes(motion_id)
        return {"motion": motion.to_dict(), "votes": votes}

    def get_motion_votes(self, motion_id: str) -> Dict[str, Any]:
        motion = self.get_motion(motion_id)
        if not motion:
            raise ValueError(f"Motion {motion_id} not found")

        responses = _read_vote_files(self.motions_root / motion_id)
        yes_votes = sum(1 for response in responses if response.get("vote") == MotionVoteDecision.YES)
        no_votes = sum(1 for response in responses if response.get("vote") == MotionVoteDecision.NO)
        voters = [
            response["voter"]
            for response in sorted(responses, key=lambda item: item.get("voted_at", ""))
            if response.get("voter")
        ]
        remaining_voters = [
            participant for participant in motion.participants if participant not in set(voters)
        ]
        total_votes = yes_votes + no_votes

        return {
            "motion_id": motion_id,
            "title": motion.title,
            "status": motion.status,
            "scope": motion.scope,
            "blocking": motion.blocking,
            "participants": motion.participants,
            "quorum": motion.quorum,
            "required_yes": motion.required_yes,
            "votes": {"yes": yes_votes, "no": no_votes},
            "total_votes": total_votes,
            "quorum_met": total_votes >= motion.quorum,
            "voters": voters,
            "remaining_voters": remaining_voters,
            "responses": sorted(responses, key=lambda item: item.get("voted_at", "")),
        }

    def close_motion(self, motion_id: str, status: str = MotionStatus.CANCELLED) -> bool:
        motion = self.get_motion(motion_id)
        if not motion:
            raise ValueError(f"Motion {motion_id} not found")
        if status not in (
            MotionStatus.ACCEPTED,
            MotionStatus.REJECTED,
            MotionStatus.CANCELLED,
        ):
            raise ValueError("Motion close status must be accepted, rejected, or cancelled")
        motion.status = status
        _write_json(self.motions_root / motion_id / "definition.json", motion.to_dict())
        return True

    def wait_for_motion(
        self,
        motion_id: str,
        timeout_seconds: Optional[float] = None,
        poll_interval_seconds: float = 2.0,
    ) -> Dict[str, Any]:
        deadline = None if timeout_seconds is None else time.monotonic() + timeout_seconds
        while True:
            state = self.get_motion_state(motion_id)
            status = state["motion"]["status"]
            if status != MotionStatus.OPEN:
                return state
            if deadline is not None and time.monotonic() >= deadline:
                raise TimeoutError(f"Timed out waiting for motion {motion_id}")
            time.sleep(max(poll_interval_seconds, 0.1))

    def _refresh_motion_status(self, motion: Motion) -> Motion:
        if motion.status != MotionStatus.OPEN:
            return motion

        responses = _read_vote_files(self.motions_root / motion.id)
        yes_votes = sum(1 for response in responses if response.get("vote") == MotionVoteDecision.YES)
        total_votes = len(responses)
        remaining_votes = max(len(motion.participants) - total_votes, 0)

        if yes_votes >= motion.required_yes and total_votes >= motion.quorum:
            motion.status = MotionStatus.ACCEPTED
        elif yes_votes + remaining_votes < motion.required_yes or total_votes >= len(motion.participants):
            motion.status = MotionStatus.REJECTED

        if motion.status != MotionStatus.OPEN:
            _write_json(self.motions_root / motion.id / "definition.json", motion.to_dict())
        return motion


def _ensure_unique(values: List[str], message: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(message)


def _validate_motion_thresholds(
    participants: List[str],
    quorum: Optional[int],
    required_yes: Optional[int],
) -> tuple[int, int]:
    participant_count = len(participants)
    quorum_value = participant_count if quorum is None else quorum
    required_yes_value = quorum_value if required_yes is None else required_yes

    if quorum_value < 1:
        raise ValueError("Motion quorum must be at least 1")
    if quorum_value > participant_count:
        raise ValueError("Motion quorum cannot exceed participant count")
    if required_yes_value < 1:
        raise ValueError("Motion required yes votes must be at least 1")
    if required_yes_value > participant_count:
        raise ValueError("Motion required yes votes cannot exceed participant count")

    return quorum_value, required_yes_value


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def _read_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _list_ballots(root: Path, cls, status: Optional[str], participant: Optional[str], created_by: Optional[str]) -> List[Any]:
    ballots: List[Any] = []
    if not root.exists():
        return ballots
    for ballot_dir in root.iterdir():
        if not ballot_dir.is_dir():
            continue
        definition_file = ballot_dir / "definition.json"
        if not definition_file.exists():
            continue
        try:
            ballot = cls.from_dict(_read_json(definition_file))
        except Exception:
            continue
        if status and status != "all" and ballot.status != status:
            continue
        if participant and ballot.participants and participant not in ballot.participants:
            continue
        if created_by and ballot.created_by != created_by:
            continue
        ballots.append(ballot)
    return sorted(ballots, key=lambda ballot: ballot.created_at, reverse=True)


def _read_vote_files(ballot_dir: Path) -> List[Dict[str, Any]]:
    responses: List[Dict[str, Any]] = []
    if not ballot_dir.exists():
        return responses
    for vote_file in ballot_dir.glob("*.json"):
        if vote_file.name == "definition.json":
            continue
        try:
            responses.append(_read_json(vote_file))
        except Exception:
            continue
    return responses
