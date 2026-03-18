# Resume Optimizer Agent (Streamlit)

A polished Streamlit app that tailors a LaTeX resume to a target job description using OpenAI.

## Features

- Premium, recruiter-focused UI (hero section, cards, tabs, metrics, and downloads).
- Job Description input with large editor.
- Optional `.tex` upload for your current resume.
- Fallback to bundled `base_resume.tex` when upload is missing.
- OpenAI-powered optimization flow using prompt templates in `prompts/`.
- Robust response parsing for two-section output:
  - `SECTION 1 — COMPREHENSIVE ATS REPORT`
  - `SECTION 2 — UPDATED LATEX RESUME`
- ATS insight rendering:
  - ATS score
  - keyword/skills match estimates
  - skill gap analysis
  - JD keyword + responsibility extraction
- Bullet improvement view (best-effort extraction from LaTeX bullets).
- PDF compilation via `pdflatex` (two-pass compile for layout stability).
- Downloadable artifacts:
  - `ats_report.md`
  - `optimized_resume.tex`
  - `optimized_resume.pdf` (when compile succeeds)

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Required setup

- OpenAI API key (entered in the UI or provided as `OPENAI_API_KEY` env var).
- Optional but recommended: local LaTeX installation with `pdflatex` for PDF export.

## File structure

```text
.
├── app.py
├── base_resume.tex
├── requirements.txt
├── prompts/
│   ├── system_prompt.txt
│   └── user_prompt.txt
└── outputs/
    ├── ats_report.md
    ├── optimized_resume.tex
    └── optimized_resume.pdf (created when compilation succeeds)
```

## How PDF export works

- The app writes optimized LaTeX into a temporary directory.
- `pdflatex` runs twice (`-interaction=nonstopmode -halt-on-error`) to stabilize references/layout.
- If compilation succeeds, the PDF is exposed for in-app preview and download.
- If compilation fails, `.md` and `.tex` downloads still remain available and logs are shown in the UI.

## Fallback resume behavior

- If a `.tex` file is uploaded, the app uses that source.
- If no upload is provided and fallback is enabled, `base_resume.tex` is used.
- If both are absent (fallback disabled + no upload), generation is blocked until a resume source is provided.

## Notes on prompts compatibility

- Existing prompt files are preserved and still loaded from `prompts/system_prompt.txt` and `prompts/user_prompt.txt`.
- The app enhances parsing/rendering without requiring prompt file changes.
