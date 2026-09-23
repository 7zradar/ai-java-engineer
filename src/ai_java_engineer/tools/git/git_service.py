"""Deterministic Git operations and PR payload generator."""

import subprocess
from pathlib import Path
from typing import Any

from ai_java_engineer.domain.artifact import PullRequestPayload
from ai_java_engineer.domain.requirement import ProductSpec
from ai_java_engineer.infrastructure.logging import get_logger
from ai_java_engineer.security.permissions import check_tool_permission

logger = get_logger("git_service")


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
        product_spec: ProductSpec | dict[str, Any],
        test_summary: str,
    ) -> PullRequestPayload:
        """Builds a structured Pull Request body."""
        if isinstance(product_spec, dict):
            try:
                product_spec = ProductSpec.model_validate(product_spec)
            except Exception:
                pass

        title = getattr(product_spec, "title", None) or (product_spec.get("title") if isinstance(product_spec, dict) else "Automated Feature")
        summary = getattr(product_spec, "summary", None) or (product_spec.get("summary") if isinstance(product_spec, dict) else "")
        user_stories = getattr(product_spec, "user_stories", None) or (product_spec.get("user_stories", []) if isinstance(product_spec, dict) else [])

        body = (
            f"## Implementación Automatizada de Funcionalidad\n\n"
            f"### Resumen del Requerimiento\n"
            f"{summary}\n\n"
            f"### Historias de Usuario Atendidas\n"
        )
        for us in user_stories:
            u_id = getattr(us, "id", None) or (us.get("id") if isinstance(us, dict) else "")
            u_title = getattr(us, "title", None) or (us.get("title") if isinstance(us, dict) else "")
            u_as_a = getattr(us, "as_a", None) or (us.get("as_a") if isinstance(us, dict) else "")
            u_i_want = getattr(us, "i_want", None) or (us.get("i_want") if isinstance(us, dict) else "")
            body += f"- **{u_id}**: {u_title} ({u_as_a} -> {u_i_want})\n"

        body += f"\n### Evidencia de Verificación y Pruebas\n{test_summary}\n"
        body += "\n---\n*Entregado de forma autónoma por la plataforma Fábrica de Agentes (AI Java Engineer).*"

        return PullRequestPayload(
            title=f"feat: {title}",
            branch=branch_name,
            base_branch=base_branch,
            body=body,
            labels=["agent-generated", "java", "spring-boot"],
        )

    def push_approved_feature_to_remote(
        self,
        branch_name: str,
        commit_message: str,
        files: list[str] | None = None,
        remote_url: str | None = None,
        remote_name: str = "origin",
    ) -> dict[str, Any]:
        """Pushes feature branch to remote GitHub repository and returns PR and branch URLs."""
        check_tool_permission("git_commit")
        self.init_repository_if_needed()

        # 1. Resolve remote repository URL
        if not remote_url:
            try:
                from ai_java_engineer.infrastructure.settings import get_settings
                remote_url = get_settings().github_repo_url
            except Exception:
                remote_url = "https://github.com/7zradar/ai-java-engineer.git"

        # 2. Configure remote origin
        try:
            remotes = self._run_git(["remote"]).splitlines()
            if remote_name in remotes:
                self._run_git(["remote", "set-url", remote_name, remote_url])
            else:
                self._run_git(["remote", "add", remote_name, remote_url])
        except Exception as e:
            logger.warning(f"Warning configuring remote {remote_name}: {e}")

        # 3. If possible, fetch origin/main to have shared history
        try:
            self._run_git(["fetch", remote_name, "main", "--depth=1"])
            self._run_git(["checkout", "-B", branch_name, f"{remote_name}/main"])
        except Exception as e:
            logger.info(f"Using local branch checkout for {branch_name}: {e}")
            try:
                self._run_git(["checkout", "-B", branch_name])
            except Exception:
                pass

        # 4. Stage and commit changes
        if files:
            for f in files:
                try:
                    self._run_git(["add", f])
                except Exception:
                    pass
        else:
            try:
                self._run_git(["add", "-A"])
            except Exception:
                pass

        head_commit = None
        try:
            self._run_git(["commit", "-m", commit_message])
            head_commit = self._run_git(["rev-parse", "HEAD"])
        except Exception:
            try:
                head_commit = self._run_git(["rev-parse", "HEAD"])
            except Exception:
                head_commit = "HEAD"

        # 5. Push branch to remote
        push_success = False
        error_msg = None
        try:
            self._run_git(["push", "-u", remote_name, branch_name])
            push_success = True
            logger.info(f"Successfully pushed branch {branch_name} to {remote_name}")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Git push failed for {branch_name} to {remote_name}: {e}")

        # 6. Parse GitHub owner/repo to build canonical links
        clean_url = remote_url
        if clean_url.endswith(".git"):
            clean_url = clean_url[:-4]
        if "github.com/" in clean_url:
            repo_part = clean_url.split("github.com/")[1]
        elif "github.com:" in clean_url:
            repo_part = clean_url.split("github.com:")[1]
        else:
            repo_part = "7zradar/ai-java-engineer"

        branch_url = f"https://github.com/{repo_part}/tree/{branch_name}"
        pr_url = f"https://github.com/{repo_part}/pull/new/{branch_name}"

        return {
            "success": push_success,
            "error": error_msg,
            "branch_name": branch_name,
            "remote_name": remote_name,
            "remote_url": remote_url,
            "branch_url": branch_url,
            "pr_url": pr_url,
            "commit_hash": head_commit,
        }
