from __future__ import annotations

import base64
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import streamlit as st
from openai import OpenAI

APP_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = APP_DIR / "prompts"
BASE_RESUME_PATH = APP_DIR / "base_resume.tex"
OUTPUTS_DIR = APP_DIR / "outputs"
OUTPUTS_DIR.mkdir(exist_ok=True)

DEFAULT_MODEL = "gpt-4.1"
MODEL_OPTIONS = [
    "gpt-4.1",
    "gpt-4.1-mini",
    "gpt-4o",
    "gpt-4o-mini",
]


st.set_page_config(
    page_title="Resume Optimizer Agent",
    page_icon="📄",
    layout="wide",
)


def inject_css() -> None:
    st.markdown(
        """
        <style>
          :root {
            --bg-soft: #f7f9fc;
            --card-bg: #ffffff;
            --text-main: #1f2937;
            --text-subtle: #6b7280;
            --line: #e5e7eb;
            --accent: #4f46e5;
            --accent-soft: #eef2ff;
          }

          .stApp {
            background: linear-gradient(180deg, #f8fafc 0%, #f6f8ff 40%, #f8fafc 100%);
          }

          .hero-wrap {
            background: linear-gradient(135deg, #111827 0%, #1f2a44 45%, #263b6d 100%);
            border-radius: 18px;
            padding: 1.6rem 1.8rem;
            color: white;
            box-shadow: 0 14px 32px rgba(17, 24, 39, 0.25);
            margin-bottom: 1rem;
          }

          .hero-title {
            margin: 0;
            font-size: 2rem;
            letter-spacing: -0.02em;
          }

          .hero-subtitle {
            margin-top: 0.35rem;
            color: #d1d5db;
            font-size: 1rem;
          }

          .badge-row {
            margin-top: 0.9rem;
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
          }

          .soft-badge {
            background: rgba(255, 255, 255, 0.14);
            border: 1px solid rgba(255, 255, 255, 0.16);
            border-radius: 999px;
            padding: 0.3rem 0.7rem;
            font-size: 0.82rem;
          }

          .card {
            background: var(--card-bg);
            border: 1px solid var(--line);
            border-radius: 16px;
            box-shadow: 0 8px 20px rgba(15, 23, 42, 0.06);
            padding: 1rem 1.1rem;
            margin-bottom: 0.8rem;
          }

          .section-title {
            font-size: 1rem;
            font-weight: 600;
            color: var(--text-main);
            margin-bottom: 0.55rem;
          }

          .chip {
            display: inline-block;
            margin: 0.2rem 0.25rem 0.2rem 0;
            padding: 0.22rem 0.55rem;
            border-radius: 999px;
            background: #f3f4f6;
            border: 1px solid #e5e7eb;
            color: #374151;
            font-size: 0.78rem;
          }

          .download-wrap {
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 14px;
            padding: 1rem;
            box-shadow: 0 8px 20px rgba(15, 23, 42, 0.06);
          }

          .muted {
            color: #6b7280;
            font-size: 0.9rem;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def strip_code_fences(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:latex|tex|markdown|md)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def split_output(output: str) -> tuple[str, str]:
    """Split model output into ATS report and LaTeX content with marker fallbacks."""
    cleaned = strip_code_fences(output)

    marker_patterns = [
        r"SECTION\s*2\s*(?:—|–|-|:)\s*UPDATED\s*LATEX\s*RESUME",
        r"SECTION\s*2\s*(?:—|–|-|:)",
        r"SECTION\s*2\b",
    ]

    for pattern in marker_patterns:
        parts = re.split(pattern, cleaned, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) == 2:
            report = parts[0].strip()
            tex = strip_code_fences(parts[1])
            return report, tex

    # fallback by locating LaTeX document start
    latex_start = re.search(r"\\documentclass|\\begin\{document\}", cleaned)
    if latex_start:
        idx = latex_start.start()
        return cleaned[:idx].strip(), cleaned[idx:].strip()

    return cleaned, ""


def parse_ats_report(report: str) -> dict[str, Any]:
    def extract_section(title: str) -> str:
        pattern = rf"{title}\s*[:\-]?\s*(.*?)(?=\n\s*[A-Z][A-Za-z\s]+:\s|\n\s*[A-Z][A-Za-z\s]+\n|$)"
        match = re.search(pattern, report, flags=re.IGNORECASE | re.DOTALL)
        return match.group(1).strip() if match else ""

    def parse_list_block(block: str) -> list[str]:
        items = []
        if not block:
            return items
        for line in block.splitlines():
            cleaned = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip()
            if cleaned:
                items.append(cleaned)
        if len(items) <= 1 and "," in block:
            items = [p.strip() for p in block.split(",") if p.strip()]
        return items

    score_match = re.search(r"ATS\s*Score\s*[:\-]?\s*(\d{1,3})\s*/?\s*100?", report, flags=re.IGNORECASE)
    ats_score = int(score_match.group(1)) if score_match else None

    top_tech = parse_list_block(extract_section(r"Top\s*10\s*Technical\s*Skills"))
    top_soft = parse_list_block(extract_section(r"Top\s*5\s*Soft\s*Skills"))
    responsibilities = parse_list_block(extract_section(r"Key\s*Responsibilities"))

    keywords_block = extract_section(r"ATS\s*Keywords")
    keywords = [k.strip() for k in re.split(r",|\n", keywords_block) if k.strip()]

    missing = parse_list_block(extract_section(r"Missing\s*Skills"))
    weak = parse_list_block(extract_section(r"Weakly\s*Represented\s*Skills|Weak\s*Skills"))
    strong = parse_list_block(extract_section(r"Strong\s*Matches|Strong\s*Skills"))

    summary_match = re.search(
        r"(?:Professional\s*Summary|Summary)\s*[:\-]?\s*(.*?)(?=\n\s*[A-Z][A-Za-z\s]+:\s|$)",
        report,
        flags=re.IGNORECASE | re.DOTALL,
    )
    optimized_summary = summary_match.group(1).strip() if summary_match else ""

    return {
        "ats_score": ats_score,
        "technical_skills": top_tech,
        "soft_skills": top_soft,
        "responsibilities": responsibilities,
        "keywords": keywords,
        "missing_skills": missing,
        "weak_skills": weak,
        "strong_skills": strong,
        "optimized_summary": optimized_summary,
    }


def infer_metrics(parsed: dict[str, Any], report: str) -> dict[str, int]:
    ats_score = parsed.get("ats_score")
    if ats_score is None:
        fallback = re.search(r"(\d{1,3})\s*/\s*100", report)
        ats_score = int(fallback.group(1)) if fallback else 70

    keywords = parsed.get("keywords", [])
    missing = parsed.get("missing_skills", [])
    weak = parsed.get("weak_skills", [])
    technical = parsed.get("technical_skills", [])
    soft = parsed.get("soft_skills", [])

    keyword_match = max(35, min(95, 100 - int(len(missing) * 2.5) - int(len(weak) * 1.5)))

    total_skills = max(1, len(technical) + len(soft))
    missing_impact = min(total_skills, len(missing) + max(0, len(weak) // 2))
    skills_match = int(max(30, min(98, ((total_skills - missing_impact) / total_skills) * 100)))

    if keywords:
        keyword_match = int(max(30, min(98, ((len(keywords) - min(len(keywords), len(missing))) / len(keywords)) * 100)))

    return {
        "ats_score": ats_score,
        "keyword_match": keyword_match,
        "skills_match": skills_match,
        "missing_skills_count": len(missing),
    }


def extract_latex_bullets(tex_content: str, limit: int = 12) -> list[str]:
    bullets = re.findall(r"\\item\s*\{([^}]*)\}", tex_content, flags=re.DOTALL)
    cleaned: list[str] = []
    for b in bullets:
        line = re.sub(r"\\textbf\{([^}]*)\}", r"\1", b)
        line = re.sub(r"\\[a-zA-Z]+", "", line)
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            cleaned.append(line)
        if len(cleaned) >= limit:
            break
    return cleaned


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
                tex_path.name,
            ]

            first = subprocess.run(
                command,
                cwd=tmp,
                capture_output=True,
                text=True,
                timeout=90,
            )
            if first.returncode != 0:
                return None, first.stdout + "\n" + first.stderr

            second = subprocess.run(
                command,
                cwd=tmp,
                capture_output=True,
                text=True,
                timeout=90,
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
    except Exception as exc:  # pragma: no cover - defensive
        return None, str(exc)


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


def render_hero() -> None:
    st.markdown(
        """
        <div class="hero-wrap">
          <h1 class="hero-title">Resume Optimizer Agent</h1>
          <p class="hero-subtitle">AI-powered ATS optimization for recruiter-ready resumes.</p>
          <div class="badge-row">
            <span class="soft-badge">ATS Score</span>
            <span class="soft-badge">Skill Gap Analysis</span>
            <span class="soft-badge">PDF Export</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("How it works"):
        st.markdown(
            """
            1. Paste your target job description.
            2. Upload a `.tex` resume (or use the bundled base resume).
            3. The model produces an ATS report + optimized LaTeX.
            4. The app compiles a PDF (if `pdflatex` is available) and enables downloads.
            """
        )


def render_metrics(metrics: dict[str, int]) -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("ATS Score", f"{metrics['ats_score']}/100")
    c2.metric("Keyword Match %", f"{metrics['keyword_match']}%", help="Estimated from parsed ATS report")
    c3.metric("Skills Match %", f"{metrics['skills_match']}%", help="Estimated from parsed skills coverage")
    c4.metric("Missing Skills Count", str(metrics["missing_skills_count"]))


def _render_chip_group(items: list[str], empty_text: str = "Not detected") -> None:
    if not items:
        st.caption(empty_text)
        return
    html = "".join(f'<span class="chip">{item.replace("<", "&lt;").replace(">", "&gt;")}</span>' for item in items)
    st.markdown(html, unsafe_allow_html=True)


def render_jd_analysis(parsed: dict[str, Any]) -> None:
    left, right = st.columns(2)
    with left:
        st.markdown('<div class="card"><div class="section-title">Top Technical Skills</div>', unsafe_allow_html=True)
        _render_chip_group(parsed.get("technical_skills", []))
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="card"><div class="section-title">Key Responsibilities</div>', unsafe_allow_html=True)
        responsibilities = parsed.get("responsibilities", [])
        if responsibilities:
            for item in responsibilities:
                st.markdown(f"- {item}")
        else:
            st.caption("Not detected")
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="card"><div class="section-title">Top Soft Skills</div>', unsafe_allow_html=True)
        _render_chip_group(parsed.get("soft_skills", []))
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="card"><div class="section-title">ATS Keywords</div>', unsafe_allow_html=True)
        _render_chip_group(parsed.get("keywords", []), empty_text="No keywords parsed")
        st.markdown("</div>", unsafe_allow_html=True)


def render_skill_gap(parsed: dict[str, Any]) -> None:
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="card"><div class="section-title">Missing Skills</div>', unsafe_allow_html=True)
        missing = parsed.get("missing_skills", [])
        if missing:
            for item in missing:
                st.markdown(f"- {item}")
        else:
            st.caption("No explicit missing skills found")
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="card"><div class="section-title">Weakly Represented</div>', unsafe_allow_html=True)
        weak = parsed.get("weak_skills", [])
        if weak:
            for item in weak:
                st.markdown(f"- {item}")
        else:
            st.caption("No weak skills section detected")
        st.markdown("</div>", unsafe_allow_html=True)

    with c3:
        st.markdown('<div class="card"><div class="section-title">Strong Matches</div>', unsafe_allow_html=True)
        strong = parsed.get("strong_skills", [])
        if strong:
            for item in strong:
                st.markdown(f"- {item}")
        else:
            st.caption("No explicit strong matches in report")
        st.markdown("</div>", unsafe_allow_html=True)


def render_bullet_improvements(original_tex: str, optimized_tex: str) -> None:
    orig = extract_latex_bullets(original_tex)
    rewritten = extract_latex_bullets(optimized_tex)

    st.markdown("<div class='muted'>Best-effort extraction from LaTeX bullet lists.</div>", unsafe_allow_html=True)
    left, right = st.columns(2)

    with left:
        st.markdown("#### Original bullets")
        if orig:
            for item in orig:
                st.code(f"• {item}", language="text")
        else:
            st.caption("Could not extract original bullets")

    with right:
        st.markdown("#### Rewritten bullets")
        if rewritten:
            for item in rewritten:
                st.code(f"• {item}", language="text")
        else:
            st.caption("Could not extract rewritten bullets")


def render_resume_tab(parsed: dict[str, Any], optimized_tex: str, pdf_bytes: bytes | None) -> None:
    summary = parsed.get("optimized_summary", "").strip()
    st.markdown("#### Optimized Professional Summary")
    if summary:
        st.info(summary)
    else:
        st.caption("No explicit summary section was detected in the ATS report.")

    st.markdown("#### Optimized LaTeX Resume")
    st.code(optimized_tex, language="latex")

    st.markdown("#### PDF Preview")
    if pdf_bytes:
        b64 = base64.b64encode(pdf_bytes).decode("utf-8")
        iframe = f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="700" type="application/pdf"></iframe>'
        st.markdown(iframe, unsafe_allow_html=True)
    else:
        st.caption("PDF preview unavailable because compilation did not succeed.")


def render_downloads(report: str, optimized_tex: str, pdf_bytes: bytes | None) -> None:
    st.markdown("<div class='download-wrap'>", unsafe_allow_html=True)
    st.markdown("### Downloads")
    d1, d2, d3 = st.columns(3)
    with d1:
        st.download_button(
            "Download ATS Report (.md)",
            data=report.encode("utf-8"),
            file_name="ats_report.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with d2:
        st.download_button(
            "Download Optimized Resume (.tex)",
            data=optimized_tex.encode("utf-8"),
            file_name="optimized_resume.tex",
            mime="text/plain",
            use_container_width=True,
        )
    with d3:
        if pdf_bytes:
            st.download_button(
                "Download Optimized Resume (.pdf)",
                data=pdf_bytes,
                file_name="optimized_resume.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.button("PDF unavailable", disabled=True, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)


def init_state() -> None:
    defaults = {
        "raw_output": "",
        "report": "",
        "optimized_tex": "",
        "pdf_bytes": None,
        "pdf_error": "",
        "parsed": {},
        "metrics": {},
        "last_resume_source": "",
        "original_resume_tex": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def main() -> None:
    inject_css()
    init_state()
    render_hero()

    st.markdown("### Input")
    left, right = st.columns([1.45, 1], gap="large")

    with left:
        jd = st.text_area(
            "Job Description",
            height=430,
            placeholder="Paste the full job description here...",
        )

    with right:
        api_key = st.text_input("OpenAI API Key", type="password", value=os.getenv("OPENAI_API_KEY", ""))
        model = st.selectbox(
            "Model",
            options=MODEL_OPTIONS,
            index=MODEL_OPTIONS.index(DEFAULT_MODEL) if DEFAULT_MODEL in MODEL_OPTIONS else 0,
            help="Choose the model used for optimization.",
        )
        uploaded_tex = st.file_uploader(
            "Optional Resume .tex File",
            type=["tex"],
            accept_multiple_files=False,
        )
        use_base_if_missing = st.checkbox(
            "Use bundled base resume if no file uploaded",
            value=True,
        )

        if uploaded_tex is not None:
            resume_tex = uploaded_tex.getvalue().decode("utf-8", errors="ignore")
            resume_source = "Uploaded .tex"
            st.success("Using uploaded resume source")
        elif use_base_if_missing:
            resume_tex = BASE_RESUME_PATH.read_text(encoding="utf-8")
            resume_source = "Bundled base_resume.tex"
            st.info("Using bundled base resume")
        else:
            resume_tex = ""
            resume_source = "No resume source selected"
            st.warning("Upload a .tex file or enable bundled base resume")

        with st.expander("Preview current resume source", expanded=False):
            if resume_tex:
                st.code(resume_tex[:7000], language="latex")
            else:
                st.caption("No resume content loaded")

    generate = st.button("Generate ATS Report + Optimized Resume", type="primary", use_container_width=True)

    if generate:
        if not api_key.strip():
            st.warning("Please provide an OpenAI API key to continue.")
            st.stop()
        if not jd.strip():
            st.warning("Please paste a job description.")
            st.stop()
        if not resume_tex.strip():
            st.warning("Please upload a .tex resume or enable bundled base resume.")
            st.stop()

        with st.spinner("Running resume optimizer and compiling PDF..."):
            try:
                raw_output, report, optimized_tex = run_agent(api_key, model, jd, resume_tex)
            except Exception as exc:
                st.exception(exc)
                st.stop()

            if not optimized_tex.strip():
                st.error("Model response did not include a detectable LaTeX section.")
                with st.expander("Raw model output (debug)"):
                    st.code(raw_output)
                st.stop()

            parsed = parse_ats_report(report)
            metrics = infer_metrics(parsed, report)

            pdf_bytes, pdf_error = compile_pdf(optimized_tex)

            report_path = OUTPUTS_DIR / "ats_report.md"
            tex_path = OUTPUTS_DIR / "optimized_resume.tex"
            report_path.write_text(report, encoding="utf-8")
            tex_path.write_text(optimized_tex, encoding="utf-8")

            if pdf_bytes:
                (OUTPUTS_DIR / "optimized_resume.pdf").write_bytes(pdf_bytes)

            st.session_state.raw_output = raw_output
            st.session_state.report = report
            st.session_state.optimized_tex = optimized_tex
            st.session_state.pdf_bytes = pdf_bytes
            st.session_state.pdf_error = pdf_error or ""
            st.session_state.parsed = parsed
            st.session_state.metrics = metrics
            st.session_state.last_resume_source = resume_source
            st.session_state.original_resume_tex = resume_tex

        st.success("Optimization complete. Review insights and downloads below.")

    if st.session_state.optimized_tex:
        st.markdown("### Results")
        render_metrics(st.session_state.metrics)

        tabs = st.tabs(
            [
                "JD Analysis",
                "Skill Gap",
                "Bullet Improvements",
                "Optimized Resume",
                "ATS Report",
                "Downloads",
            ]
        )

        with tabs[0]:
            render_jd_analysis(st.session_state.parsed)

        with tabs[1]:
            render_skill_gap(st.session_state.parsed)

        with tabs[2]:
            render_bullet_improvements(
                st.session_state.original_resume_tex,
                st.session_state.optimized_tex,
            )

        with tabs[3]:
            render_resume_tab(st.session_state.parsed, st.session_state.optimized_tex, st.session_state.pdf_bytes)
            if st.session_state.pdf_error:
                st.warning("PDF could not be compiled automatically.")
                with st.expander("Compilation log"):
                    st.text(st.session_state.pdf_error)

        with tabs[4]:
            st.markdown(st.session_state.report)
            with st.expander("Raw model output (debug)"):
                st.code(st.session_state.raw_output)

        with tabs[5]:
            render_downloads(st.session_state.report, st.session_state.optimized_tex, st.session_state.pdf_bytes)


if __name__ == "__main__":
    main()
