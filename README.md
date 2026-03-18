# Resume Optimizer Agent - Streamlit UI

## What it does
- Accepts a full job description
- Accepts an optional LaTeX resume file (`.tex`)
- Falls back to `base_resume.tex` if no resume is uploaded
- Generates:
  - ATS report (`.md`)
  - optimized LaTeX resume (`.tex`)
  - PDF if `pdflatex` is available

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Files
- `app.py` - Streamlit app
- `prompts/system_prompt.txt` - System prompt
- `prompts/user_prompt.txt` - User prompt template
- `base_resume.tex` - Default resume used when no file is uploaded
