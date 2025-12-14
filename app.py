from __future__ import annotations

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from src.gitgrade import evaluate_repository
from src.gitgrade.render import render_text_report


load_dotenv()

APP_TITLE = "GitGrade — Repo Evaluator"
MODEL_NAME = "gemini-2.5-flash"  # user requested


def _get_cache_dir() -> Path:
    return Path(".cache") / "repos"


st.set_page_config(page_title=APP_TITLE, page_icon="📦", layout="centered")

st.title("GitGrade")
st.caption("Paste a GitHub repo URL to get Score + Summary + Roadmap")

with st.sidebar:
    st.subheader("Settings")
    st.write(f"Model: `{MODEL_NAME}`")

    # Prefer env var, allow manual override for convenience.
    env_key = os.getenv("GOOGLE_API_KEY", "").strip()
    api_key = st.text_input(
        "GOOGLE_API_KEY",
        value=env_key,
        type="password",
        placeholder="paste your key here",
        help="Leave blank to run without LLM summary.",
    ).strip()

    force_refresh = st.checkbox("Force re-clone", value=False, help="Re-clone even if cached")

repo_url = st.text_input(
    "GitHub Repository URL",
    placeholder="https://github.com/username/repo",
)

analyze = st.button("Evaluate", type="primary")

if analyze:
    if not repo_url.strip():
        st.error("Please enter a GitHub repository URL.")
        st.stop()

    with st.spinner("Cloning and evaluating repository..."):
        try:
            result = evaluate_repository(
                repo_url=repo_url.strip(),
                cache_dir=_get_cache_dir(),
                google_api_key=api_key or None,
                model=MODEL_NAME,
                force_refresh=force_refresh,
            )
        except Exception as e:
            st.error(str(e))
            st.stop()

    st.markdown("---")
    st.subheader("Result")

    st.metric("Score", f"{result.score.total} / 100")

    st.markdown("**Summary**")
    st.write(result.summary)

    st.markdown("**Roadmap**")
    for item in result.roadmap:
        st.write(f"- {item}")

    with st.expander("Score breakdown"):
        st.json(
            {
                "documentation": result.score.documentation,
                "structure": result.score.structure,
                "testing_ci": result.score.testing_ci,
                "git_hygiene": result.score.git_hygiene,
                "code_health": result.score.code_health,
            }
        )

    with st.expander("Raw text output"):
        st.code(render_text_report(result), language="text")
