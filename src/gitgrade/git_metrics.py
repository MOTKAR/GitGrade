from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Tuple

from git import Repo

from .models import GitMetrics


def _is_good_commit_message(msg: str) -> bool:
    m = (msg or "").strip()
    if len(m) < 12:
        return False
    if m.lower() in {"update", "updates", "fix", "fixed", "changes"}:
        return False
    # Heuristic: first line should not be a file name or just a version bump.
    first = m.splitlines()[0]
    if first.endswith(('.py', '.js', '.ts', '.java', '.md')):
        return False
    return True


def compute_git_metrics(repo_path: Path) -> Tuple[GitMetrics, Dict]:
    repo = Repo(str(repo_path))
    commits = list(repo.iter_commits())

    commit_count = len(commits)
    if commit_count == 0:
        gm = GitMetrics(
            commit_count=0,
            contributor_count=0,
            days_covered=0,
            commits_last_30d=0,
            commits_last_90d=0,
            avg_commit_msg_len=0.0,
            pct_good_messages=0.0,
        )
        return gm, {"raw": asdict(gm)}

    # Contributors (by email)
    contributors = {c.author.email for c in commits if c.author and c.author.email}

    now = datetime.now(timezone.utc)

    def _to_dt(c):
        dt = c.committed_datetime
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    newest = _to_dt(commits[0])
    oldest = _to_dt(commits[-1])
    days_covered = max(1, int((newest - oldest).total_seconds() // 86400))

    commits_last_30d = 0
    commits_last_90d = 0

    msg_lens = []
    good = 0

    for c in commits:
        dt = _to_dt(c)
        age_days = (now - dt).total_seconds() / 86400
        if age_days <= 30:
            commits_last_30d += 1
        if age_days <= 90:
            commits_last_90d += 1

        msg = c.message or ""
        msg_lens.append(len(msg.strip()))
        if _is_good_commit_message(msg):
            good += 1

    avg_msg_len = sum(msg_lens) / max(1, len(msg_lens))
    pct_good = good / max(1, commit_count)

    gm = GitMetrics(
        commit_count=commit_count,
        contributor_count=len(contributors),
        days_covered=days_covered,
        commits_last_30d=commits_last_30d,
        commits_last_90d=commits_last_90d,
        avg_commit_msg_len=avg_msg_len,
        pct_good_messages=pct_good,
    )

    # Extra raw stats useful for LLM.
    raw = {
        "newest_commit": newest.isoformat(),
        "oldest_commit": oldest.isoformat(),
    }
    return gm, {"raw": raw, "metrics": asdict(gm)}
