"""Secure filesystem operations bounded strictly to an authorized workspace."""

import hashlib
from pathlib import Path

from pydantic import BaseModel

from ai_java_engineer.infrastructure.errors import PathOutOfBoundsError
from ai_java_engineer.security.permissions import check_tool_permission


class ReadFileInput(BaseModel):
    path: str
    start_line: int | None = None
    end_line: int | None = None


class ReadFileOutput(BaseModel):
    path: str
    content: str
    sha256: str
    total_lines: int
    truncated: bool = False


class WriteFileInput(BaseModel):
    path: str
    content: str


class WriteFileOutput(BaseModel):
    path: str
    bytes_written: int
    sha256: str


class SecureFilesystem:
    """Bounded filesystem sandbox protecting against path traversal outside workspace."""

    def __init__(self, workspace_root: str | Path):
        self.workspace_root = Path(workspace_root).resolve()
        if not self.workspace_root.exists():
            self.workspace_root.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, relative_path: str) -> Path:
        """Resolves target path and strictly verifies it is inside workspace root."""
        clean_rel = relative_path.lstrip("/\\")
        target_path = (self.workspace_root / clean_rel).resolve()
        try:
            target_path.relative_to(self.workspace_root)
        except ValueError:
            raise PathOutOfBoundsError(relative_path, str(self.workspace_root)) from None
        return target_path

    def read_file(self, inp: ReadFileInput) -> ReadFileOutput:
        check_tool_permission("read_file")
        target = self._resolve_safe_path(inp.path)
        if not target.exists() or not target.is_file():
            raise FileNotFoundError(f"File not found: {inp.path}")

        raw_text = target.read_text(encoding="utf-8", errors="replace")
        sha256_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
        lines = raw_text.splitlines()
        total_lines = len(lines)

        start = (inp.start_line - 1) if inp.start_line and inp.start_line > 0 else 0
        end = inp.end_line if inp.end_line and inp.end_line <= total_lines else total_lines
        sliced_lines = lines[start:end]
        content = "\n".join(sliced_lines)

        return ReadFileOutput(
            path=inp.path,
            content=content,
            sha256=sha256_hash,
            total_lines=total_lines,
            truncated=(start > 0 or end < total_lines),
        )

    def write_file(self, inp: WriteFileInput) -> WriteFileOutput:
        check_tool_permission("write_file")
        target = self._resolve_safe_path(inp.path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(inp.content, encoding="utf-8")

        content_bytes = inp.content.encode("utf-8")
        sha256_hash = hashlib.sha256(content_bytes).hexdigest()

        return WriteFileOutput(
            path=inp.path,
            bytes_written=len(content_bytes),
            sha256=sha256_hash,
        )

    def apply_patch(self, path: str, target_block: str, replacement_block: str) -> WriteFileOutput:
        """Surgically replaces a unique block in target file."""
        check_tool_permission("apply_patch")
        target = self._resolve_safe_path(path)
        if not target.exists():
            raise FileNotFoundError(f"File not found for patch: {path}")

        content = target.read_text(encoding="utf-8", errors="replace")
        if target_block not in content:
            raise ValueError(f"Target block to replace not found in {path}")

        new_content = content.replace(target_block, replacement_block, 1)
        return self.write_file(WriteFileInput(path=path, content=new_content))
