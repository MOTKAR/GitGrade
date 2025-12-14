from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple


_GITHUB_RE = re.compile(
    r"^https?://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<name>[A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)


@dataclass
class CloneResult:
    local_path: Path
    owner: Optional[str]
    name: Optional[str]
    default_branch: Optional[str]


def parse_github_url(url: str) -> Tuple[Optional[str], Optional[str]]:
    m = _GITHUB_RE.match(url.strip())
    if not m:
        return None, None
    return m.group("owner"), m.group("name")


def _repo_cache_dir(base: Path, repo_url: str) -> Path:
    h = hashlib.sha256(repo_url.strip().encode("utf-8")).hexdigest()[:16]
    return base / h


def _run_git(args: list[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    # Avoid pagers / prompts.
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def get_default_branch(repo_url: str) -> Optional[str]:
    # Uses ls-remote to discover HEAD without cloning full history.
    # Output line example:
    #   ref: refs/heads/main	HEAD
    p = _run_git(["ls-remote", "--symref", repo_url, "HEAD"])
    if p.returncode != 0:
        return None
    for line in p.stdout.splitlines():
        if line.startswith("ref:") and "\tHEAD" in line:
            # ref: refs/heads/main	HEAD
            parts = line.split()
            if len(parts) >= 2:
                ref = parts[1].split("\t")[0]
                if ref.startswith("refs/heads/"):
                    return ref.replace("refs/heads/", "")
    return None


def clone_repo(
    repo_url: str,
    cache_base: Path,
    depth: int = 200,
    force_refresh: bool = False,
) -> CloneResult:
    owner, name = parse_github_url(repo_url)
    if not owner or not name:
        raise ValueError(
            "Invalid GitHub URL. Expected format: https://github.com/<owner>/<repo>"
        )

    dest = _repo_cache_dir(cache_base, repo_url)

    if force_refresh and dest.exists():
        shutil.rmtree(dest, ignore_errors=True)

    if dest.exists() and (dest / ".git").exists():
        return CloneResult(
            local_path=dest,
            owner=owner,
            name=name,
            default_branch=get_default_branch(repo_url),
        )

    dest.parent.mkdir(parents=True, exist_ok=True)

    # Shallow clone to reduce time/disk. We do not execute any code from the repo.
    p = _run_git(["clone", "--depth", str(depth), "--no-tags", repo_url, str(dest)])
    if p.returncode != 0:
        # Cleanup partial clone.
        shutil.rmtree(dest, ignore_errors=True)
        raise RuntimeError(f"git clone failed: {p.stderr.strip() or p.stdout.strip()}")

    return CloneResult(local_path=dest, owner=owner, name=name, default_branch=get_default_branch(repo_url))
