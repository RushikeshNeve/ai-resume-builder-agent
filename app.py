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
OUTPUT_PDF_PATH = OUTPUTS_DIR / "optimized_resume.pdf"

DEFAULT_MODEL = "gpt-4.1"
MODEL_OPTIONS = ["gpt-4.1", "gpt-4.1-mini", "gpt-4o", "gpt-4o-mini"]

st.set_page_config(
    page_title="Resume Optimizer Agent",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_css() -> None:
    st.markdown(
        """
        <style>
          :root {
            --bg-main: #06090f;
            --bg-elev: #0b1220;
            --bg-card: rgba(14, 22, 37, 0.82);
            --bg-card-2: rgba(18, 28, 48, 0.88);
            --text-main: #ecf2ff;
            --text-subtle: #9eb0cb;
            --line: rgba(168, 189, 255, 0.2);
            --line-strong: rgba(168, 189, 255, 0.32);
            --accent: #7c8cff;
            --accent-2: #56d7ff;
            --danger: #ff6f7d;
            --warning: #ffc96e;
            --success: #50d890;
            --shadow: 0 18px 38px rgba(0, 0, 0, 0.36);
          }

          .stApp {
            background:
              radial-gradient(circle at 10% 5%, rgba(60, 91, 198, 0.25), transparent 35%),
              radial-gradient(circle at 90% 1%, rgba(64, 160, 255, 0.18), transparent 36%),
              linear-gradient(180deg, #05070d 0%, #090f1a 48%, #05070d 100%);
            color: var(--text-main);
          }

          .block-container {
            max-width: 1400px;
            padding-top: 1.5rem;
            padding-bottom: 2.5rem;
          }

          [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #070d18 0%, #0b1425 100%);
            border-right: 1px solid rgba(142, 169, 235, 0.2);
          }

          [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
          [data-testid="stSidebar"] label,
          [data-testid="stSidebar"] .st-bq {
            color: #dbe6ff;
          }

          .hero-banner {
            position: relative;
            overflow: hidden;
            padding: 2rem 2.2rem;
            margin-bottom: 1rem;
            border: 1px solid var(--line-strong);
            border-radius: 22px;
            background:
              radial-gradient(circle at 80% 20%, rgba(92, 144, 255, 0.33), transparent 38%),
              linear-gradient(135deg, rgba(31, 47, 83, 0.95) 0%, rgba(34, 62, 129, 0.92) 48%, rgba(18, 143, 178, 0.88) 100%);
            box-shadow: var(--shadow);
          }

          .hero-banner::after {
            content: "";
            position: absolute;
            right: -80px;
            top: -80px;
            width: 220px;
            height: 220px;
            background: radial-gradient(circle, rgba(255, 255, 255, 0.16), transparent 68%);
            pointer-events: none;
          }

          .hero-title {
            margin: 0;
            font-size: 2.1rem;
            line-height: 1.2;
            letter-spacing: -0.02em;
            color: #f4f8ff;
          }

          .app-subtitle {
            margin-top: 0.45rem;
            margin-bottom: 0;
            color: #d8e4ff;
            font-size: 1.02rem;
          }

          .badge-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            margin-top: 1rem;
          }

          .feature-badge {
            border-radius: 999px;
            padding: 0.32rem 0.8rem;
            background: rgba(255, 255, 255, 0.12);
            border: 1px solid rgba(255, 255, 255, 0.25);
            color: #f4f9ff;
            font-size: 0.8rem;
            backdrop-filter: blur(5px);
          }

          .glass-card,
          .section-card,
          .status-card,
          .download-card,
          .summary-card,
          .code-card,
          .metric-card {
            border-radius: 18px;
            border: 1px solid var(--line);
            box-shadow: var(--shadow);
            backdrop-filter: blur(6px);
          }

          .glass-card,
          .section-card,
          .status-card,
          .summary-card,
          .code-card,
          .download-card {
            background: linear-gradient(160deg, var(--bg-card) 0%, var(--bg-card-2) 100%);
            padding: 1rem 1.1rem;
            margin-bottom: 0.95rem;
          }

          .card-title {
            margin: 0 0 0.55rem 0;
            color: #f2f7ff;
            font-size: 1rem;
            letter-spacing: 0.01em;
          }

          .card-subtitle {
            color: var(--text-subtle);
            margin: 0;
            font-size: 0.87rem;
          }

          .metric-card {
            min-height: 118px;
            padding: 0.9rem 1rem;
            background: linear-gradient(165deg, rgba(19, 32, 58, 0.95), rgba(29, 49, 88, 0.88));
            transition: transform .15s ease, border-color .15s ease;
          }

          .metric-card:hover {
            transform: translateY(-2px);
            border-color: rgba(140, 190, 255, 0.45);
          }

          .metric-value {
            margin-top: 0.25rem;
            font-size: 1.85rem;
            font-weight: 700;
            color: #ffffff;
          }

          .metric-label {
            margin: 0;
            color: #cfddff;
            font-size: 0.83rem;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.06em;
          }

          .metric-helper {
            margin-top: 0.28rem;
            color: #9db3d9;
            font-size: 0.75rem;
          }

          .chip {
            display: inline-block;
            border: 1px solid rgba(156, 186, 245, 0.42);
            color: #e8f1ff;
            background: rgba(71, 97, 152, 0.35);
            margin: 0.2rem 0.28rem 0.2rem 0;
            border-radius: 999px;
            padding: 0.26rem 0.65rem;
            font-size: 0.78rem;
          }

          .chip-danger { background: rgba(221, 94, 113, 0.2); border-color: rgba(255, 128, 148, 0.55); }
          .chip-warning { background: rgba(244, 177, 70, 0.17); border-color: rgba(255, 206, 126, 0.5); }
          .chip-success { background: rgba(65, 175, 109, 0.2); border-color: rgba(109, 232, 159, 0.54); }

          .bullet-block {
            border: 1px solid rgba(159, 186, 244, 0.28);
            border-left: 3px solid rgba(124, 177, 255, 0.75);
            border-radius: 12px;
            background: rgba(17, 28, 48, 0.72);
            padding: 0.65rem 0.75rem;
            margin-bottom: 0.55rem;
            color: #ecf3ff;
            font-size: 0.88rem;
          }

          .download-card {
            min-height: 175px;
          }

          .status-card.success { border-color: rgba(80, 216, 144, 0.55); }
          .status-card.error { border-color: rgba(255, 111, 125, 0.58); }
          .status-card.warning { border-color: rgba(255, 196, 111, 0.58); }

          .pdf-frame {
            border-radius: 14px;
            border: 1px solid rgba(157, 186, 244, 0.28);
            overflow: hidden;
            box-shadow: inset 0 0 0 1px rgba(157, 186, 244, 0.1);
          }

          .muted { color: var(--text-subtle); }

          [data-testid="stTabs"] [data-baseweb="tab-list"] {
            gap: 0.25rem;
            background: rgba(9, 15, 26, 0.72);
            padding: 0.3rem;
            border: 1px solid rgba(159, 186, 244, 0.22);
            border-radius: 12px;
          }

          [data-testid="stTabs"] [data-baseweb="tab"] {
            color: #c3d5fa;
            border-radius: 9px;
            background: transparent;
            padding-top: 0.45rem;
            padding-bottom: 0.45rem;
            border: 1px solid transparent;
          }

          [data-testid="stTabs"] [aria-selected="true"] {
            background: rgba(54, 82, 140, 0.58) !important;
            color: #f2f7ff !important;
            border-color: rgba(159, 186, 244, 0.35) !important;
          }

          .stDownloadButton > button,
          .stButton > button {
            border-radius: 10px;
            border: 1px solid rgba(140, 172, 243, 0.42);
            background: linear-gradient(180deg, rgba(58, 87, 146, 0.95), rgba(40, 68, 121, 0.96));
            color: #f0f6ff;
            font-weight: 600;
            transition: transform .14s ease, box-shadow .14s ease;
          }

          .stDownloadButton > button:hover,
          .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 10px 20px rgba(28, 49, 90, 0.4);
          }

          .stTextArea textarea,
          .stTextInput input,
          .stSelectbox [data-baseweb="select"] > div,
          .stFileUploader > div {
            background: rgba(7, 13, 24, 0.75) !important;
            color: #e4efff !important;
            border-radius: 10px !important;
            border-color: rgba(130, 161, 226, 0.35) !important;
          }

          .stExpander {
            border: 1px solid rgba(156, 186, 245, 0.24) !important;
            background: rgba(10, 17, 30, 0.65) !important;
            border-radius: 12px !important;
          }

          code {
            color: #eaf2ff !important;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def normalize_text(text: str) -> str:
    return text.replace("—", "-").replace("–", "-")


def strip_code_fences(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:latex|tex|markdown|md)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def split_output(output: str) -> tuple[str, str]:
    cleaned = output.strip()
    normalized = normalize_text(cleaned)

    marker_patterns = [
        r"section\s*2\s*[:\-]\s*updated\s*latex\s*resume",
        r"section\s*2\s*[:\-]\s*(?:latex|resume)",
        r"section\s*2\b",
    ]

    for pattern in marker_patterns:
        match = re.search(pattern, normalized, flags=re.IGNORECASE)
        if match:
            report = strip_code_fences(cleaned[: match.start()])
            tex_part = strip_code_fences(cleaned[match.end() :])
            tex_part = re.sub(r"^[:\-\n\s]+", "", tex_part)
            return report, tex_part

    latex_fence = re.search(r"```(?:latex|tex)?\s*(.*?)```", cleaned, flags=re.IGNORECASE | re.DOTALL)
    if latex_fence:
        tex = strip_code_fences(latex_fence.group(0))
        report = cleaned.replace(latex_fence.group(0), "").strip()
        return report, tex

    latex_start = re.search(r"\\documentclass|\\begin\{document\}", cleaned)
    if latex_start:
        idx = latex_start.start()
        return cleaned[:idx].strip(), cleaned[idx:].strip()

    return strip_code_fences(cleaned), ""


def parse_marked_list(section_text: str) -> list[str]:
    if not section_text:
        return []

    lines = [line.strip() for line in section_text.splitlines() if line.strip()]
    parsed: list[str] = []
    for line in lines:
        cleaned = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip()
        if cleaned:
            parsed.append(cleaned)

    if not parsed and "," in section_text:
        parsed = [item.strip() for item in section_text.split(",") if item.strip()]

    return parsed


def extract_section(report: str, aliases: list[str]) -> str:
    heading_pattern = "|".join(rf"{a}" for a in aliases)
    boundary = r"(?=\n\s*(?:[A-Z][A-Za-z0-9\s/&()+-]{2,45}[:\-]|SECTION\s*\d)|\Z)"

    patterns = [
        rf"(?:^|\n)\s*(?:{heading_pattern})\s*[:\-]\s*(.*?){boundary}",
        rf"(?:^|\n)\s*(?:{heading_pattern})\s*\n(.*?){boundary}",
    ]

    for pattern in patterns:
        match = re.search(pattern, report, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()

    return ""


def parse_summary(report: str) -> str:
    summary = extract_section(report, [r"Professional\s*Summary", r"Summary", r"Rewritten\s*Summary"])
    if summary:
        return summary

    summary_match = re.search(
        r"(?:professional\s*summary|summary)\s*[:\-]\s*(.+)",
        report,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return summary_match.group(1).strip() if summary_match else ""


def parse_bullets(report: str) -> list[str]:
    bullet_section = extract_section(
        report,
        [
            r"Optimized\s*Bullet\s*Points",
            r"Optimized\s*Bullets",
            r"Bullet\s*Improvements",
            r"Rewritten\s*Bullet\s*Points",
        ],
    )
    return parse_marked_list(bullet_section)


def parse_ats_report(report: str) -> dict[str, Any]:
    score_match = re.search(r"ATS\s*Score\s*[:\-]?\s*(\d{1,3})\s*(?:/\s*100)?", report, flags=re.IGNORECASE)
    keyword_match = re.search(r"keyword\s*match\s*[:\-]?\s*(\d{1,3})\s*%", report, flags=re.IGNORECASE)
    skill_match = re.search(r"skills?\s*match\s*[:\-]?\s*(\d{1,3})\s*%", report, flags=re.IGNORECASE)
    missing_count = re.search(r"missing\s*skills\s*(?:count|total)?\s*[:\-]?\s*(\d{1,3})", report, flags=re.IGNORECASE)

    technical = parse_marked_list(
        extract_section(report, [r"Top\s*10\s*Technical\s*Skills", r"Technical\s*Skills", r"Core\s*Technical\s*Skills"])
    )
    soft = parse_marked_list(extract_section(report, [r"Top\s*5\s*Soft\s*Skills", r"Soft\s*Skills", r"Behavioral\s*Skills"]))
    responsibilities = parse_marked_list(extract_section(report, [r"Key\s*Responsibilities", r"Responsibilities"]))

    keywords_block = extract_section(report, [r"ATS\s*Keywords", r"Keywords", r"Keyword\s*Targets"])
    keywords = parse_marked_list(keywords_block)
    if not keywords and keywords_block:
        keywords = [item.strip() for item in re.split(r",|\|", keywords_block) if item.strip()]

    missing = parse_marked_list(extract_section(report, [r"Missing\s*Skills", r"Skill\s*Gaps"]))
    weak = parse_marked_list(extract_section(report, [r"Weakly\s*Represented\s*Skills", r"Weak\s*Skills"]))
    strong = parse_marked_list(extract_section(report, [r"Strong\s*Matches", r"Strong\s*Skills", r"Well\s*Represented\s*Skills"]))

    optimized_summary = parse_summary(report)
    optimized_bullets = parse_bullets(report)

    return {
        "ats_score": int(score_match.group(1)) if score_match else None,
        "keyword_match": int(keyword_match.group(1)) if keyword_match else None,
        "skills_match": int(skill_match.group(1)) if skill_match else None,
        "missing_skills_count": int(missing_count.group(1)) if missing_count else None,
        "technical_skills": technical,
        "soft_skills": soft,
        "responsibilities": responsibilities,
        "keywords": keywords,
        "missing_skills": missing,
        "weak_skills": weak,
        "strong_skills": strong,
        "optimized_summary": optimized_summary,
        "optimized_bullets": optimized_bullets,
    }


def infer_metrics(parsed: dict[str, Any], report: str) -> dict[str, Any]:
    estimates: dict[str, bool] = {}

    ats_score = parsed.get("ats_score")
    if ats_score is None:
        fallback = re.search(r"(\d{1,3})\s*/\s*100", report)
        ats_score = int(fallback.group(1)) if fallback else 70
        estimates["ats_score"] = True
    else:
        estimates["ats_score"] = False

    keyword_match = parsed.get("keyword_match")
    if keyword_match is None:
        missing = parsed.get("missing_skills", [])
        keywords = parsed.get("keywords", [])
        if keywords:
            keyword_match = int(max(35, min(98, ((len(keywords) - min(len(keywords), len(missing))) / len(keywords)) * 100)))
        else:
            keyword_match = max(35, min(95, 100 - int(len(missing) * 2.5)))
        estimates["keyword_match"] = True
    else:
        estimates["keyword_match"] = False

    skills_match = parsed.get("skills_match")
    if skills_match is None:
        total_skills = max(1, len(parsed.get("technical_skills", [])) + len(parsed.get("soft_skills", [])))
        weak = parsed.get("weak_skills", [])
        missing = parsed.get("missing_skills", [])
        impact = min(total_skills, len(missing) + max(0, len(weak) // 2))
        skills_match = int(max(30, min(98, ((total_skills - impact) / total_skills) * 100)))
        estimates["skills_match"] = True
    else:
        estimates["skills_match"] = False

    missing_count = parsed.get("missing_skills_count")
    if missing_count is None:
        missing_count = len(parsed.get("missing_skills", []))
        estimates["missing_skills_count"] = True
    else:
        estimates["missing_skills_count"] = False

    return {
        "ats_score": ats_score,
        "keyword_match": keyword_match,
        "skills_match": skills_match,
        "missing_skills_count": missing_count,
        "estimate_flags": estimates,
    }


def extract_latex_bullets(tex_content: str, limit: int = 14) -> list[str]:
    bullets = re.findall(r"\\item\s*(?:\{)?(.+?)(?:\})?(?=\n|$)", tex_content, flags=re.DOTALL)
    cleaned: list[str] = []
    for bullet in bullets:
        line = re.sub(r"\\textbf\{([^}]*)\}", r"\1", bullet)
        line = re.sub(r"\\[a-zA-Z]+(?:\[[^\]]*\])?(?:\{[^}]*\})?", "", line)
        line = re.sub(r"\s+", " ", line).strip(" {}")
        if line:
            cleaned.append(line)
        if len(cleaned) >= limit:
            break
    return cleaned


def compile_pdf(tex_content: str) -> tuple[bytes | None, str | None]:
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            tex_path = tmp_path / "optimized_resume.tex"
            tex_path.write_text(tex_content, encoding="utf-8")

            command = ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex_path.name]

            logs: list[str] = []
            for run_number in (1, 2):
                result = subprocess.run(
                    command,
                    cwd=tmp_path,
                    capture_output=True,
                    text=True,
                    timeout=90,
                )
                logs.append(f"--- pdflatex run {run_number} ---\n{result.stdout}\n{result.stderr}")
                if result.returncode != 0:
                    return None, "\n".join(logs)

            pdf_path = tmp_path / "optimized_resume.pdf"
            if pdf_path.exists():
                return pdf_path.read_bytes(), None
            return None, "PDF compilation reported success but no PDF file was produced."
    except FileNotFoundError:
        return None, "pdflatex is not installed in this environment."
    except subprocess.TimeoutExpired:
        return None, "pdflatex timed out while compiling the LaTeX resume."
    except Exception as exc:  # pragma: no cover
        return None, str(exc)


def load_cached_pdf() -> bytes | None:
    if OUTPUT_PDF_PATH.exists():
        try:
            return OUTPUT_PDF_PATH.read_bytes()
        except Exception:
            return None
    return None


def run_agent(api_key: str, model: str, jd: str, resume_tex: str) -> tuple[str, str, str]:
    client = OpenAI(api_key=api_key)
    system_prompt = load_prompt("system_prompt.txt")
    user_prompt = load_prompt("user_prompt.txt").format(job_description=jd.strip(), resume_tex=resume_tex.strip())

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
        <div class="hero-banner">
          <h1 class="hero-title">Resume Optimizer Agent</h1>
          <p class="app-subtitle">Recruiter-grade resume intelligence for ATS performance, skill alignment, and production-ready LaTeX/PDF outputs.</p>
          <div class="badge-row">
            <span class="feature-badge">ATS Score</span>
            <span class="feature-badge">Skill Gap Analysis</span>
            <span class="feature-badge">LaTeX Resume</span>
            <span class="feature-badge">PDF Export</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("How it works", expanded=False):
        st.markdown(
            """
            1. Paste a target Job Description.
            2. Upload a `.tex` resume or use the bundled `base_resume.tex`.
            3. Generate ATS analysis, rewritten summary, and optimized resume bullets.
            4. Export ATS report, optimized `.tex`, and compiled `.pdf` (when `pdflatex` is available).
            """
        )


def render_sidebar() -> tuple[str, str, bytes | None, bool, bool, str]:
    with st.sidebar:
        st.markdown("### ⚙️ Workspace Controls")
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        api_key = st.text_input("OpenAI API Key", type="password", value=os.getenv("OPENAI_API_KEY", ""))
        model = st.selectbox(
            "Model",
            options=MODEL_OPTIONS,
            index=MODEL_OPTIONS.index(DEFAULT_MODEL) if DEFAULT_MODEL in MODEL_OPTIONS else 0,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("### 📄 Resume Source")
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        uploaded_tex = st.file_uploader("Optional resume (.tex)", type=["tex"], accept_multiple_files=False)
        use_base_if_missing = st.checkbox("Use bundled base resume when upload is missing", value=True)
        show_resume_preview = st.checkbox("Show resume preview", value=False)
        st.markdown("</div>", unsafe_allow_html=True)

        if uploaded_tex is not None:
            resume_tex = uploaded_tex.getvalue().decode("utf-8", errors="ignore")
            resume_source = "Uploaded .tex file"
            resume_icon = "✅"
        elif use_base_if_missing:
            resume_tex = BASE_RESUME_PATH.read_text(encoding="utf-8")
            resume_source = "Bundled base_resume.tex"
            resume_icon = "🧩"
        else:
            resume_tex = ""
            resume_source = "No resume loaded"
            resume_icon = "⚠️"

        readiness = "Ready" if api_key.strip() and resume_tex.strip() else "Missing required input"
        st.markdown(
            f"""
            <div class="status-card">
              <p class="card-title">Status</p>
              <p class="card-subtitle"><strong>Resume source:</strong> {resume_icon} {resume_source}</p>
              <p class="card-subtitle"><strong>Model:</strong> {model}</p>
              <p class="card-subtitle"><strong>Readiness:</strong> {readiness}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return api_key, model, uploaded_tex, use_base_if_missing, show_resume_preview, resume_source


def render_input_section(job_description: str, resume_source: str, resume_tex: str) -> str:
    st.markdown("## Input Workspace")
    left, right = st.columns([1.65, 1], gap="large")

    with left:
        st.markdown(
            """
            <div class="section-card">
              <p class="card-title">Job Description (Required)</p>
              <p class="card-subtitle">Paste the full role description for best keyword extraction and ATS scoring precision.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        jd_value = st.text_area(
            "JD",
            value=job_description,
            label_visibility="collapsed",
            height=360,
            placeholder="Paste job description, requirements, tools, skills, and responsibilities...",
        )

    with right:
        st.markdown(
            f"""
            <div class="section-card">
              <p class="card-title">Resume Source Summary</p>
              <p class="card-subtitle">Current source: <strong>{resume_source}</strong></p>
              <p class="card-subtitle">Required fields: API key + Job Description + resume source.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if resume_tex.strip():
            st.success("Resume source is loaded and ready.")
        else:
            st.warning("No resume source loaded. Upload `.tex` or enable bundled fallback.")

    return jd_value


def render_metric_cards(metrics: dict[str, Any]) -> None:
    labels = [
        ("ATS Score", f"{metrics['ats_score']}/100", "Model + parser score"),
        ("Keyword Match %", f"{metrics['keyword_match']}%", "Coverage of extracted ATS keywords"),
        ("Skills Match %", f"{metrics['skills_match']}%", "Alignment across technical + soft skills"),
        ("Missing Skills", str(metrics["missing_skills_count"]), "Unrepresented critical requirements"),
    ]

    columns = st.columns(4)
    for idx, (label, value, helper) in enumerate(labels):
        estimate = metrics.get("estimate_flags", {}).get(
            ["ats_score", "keyword_match", "skills_match", "missing_skills_count"][idx],
            False,
        )
        helper_line = f"{helper}{' • estimate' if estimate else ''}"
        columns[idx].markdown(
            f"""
            <div class="metric-card">
              <p class="metric-label">{label}</p>
              <div class="metric-value">{value}</div>
              <div class="metric-helper">{helper_line}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_chip_group(items: list[str], variant: str = "") -> None:
    if not items:
        st.caption("No items detected")
        return
    klass = "chip"
    if variant:
        klass += f" {variant}"
    html = "".join(f'<span class="{klass}">{item.replace("<", "&lt;").replace(">", "&gt;")}</span>' for item in items)
    st.markdown(html, unsafe_allow_html=True)


def render_jd_breakdown(parsed: dict[str, Any]) -> None:
    c1, c2 = st.columns(2, gap="large")

    with c1:
        st.markdown('<div class="section-card"><p class="card-title">Technical Skills</p>', unsafe_allow_html=True)
        render_chip_group(parsed.get("technical_skills", []))
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section-card"><p class="card-title">Responsibilities</p>', unsafe_allow_html=True)
        responsibilities = parsed.get("responsibilities", [])
        if responsibilities:
            for item in responsibilities:
                st.markdown(f"- {item}")
        else:
            st.caption("No responsibilities parsed")
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="section-card"><p class="card-title">Soft Skills</p>', unsafe_allow_html=True)
        render_chip_group(parsed.get("soft_skills", []))
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="section-card"><p class="card-title">ATS Keywords</p>', unsafe_allow_html=True)
        render_chip_group(parsed.get("keywords", []))
        st.markdown("</div>", unsafe_allow_html=True)


def render_skill_gap(parsed: dict[str, Any]) -> None:
    c1, c2, c3 = st.columns(3, gap="medium")

    with c1:
        st.markdown('<div class="section-card"><p class="card-title">Missing Skills</p>', unsafe_allow_html=True)
        render_chip_group(parsed.get("missing_skills", []), "chip-danger")
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="section-card"><p class="card-title">Weakly Represented</p>', unsafe_allow_html=True)
        render_chip_group(parsed.get("weak_skills", []), "chip-warning")
        st.markdown("</div>", unsafe_allow_html=True)

    with c3:
        st.markdown('<div class="section-card"><p class="card-title">Strong Matches</p>', unsafe_allow_html=True)
        render_chip_group(parsed.get("strong_skills", []), "chip-success")
        st.markdown("</div>", unsafe_allow_html=True)


def render_bullet_tab(original_tex: str, optimized_tex: str, parsed: dict[str, Any]) -> None:
    source_bullets = extract_latex_bullets(original_tex)
    optimized_from_tex = extract_latex_bullets(optimized_tex)
    optimized_from_report = parsed.get("optimized_bullets", [])
    optimized = optimized_from_tex or optimized_from_report

    st.markdown('<div class="section-card"><p class="card-title">Bullet Optimization Comparison</p><p class="card-subtitle">Copy-friendly, recruiter-focused bullet rewrite output.</p></div>', unsafe_allow_html=True)

    if source_bullets and optimized:
        left, right = st.columns(2, gap="large")
        with left:
            st.markdown("#### Original bullets")
            for bullet in source_bullets:
                st.markdown(f'<div class="bullet-block">• {bullet}</div>', unsafe_allow_html=True)
        with right:
            st.markdown("#### Optimized bullets")
            for bullet in optimized:
                st.markdown(f'<div class="bullet-block">• {bullet}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="summary-card"><p class="card-title">Optimized Highlights</p>', unsafe_allow_html=True)
        if optimized:
            for bullet in optimized:
                st.markdown(f'<div class="bullet-block">• {bullet}</div>', unsafe_allow_html=True)
        else:
            st.caption("Unable to reliably extract bullet groups from model output.")
        st.markdown("</div>", unsafe_allow_html=True)


def render_resume_tab(parsed: dict[str, Any], optimized_tex: str, pdf_bytes: bytes | None, pdf_error: str) -> None:
    summary = parsed.get("optimized_summary", "").strip()
    st.markdown('<div class="summary-card"><p class="card-title">Rewritten Professional Summary</p>', unsafe_allow_html=True)
    if summary:
        st.markdown(summary)
    else:
        st.caption("No explicit summary section was parsed from the report.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="code-card"><p class="card-title">Optimized LaTeX Resume</p>', unsafe_allow_html=True)
    st.code(optimized_tex, language="latex")
    st.markdown("</div>", unsafe_allow_html=True)

    status_class = "success" if pdf_bytes and not pdf_error else "warning"
    status_text = "PDF compiled successfully." if pdf_bytes and not pdf_error else "PDF unavailable or fallback cache is being used."
    st.markdown(
        f'<div class="status-card {status_class}"><p class="card-title">Compilation Status</p><p class="card-subtitle">{status_text}</p></div>',
        unsafe_allow_html=True,
    )

    st.markdown("#### PDF Preview")
    if pdf_bytes:
        b64 = base64.b64encode(pdf_bytes).decode("utf-8")
        iframe = f'<div class="pdf-frame"><iframe src="data:application/pdf;base64,{b64}" width="100%" height="760" type="application/pdf"></iframe></div>'
        st.markdown(iframe, unsafe_allow_html=True)
    else:
        st.info("PDF preview unavailable because compilation did not succeed.")


def render_downloads(report: str, optimized_tex: str, pdf_bytes: bytes | None) -> None:
    c1, c2, c3 = st.columns(3, gap="large")

    with c1:
        st.markdown('<div class="download-card"><p class="card-title">ATS Report</p><p class="card-subtitle">Markdown analysis including score, keyword alignment, and skill gaps.</p></div>', unsafe_allow_html=True)
        st.download_button(
            "Download ATS report (.md)",
            data=report.encode("utf-8"),
            file_name="ats_report.md",
            mime="text/markdown",
            use_container_width=True,
        )

    with c2:
        st.markdown('<div class="download-card"><p class="card-title">Optimized LaTeX</p><p class="card-subtitle">Editable ATS-optimized resume source in `.tex` format.</p></div>', unsafe_allow_html=True)
        st.download_button(
            "Download optimized resume (.tex)",
            data=optimized_tex.encode("utf-8"),
            file_name="optimized_resume.tex",
            mime="text/plain",
            use_container_width=True,
        )

    with c3:
        st.markdown('<div class="download-card"><p class="card-title">Compiled PDF</p><p class="card-subtitle">Production-ready PDF from `pdflatex` two-pass compile.</p></div>', unsafe_allow_html=True)
        if pdf_bytes:
            st.download_button(
                "Download optimized resume (.pdf)",
                data=pdf_bytes,
                file_name="optimized_resume.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.button("PDF unavailable", disabled=True, use_container_width=True)


def render_debug_panel(raw_output: str, report: str, pdf_error: str, parsing_issue: str) -> None:
    with st.expander("Debug / Logs", expanded=False):
        if parsing_issue:
            st.error(parsing_issue)
        st.markdown("#### Parsing report snapshot")
        st.code(report or "No parsed report")

        if pdf_error:
            st.markdown("#### LaTeX compilation logs")
            st.text(pdf_error)

        st.markdown("#### Raw model output")
        st.code(raw_output or "No output")


def init_state() -> None:
    cached_pdf = load_cached_pdf()
    defaults = {
        "job_description": "",
        "raw_output": "",
        "report": "",
        "optimized_tex": "",
        "pdf_bytes": cached_pdf,
        "pdf_error": "",
        "parsed": {},
        "metrics": {},
        "parsing_issue": "",
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

    api_key, model, uploaded_tex, use_base_if_missing, show_resume_preview, resume_source = render_sidebar()

    if uploaded_tex is not None:
        resume_tex = uploaded_tex.getvalue().decode("utf-8", errors="ignore")
    elif use_base_if_missing:
        resume_tex = BASE_RESUME_PATH.read_text(encoding="utf-8")
    else:
        resume_tex = ""

    jd = render_input_section(st.session_state.job_description, resume_source, resume_tex)
    st.session_state.job_description = jd

    if show_resume_preview:
        with st.expander("Resume preview", expanded=False):
            if resume_tex:
                st.code(resume_tex[:8000], language="latex")
            else:
                st.caption("No resume source loaded.")

    generate = st.button("Generate ATS Report + Optimized Resume", type="primary", use_container_width=True)

    if generate:
        if not api_key.strip():
            st.error("Missing API key. Please provide your OpenAI API key in the sidebar.")
            st.stop()
        if not jd.strip():
            st.error("Missing Job Description. Please paste a JD in the input section.")
            st.stop()
        if not resume_tex.strip():
            st.error("Missing resume source. Upload a `.tex` file or enable bundled fallback resume.")
            st.stop()

        with st.spinner("Analyzing JD, optimizing resume, and compiling PDF..."):
            try:
                raw_output, report, optimized_tex = run_agent(api_key, model, jd, resume_tex)
            except Exception as exc:
                st.exception(exc)
                st.stop()

            if not report.strip():
                report = raw_output
                parsing_issue = "ATS report parsing fallback triggered: report section not explicitly detected."
            else:
                parsing_issue = ""

            if not optimized_tex.strip():
                st.error("Could not detect optimized LaTeX section in model output.")
                st.session_state.raw_output = raw_output
                st.session_state.report = report
                st.session_state.optimized_tex = ""
                st.session_state.parsing_issue = (
                    parsing_issue + " LaTeX split failed. Check raw output format from model."
                ).strip()
                st.stop()

            parsed = parse_ats_report(report)
            metrics = infer_metrics(parsed, report)
            pdf_bytes, pdf_error = compile_pdf(optimized_tex)

            (OUTPUTS_DIR / "ats_report.md").write_text(report, encoding="utf-8")
            (OUTPUTS_DIR / "optimized_resume.tex").write_text(optimized_tex, encoding="utf-8")

            if pdf_bytes:
                OUTPUT_PDF_PATH.write_bytes(pdf_bytes)
            else:
                cached_pdf = load_cached_pdf()
                if cached_pdf:
                    pdf_bytes = cached_pdf
                    pdf_error = (pdf_error + "\n\n" if pdf_error else "") + (
                        "Using last successful PDF from outputs/optimized_resume.pdf."
                    )

            st.session_state.raw_output = raw_output
            st.session_state.report = report
            st.session_state.optimized_tex = optimized_tex
            st.session_state.pdf_bytes = pdf_bytes
            st.session_state.pdf_error = pdf_error or ""
            st.session_state.parsed = parsed
            st.session_state.metrics = metrics
            st.session_state.parsing_issue = parsing_issue
            st.session_state.last_resume_source = resume_source
            st.session_state.original_resume_tex = resume_tex

        st.success("Optimization complete. Explore results in the dashboard tabs below.")

    if st.session_state.optimized_tex:
        st.markdown("## ATS Overview")
        render_metric_cards(st.session_state.metrics)

        tabs = st.tabs(
            [
                "JD Breakdown",
                "Skill Gap Analysis",
                "Bullet Improvements",
                "Optimized Resume",
                "Downloads",
            ]
        )

        with tabs[0]:
            render_jd_breakdown(st.session_state.parsed)

        with tabs[1]:
            render_skill_gap(st.session_state.parsed)

        with tabs[2]:
            render_bullet_tab(
                st.session_state.original_resume_tex,
                st.session_state.optimized_tex,
                st.session_state.parsed,
            )

        with tabs[3]:
            render_resume_tab(
                st.session_state.parsed,
                st.session_state.optimized_tex,
                st.session_state.pdf_bytes,
                st.session_state.pdf_error,
            )

        with tabs[4]:
            render_downloads(
                st.session_state.report,
                st.session_state.optimized_tex,
                st.session_state.pdf_bytes,
            )

        render_debug_panel(
            st.session_state.raw_output,
            st.session_state.report,
            st.session_state.pdf_error,
            st.session_state.parsing_issue,
        )


if __name__ == "__main__":
    main()
