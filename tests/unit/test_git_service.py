"""Unit tests for GitService and remote GitHub push operations."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ai_java_engineer.tools.git.git_service import GitService
from ai_java_engineer.domain.requirement import ProductSpec, UserStory, AcceptanceCriterion


def test_git_service_local_operations():
    with tempfile.TemporaryDirectory() as tmp_dir:
        git = GitService(tmp_dir)
        git.init_repository_if_needed()

        assert (Path(tmp_dir) / ".git").exists()

        branch = git.create_feature_branch("feat/test-branch")
        assert branch == "feat/test-branch"

        test_file = Path(tmp_dir) / "Test.java"
        test_file.write_text("public class Test {}")

        commit_hash = git.commit_changes("feat: initial commit", ["Test.java"])
        assert commit_hash is not None
        assert len(commit_hash) >= 7

        diff = git.get_diff("HEAD~1")
        assert isinstance(diff, str)


def test_git_service_build_pr_payload():
    with tempfile.TemporaryDirectory() as tmp_dir:
        git = GitService(tmp_dir)
        spec = ProductSpec(
            title="Payment Processing",
            summary="Handles credit card payments",
            user_stories=[
                UserStory(id="US-1", title="Pay", as_a="User", i_want="To Pay", so_that="I get items")
            ],
            acceptance_criteria=[
                AcceptanceCriterion(id="AC-1", scenario="Success", given="Funds", when="Click", then="Charged")
            ]
        )
        pr = git.build_pr_payload(
            branch_name="feat/ai-scrum-5",
            base_branch="main",
            product_spec=spec,
            test_summary="Passed 5/5",
        )
        assert pr.title == "feat: Payment Processing"
        assert pr.branch == "feat/ai-scrum-5"
        assert pr.base_branch == "main"
        assert "Handles credit card payments" in pr.body
        assert "Passed 5/5" in pr.body


def test_git_service_push_approved_feature_dry_run(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp_dir:
        git = GitService(tmp_dir)
        git.init_repository_if_needed()

        sample_file = Path(tmp_dir) / "Sample.java"
        sample_file.write_text("public class Sample {}")

        # Mock git commands to test URL resolution and payload without actual external network
        calls = []
        original_run = git._run_git

        def mock_run_git(args):
            calls.append(args)
            if args == ["remote"]:
                return "origin"
            if args[:2] == ["rev-parse", "HEAD"]:
                return "mock_commit_hash_12345"
            return ""

        monkeypatch.setattr(git, "_run_git", mock_run_git)

        res = git.push_approved_feature_to_remote(
            branch_name="feat/ai-test-task",
            commit_message="feat: automated changes",
            remote_url="https://github.com/7zradar/ai-java-engineer.git",
        )

        assert res["success"] is True
        assert res["branch_name"] == "feat/ai-test-task"
        assert res["branch_url"] == "https://github.com/7zradar/ai-java-engineer/tree/feat/ai-test-task"
        assert res["pr_url"] == "https://github.com/7zradar/ai-java-engineer/pull/new/feat/ai-test-task"
