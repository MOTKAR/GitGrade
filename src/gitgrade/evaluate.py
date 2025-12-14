from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from .git_metrics import compute_git_metrics
from .git_ops import clone_repo
from .models import EvaluationResult, RepoIdentity
from .repo_metrics import compute_repo_file_metrics, compute_structure_flags
from .scoring import score_repository


def evaluate_repository(
    *,
    repo_url: str,
    cache_dir: Path,
    google_api_key: Optional[str],
    model: str,
    force_refresh: bool = False,
) -> EvaluationResult:
    clone = clone_repo(repo_url, cache_base=cache_dir, force_refresh=force_refresh)

    repo_path = clone.local_path

    file_metrics = compute_repo_file_metrics(repo_path)
    structure_flags = compute_structure_flags(repo_path)
    git_metrics, git_debug = compute_git_metrics(repo_path)

    breakdown, debug = score_repository(file_metrics, structure_flags, git_metrics)

    identity = RepoIdentity(
        url=repo_url,
        owner=clone.owner,
        name=clone.name,
        default_branch=clone.default_branch,
    )

    # Build a compact metrics object for the LLM.
    llm_metrics: Dict[str, Any] = {
        "repo": {
            "url": repo_url,
            "owner": clone.owner,
            "name": clone.name,
            "default_branch": clone.default_branch,
        },
        "score_breakdown": {
            "documentation": breakdown.documentation,
            "structure": breakdown.structure,
            "testing_ci": breakdown.testing_ci,
            "git_hygiene": breakdown.git_hygiene,
            "code_health": breakdown.code_health,
        },
        "static": {
            "readme_present": file_metrics.readme_present,
            "readme_words": file_metrics.readme_words,
            "readme_quality": file_metrics.readme_quality,
            "license_present": file_metrics.license_present,
            "contributing_present": file_metrics.contributing_present,
            "code_of_conduct_present": file_metrics.code_of_conduct_present,
            "changelog_present": file_metrics.changelog_present,
            "has_tests": file_metrics.has_tests,
            "has_ci": file_metrics.has_ci,
            "language_breakdown": file_metrics.language_breakdown,
            "total_files": file_metrics.total_files,
            "total_bytes": file_metrics.total_bytes,
        },
        "structure_flags": structure_flags,
        "git": git_debug,
    }

    summary = ""
    roadmap = []

    if google_api_key:
        # Lazy import so the app can run without pulling LLM deps / warnings.
        from .llm_report import generate_summary_and_roadmap

        summary, roadmap = generate_summary_and_roadmap(
            google_api_key=google_api_key,
            model=model,
            score_total=breakdown.total,
            metrics=llm_metrics,
        )
    else:
        summary = "Add GOOGLE_API_KEY to enable AI-generated summary and roadmap."
        roadmap = [
            "Add README with setup and usage",
            "Add tests and CI workflows",
            "Commit more regularly with meaningful messages",
        ]

    return EvaluationResult(
        identity=identity,
        score=breakdown,
        metrics={"debug": debug, "llm_metrics": llm_metrics},
        summary=summary,
        roadmap=roadmap,
    )
