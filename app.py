from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path

import streamlit as st
from openai import OpenAI

APP_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = APP_DIR / "prompts"
BASE_RESUME_PATH = APP_DIR / "base_resume.tex"
OUTPUTS_DIR = APP_DIR / "outputs"
OUTPUTS_DIR.mkdir(exist_ok=True)

DEFAULT_MODEL = "gpt-4.1"

st.set_page_config(
    page_title="Resume Optimizer Agent",
    page_icon="📄",
    layout="wide",
)

def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")

def split_output(output: str) -> tuple[str, str]:
    cleaned = output.strip()

    # remove code fences if model added them
    cleaned = re.sub(r"^```(?:latex|tex|markdown)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    patterns = [
        r"SECTION\s*2\s*[—\-:]\s*UPDATED LATEX RESUME",
        r"SECTION\s*2",
    ]
    for pattern in patterns:
        parts = re.split(pattern, cleaned, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) == 2:
            report = parts[0].strip()
            tex = parts[1].strip()
            tex = re.sub(r"^```(?:latex|tex)?\s*", "", tex)
            tex = re.sub(r"\s*```$", "", tex)
            return report, tex

    return cleaned, ""

def compile_pdf(tex_content: str) -> tuple[bytes | None, str | None]:
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            tex_path = tmp / "optimized_resume.tex"
            tex_path.write_text(tex_content, encoding="utf-8")

            command = [
                "pdflatex",
                "-interaction=nonstopmode",
                "-halt-on-error",
                str(tex_path.name),
            ]

            first = subprocess.run(
                command,
                cwd=tmp,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if first.returncode != 0:
                return None, first.stdout + "\n" + first.stderr

            # Run twice for references/layout stability
            second = subprocess.run(
                command,
                cwd=tmp,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if second.returncode != 0:
                return None, second.stdout + "\n" + second.stderr

            pdf_path = tmp / "optimized_resume.pdf"
            if pdf_path.exists():
                return pdf_path.read_bytes(), None
            return None, "PDF compilation finished, but PDF file was not found."
    except FileNotFoundError:
        return None, "pdflatex is not installed in this environment."
    except subprocess.TimeoutExpired:
        return None, "PDF compilation timed out."
    except Exception as e:
        return None, str(e)

def run_agent(api_key: str, model: str, jd: str, resume_tex: str) -> tuple[str, str, str]:
    client = OpenAI(api_key=api_key)
    system_prompt = load_prompt("system_prompt.txt")
    user_prompt = load_prompt("user_prompt.txt").format(
        job_description=jd.strip(),
        resume_tex=resume_tex.strip(),
    )

    response = client.chat.completions.create(
        model=model,
        temperature=0.2,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    output = response.choices[0].message.content or ""
    report, tex = split_output(output)
    return output, report, tex

st.title("📄 Resume Optimizer Agent")
st.caption("Paste a job description, optionally upload a .tex resume, and generate an ATS report + optimized LaTeX resume + PDF.")

with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("OpenAI API Key", type="password")
    model = st.text_input("Model", value=DEFAULT_MODEL)
    use_base_hint = st.info("If no .tex file is uploaded, the bundled base resume will be used.")
    show_base = st.checkbox("Preview bundled base resume", value=False)

if show_base:
    st.subheader("Bundled Base Resume")
    st.code(BASE_RESUME_PATH.read_text(encoding="utf-8"), language="latex")

col1, col2 = st.columns([1.4, 1])

with col1:
    jd = st.text_area(
        "Job Description",
        height=420,
        placeholder="Paste the full job description here...",
    )

with col2:
    uploaded_tex = st.file_uploader(
        "Optional Resume .tex File",
        type=["tex"],
        accept_multiple_files=False,
    )
    st.markdown("**Current resume source**")
    if uploaded_tex is not None:
        resume_tex = uploaded_tex.getvalue().decode("utf-8", errors="ignore")
        st.success("Using uploaded .tex resume")
    else:
        resume_tex = BASE_RESUME_PATH.read_text(encoding="utf-8")
        st.warning("No .tex uploaded — using bundled base resume")
    st.code(resume_tex[:5000], language="latex")

generate = st.button("Generate ATS Report + Resume", type="primary", use_container_width=True)

if generate:
    if not api_key:
        st.error("Please enter your OpenAI API key.")
        st.stop()
    if not jd.strip():
        st.error("Please paste a job description.")
        st.stop()

    with st.spinner("Running resume optimizer..."):
        try:
            raw_output, report, optimized_tex = run_agent(api_key, model, jd, resume_tex)
        except Exception as e:
            st.exception(e)
            st.stop()

    if not optimized_tex.strip():
        st.error("The model response did not contain a detectable LaTeX section. Check the raw output below.")
        st.subheader("Raw Output")
        st.code(raw_output)
        st.stop()

    report_path = OUTPUTS_DIR / "ats_report.md"
    tex_path = OUTPUTS_DIR / "optimized_resume.tex"
    report_path.write_text(report, encoding="utf-8")
    tex_path.write_text(optimized_tex, encoding="utf-8")

    pdf_bytes, pdf_error = compile_pdf(optimized_tex)
    if pdf_bytes:
        pdf_path = OUTPUTS_DIR / "optimized_resume.pdf"
        pdf_path.write_bytes(pdf_bytes)

    tab1, tab2, tab3 = st.tabs(["ATS Report", "Optimized LaTeX", "Downloads"])

    with tab1:
        st.markdown(report if report.strip() else "_No report section detected._")

    with tab2:
        st.code(optimized_tex, language="latex")

    with tab3:
        st.download_button(
            "Download ATS Report (.md)",
            data=report.encode("utf-8"),
            file_name="ats_report.md",
            mime="text/markdown",
            use_container_width=True,
        )
        st.download_button(
            "Download Optimized Resume (.tex)",
            data=optimized_tex.encode("utf-8"),
            file_name="optimized_resume.tex",
            mime="text/plain",
            use_container_width=True,
        )
        if pdf_bytes:
            st.download_button(
                "Download Optimized Resume (.pdf)",
                data=pdf_bytes,
                file_name="optimized_resume.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
            st.success("PDF compiled successfully.")
        else:
            st.warning("PDF could not be compiled automatically.")
            if pdf_error:
                with st.expander("Compilation log"):
                    st.text(pdf_error)
