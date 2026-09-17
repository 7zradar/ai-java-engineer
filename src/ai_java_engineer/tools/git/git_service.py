"""Deterministic Git operations and PR payload generator."""

import subprocess
from pathlib import Path

from ai_java_engineer.domain.artifact import PullRequestPayload
from ai_java_engineer.domain.requirement import ProductSpec
from ai_java_engineer.security.permissions import check_tool_permission


class GitService:
    """Manages feature branches, atomic commits, diffs, and PR creation."""

    def __init__(self, workspace_root: str | Path):
        self.workspace_root = Path(workspace_root).resolve()

    def _run_git(self, args: list[str]) -> str:
        res = subprocess.run(
            ["git"] + args,
            cwd=self.workspace_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode != 0:
            raise RuntimeError(f"Git command failed: git {' '.join(args)}\n{res.stderr}")
        return res.stdout.strip()

    def init_repository_if_needed(self) -> None:
        """Ensures the directory is a git repository."""
        if not (self.workspace_root / ".git").exists():
            self._run_git(["init"])
            self._run_git(["config", "user.name", "AI Java Engineer"])
            self._run_git(["config", "user.email", "agent@ailab.org"])

    def create_feature_branch(self, branch_name: str) -> str:
        """Creates and checks out a feature branch."""
        check_tool_permission("git_commit")
        self.init_repository_if_needed()
        self._run_git(["checkout", "-B", branch_name])
        return branch_name

    def commit_changes(self, message: str, files: list[str] | None = None) -> str:
        """Stages files and creates an atomic commit."""
        check_tool_permission("git_commit")
        if files:
            for f in files:
                self._run_git(["add", f])
        else:
            self._run_git(["add", "-A"])

        self._run_git(["commit", "-m", message])
        return self._run_git(["rev-parse", "HEAD"])

    def get_diff(self, base_ref: str = "HEAD~1") -> str:
        """Returns the unified diff safely."""
        check_tool_permission("read_file")
        self.init_repository_if_needed()
        try:
            self._run_git(["rev-parse", "--verify", "HEAD"])
            try:
                return self._run_git(["diff", base_ref])
            except Exception:
                return self._run_git(["diff", "HEAD"])
        except Exception:
            try:
                return self._run_git(["diff"])
            except Exception:
                return ""

    def build_pr_payload(
        self,
        branch_name: str,
        base_branch: str,
        product_spec: ProductSpec,
        test_summary: str,
    ) -> PullRequestPayload:
        """Builds a structured Pull Request body."""
        body = (
            f"## Automated Feature Implementation\n\n"
            f"### Requirement Summary\n"
            f"{product_spec.summary}\n\n"
            f"### User Stories Addressed\n"
        )
        for us in product_spec.user_stories:
            body += f"- **{us.id}**: {us.title} ({us.as_a} -> {us.i_want})\n"

        body += f"\n### Verification Evidence\n{test_summary}\n"
        body += "\n---\n*Delivered autonomously by AI Java Engineer platform.*"

        return PullRequestPayload(
            title=f"feat: {product_spec.title}",
            branch=branch_name,
            base_branch=base_branch,
            body=body,
            labels=["agent-generated", "java", "spring-boot"],
        )
