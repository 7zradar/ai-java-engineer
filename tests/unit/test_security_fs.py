"""Unit tests for secure filesystem containment and secret sanitization."""

import tempfile
from pathlib import Path

import pytest

from ai_java_engineer.infrastructure.errors import PathOutOfBoundsError, SecurityViolationError
from ai_java_engineer.security.permissions import check_tool_permission
from ai_java_engineer.security.sanitizer import SecretSanitizer
from ai_java_engineer.tools.filesystem.secure_fs import (
    ReadFileInput,
    SecureFilesystem,
    WriteFileInput,
)


def test_secret_sanitizer_masks_tokens():
    raw = "My OpenAI key is sk-1234567890abcdef1234567890 and Gemini AIzaSyA1234567890abcdef1234567890abcde"
    sanitized = SecretSanitizer.sanitize(raw)
    assert "sk-" not in sanitized
    assert "AIzaSy" not in sanitized
    assert "[REDACTED_API_KEY]" in sanitized
    assert "[REDACTED_GEMINI_KEY]" in sanitized


def test_secure_fs_boundary_enforcement():
    with tempfile.TemporaryDirectory() as temp_dir:
        fs = SecureFilesystem(temp_dir)

        # Valid write within boundary
        out = fs.write_file(WriteFileInput(path="src/Main.java", content="public class Main {}"))
        assert out.bytes_written > 0
        assert (Path(temp_dir) / "src/Main.java").exists()

        # Valid read within boundary
        read_out = fs.read_file(ReadFileInput(path="src/Main.java"))
        assert "public class Main" in read_out.content

        # Path traversal attack outside boundary must raise PathOutOfBoundsError
        with pytest.raises(PathOutOfBoundsError):
            fs.read_file(ReadFileInput(path="../../etc/passwd"))

        with pytest.raises(PathOutOfBoundsError):
            fs.write_file(WriteFileInput(path="../outside.txt", content="hack"))


def test_tool_permissions():
    # Low risk allowed
    check_tool_permission("read_file")

    # High risk without approval raises error
    with pytest.raises(SecurityViolationError):
        check_tool_permission("git_push", human_approved=False)

    # High risk with approval passes
    check_tool_permission("git_push", human_approved=True)

    # Forbidden tool always raises error
    with pytest.raises(SecurityViolationError):
        check_tool_permission("merge_to_main")
