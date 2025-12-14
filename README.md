# GitGrade (Streamlit)
Evaluate a student GitHub repository and convert it into a **Score (0–100)** + **Summary** + **Personalized Roadmap**.

## Features
- Streamlit UI: paste a GitHub repo URL and get an instant report
- Safe analysis: does **not** execute repo code (static + git metadata only)
- Hybrid scoring:
  - Deterministic heuristics for a stable score
  - Gemini (via LangChain) for human-readable summary + roadmap

## Setup
1. Create a virtual environment
2. Install dependencies:
   - `pip install -r requirements.txt`
   - (optional dev tools) `pip install -r requirements-dev.txt`
3. Add your Gemini API key:
   - Copy `.env.example` to `.env`
   - Set `GOOGLE_API_KEY=...`

## Run
- `streamlit run app.py`

## Example (from prompt)
Input:
- `https://github.com/rasbt/python-machine-learning-book`

Output (format):
- Score: 42 / 100
- Summary: Basic project structure but poor documentation and inconsistent commits.
- Roadmap:
  - Add README with setup instructions
  - Restructure folders
  - Commit regularly with meaningful messages

## Example (smoke test)
Input:
- `https://github.com/octocat/Hello-World`

Output (no API key):
- Score: 22 / 100
- Summary: Add GOOGLE_API_KEY to enable AI-generated summary and roadmap.
- Roadmap:
  - Add README with setup and usage
  - Add tests and CI workflows
  - Commit more regularly with meaningful messages

## Notes
- Scores are best-effort heuristics.
- Private repositories are not supported unless you extend cloning with auth.

