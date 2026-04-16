"""Core poll and election support using filesystem state."""

import json
from typing import List, Optional, Dict, Any
from enum import Enum

from .util import (
    get_shared_mailbox,
    generate_id,
    generate_timestamp,
)


class PollStatus(str, Enum):
    """Poll status."""
    OPEN = "open"
    CLOSED = "closed"


class ElectionStatus(str, Enum):
    """Election status."""
    OPEN = "open"
    CLOSED = "closed"


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
        """Serialize to dict."""
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
        """Deserialize from dict."""
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
        """Serialize to dict."""
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
        """Deserialize from dict."""
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


class BallotBox:
    """Manages polls and elections."""

    def __init__(self):
        self.shared_mailbox = get_shared_mailbox()
        self.polls_root = self.shared_mailbox / "shared" / "polls"
        self.elections_root = self.shared_mailbox / "shared" / "elections"

    def _ensure_dirs(self) -> None:
        """Ensure ballot directories exist."""
        self.polls_root.mkdir(parents=True, exist_ok=True)
        self.elections_root.mkdir(parents=True, exist_ok=True)

    def create_poll(
        self,
        question: str,
        options: List[str],
        created_by: str,
        participants: Optional[List[str]] = None,
        description: Optional[str] = None,
    ) -> Poll:
        """Create a new poll."""
        if not options:
            raise ValueError("Poll must have at least one option")
        if len(options) != len(set(options)):
            raise ValueError("Duplicate options not allowed")
        
        self._ensure_dirs()
        
        poll_id = generate_id()
        poll = Poll(
            poll_id=poll_id,
            question=question,
            options=options,
            created_by=created_by,
            created_at=generate_timestamp(),
            participants=participants,
            description=description,
        )
        
        poll_dir = self.polls_root / poll_id
        poll_dir.mkdir(parents=True, exist_ok=True)
        
        # Save poll definition
        definition_file = poll_dir / "definition.json"
        with open(definition_file, "w") as f:
            json.dump(poll.to_dict(), f, indent=2)
        
        return poll

    def get_poll(self, poll_id: str) -> Optional[Poll]:
        """Retrieve a poll."""
        poll_dir = self.polls_root / poll_id
        definition_file = poll_dir / "definition.json"
        
        if not definition_file.exists():
            return None
        
        with open(definition_file, "r") as f:
            data = json.load(f)
        
        return Poll.from_dict(data)

    def list_polls(
        self,
        status: Optional[str] = None,
        participant: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> List[Poll]:
        """List polls with optional filters."""
        self._ensure_dirs()
        
        polls = []
        if not self.polls_root.exists():
            return polls
        
        for poll_dir in self.polls_root.iterdir():
            if not poll_dir.is_dir():
                continue
            
            definition_file = poll_dir / "definition.json"
            if not definition_file.exists():
                continue
            
            try:
                with open(definition_file, "r") as f:
                    data = json.load(f)
                poll = Poll.from_dict(data)
                
                # Apply filters
                if status and status != "all" and poll.status != status:
                    continue
                if participant and poll.participants and participant not in poll.participants:
                    continue
                if created_by and poll.created_by != created_by:
                    continue
                
                polls.append(poll)
            except Exception:
                continue
        
        return sorted(polls, key=lambda p: p.created_at, reverse=True)

    def vote_poll(self, poll_id: str, voter: str, option: str) -> bool:
        """Record a vote on a poll."""
        poll = self.get_poll(poll_id)
        if not poll:
            raise ValueError(f"Poll {poll_id} not found")
        
        if poll.status != PollStatus.OPEN:
            raise ValueError(f"Poll is {poll.status}")
        
        if option not in poll.options:
            raise ValueError(f"Invalid option: {option}")
        
        if poll.participants and voter not in poll.participants:
            raise ValueError(f"Voter {voter} not in poll participants")
        
        # Save vote
        poll_dir = self.polls_root / poll_id
        vote_file = poll_dir / f"{voter}.json"
        
        with open(vote_file, "w") as f:
            json.dump({"voter": voter, "option": option, "voted_at": generate_timestamp()}, f, indent=2)
        
        return True

    def get_poll_votes(self, poll_id: str) -> Dict[str, Any]:
        """Get vote tallies for a poll."""
        poll = self.get_poll(poll_id)
        if not poll:
            raise ValueError(f"Poll {poll_id} not found")
        
        votes = {}
        for option in poll.options:
            votes[option] = 0
        
        voters = []
        poll_dir = self.polls_root / poll_id
        
        if poll_dir.exists():
            for vote_file in poll_dir.glob("*.json"):
                if vote_file.name == "definition.json":
                    continue
                
                try:
                    with open(vote_file, "r") as f:
                        vote_data = json.load(f)
                    option = vote_data.get("option")
                    if option in votes:
                        votes[option] += 1
                    voters.append(vote_data.get("voter"))
                except Exception:
                    continue
        
        return {
            "poll_id": poll_id,
            "question": poll.question,
            "status": poll.status,
            "options": poll.options,
            "votes": votes,
            "total_votes": sum(votes.values()),
            "voters": voters,
        }

    def close_poll(self, poll_id: str) -> bool:
        """Close a poll."""
        poll = self.get_poll(poll_id)
        if not poll:
            raise ValueError(f"Poll {poll_id} not found")
        
        poll.status = PollStatus.CLOSED
        poll_dir = self.polls_root / poll_id
        definition_file = poll_dir / "definition.json"
        
        with open(definition_file, "w") as f:
            json.dump(poll.to_dict(), f, indent=2)
        
        return True

    def create_election(
        self,
        role: str,
        candidates: List[str],
        created_by: str,
        participants: Optional[List[str]] = None,
        description: Optional[str] = None,
    ) -> Election:
        """Create a new election."""
        if not candidates:
            raise ValueError("Election must have at least one candidate")
        if len(candidates) != len(set(candidates)):
            raise ValueError("Duplicate candidates not allowed")
        
        self._ensure_dirs()
        
        election_id = generate_id()
        election = Election(
            election_id=election_id,
            role=role,
            candidates=candidates,
            created_by=created_by,
            created_at=generate_timestamp(),
            participants=participants,
            description=description,
        )
        
        election_dir = self.elections_root / election_id
        election_dir.mkdir(parents=True, exist_ok=True)
        
        # Save election definition
        definition_file = election_dir / "definition.json"
        with open(definition_file, "w") as f:
            json.dump(election.to_dict(), f, indent=2)
        
        return election

    def get_election(self, election_id: str) -> Optional[Election]:
        """Retrieve an election."""
        election_dir = self.elections_root / election_id
        definition_file = election_dir / "definition.json"
        
        if not definition_file.exists():
            return None
        
        with open(definition_file, "r") as f:
            data = json.load(f)
        
        return Election.from_dict(data)

    def list_elections(
        self,
        status: Optional[str] = None,
        participant: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> List[Election]:
        """List elections with optional filters."""
        self._ensure_dirs()
        
        elections = []
        if not self.elections_root.exists():
            return elections
        
        for election_dir in self.elections_root.iterdir():
            if not election_dir.is_dir():
                continue
            
            definition_file = election_dir / "definition.json"
            if not definition_file.exists():
                continue
            
            try:
                with open(definition_file, "r") as f:
                    data = json.load(f)
                election = Election.from_dict(data)
                
                # Apply filters
                if status and status != "all" and election.status != status:
                    continue
                if participant and election.participants and participant not in election.participants:
                    continue
                if created_by and election.created_by != created_by:
                    continue
                
                elections.append(election)
            except Exception:
                continue
        
        return sorted(elections, key=lambda e: e.created_at, reverse=True)

    def vote_election(self, election_id: str, voter: str, candidate: str) -> bool:
        """Record a vote in an election."""
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
        
        # Save vote
        election_dir = self.elections_root / election_id
        vote_file = election_dir / f"{voter}.json"
        
        with open(vote_file, "w") as f:
            json.dump({"voter": voter, "candidate": candidate, "voted_at": generate_timestamp()}, f, indent=2)
        
        return True

    def get_election_votes(self, election_id: str) -> Dict[str, Any]:
        """Get vote tallies for an election."""
        election = self.get_election(election_id)
        if not election:
            raise ValueError(f"Election {election_id} not found")
        
        votes = {}
        for candidate in election.candidates:
            votes[candidate] = 0
        
        voters = []
        election_dir = self.elections_root / election_id
        
        if election_dir.exists():
            for vote_file in election_dir.glob("*.json"):
                if vote_file.name == "definition.json":
                    continue
                
                try:
                    with open(vote_file, "r") as f:
                        vote_data = json.load(f)
                    candidate = vote_data.get("candidate")
                    if candidate in votes:
                        votes[candidate] += 1
                    voters.append(vote_data.get("voter"))
                except Exception:
                    continue
        
        return {
            "election_id": election_id,
            "role": election.role,
            "status": election.status,
            "candidates": election.candidates,
            "votes": votes,
            "total_votes": sum(votes.values()),
            "voters": voters,
        }

    def close_election(self, election_id: str) -> bool:
        """Close an election."""
        election = self.get_election(election_id)
        if not election:
            raise ValueError(f"Election {election_id} not found")
        
        election.status = ElectionStatus.CLOSED
        election_dir = self.elections_root / election_id
        definition_file = election_dir / "definition.json"
        
        with open(definition_file, "w") as f:
            json.dump(election.to_dict(), f, indent=2)
        
        return True
