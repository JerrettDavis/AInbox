import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class BallotTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.home = self.root / "home"
        self.home.mkdir(parents=True, exist_ok=True)
        
        # Add repo to path
        sys.path.insert(0, str(REPO_ROOT))
        
        # Set up environment
        os.environ["MAILBOX_SHARED"] = str(self.home / "shared")
        if os.name == "nt":
            os.environ["USERPROFILE"] = str(self.home)
        else:
            os.environ["HOME"] = str(self.home)

    def tearDown(self):
        self.temp_dir.cleanup()
        # Clean up sys.path
        if str(REPO_ROOT) in sys.path:
            sys.path.remove(str(REPO_ROOT))

    def test_create_poll(self):
        """Test creating a poll."""
        from ainbox.ballot import BallotBox
        
        ballot_box = BallotBox()
        poll = ballot_box.create_poll(
            question="What is your favorite color?",
            options=["Red", "Blue", "Green"],
            created_by="agent1",
        )
        
        self.assertIsNotNone(poll.id)
        self.assertEqual(poll.question, "What is your favorite color?")
        self.assertEqual(poll.options, ["Red", "Blue", "Green"])
        self.assertEqual(poll.created_by, "agent1")
        self.assertEqual(poll.status, "open")

    def test_get_poll(self):
        """Test retrieving a poll."""
        from ainbox.ballot import BallotBox
        
        ballot_box = BallotBox()
        created_poll = ballot_box.create_poll(
            question="Test question",
            options=["Option A", "Option B"],
            created_by="agent1",
        )
        
        retrieved_poll = ballot_box.get_poll(created_poll.id)
        self.assertIsNotNone(retrieved_poll)
        self.assertEqual(retrieved_poll.id, created_poll.id)
        self.assertEqual(retrieved_poll.question, "Test question")

    def test_vote_poll(self):
        """Test voting in a poll."""
        from ainbox.ballot import BallotBox
        
        ballot_box = BallotBox()
        poll = ballot_box.create_poll(
            question="Vote test",
            options=["A", "B", "C"],
            created_by="agent1",
        )
        
        ballot_box.vote_poll(poll.id, "agent2", "A")
        ballot_box.vote_poll(poll.id, "agent3", "A")
        ballot_box.vote_poll(poll.id, "agent4", "B")
        
        votes = ballot_box.get_poll_votes(poll.id)
        self.assertEqual(votes["votes"]["A"], 2)
        self.assertEqual(votes["votes"]["B"], 1)
        self.assertEqual(votes["votes"]["C"], 0)
        self.assertEqual(votes["total_votes"], 3)

    def test_close_poll(self):
        """Test closing a poll."""
        from ainbox.ballot import BallotBox
        
        ballot_box = BallotBox()
        poll = ballot_box.create_poll(
            question="Close test",
            options=["Yes", "No"],
            created_by="agent1",
        )
        
        self.assertEqual(poll.status, "open")
        ballot_box.close_poll(poll.id)
        
        closed_poll = ballot_box.get_poll(poll.id)
        self.assertEqual(closed_poll.status, "closed")

    def test_vote_closed_poll_fails(self):
        """Test that voting on closed poll fails."""
        from ainbox.ballot import BallotBox
        
        ballot_box = BallotBox()
        poll = ballot_box.create_poll(
            question="Closed poll",
            options=["A", "B"],
            created_by="agent1",
        )
        
        ballot_box.close_poll(poll.id)
        
        with self.assertRaises(ValueError) as ctx:
            ballot_box.vote_poll(poll.id, "agent2", "A")
        self.assertIn("closed", str(ctx.exception))

    def test_invalid_poll_option_fails(self):
        """Test voting for invalid option fails."""
        from ainbox.ballot import BallotBox
        
        ballot_box = BallotBox()
        poll = ballot_box.create_poll(
            question="Invalid option test",
            options=["A", "B"],
            created_by="agent1",
        )
        
        with self.assertRaises(ValueError) as ctx:
            ballot_box.vote_poll(poll.id, "agent2", "C")
        self.assertIn("Invalid option", str(ctx.exception))

    def test_list_polls(self):
        """Test listing polls."""
        from ainbox.ballot import BallotBox
        
        ballot_box = BallotBox()
        
        poll1 = ballot_box.create_poll(
            question="Poll 1",
            options=["A", "B"],
            created_by="agent1",
        )
        
        poll2 = ballot_box.create_poll(
            question="Poll 2",
            options=["X", "Y"],
            created_by="agent2",
        )
        
        polls = ballot_box.list_polls()
        self.assertEqual(len(polls), 2)

    def test_list_polls_filter_by_creator(self):
        """Test filtering polls by creator."""
        from ainbox.ballot import BallotBox
        
        ballot_box = BallotBox()
        
        ballot_box.create_poll(
            question="Poll 1",
            options=["A", "B"],
            created_by="agent1",
        )
        
        ballot_box.create_poll(
            question="Poll 2",
            options=["X", "Y"],
            created_by="agent2",
        )
        
        polls = ballot_box.list_polls(created_by="agent1")
        self.assertEqual(len(polls), 1)
        self.assertEqual(polls[0].created_by, "agent1")

    def test_create_election(self):
        """Test creating an election."""
        from ainbox.ballot import BallotBox
        
        ballot_box = BallotBox()
        election = ballot_box.create_election(
            role="Lead Developer",
            candidates=["Alice", "Bob", "Charlie"],
            created_by="admin",
        )
        
        self.assertIsNotNone(election.id)
        self.assertEqual(election.role, "Lead Developer")
        self.assertEqual(election.candidates, ["Alice", "Bob", "Charlie"])
        self.assertEqual(election.created_by, "admin")
        self.assertEqual(election.status, "open")

    def test_vote_election(self):
        """Test voting in an election."""
        from ainbox.ballot import BallotBox
        
        ballot_box = BallotBox()
        election = ballot_box.create_election(
            role="Manager",
            candidates=["Alice", "Bob"],
            created_by="admin",
        )
        
        ballot_box.vote_election(election.id, "voter1", "Alice")
        ballot_box.vote_election(election.id, "voter2", "Alice")
        ballot_box.vote_election(election.id, "voter3", "Bob")
        
        votes = ballot_box.get_election_votes(election.id)
        self.assertEqual(votes["votes"]["Alice"], 2)
        self.assertEqual(votes["votes"]["Bob"], 1)
        self.assertEqual(votes["total_votes"], 3)

    def test_self_vote_election_fails(self):
        """Test that self-voting in election fails."""
        from ainbox.ballot import BallotBox
        
        ballot_box = BallotBox()
        election = ballot_box.create_election(
            role="Manager",
            candidates=["Alice", "Bob"],
            created_by="admin",
        )
        
        with self.assertRaises(ValueError) as ctx:
            ballot_box.vote_election(election.id, "Alice", "Alice")
        self.assertIn("Cannot vote for yourself", str(ctx.exception))

    def test_close_election(self):
        """Test closing an election."""
        from ainbox.ballot import BallotBox
        
        ballot_box = BallotBox()
        election = ballot_box.create_election(
            role="Manager",
            candidates=["Alice", "Bob"],
            created_by="admin",
        )
        
        self.assertEqual(election.status, "open")
        ballot_box.close_election(election.id)
        
        closed_election = ballot_box.get_election(election.id)
        self.assertEqual(closed_election.status, "closed")

    def test_motion_accepts_when_quorum_and_yes_threshold_met(self):
        """Test that motions resolve accepted once enough yes votes arrive."""
        from ainbox.ballot import BallotBox

        ballot_box = BallotBox()
        motion = ballot_box.create_motion(
            title="Pause deploy",
            created_by="orchestrator",
            participants=["agent1", "agent2", "agent3"],
            quorum=2,
            required_yes=2,
            description="Stop work and report status.",
        )

        ballot_box.vote_motion(motion.id, "agent1", "yes", "Investigating")
        state = ballot_box.vote_motion(motion.id, "agent2", "yes", "Acknowledged")

        self.assertEqual(state["motion"]["status"], "accepted")
        self.assertEqual(state["votes"]["votes"]["yes"], 2)
        self.assertEqual(state["votes"]["votes"]["no"], 0)

    def test_motion_rejects_when_yes_threshold_becomes_unreachable(self):
        """Test that motions reject once acceptance is no longer possible."""
        from ainbox.ballot import BallotBox

        ballot_box = BallotBox()
        motion = ballot_box.create_motion(
            title="Redirect sprint",
            created_by="orchestrator",
            participants=["agent1", "agent2", "agent3"],
            quorum=3,
            required_yes=3,
        )

        state = ballot_box.vote_motion(motion.id, "agent1", "no", "Keep current plan")

        self.assertEqual(state["motion"]["status"], "rejected")
        self.assertEqual(state["votes"]["votes"]["yes"], 0)
        self.assertEqual(state["votes"]["votes"]["no"], 1)

    def test_list_elections(self):
        """Test listing elections."""
        from ainbox.ballot import BallotBox
        
        ballot_box = BallotBox()
        
        ballot_box.create_election(
            role="Manager",
            candidates=["A", "B"],
            created_by="admin",
        )
        
        ballot_box.create_election(
            role="Lead",
            candidates=["X", "Y"],
            created_by="admin",
        )
        
        elections = ballot_box.list_elections()
        self.assertEqual(len(elections), 2)

    def test_duplicate_options_poll_fails(self):
        """Test that creating poll with duplicate options fails."""
        from ainbox.ballot import BallotBox
        
        ballot_box = BallotBox()
        
        with self.assertRaises(ValueError) as ctx:
            ballot_box.create_poll(
                question="Duplicate test",
                options=["A", "B", "A"],
                created_by="agent1",
            )
        self.assertIn("Duplicate", str(ctx.exception))

    def test_duplicate_candidates_election_fails(self):
        """Test that creating election with duplicate candidates fails."""
        from ainbox.ballot import BallotBox
        
        ballot_box = BallotBox()
        
        with self.assertRaises(ValueError) as ctx:
            ballot_box.create_election(
                role="Manager",
                candidates=["Alice", "Bob", "Alice"],
                created_by="admin",
            )
        self.assertIn("Duplicate", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
