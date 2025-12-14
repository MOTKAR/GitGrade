from __future__ import annotations

import os
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

from .models import RepoFileMetrics


IGNORE_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".next",
}

IGNORE_EXTS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".pdf",
    ".zip",
    ".gz",
    ".tar",
    ".7z",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".pkl",
    ".pt",
    ".onnx",
    ".pyc",
}

LANG_BY_EXT = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".jsx": "JavaScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".kt": "Kotlin",
    ".go": "Go",
    ".rs": "Rust",
    ".cpp": "C++",
    ".cc": "C++",
    ".c": "C",
    ".cs": "C#",
    ".php": "PHP",
    ".rb": "Ruby",
    ".swift": "Swift",
    ".dart": "Dart",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "CSS",
    ".md": "Markdown",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
}


def _iter_files(repo_path: Path) -> Iterable[Path]:
    for root, dirs, files in os.walk(repo_path):
        # prune ignored dirs
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for f in files:
            yield Path(root) / f


def _has_any(repo_path: Path, candidates: Tuple[str, ...]) -> bool:
    for c in candidates:
        if (repo_path / c).exists():
            return True
    # Also check case-insensitively at repo root
    root_files = {p.name.lower() for p in repo_path.iterdir() if p.is_file()}
    return any(c.lower() in root_files for c in candidates)


def _find_readme(repo_path: Path) -> Optional[Path]:
    # Only check repo root (fast and typically where README lives).
    for p in repo_path.iterdir():
        if not p.is_file():
            continue
        n = p.name.lower()
        if n in {"readme", "readme.md", "readme.txt", "readme.rst"}:
            return p
        if n.startswith("readme."):
            return p
    return None


def _readme_quality(text: str) -> float:
    t = (text or "").lower()
    # Score based on presence of common README sections.
    buckets = [
        {"install", "installation", "setup", "requirements"},
        {"usage", "run", "running", "how to"},
        {"features", "about", "overview", "description"},
    ]
    hits = 0
    for keys in buckets:
        if any(k in t for k in keys):
            hits += 1
    return hits / len(buckets)


def compute_repo_file_metrics(repo_path: Path) -> RepoFileMetrics:
    # Documentation files
    readme_path = _find_readme(repo_path)
    readme_present = readme_path is not None

    readme_words = 0
    readme_quality = 0.0
    if readme_path is not None:
        try:
            # Cap read size so large READMEs don't waste time.
            content = readme_path.read_text(encoding="utf-8", errors="ignore")
            if len(content) > 50_000:
                content = content[:50_000]
            readme_words = len(content.split())
            readme_quality = _readme_quality(content)
        except OSError:
            pass

    license_present = _has_any(repo_path, ("LICENSE", "LICENSE.md"))
    contributing_present = _has_any(repo_path, ("CONTRIBUTING.md", "CONTRIBUTING"))
    code_of_conduct_present = _has_any(repo_path, ("CODE_OF_CONDUCT.md", "CODE_OF_CONDUCT"))
    changelog_present = _has_any(repo_path, ("CHANGELOG.md", "CHANGELOG"))

    # CI signals
    has_ci = (repo_path / ".github" / "workflows").exists() or _has_any(
        repo_path, (".gitlab-ci.yml", ".circleci", "azure-pipelines.yml")
    )

    # Tests signals
    has_tests = any(
        (repo_path / d).exists()
        for d in (
            "tests",
            "test",
            "__tests__",
            "spec",
        )
    )

    # File counts / languages
    total_files = 0
    total_bytes = 0
    lang_counter: Counter[str] = Counter()

    for p in _iter_files(repo_path):
        ext = p.suffix.lower()
        if p.name == ".gitignore":
            # keep it counted as file, but don't include for lang
            pass
        if ext in IGNORE_EXTS:
            continue
        try:
            st = p.stat()
        except OSError:
            continue

        total_files += 1
        total_bytes += st.st_size
        lang = LANG_BY_EXT.get(ext)
        if lang and lang not in ("Markdown", "JSON", "YAML"):
            lang_counter[lang] += 1

    return RepoFileMetrics(
        readme_present=readme_present,
        readme_words=readme_words,
        readme_quality=readme_quality,
        license_present=license_present,
        contributing_present=contributing_present,
        code_of_conduct_present=code_of_conduct_present,
        changelog_present=changelog_present,
        has_tests=has_tests,
        has_ci=has_ci,
        language_breakdown=dict(lang_counter),
        total_files=total_files,
        total_bytes=total_bytes,
    )


def compute_structure_flags(repo_path: Path) -> Dict[str, bool]:
    # Light-weight structure hints
    flags = {
        "has_src_dir": (repo_path / "src").exists(),
        "has_docs_dir": (repo_path / "docs").exists(),
        "has_package_json": (repo_path / "package.json").exists(),
        "has_pyproject": (repo_path / "pyproject.toml").exists(),
        "has_requirements": (repo_path / "requirements.txt").exists(),
        "has_dockerfile": (repo_path / "Dockerfile").exists(),
        "has_makefile": (repo_path / "Makefile").exists(),
        "has_gitignore": (repo_path / ".gitignore").exists(),
    }
    return flags
