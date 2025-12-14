from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Tuple

from .models import GitMetrics, RepoFileMetrics, ScoreBreakdown


def _clamp(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, n))


def score_repository(
    file_metrics: RepoFileMetrics,
    structure_flags: Dict[str, bool],
    git_metrics: GitMetrics,
) -> Tuple[ScoreBreakdown, Dict[str, Any]]:
    # Weights (sum=100)
    # docs=25, structure=20, testing/ci=20, git=20, health=15

    # 1) Documentation (0..25)
    docs = 0

    # README presence + quality + length
    if file_metrics.readme_present:
        docs += 8
        docs += int(round(8 * file_metrics.readme_quality))
        if file_metrics.readme_words >= 200:
            docs += 4
        elif file_metrics.readme_words >= 80:
            docs += 2
        elif file_metrics.readme_words >= 20:
            docs += 1

    docs += 3 if file_metrics.license_present else 0
    docs += 1 if file_metrics.contributing_present else 0
    docs += 1 if file_metrics.code_of_conduct_present else 0
    docs += 0 if not file_metrics.changelog_present else 1

    documentation = _clamp(docs, 0, 25)

    # 2) Structure (0..20)
    structure = 0
    structure += 6 if structure_flags.get("has_src_dir") else 0
    structure += 4 if structure_flags.get("has_docs_dir") else 0
    structure += 3 if structure_flags.get("has_dockerfile") else 0
    structure += 3 if structure_flags.get("has_makefile") else 0
    structure += 2 if structure_flags.get("has_gitignore") else 0
    # Project metadata (package.json or python deps)
    structure += 2 if (
        structure_flags.get("has_package_json")
        or structure_flags.get("has_pyproject")
        or structure_flags.get("has_requirements")
    ) else 0
    structure = _clamp(structure, 0, 20)

    # 3) Testing & CI (0..20)
    testing_ci = 0
    testing_ci += 10 if file_metrics.has_tests else 0
    testing_ci += 10 if file_metrics.has_ci else 0
    testing_ci = _clamp(testing_ci, 0, 20)

    # 4) Git hygiene (0..20)
    git = 0
    # Commit volume
    if git_metrics.commit_count >= 30:
        git += 6
    elif git_metrics.commit_count >= 10:
        git += 4
    elif git_metrics.commit_count >= 3:
        git += 2

    # Recency / cadence (based on last 90 days)
    if git_metrics.commits_last_90d >= 12:
        git += 6
    elif git_metrics.commits_last_90d >= 4:
        git += 4
    elif git_metrics.commits_last_90d >= 1:
        git += 2

    # Commit message quality
    git += int(round(8 * git_metrics.pct_good_messages))
    git = _clamp(git, 0, 20)

    # 5) Code health signals (0..15)
    health = 0
    # Languages: reward at least one recognized language file
    health += 4 if sum(file_metrics.language_breakdown.values()) > 0 else 0
    # Repo size sanity (avoid empty repos)
    if file_metrics.total_files >= 20:
        health += 5
    elif file_metrics.total_files >= 5:
        health += 3
    elif file_metrics.total_files >= 1:
        health += 1
    # Contributors
    if git_metrics.contributor_count >= 3:
        health += 3
    elif git_metrics.contributor_count >= 2:
        health += 2
    elif git_metrics.contributor_count >= 1:
        health += 1

    # Add 0..3 bonus for having CI+tests together (realistic engineering)
    if file_metrics.has_ci and file_metrics.has_tests:
        health += 3

    health = _clamp(health, 0, 15)

    total = documentation + structure + testing_ci + git + health

    breakdown = ScoreBreakdown(
        documentation=documentation,
        structure=structure,
        testing_ci=testing_ci,
        git_hygiene=git,
        code_health=health,
        total=total,
    )

    debug = {
        "weights": {
            "documentation": 25,
            "structure": 20,
            "testing_ci": 20,
            "git_hygiene": 20,
            "code_health": 15,
        },
        "file_metrics": asdict(file_metrics),
        "structure_flags": structure_flags,
        "git_metrics": asdict(git_metrics),
    }
    return breakdown, debug
