from __future__ import annotations

from typing import List

from .models import EvaluationResult


def render_text_report(result: EvaluationResult) -> str:
    lines: List[str] = []
    lines.append(f"Score: {result.score.total} / 100")
    lines.append("")
    lines.append("Summary: " + result.summary.strip())
    lines.append("")
    lines.append("Roadmap:")
    for item in result.roadmap:
        lines.append(f"● {item}")
    return "\n".join(lines)
