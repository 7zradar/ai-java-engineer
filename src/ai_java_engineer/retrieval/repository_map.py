"""Static code intelligence for Java projects (AST/Regex symbol indexing)."""

import os
import re
from pathlib import Path

from pydantic import BaseModel, Field

PACKAGE_REGEX = re.compile(r"^\s*package\s+([a-zA-Z0-9_\.]+)\s*;", re.MULTILINE)
CLASS_REGEX = re.compile(
    r"(?:public\s+|protected\s+|private\s+)?(?:abstract\s+|final\s+)?(class|interface|record|enum)\s+([A-Za-z0-9_]+)",
    re.MULTILINE,
)
ANNOTATION_REGEX = re.compile(r"@([A-Za-z0-9_]+)")
METHOD_REGEX = re.compile(
    r"(?:public|protected|private)\s+(?:static\s+)?[A-Za-z0-9_<>,\[\]]+\s+([A-Za-z0-9_]+)\s*\([^\)]*\)",
    re.MULTILINE,
)


class JavaSymbolInfo(BaseModel):
    file_path: str
    package: str
    kind: str  # class, interface, record, enum
    name: str
    annotations: list[str] = Field(default_factory=list)
    methods: list[str] = Field(default_factory=list)


class RepositoryMap(BaseModel):
    root_path: str
    total_files: int = 0
    symbols: list[JavaSymbolInfo] = Field(default_factory=list)
    pom_files: list[str] = Field(default_factory=list)


class RepositoryScanner:
    """Scans and indexes Java projects without needing external compilers or heavy embeddings."""

    EXCLUDED_DIRS = {".git", "target", ".idea", ".vscode", "build", "node_modules"}

    @classmethod
    def scan(cls, root_path: str | Path) -> RepositoryMap:
        root = Path(root_path).resolve()
        repo_map = RepositoryMap(root_path=str(root))

        if not root.exists():
            return repo_map

        for dirpath, dirnames, filenames in os.walk(root):
            # Prune excluded directories
            dirnames[:] = [d for d in dirnames if d not in cls.EXCLUDED_DIRS]

            for filename in filenames:
                file_path = Path(dirpath) / filename
                rel_path = str(file_path.relative_to(root)).replace("\\", "/")
                repo_map.total_files += 1

                if filename == "pom.xml":
                    repo_map.pom_files.append(rel_path)

                if filename.endswith(".java"):
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="replace")
                        symbols = cls._parse_java_symbols(rel_path, content)
                        repo_map.symbols.extend(symbols)
                    except Exception:
                        continue

        return repo_map

    @classmethod
    def _parse_java_symbols(cls, rel_path: str, content: str) -> list[JavaSymbolInfo]:
        pkg_match = PACKAGE_REGEX.search(content)
        package_name = pkg_match.group(1) if pkg_match else "default"

        annotations = ANNOTATION_REGEX.findall(content)
        methods = METHOD_REGEX.findall(content)

        symbols = []
        for match in CLASS_REGEX.finditer(content):
            kind, name = match.group(1), match.group(2)
            symbols.append(
                JavaSymbolInfo(
                    file_path=rel_path,
                    package=package_name,
                    kind=kind,
                    name=name,
                    annotations=list(set(annotations)),
                    methods=list(set(methods))[:15],  # Cap for context compactness
                )
            )

        return symbols
