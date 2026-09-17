"""Context Engineering: assembling bounded context windows for LLM agents."""

from pathlib import Path

from ai_java_engineer.retrieval.repository_map import RepositoryMap
from ai_java_engineer.security.injection_guard import InjectionGuard


class ContextBuilder:
    """Selects and bundles repository context under explicit token ceilings."""

    def __init__(self, workspace_root: str | Path, max_context_chars: int = 120_000):
        self.workspace_root = Path(workspace_root).resolve()
        self.max_context_chars = max_context_chars

    def build_context(self, repo_map: RepositoryMap, target_packages: list[str] | None = None) -> str:
        """Assembles a secure context bundle containing repository structure and critical source files."""
        context_parts = []
        current_length = 0

        # 1. Structural Overview
        summary_block = (
            f"=== REPOSITORY OVERVIEW ===\n"
            f"Total indexed files: {repo_map.total_files}\n"
            f"Java Symbols identified: {len(repo_map.symbols)}\n"
            f"Build manifests: {', '.join(repo_map.pom_files) if repo_map.pom_files else 'None'}\n\n"
            f"=== SYMBOL CATALOG ===\n"
        )
        for sym in repo_map.symbols[:30]:
            ann_str = f" [@{', @'.join(sym.annotations)}]" if sym.annotations else ""
            summary_block += f"- {sym.kind} {sym.package}.{sym.name}{ann_str} ({sym.file_path})\n"

        context_parts.append(summary_block)
        current_length += len(summary_block)

        # 2. Select Relevant Source Files
        for sym in repo_map.symbols:
            if target_packages and not any(pkg in sym.package for pkg in target_packages):
                continue

            file_path = self.workspace_root / sym.file_path
            if file_path.exists() and file_path.is_file():
                try:
                    content = file_path.read_text(encoding="utf-8", errors="replace")
                    wrapped = InjectionGuard.wrap_untrusted_data(sym.file_path, content)
                    if current_length + len(wrapped) > self.max_context_chars:
                        break
                    context_parts.append(wrapped)
                    current_length += len(wrapped)
                except Exception:
                    continue

        return "\n".join(context_parts)
