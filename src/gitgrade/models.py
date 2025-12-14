from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class RepoIdentity:
    url: str
    owner: Optional[str] = None
    name: Optional[str] = None
    default_branch: Optional[str] = None


@dataclass
class RepoFileMetrics:
    readme_present: bool
    readme_words: int
    readme_quality: float  # 0..1 (keywords-based heuristic)

    license_present: bool
    contributing_present: bool
    code_of_conduct_present: bool
    changelog_present: bool

    has_tests: bool
    has_ci: bool

    language_breakdown: Dict[str, int]  # language -> files
    total_files: int
    total_bytes: int


@dataclass
class GitMetrics:
    commit_count: int
    contributor_count: int
    days_covered: int

    commits_last_30d: int
    commits_last_90d: int

    avg_commit_msg_len: float
    pct_good_messages: float  # 0..1


@dataclass
class ScoreBreakdown:
    documentation: int
    structure: int
    testing_ci: int
    git_hygiene: int
    code_health: int

    total: int


@dataclass
class EvaluationResult:
    identity: RepoIdentity
    score: ScoreBreakdown
    metrics: Dict[str, Any]

    summary: str
    roadmap: List[str]
