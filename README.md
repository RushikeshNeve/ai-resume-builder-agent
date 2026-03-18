# Resume Optimizer Agent (Premium Streamlit Dashboard)

A recruiter-grade, dark-theme Streamlit SaaS interface for optimizing LaTeX resumes against a target Job Description (JD).

## Overview

Resume Optimizer Agent accepts a JD + LaTeX resume, runs OpenAI analysis/generation, and produces:

- ATS report with score + breakdown
- JD keyword extraction
- Skill gap analysis
- Rewritten professional summary
- Optimized bullet points
- Full optimized LaTeX resume
- Compiled PDF (when `pdflatex` is installed)

The app preserves fallback behavior using `base_resume.tex` when no resume file is uploaded.

---

## Features

### Premium Dashboard UI

- Dark, glassmorphism-inspired SaaS design
- Gradient hero header with feature badges
- Styled sidebar controls and status panel
- Card-based information architecture
- Metric cards for ATS overview
- Tabbed analysis workspace
- Styled download cards and action buttons
- Collapsed debug/logs panel for diagnostics

### Functional Workflow

1. Input JD text.
2. Upload optional `.tex` resume.
3. Fallback to bundled `base_resume.tex` if upload is missing and fallback is enabled.
4. Generate ATS report + optimized LaTeX via OpenAI.
5. Compile LaTeX to PDF (two-pass `pdflatex`).
6. Download:
   - `ats_report.md`
   - `optimized_resume.tex`
   - `optimized_resume.pdf`

### Robust Parsing

- Handles section marker variations, including different punctuation and casing.
- Supports markdown fenced LaTeX blocks.
- Uses regex + safe fallbacks for:
  - ATS score
  - keyword/skills match
  - missing skills count
  - technical/soft skills
  - responsibilities
  - keywords
  - missing/weak/strong skill groups
  - summary and bullet sections

---

## UI Information Architecture

1. **Hero Header**
2. **Sidebar Controls**
3. **Input Workspace**
4. **ATS Overview Metrics**
5. **Analysis Tabs**
   - JD Breakdown
   - Skill Gap Analysis
   - Bullet Improvements
   - Optimized Resume
   - Downloads
6. **PDF Preview** (inside Optimized Resume tab)
7. **Debug / Logs** (collapsed)

---

## Setup

### Prerequisites

- Python 3.10+
- OpenAI API key
- Optional (recommended): LaTeX with `pdflatex` for PDF generation

### Install

```bash
pip install -r requirements.txt
```

### Run

```bash
streamlit run app.py
```

Then open the local Streamlit URL printed in your terminal.

---

## Configuration Notes

- API key can be provided in:
  - Sidebar input field, or
  - `OPENAI_API_KEY` environment variable.
- Model is selectable in the sidebar.
- Resume source behavior:
  - Uploaded `.tex` takes priority.
  - If none uploaded and fallback enabled, `base_resume.tex` is used.
  - If fallback disabled and no upload provided, generation is blocked.

---

## File Structure

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
    └── optimized_resume.pdf
```

---

## PDF Generation Details

- Optimized `.tex` is written to a temporary directory.
- `pdflatex` runs **twice** with:
  - `-interaction=nonstopmode`
  - `-halt-on-error`
- On success:
  - PDF bytes are returned
  - file is saved under `outputs/optimized_resume.pdf`
  - inline PDF preview is shown in the app
- On failure:
  - compile logs are surfaced in Debug/Logs
  - `.md` and `.tex` downloads remain available
  - previous successful PDF may be reused from cache when present

---

## Troubleshooting

### Missing API key

- Symptom: generation blocked with error.
- Fix: provide a valid key in sidebar or export `OPENAI_API_KEY`.

### Missing JD text

- Symptom: generation blocked.
- Fix: paste complete job description into JD editor.

### No resume source

- Symptom: generation blocked.
- Fix: upload `.tex` or enable bundled base resume fallback.

### PDF compile fails

- Symptom: no PDF preview/download.
- Fixes:
  - install LaTeX/`pdflatex`
  - inspect compile logs in Debug/Logs
  - still download `.tex`, fix LaTeX locally, and compile offline

### Parsing quality issues

- Symptom: partial metrics or sections not extracted.
- Fix: inspect raw model output in Debug/Logs and adjust prompts/format if needed.

---

## Prompt Files

Prompt templates remain in:

- `prompts/system_prompt.txt`
- `prompts/user_prompt.txt`

No prompt changes are required for the upgraded dashboard.
