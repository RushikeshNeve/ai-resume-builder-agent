# Resume Optimizer Agent — Premium AI Career Copilot

A polished, dark-theme Streamlit dashboard that upgrades a standard resume optimizer into a premium SaaS-style career copilot.

## Overview

Resume Optimizer Agent accepts:

- a target Job Description (required)
- an optional `.tex` resume upload
- bundled `base_resume.tex` fallback (when upload is missing)

It preserves the original OpenAI optimization flow and now adds recruiter simulation, role-mode optimization, resume diffs, cover letter generation, radar scoring, and selective apply controls.

---

## Core Features

### 1) Recruiter Simulation Engine

After generation, the app shows a recruiter-style hiring panel with:

- verdict (`Reject`, `Borderline`, `Shortlist`, `Strong Hire`)
- confidence score (0–100)
- reasons for verdict
- what is working well
- what needs fixing
- top recommendations

Color-coded verdict badges and a prominent recruiter card are included.

### 2) Role-Specific Optimization Mode

Sidebar role selector:

- Backend Engineer
- Full Stack Engineer
- GenAI Engineer
- Data Engineer

Role mode directly modifies prompt behavior so optimization emphasizes role-relevant outcomes.

### 3) Resume Diff Viewer

Dedicated **Diff Viewer** tab with before/after comparisons for:

- summary
- bullets

Uses stable card-based side-by-side comparisons (best effort bullet pairing).

### 4) JD-Aligned Cover Letter Generator

Dedicated **Cover Letter** tab with:

- editable large text area
- **Use this** button (stores active cover letter in session)
- **Regenerate** button (new LLM version)
- **Copy-ready** button (plain text presentation)
- download support (`cover_letter.txt`, `cover_letter.md`)

### 5) Resume Strength Radar Chart

Radar/spider chart dimensions:

- Technical Depth
- Impact
- Keywords
- Clarity
- ATS Score

Values are parsed when available and inferred safely when missing.

### 6) ATS Score + Breakdown Metrics

Polished metric cards for:

- ATS Score
- Keyword Match %
- Skills Match %
- Missing Skills Count

With estimate labeling when values are inferred.

### 7) PDF Compilation + Download

Preserved and improved two-pass `pdflatex` compilation:

- compile in temp directory
- run `pdflatex` twice
- capture logs
- inline PDF preview when available
- fallback to `.tex` download even when compile fails

### 8) Premium Styling System

Reusable design classes and dark SaaS styling including:

- hero banner
- glass/section cards
- metric cards
- recruiter card + verdict badge
- diff cards
- radar and cover letter cards
- status/download cards

---

## App Sections

1. **Hero Header** (title, subtitle, feature badges, How-it-works expander)
2. **Sidebar** (API key, model, role mode, upload/fallback controls, status card)
3. **Input Workspace** (JD editor + resume source summary)
4. **ATS Metrics Row** (4 metric cards)
5. **Recruiter Simulation Card**
6. **Tabs**:
   - JD Breakdown
   - Skill Gap
   - Diff Viewer
   - Cover Letter
   - Optimized Resume
   - Downloads
   - Debug

---

## Setup

### Prerequisites

- Python 3.10+
- OpenAI API key
- Optional: local LaTeX distribution with `pdflatex`

### Install

```bash
pip install -r requirements.txt
```

### Run

```bash
streamlit run app.py
```

---

## File Structure

```text
.
├── app.py
├── base_resume.tex
├── requirements.txt
├── README.md
├── prompts/
│   ├── system_prompt.txt
│   └── user_prompt.txt
└── outputs/
    ├── ats_report.md
    ├── optimized_resume.tex
    └── optimized_resume.pdf
```

---

## Troubleshooting

### Missing API key

- Add key in sidebar or set `OPENAI_API_KEY` environment variable.

### Missing JD

- Provide full job description text in the input area.

### No resume source loaded

- Upload `.tex`, or enable bundled fallback.

### PDF compile errors

- Install LaTeX/`pdflatex` and check Debug tab logs.
- You can still download optimized `.tex`.

### Parsing variability

- Model output formatting can vary; parser uses regex + fallbacks.
- Use Debug tab to inspect raw output and parsed sections.

---

## Notes

- Existing behavior is preserved: ATS report + optimized LaTeX + optional PDF generation with downloads.
- Prompt files are unchanged; role-specific and extended output instructions are appended dynamically in `app.py`.
