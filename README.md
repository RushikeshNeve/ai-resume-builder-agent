# Resume Optimizer Agent

A premium dark-theme Streamlit app for resume optimization that feels like a production SaaS product, while preserving the full original ATS + rewrite workflow.

## What this app does

- Paste a target job description.
- Upload an optional `.tex` resume.
- Fallback to bundled `base_resume.tex` when no upload is provided.
- Generate:
  - ATS score and alignment metrics
  - skill-gap analysis
  - recruiter simulation verdict
  - before/after resume diff
  - JD-aligned cover letter
  - optimized LaTeX resume
  - PDF compile + preview + download

---

## UX / UI redesign highlights

The UI has been fully reworked into a cleaner, less boxy, production-grade interface:

- **Hero header** with refined copy and feature pills
- **Sidebar control panel** with compact status summary
- **ATS overview KPI cards** with one primary card + supporting cards
- **Recruiter simulation panel** with clear verdict strip and structured analysis blocks
- **Resume strength insights** pairing radar chart + interpretation panel
- **Analysis workspace tabs**:
  - JD Breakdown
  - Skill Gap
  - Diff Viewer
  - Cover Letter
  - Optimized Resume
  - Downloads
  - Debug
- **Diff viewer redesign** with editorial-style row comparisons
- **Cover letter workspace** with editor + compact action bar
- **Export center** with production-like asset cards

---

## Stateful workflow

Session state is used so the app preserves:

- generated report/results
- accepted changes
- generated cover letter
- selected model and role mode
- uploaded resume content (where possible)

---

## Setup

### Prerequisites

- Python 3.10+
- OpenAI API key
- Optional: LaTeX installation with `pdflatex`, `xelatex`, or `lualatex`

### Install

```bash
pip install -r requirements.txt
```

### Run

```bash
streamlit run app.py
```

---

## Project structure

```text
.
├── app.py
├── base_resume.tex
├── README.md
├── requirements.txt
├── prompts/
│   ├── system_prompt.txt
│   └── user_prompt.txt
└── outputs/
    ├── ats_report.md
    ├── optimized_resume.tex
    └── optimized_resume.pdf
```

---

## Notes

- Prompt files are unchanged; role guidance and output requirements are injected in `app.py`.
- PDF generation uses two-pass LaTeX compilation (`pdflatex` first, then `xelatex` or `lualatex` as fallback) and will gracefully fallback to cached PDF when available.
- If PDF export is unavailable, install a TeX distribution and verify one compiler is on `PATH`, e.g. `pdflatex --version`.
- Debug output is intentionally collapsed and low-visual-priority.
