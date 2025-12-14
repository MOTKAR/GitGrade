from __future__ import annotations

import json
import re
from typing import List, Tuple


_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def _extract_json_object(text: str) -> str:
    """Best-effort extraction of the first JSON object from an LLM response."""
    t = (text or "").strip()
    if not t:
        return ""

    # Remove common ```json fences.
    t = _CODE_FENCE_RE.sub("", t).strip()

    # If there's extra text, slice from first { to last }.
    i = t.find("{")
    j = t.rfind("}")
    if i == -1 or j == -1 or j <= i:
        return ""
    return t[i : j + 1]


def _safe_json_loads(s: str) -> dict:
    try:
        return json.loads(s)
    except Exception:
        return {}


def _heuristic_fallback(score_total: int, metrics: dict) -> Tuple[str, List[str]]:
    """Fallback when the model doesn't return valid JSON."""

    sb = metrics.get("score_breakdown", {}) if isinstance(metrics, dict) else {}
    static = metrics.get("static", {}) if isinstance(metrics, dict) else {}
    git = (metrics.get("git", {}) or {}).get("metrics", {}) if isinstance(metrics, dict) else {}

    def _low(name: str, threshold: int) -> bool:
        v = int(sb.get(name, 0) or 0)
        return v <= threshold

    issues: List[str] = []
    if _low("documentation", 10) or not static.get("readme_present"):
        issues.append("weak documentation")
    if _low("testing_ci", 5) or (not static.get("has_tests") and not static.get("has_ci")):
        issues.append("missing tests/CI")
    if _low("git_hygiene", 6) or float(git.get("pct_good_messages", 0) or 0) < 0.4:
        issues.append("inconsistent commit quality")
    if _low("structure", 6):
        issues.append("project structure can be improved")

    if not issues:
        issues = ["a few opportunities to improve overall polish"]

    summary = (
        f"Score is {score_total}/100. The repository shows {issues[0]}"
        + (f" and {issues[1]}." if len(issues) > 1 else ".")
        + " Focus on the highest-impact fundamentals first."
    )

    roadmap: List[str] = []
    if not static.get("readme_present") or int(static.get("readme_words", 0) or 0) < 80:
        roadmap.append("Add README with setup and usage")
    if not static.get("has_tests"):
        roadmap.append("Add a basic test suite")
    if not static.get("has_ci"):
        roadmap.append("Add CI workflow (GitHub Actions)")
    if float(git.get("pct_good_messages", 0) or 0) < 0.6:
        roadmap.append("Write clearer commit messages")
    roadmap.append("Improve folder structure and separation of concerns")

    # Keep it short.
    roadmap = roadmap[:6]
    return summary, roadmap


def generate_summary_and_roadmap(
    *,
    google_api_key: str,
    model: str,
    score_total: int,
    metrics: dict,
) -> Tuple[str, List[str]]:
    """Generate human-readable feedback using only high-level metrics (no full codebase dump)."""

    # Lazy imports: avoids importing LangChain when API key isn't provided.
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_google_genai import ChatGoogleGenerativeAI

    llm = ChatGoogleGenerativeAI(
        model=model,
        google_api_key=google_api_key,
        temperature=0.0,
    )

    # Ask for JSON to make parsing reliable.
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a senior engineer reviewing a student project repository. "
                "Be honest, constructive, and specific. Do not invent facts beyond the provided metrics.",
            ),
            (
                "human",
                "Repository evaluation metrics (JSON):\n{metrics_json}\n\n"
                "The computed score is: {score_total}/100\n\n"
                "Return STRICT JSON ONLY with this schema:\n"
                "{{\"summary\": string, \"roadmap\": [string, string, string, ...]}}\n\n"
                "Important:\n"
                "- Output JSON only (no markdown, no code fences, no extra text).\n"
                "Rules:\n"
                "- summary: 2-3 sentences.\n"
                "- roadmap: 3-6 bullet items, each starting with a verb, actionable, no fluff.\n"
                "- Keep roadmap items short (<= 12 words each).\n",
            ),
        ]
    )

    metrics_json = json.dumps(metrics, ensure_ascii=False, indent=2)
    resp = (prompt | llm).invoke({"metrics_json": metrics_json, "score_total": score_total})
    content = (getattr(resp, "content", "") or "").strip()

    # Parse JSON robustly.
    extracted = _extract_json_object(content)
    data = _safe_json_loads(extracted)

    summary = (data.get("summary") or "").strip() if isinstance(data, dict) else ""
    roadmap = data.get("roadmap") if isinstance(data, dict) else None
    roadmap = roadmap if isinstance(roadmap, list) else []
    roadmap = [str(x).strip() for x in roadmap if str(x).strip()]

    # Fallback to heuristic output if model didn't comply.
    if not summary or not roadmap:
        return _heuristic_fallback(score_total=score_total, metrics=metrics)

    return summary, roadmap
