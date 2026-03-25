from __future__ import annotations

import base64
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
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
ROLE_MODES = ["Backend Engineer", "Full Stack Engineer", "GenAI Engineer", "Data Engineer"]
ROLE_HINTS = {
    "Backend Engineer": "Prioritize APIs, scalability, distributed systems, performance, backend reliability, and databases.",
    "Full Stack Engineer": "Balance frontend and backend impact, product delivery velocity, and end-to-end ownership.",
    "GenAI Engineer": "Prioritize LLM integrations, prompt engineering, RAG/pipelines, model evaluation, and AI productization.",
    "Data Engineer": "Prioritize data pipelines, ETL/ELT, warehousing, data quality, storage, and platform reliability.",
}

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
            --bg-0: #06090f;
            --bg-1: #0c1220;
            --bg-2: #121b2f;
            --surface: rgba(15, 22, 37, 0.82);
            --surface-2: rgba(18, 28, 46, 0.9);
            --line-soft: rgba(148, 169, 213, 0.16);
            --line-strong: rgba(148, 169, 213, 0.32);
            --text-main: #edf3ff;
            --text-sub: #95a7c7;
            --accent: #7d8fff;
            --accent-soft: rgba(125, 143, 255, 0.2);
            --ok: #63d59c;
            --warn: #e6b86a;
            --err: #f28597;
            --shadow: 0 14px 30px rgba(1, 4, 12, 0.4);
          }

          .stApp {
            background:
              radial-gradient(circle at 9% 3%, rgba(68, 93, 176, 0.22), transparent 34%),
              radial-gradient(circle at 94% 6%, rgba(59, 149, 193, 0.18), transparent 36%),
              linear-gradient(180deg, var(--bg-0) 0%, #0a101b 45%, var(--bg-0) 100%);
            color: var(--text-main);
          }

          .block-container {
            max-width: 1400px;
            padding-top: 1rem;
            padding-bottom: 2.5rem;
          }

          [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0a111e 0%, #0d1524 100%);
            border-right: 1px solid var(--line-soft);
          }

          [data-testid="stSidebar"] .stMarkdown p,
          [data-testid="stSidebar"] label,
          [data-testid="stSidebar"] .stCaption {
            color: #dce7ff !important;
          }

          .app-shell { margin-bottom: 1.2rem; }

          .hero-wrap {
            border-radius: 22px;
            padding: 1.4rem 1.5rem 1.2rem 1.5rem;
            background:
              radial-gradient(circle at 85% 14%, rgba(126, 143, 255, 0.2), transparent 42%),
              linear-gradient(140deg, rgba(18, 28, 46, 0.95), rgba(20, 34, 58, 0.92));
            border: 1px solid var(--line-soft);
            box-shadow: var(--shadow);
          }

          .hero-title {
            margin: 0;
            font-size: 2rem;
            letter-spacing: -0.03em;
            color: #f5f8ff;
          }

          .hero-subtitle {
            margin: 0.42rem 0 0 0;
            max-width: 800px;
            color: #c9d7f2;
            line-height: 1.45;
          }

          .pill-row { display:flex; flex-wrap:wrap; gap:0.42rem; margin-top:0.9rem; }
          .feature-pill {
            border-radius: 999px;
            font-size: 0.74rem;
            border: 1px solid var(--line-strong);
            color: #dfebff;
            background: rgba(130, 150, 212, 0.14);
            padding: 0.28rem 0.68rem;
          }

          .section-wrap,
          .control-group,
          .recruiter-panel,
          .insight-card,
          .muted-card,
          .editor-panel,
          .asset-card,
          .code-wrap,
          .diff-row,
          .status-strip {
            border-radius: 16px;
            background: linear-gradient(160deg, var(--surface), var(--surface-2));
            border: 1px solid var(--line-soft);
          }

          .section-wrap,
          .control-group,
          .recruiter-panel,
          .insight-card,
          .muted-card,
          .editor-panel,
          .asset-card,
          .code-wrap,
          .status-strip {
            padding: 0.95rem 1rem;
          }

          .section-title { margin:0; font-size: 1.05rem; color:#edf3ff; }
          .section-subtitle { margin:0.35rem 0 0 0; color: var(--text-sub); font-size: 0.88rem; }
          .helper-text { color: var(--text-sub); font-size: 0.8rem; }
          .soft-divider { border-top: 1px solid var(--line-soft); margin: 0.8rem 0; }

          .kpi-card {
            min-height: 104px;
            border-radius: 14px;
            padding: 0.8rem 0.85rem;
            border: 1px solid var(--line-soft);
            background: rgba(17, 26, 42, 0.78);
          }
          .kpi-primary {
            background: linear-gradient(150deg, rgba(25, 40, 68, 0.96), rgba(34, 53, 89, 0.94));
            border-color: rgba(125, 143, 255, 0.42);
          }
          .kpi-value { margin-top: 0.24rem; font-size: 1.6rem; font-weight: 700; color: #f5f9ff; }
          .kpi-label { margin:0; font-size: 0.76rem; letter-spacing: 0.06em; text-transform: uppercase; color:#c7d8fc; }

          .status-strip {
            padding: 0.7rem 0.9rem;
            display:flex;
            align-items:center;
            justify-content:space-between;
          }

          .verdict-pill {
            border-radius: 999px;
            padding: 0.27rem 0.7rem;
            font-size: 0.76rem;
            font-weight: 700;
            border: 1px solid transparent;
          }
          .verdict-reject { background: rgba(242, 133, 151, 0.17); border-color: rgba(242, 133, 151, 0.46); color: #ffd8df; }
          .verdict-borderline { background: rgba(230, 184, 106, 0.15); border-color: rgba(230, 184, 106, 0.44); color: #ffe9c7; }
          .verdict-shortlist { background: rgba(125, 143, 255, 0.18); border-color: rgba(125, 143, 255, 0.5); color: #dee5ff; }
          .verdict-strong { background: rgba(99, 213, 156, 0.17); border-color: rgba(99, 213, 156, 0.46); color: #dcffe9; }

          .chip {
            display: inline-block;
            margin: 0.15rem 0.2rem 0.18rem 0;
            padding: 0.22rem 0.62rem;
            border-radius: 999px;
            font-size: 0.75rem;
            border: 1px solid rgba(145, 164, 214, 0.35);
            background: rgba(92, 112, 164, 0.2);
            color: #e6efff;
          }
          .chip-danger { border-color: rgba(242, 133, 151, 0.44); background: rgba(242, 133, 151, 0.14); }
          .chip-warning { border-color: rgba(230, 184, 106, 0.44); background: rgba(230, 184, 106, 0.12); }
          .chip-success { border-color: rgba(99, 213, 156, 0.44); background: rgba(99, 213, 156, 0.12); }

          .diff-row {
            padding: 0.78rem;
            margin-bottom: 0.56rem;
            background: rgba(15, 22, 36, 0.78);
          }
          .diff-side {
            border-radius: 12px;
            border: 1px solid var(--line-soft);
            background: rgba(11, 17, 29, 0.62);
            padding: 0.64rem 0.72rem;
            min-height: 72px;
          }
          .diff-before { border-color: rgba(230, 184, 106, 0.34); }
          .diff-after { border-color: rgba(99, 213, 156, 0.34); }

          .empty-state {
            border-radius: 12px;
            border: 1px dashed var(--line-strong);
            background: rgba(14, 20, 34, 0.58);
            color: var(--text-sub);
            padding: 0.75rem 0.85rem;
            font-size: 0.86rem;
          }

          .code-wrap code { font-size: 0.82rem; }

          [data-testid="stTabs"] [data-baseweb="tab-list"] {
            gap: 0.26rem;
            background: rgba(9, 14, 25, 0.68);
            border: 1px solid var(--line-soft);
            border-radius: 12px;
            padding: 0.3rem;
          }
          [data-testid="stTabs"] [data-baseweb="tab"] {
            color: #c7d7f6;
            border-radius: 9px;
            border: 1px solid transparent;
            padding-top: 0.42rem;
            padding-bottom: 0.42rem;
          }
          [data-testid="stTabs"] [aria-selected="true"] {
            background: rgba(125, 143, 255, 0.2) !important;
            border-color: rgba(125, 143, 255, 0.45) !important;
            color: #f3f7ff !important;
          }

          .stButton > button,
          .stDownloadButton > button {
            border-radius: 10px;
            border: 1px solid rgba(146, 165, 214, 0.34);
            background: linear-gradient(180deg, rgba(37, 54, 84, 0.92), rgba(26, 40, 64, 0.94));
            color: #eaf2ff;
            font-weight: 600;
          }

          .stTextArea textarea,
          .stTextInput input,
          .stSelectbox [data-baseweb="select"] > div,
          .stFileUploader > div,
          .stRadio > div {
            background: rgba(9, 14, 24, 0.76) !important;
            color: #e4eeff !important;
            border-radius: 10px !important;
            border-color: rgba(143, 163, 206, 0.34) !important;
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
    cleaned = re.sub(r"^```(?:latex|tex|markdown|md|text)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def split_output(output: str) -> tuple[str, str]:
    cleaned = output.strip()
    normalized = normalize_text(cleaned)

    markers = [
        r"section\s*2\s*[:\-]\s*updated\s*latex\s*resume",
        r"section\s*2\s*[:\-]\s*(?:latex|resume)",
        r"section\s*2\b",
    ]

    for pattern in markers:
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


def extract_section(text: str, aliases: list[str]) -> str:
    heading_pattern = "|".join(rf"{a}" for a in aliases)
    boundary = r"(?=\n\s*(?:[A-Z][A-Za-z0-9\s/&()+\-]{2,55}[:\-]|SECTION\s*\d)|\Z)"

    patterns = [
        rf"(?:^|\n)\s*(?:{heading_pattern})\s*[:\-]\s*(.*?){boundary}",
        rf"(?:^|\n)\s*(?:{heading_pattern})\s*\n(.*?){boundary}",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
    return ""


def parse_summary(text: str) -> str:
    return extract_section(text, [r"Professional\s*Summary", r"Summary", r"Rewritten\s*Summary", r"Optimized\s*Summary"]).strip()


def parse_bullets(text: str) -> list[str]:
    section = extract_section(
        text,
        [
            r"Optimized\s*Bullet\s*Points",
            r"Optimized\s*Bullets",
            r"Bullet\s*Improvements",
            r"Rewritten\s*Bullet\s*Points",
            r"Experience\s*Highlights",
        ],
    )
    return parse_marked_list(section)


def parse_recruiter_feedback(report: str) -> dict[str, Any]:
    block = extract_section(report, [r"Recruiter\s*Simulation(?:\s*Engine)?", r"Recruiter\s*Review", r"Hiring\s*Manager\s*Assessment"])
    target = block or report

    verdict_match = re.search(r"verdict\s*[:\-]\s*(Reject|Borderline|Shortlist|Strong\s*Hire)", target, flags=re.IGNORECASE)
    confidence_match = re.search(r"confidence\s*(?:score)?\s*[:\-]\s*(\d{1,3})", target, flags=re.IGNORECASE)

    return {
        "verdict": (verdict_match.group(1).title().replace("Strong Hire", "Strong Hire") if verdict_match else "Borderline"),
        "confidence": max(0, min(100, int(confidence_match.group(1)) if confidence_match else 68)),
        "reasons": parse_marked_list(extract_section(target, [r"Reasons", r"Why\s*this\s*verdict"])),
        "working": parse_marked_list(extract_section(target, [r"What\s*is\s*working\s*well", r"Strengths", r"Working\s*well"])),
        "fixing": parse_marked_list(extract_section(target, [r"What\s*needs\s*fixing", r"Needs\s*fixing", r"Risks", r"Concerns"])),
        "recommendations": parse_marked_list(extract_section(target, [r"Top\s*Recommendations", r"Recommendations", r"Next\s*actions"])),
    }


def parse_strength_scores(report: str, metrics: dict[str, Any]) -> dict[str, int]:
    score_block = extract_section(report, [r"Resume\s*Strength\s*Scores", r"Strength\s*Scores", r"Radar\s*Scores"])
    base = {
        "Technical Depth": None,
        "Impact": None,
        "Keywords": None,
        "Clarity": None,
        "ATS Score": metrics.get("ats_score"),
    }

    search_text = score_block or report
    for key in list(base.keys()):
        match = re.search(rf"{re.escape(key)}\s*[:\-]\s*(\d{{1,3}})", search_text, flags=re.IGNORECASE)
        if match:
            base[key] = int(match.group(1))

    tech = len(metrics.get("technical_skills", []))
    weak = len(metrics.get("weak_skills", []))
    missing = len(metrics.get("missing_skills", []))
    keyword_match = metrics.get("keyword_match", 65)

    if base["Technical Depth"] is None:
        base["Technical Depth"] = int(max(35, min(95, 54 + tech * 3 - weak * 2)))
    if base["Impact"] is None:
        base["Impact"] = 76 if re.search(r"\b(led|scaled|increased|improved|reduced|delivered|launched|optimized)\b", report, flags=re.IGNORECASE) else 64
    if base["Keywords"] is None:
        base["Keywords"] = int(max(30, min(98, keyword_match)))
    if base["Clarity"] is None:
        base["Clarity"] = 82 if len(parse_summary(report).split()) >= 30 else 70
    if base["ATS Score"] is None:
        base["ATS Score"] = 100 - min(45, missing * 4)

    return {k: max(0, min(100, int(v or 0))) for k, v in base.items()}


def parse_cover_letter(report: str) -> str:
    direct = extract_section(report, [r"Cover\s*Letter", r"JD\s*Aligned\s*Cover\s*Letter"])
    if direct:
        return direct.strip()
    fence = re.search(r"```(?:text|markdown|md)?\s*(Dear\s+[\s\S]*?)```", report, flags=re.IGNORECASE)
    if fence:
        return strip_code_fences(fence.group(0))
    start = re.search(r"Dear\s+Hiring\s+Manager[\s\S]*", report, flags=re.IGNORECASE)
    return start.group(0).strip() if start else ""


def parse_ats_report(report: str) -> dict[str, Any]:
    score_match = re.search(r"ATS\s*Score\s*[:\-]?\s*(\d{1,3})\s*(?:/\s*100)?", report, flags=re.IGNORECASE)
    keyword_match = re.search(r"keyword\s*match\s*[:\-]?\s*(\d{1,3})\s*%", report, flags=re.IGNORECASE)
    skill_match = re.search(r"skills?\s*match\s*[:\-]?\s*(\d{1,3})\s*%", report, flags=re.IGNORECASE)
    missing_count = re.search(r"missing\s*skills\s*(?:count|total)?\s*[:\-]?\s*(\d{1,3})", report, flags=re.IGNORECASE)

    return {
        "ats_score": int(score_match.group(1)) if score_match else None,
        "keyword_match": int(keyword_match.group(1)) if keyword_match else None,
        "skills_match": int(skill_match.group(1)) if skill_match else None,
        "missing_skills_count": int(missing_count.group(1)) if missing_count else None,
        "technical_skills": parse_marked_list(extract_section(report, [r"Top\s*10\s*Technical\s*Skills", r"Technical\s*Skills", r"Core\s*Technical\s*Skills", r"Required\s*Technical\s*Skills"])),
        "soft_skills": parse_marked_list(extract_section(report, [r"Top\s*5\s*Soft\s*Skills", r"Soft\s*Skills", r"Behavioral\s*Skills", r"Collaboration\s*Skills"])),
        "responsibilities": parse_marked_list(extract_section(report, [r"Key\s*Responsibilities", r"Responsibilities"])),
        "keywords": parse_marked_list(extract_section(report, [r"ATS\s*Keywords", r"Keywords", r"Keyword\s*Targets"])),
        "missing_skills": parse_marked_list(extract_section(report, [r"Missing\s*Skills", r"Skill\s*Gaps"])),
        "weak_skills": parse_marked_list(extract_section(report, [r"Weakly\s*Represented\s*Skills", r"Weak\s*Skills"])),
        "strong_skills": parse_marked_list(extract_section(report, [r"Strong\s*Matches", r"Strong\s*Skills", r"Well\s*Represented\s*Skills"])),
        "optimized_summary": parse_summary(report),
        "optimized_bullets": parse_bullets(report),
    }


def infer_lists_from_jd(jd: str) -> dict[str, list[str]]:
    if not jd.strip():
        return {"technical_skills": [], "soft_skills": [], "keywords": []}

    lower = jd.lower()
    tech_candidates = [
        "python", "java", "go", "node", "typescript", "javascript", "react", "sql", "postgres", "mysql", "redis",
        "kafka", "aws", "gcp", "azure", "docker", "kubernetes", "airflow", "spark", "llm", "rag", "etl", "api", "microservices",
    ]
    soft_candidates = ["communication", "collaboration", "leadership", "mentoring", "ownership", "stakeholder", "problem solving", "adaptability", "teamwork"]

    technical = [s for s in tech_candidates if re.search(rf"\b{re.escape(s)}\b", lower)]
    soft = [s.title() for s in soft_candidates if re.search(rf"\b{re.escape(s)}\b", lower)]

    stop_words = {"the", "and", "for", "with", "you", "our", "will", "this", "that", "are", "from", "have", "your", "years", "experience", "required", "preferred", "ability"}
    raw_tokens = re.findall(r"\b[A-Za-z][A-Za-z0-9+\-#/]{2,}\b", jd)
    keywords: list[str] = []
    for token in raw_tokens:
        if token.lower() in stop_words:
            continue
        if token.lower() not in [k.lower() for k in keywords]:
            keywords.append(token)
        if len(keywords) >= 20:
            break

    return {"technical_skills": technical[:12], "soft_skills": soft[:8], "keywords": keywords}


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
        keyword_match = int(max(35, min(98, ((len(keywords) - min(len(keywords), len(missing))) / max(1, len(keywords))) * 100)))
        estimates["keyword_match"] = True
    else:
        estimates["keyword_match"] = False

    skills_match = parsed.get("skills_match")
    if skills_match is None:
        total = max(1, len(parsed.get("technical_skills", [])) + len(parsed.get("soft_skills", [])))
        impact = min(total, len(parsed.get("missing_skills", [])) + max(0, len(parsed.get("weak_skills", [])) // 2))
        skills_match = int(max(30, min(98, ((total - impact) / total) * 100)))
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
        "technical_skills": parsed.get("technical_skills", []),
        "weak_skills": parsed.get("weak_skills", []),
        "missing_skills": parsed.get("missing_skills", []),
    }


def extract_latex_bullets(tex_content: str, limit: int = 16) -> list[str]:
    bullets = re.findall(r"\\item\s*(.+?)(?=\n\\item|\n\\end\{itemize\}|$)", tex_content, flags=re.DOTALL)
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


def extract_summary_from_tex(tex_content: str) -> str:
    match = re.search(r"\\section\*?\{(?:Summary|Professional\s*Summary)\}(.*?)(?=\\section\*?\{|\\end\{document\})", tex_content, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    summary = re.sub(r"\\[a-zA-Z]+(?:\[[^\]]*\])?(?:\{[^}]*\})?", "", match.group(1))
    return re.sub(r"\s+", " ", summary).strip()


def compute_diff_pairs(before: list[str], after: list[str]) -> list[tuple[str, str]]:
    size = max(len(before), len(after))
    return [(before[i] if i < len(before) else "", after[i] if i < len(after) else "") for i in range(size)]


def compile_pdf(tex_content: str) -> tuple[bytes | None, str | None]:
    latex_engine = next((engine for engine in ("pdflatex", "xelatex", "lualatex") if shutil.which(engine)), None)
    if not latex_engine:
        return None, (
            "No LaTeX compiler found. Install a TeX distribution and ensure one of these commands is on PATH: "
            "pdflatex, xelatex, or lualatex."
        )

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            tex_path = tmp_path / "optimized_resume.tex"
            tex_path.write_text(tex_content, encoding="utf-8")
            cmd = [latex_engine, "-interaction=nonstopmode", "-halt-on-error", tex_path.name]
            logs: list[str] = []
            for run_number in (1, 2):
                result = subprocess.run(cmd, cwd=tmp_path, capture_output=True, text=True, timeout=90)
                logs.append(f"--- {latex_engine} run {run_number} ---\n{result.stdout}\n{result.stderr}")
                if result.returncode != 0:
                    return None, "\n".join(logs)
            pdf_path = tmp_path / "optimized_resume.pdf"
            return (pdf_path.read_bytes(), None) if pdf_path.exists() else (None, "PDF compilation reported success but no PDF file was produced.")
    except FileNotFoundError:
        return None, f"{latex_engine} is not installed in this environment."
    except subprocess.TimeoutExpired:
        return None, f"{latex_engine} timed out while compiling the LaTeX resume."
    except Exception as exc:  # pragma: no cover
        return None, str(exc)


def load_cached_pdf() -> bytes | None:
    if OUTPUT_PDF_PATH.exists():
        try:
            return OUTPUT_PDF_PATH.read_bytes()
        except Exception:
            return None
    return None


def run_agent(api_key: str, model: str, jd: str, resume_tex: str, role_mode: str) -> tuple[str, str, str]:
    client = OpenAI(api_key=api_key)
    system_prompt = load_prompt("system_prompt.txt")
    role_instruction = ROLE_HINTS.get(role_mode, "")
    extension = f"""

ROLE OPTIMIZATION MODE: {role_mode}
Role-specific rewrite guidance: {role_instruction}

ADDITIONAL OUTPUT REQUIREMENTS (inside SECTION 1):
- ATS Score, Keyword Match %, Skills Match %, Missing Skills Count
- Recruiter Simulation Engine:
  - Verdict: Reject | Borderline | Shortlist | Strong Hire
  - Confidence Score (0-100)
  - Reasons for verdict
  - What is working well
  - What needs fixing
  - Top recommendations
- Resume Strength Scores (0-100 each):
  - Technical Depth
  - Impact
  - Keywords
  - Clarity
  - ATS Score
- Optimized Summary
- Optimized Bullet Points
- JD-Aligned Cover Letter

Keep the same two-section top-level format:
SECTION 1 — COMPREHENSIVE ATS REPORT
SECTION 2 — UPDATED LATEX RESUME
"""
    user_prompt = load_prompt("user_prompt.txt").format(job_description=jd.strip(), resume_tex=resume_tex.strip())
    response = client.chat.completions.create(
        model=model,
        temperature=0.25,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt + "\n" + extension},
        ],
    )
    output = response.choices[0].message.content or ""
    report, tex = split_output(output)
    return output, report, tex


def run_cover_letter_generation(api_key: str, model: str, jd: str, resume_tex: str, role_mode: str) -> str:
    client = OpenAI(api_key=api_key)
    role_instruction = ROLE_HINTS.get(role_mode, "")
    response = client.chat.completions.create(
        model=model,
        temperature=0.55,
        messages=[
            {"role": "system", "content": "You are an expert career coach and recruiter. Produce concise, high-impact, personalized cover letters."},
            {
                "role": "user",
                "content": (
                    f"Role mode: {role_mode}\nGuidance: {role_instruction}\n\n"
                    "Write a JD-aligned cover letter in plain text, no markdown headings.\n"
                    "Use concrete achievements and relevant skills from this resume.\n"
                    "Keep to 230-320 words.\n\n"
                    f"JOB DESCRIPTION:\n{jd}\n\nRESUME (LATEX):\n{resume_tex}"
                ),
            },
        ],
    )
    return (response.choices[0].message.content or "").strip()


def render_top_shell() -> None:
    st.markdown('<div class="app-shell"></div>', unsafe_allow_html=True)


def render_hero() -> None:
    st.markdown(
        """
        <div class="hero-wrap">
          <h1 class="hero-title">Resume Optimizer Agent</h1>
          <p class="hero-subtitle">A production-style AI workspace for ATS analysis, recruiter simulation, high-signal resume rewriting, and export-ready deliverables.</p>
          <div class="pill-row">
            <span class="feature-pill">ATS Analysis</span>
            <span class="feature-pill">Recruiter Review</span>
            <span class="feature-pill">Resume Diff</span>
            <span class="feature-pill">Cover Letter</span>
            <span class="feature-pill">PDF Export</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander("How it works", expanded=False):
        st.caption("Paste a JD, choose role mode, attach or fallback to a resume, run optimization, then review ATS/recruiter outputs and export final assets.")


def render_sidebar() -> tuple[str, str, str, str, bool, bool, str]:
    with st.sidebar:
        st.markdown("### Control Panel")
        st.markdown('<div class="control-group">', unsafe_allow_html=True)
        api_key = st.text_input("OpenAI API Key", type="password", value=st.session_state.api_key)
        model = st.selectbox("Model", MODEL_OPTIONS, index=MODEL_OPTIONS.index(st.session_state.model))
        role_mode = st.selectbox("Role mode", ROLE_MODES, index=ROLE_MODES.index(st.session_state.role_mode))
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("### Resume Source")
        st.markdown('<div class="control-group">', unsafe_allow_html=True)
        upload = st.file_uploader("Upload .tex resume", type=["tex"], accept_multiple_files=False)
        use_base_if_missing = st.checkbox("Use bundled base resume fallback", value=st.session_state.use_base_if_missing)
        show_preview = st.checkbox("Preview loaded resume", value=st.session_state.show_resume_preview)

        if upload is not None:
            st.session_state.uploaded_resume_name = upload.name
            st.session_state.uploaded_resume_content = upload.getvalue().decode("utf-8", errors="ignore")

        if st.session_state.uploaded_resume_content.strip():
            resume_tex = st.session_state.uploaded_resume_content
            resume_source = f"Upload · {st.session_state.uploaded_resume_name}"
        elif use_base_if_missing:
            resume_tex = BASE_RESUME_PATH.read_text(encoding="utf-8")
            resume_source = "Bundled · base_resume.tex"
        else:
            resume_tex = ""
            resume_source = "No resume loaded"

        st.markdown(f"<p class='helper-text'><strong>Active file:</strong> {resume_source}</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        ready = bool(api_key.strip() and resume_tex.strip())
        st.markdown(
            f"""
            <div class="status-strip">
              <div>
                <div class="helper-text">Current state</div>
                <div class="helper-text">Model: {model}</div>
                <div class="helper-text">Role: {role_mode}</div>
                <div class="helper-text">Source: {resume_source}</div>
              </div>
              <div class="verdict-pill {'verdict-strong' if ready else 'verdict-borderline'}">{'Ready' if ready else 'Needs input'}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.session_state.api_key = api_key
    st.session_state.model = model
    st.session_state.role_mode = role_mode
    st.session_state.use_base_if_missing = use_base_if_missing
    st.session_state.show_resume_preview = show_preview

    return api_key, model, role_mode, resume_tex, use_base_if_missing, show_preview, resume_source


def render_chip_group(items: list[str], variant: str = "") -> None:
    if not items:
        st.markdown('<div class="empty-state">No data detected for this section yet.</div>', unsafe_allow_html=True)
        return
    klass = "chip" if not variant else f"chip {variant}"
    html = "".join(f'<span class="{klass}">{i.replace("<", "&lt;").replace(">", "&gt;")}</span>' for i in items)
    st.markdown(html, unsafe_allow_html=True)


def render_kpi_section(metrics: dict[str, Any]) -> None:
    st.markdown("## ATS Overview")
    c1, c2, c3, c4 = st.columns(4, gap="small")
    specs = [
        ("ATS Score", f"{metrics['ats_score']}/100", "Overall parsing + alignment score", "ats_score", True),
        ("Keyword Match %", f"{metrics['keyword_match']}%", "Coverage of JD keyword targets", "keyword_match", False),
        ("Skills Match %", f"{metrics['skills_match']}%", "Skill alignment across hard/soft", "skills_match", False),
        ("Missing Skills", f"{metrics['missing_skills_count']}", "Critical JD skills not represented", "missing_skills_count", False),
    ]
    for col, (label, value, helper, key, primary) in zip((c1, c2, c3, c4), specs):
        estimated = metrics.get("estimate_flags", {}).get(key, False)
        col.markdown(
            f"""
            <div class="kpi-card {'kpi-primary' if primary else ''}">
              <p class="kpi-label">{label}</p>
              <div class="kpi-value">{value}</div>
              <div class="helper-text">{helper}{' · estimated' if estimated else ''}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_recruiter_panel(data: dict[str, Any]) -> None:
    st.markdown("## Recruiter Simulation")
    verdict = data.get("verdict", "Borderline")
    key = verdict.lower().replace(" ", "")
    klass = {
        "reject": "verdict-reject",
        "borderline": "verdict-borderline",
        "shortlist": "verdict-shortlist",
        "stronghire": "verdict-strong",
    }.get(key, "verdict-borderline")

    st.markdown(
        f"""
        <div class="recruiter-panel">
          <div class="status-strip">
            <div>
              <p class="section-title">Recruiter Evaluation</p>
              <p class="section-subtitle">Simulated hiring decision with rationale and next actions.</p>
            </div>
            <div>
              <span class="verdict-pill {klass}">{verdict}</span>
              <span class="helper-text" style="margin-left:0.45rem;">Confidence {data.get('confidence', 0)}/100</span>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    a, b, c = st.columns(3, gap="small")
    with a:
        st.markdown('<div class="insight-card"><p class="section-title">Reasons for Verdict</p>', unsafe_allow_html=True)
        for item in data.get("reasons", []) or ["The model did not provide explicit reasons."]:
            st.markdown(f"- {item}")
        st.markdown("</div>", unsafe_allow_html=True)
    with b:
        st.markdown('<div class="insight-card"><p class="section-title">What is Working Well</p>', unsafe_allow_html=True)
        for item in data.get("working", []) or ["No strengths were explicitly listed."]:
            st.markdown(f"- {item}")
        st.markdown("</div>", unsafe_allow_html=True)
    with c:
        st.markdown('<div class="insight-card"><p class="section-title">What Needs Fixing</p>', unsafe_allow_html=True)
        for item in data.get("fixing", []) or ["No concrete risks were explicitly listed."]:
            st.markdown(f"- {item}")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="muted-card"><p class="section-title">Top Recommendations</p>', unsafe_allow_html=True)
    for item in data.get("recommendations", []) or ["No extra recommendations were generated."]:
        st.markdown(f"- {item}")
    st.markdown("</div>", unsafe_allow_html=True)


def render_strength_section(scores: dict[str, int]) -> None:
    st.markdown("## Resume Strength + Insights")
    left, right = st.columns([1.2, 1], gap="large")
    with left:
        labels = list(scores.keys())
        values = [scores[k] for k in labels]
        values += values[:1]
        angles = [n / float(len(labels)) * 2 * 3.1415926 for n in range(len(labels))]
        angles += angles[:1]

        fig = plt.figure(figsize=(4.9, 4.5), facecolor="#0f1728")
        ax = fig.add_subplot(111, polar=True)
        ax.set_facecolor("#111b2f")
        ax.plot(angles, values, linewidth=2.0, color="#7d8fff")
        ax.fill(angles, values, color="#7d8fff", alpha=0.2)
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(labels, color="#dbe7ff", fontsize=8)
        ax.set_yticks([20, 40, 60, 80, 100])
        ax.set_yticklabels(["20", "40", "60", "80", "100"], color="#9bb0d5", fontsize=7)
        ax.grid(color="#314664", alpha=0.48)
        ax.spines["polar"].set_color("#3a4f77")
        ax.set_ylim(0, 100)
        st.markdown('<div class="section-wrap"><p class="section-title">Radar View</p></div>', unsafe_allow_html=True)
        st.pyplot(fig, use_container_width=False)
        plt.close(fig)

    with right:
        strongest = max(scores, key=scores.get)
        weakest = min(scores, key=scores.get)
        st.markdown(
            f"""
            <div class="insight-card">
              <p class="section-title">Interpretation</p>
              <p class="helper-text"><strong>Strongest dimension:</strong> {strongest} ({scores[strongest]}/100)</p>
              <p class="helper-text"><strong>Weakest dimension:</strong> {weakest} ({scores[weakest]}/100)</p>
              <div class="soft-divider"></div>
              <p class="section-subtitle">Quick recommendation</p>
              <p class="helper-text">Increase keyword depth and quantifiable impact language in the weakest area before final export.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_jd_breakdown(parsed: dict[str, Any]) -> None:
    st.markdown('<div class="section-wrap"><p class="section-title">JD Breakdown</p><p class="section-subtitle">Extracted requirements and signals from the job description.</p></div>', unsafe_allow_html=True)
    a, b = st.columns([1.2, 1], gap="small")
    with a:
        st.markdown('<div class="insight-card"><p class="section-title">Technical Skills</p>', unsafe_allow_html=True)
        render_chip_group(parsed.get("technical_skills", []))
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown('<div class="muted-card"><p class="section-title">Responsibilities</p>', unsafe_allow_html=True)
        for item in parsed.get("responsibilities", []) or ["No responsibilities parsed."]:
            st.markdown(f"- {item}")
        st.markdown("</div>", unsafe_allow_html=True)
    with b:
        st.markdown('<div class="muted-card"><p class="section-title">ATS Keywords</p>', unsafe_allow_html=True)
        render_chip_group(parsed.get("keywords", []))
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown('<div class="insight-card"><p class="section-title">Soft Skills</p>', unsafe_allow_html=True)
        render_chip_group(parsed.get("soft_skills", []))
        st.markdown("</div>", unsafe_allow_html=True)


def render_skill_gap(parsed: dict[str, Any]) -> None:
    st.markdown('<div class="section-wrap"><p class="section-title">Skill Gap Analysis</p><p class="section-subtitle">Coverage quality across missing, weak, and strong skill clusters.</p></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3, gap="small")
    with c1:
        st.markdown('<div class="insight-card"><p class="section-title">Missing Skills</p>', unsafe_allow_html=True)
        render_chip_group(parsed.get("missing_skills", []), "chip-danger")
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="insight-card"><p class="section-title">Weakly Represented</p>', unsafe_allow_html=True)
        render_chip_group(parsed.get("weak_skills", []), "chip-warning")
        st.markdown("</div>", unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="insight-card"><p class="section-title">Strong Matches</p>', unsafe_allow_html=True)
        render_chip_group(parsed.get("strong_skills", []), "chip-success")
        st.markdown("</div>", unsafe_allow_html=True)


def render_diff_viewer(original_tex: str, optimized_tex: str, parsed: dict[str, Any]) -> None:
    st.markdown('<div class="section-wrap"><p class="section-title">Resume Diff Viewer</p><p class="section-subtitle">Editorial before/after review for summary and bullet transformations.</p></div>', unsafe_allow_html=True)
    before_summary = extract_summary_from_tex(original_tex)
    after_summary = parsed.get("optimized_summary", "") or extract_summary_from_tex(optimized_tex)

    l, r = st.columns(2, gap="small")
    with l:
        st.markdown('<div class="diff-side diff-before"><p class="helper-text"><strong>BEFORE SUMMARY</strong></p>', unsafe_allow_html=True)
        st.write(before_summary or "No original summary extracted.")
        st.markdown("</div>", unsafe_allow_html=True)
    with r:
        st.markdown('<div class="diff-side diff-after"><p class="helper-text"><strong>AFTER SUMMARY</strong></p>', unsafe_allow_html=True)
        st.write(after_summary or "No optimized summary extracted.")
        st.markdown("</div>", unsafe_allow_html=True)

    before_bullets = extract_latex_bullets(original_tex)
    after_bullets = extract_latex_bullets(optimized_tex) or parsed.get("optimized_bullets", [])
    pairs = compute_diff_pairs(before_bullets, after_bullets)

    st.markdown('<div class="soft-divider"></div>', unsafe_allow_html=True)
    st.markdown("#### Bullet Transformations")

    if not pairs:
        st.markdown('<div class="empty-state">No bullet-level diff could be extracted. Try generating again or inspect debug output.</div>', unsafe_allow_html=True)
        return

    if len(pairs) > 10:
        with st.expander(f"Showing first 10 of {len(pairs)} bullet changes", expanded=True):
            pairs_to_show = pairs[:10]
            for idx, (before, after) in enumerate(pairs_to_show, start=1):
                _render_diff_row(idx, before, after)
    else:
        for idx, (before, after) in enumerate(pairs, start=1):
            _render_diff_row(idx, before, after)


def _render_diff_row(index: int, before: str, after: str) -> None:
    st.markdown(f'<div class="diff-row"><p class="helper-text"><strong>Change {index}</strong> · BEFORE → AFTER</p></div>', unsafe_allow_html=True)
    a, b = st.columns(2, gap="small")
    with a:
        st.markdown('<div class="diff-side diff-before">', unsafe_allow_html=True)
        st.write(before or "—")
        st.markdown("</div>", unsafe_allow_html=True)
    with b:
        st.markdown('<div class="diff-side diff-after">', unsafe_allow_html=True)
        st.write(after or "—")
        st.markdown("</div>", unsafe_allow_html=True)


def render_cover_letter_workspace(api_key: str, model: str, role_mode: str, jd: str, resume_tex: str) -> None:
    st.markdown('<div class="section-wrap"><p class="section-title">Cover Letter Workspace</p><p class="section-subtitle">Edit, regenerate, approve, and export your tailored letter.</p></div>', unsafe_allow_html=True)
    a, b = st.columns([2.1, 1], gap="small")
    with b:
        st.markdown('<div class="insight-card"><p class="section-title">Why this works</p><ul><li>Aligns directly to JD language.</li><li>Balances credibility and specificity.</li><li>Highlights business impact, not only tools.</li></ul></div>', unsafe_allow_html=True)

    with a:
        st.markdown('<div class="editor-panel">', unsafe_allow_html=True)
        st.session_state.cover_letter_text = st.text_area(
            "Cover Letter",
            value=st.session_state.cover_letter_text,
            key="cover_letter_editor",
            height=430,
            label_visibility="collapsed",
        )
        st.markdown("</div>", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4, gap="small")
    with c1:
        if st.button("Use this", use_container_width=True):
            st.session_state.active_cover_letter = st.session_state.cover_letter_text
            st.session_state.accepted_changes["cover_letter"] = True
            st.success("Marked as active cover letter.")
    with c2:
        if st.button("Regenerate", use_container_width=True):
            if not api_key.strip() or not jd.strip() or not resume_tex.strip():
                st.warning("Need API key + JD + resume to regenerate.")
            else:
                with st.spinner("Generating recruiter-aligned cover letter..."):
                    st.session_state.cover_letter_text = run_cover_letter_generation(api_key, model, jd, resume_tex, role_mode)
                    st.session_state.cover_letter_editor = st.session_state.cover_letter_text
                st.rerun()
    with c3:
        if st.button("Copy-ready", use_container_width=True):
            st.code(st.session_state.cover_letter_text.strip() or "No cover letter text available.", language="text")
    with c4:
        st.download_button(
            "Download",
            data=(st.session_state.cover_letter_text or "").encode("utf-8"),
            file_name="cover_letter.txt",
            mime="text/plain",
            use_container_width=True,
        )


def apply_selected_changes() -> None:
    accepted = st.session_state.accepted_changes
    if st.button("Apply optimized summary", use_container_width=True):
        accepted["summary"] = True
    if st.button("Apply optimized bullets", use_container_width=True):
        accepted["bullets"] = True
    if st.button("Apply optimized skills", use_container_width=True):
        accepted["skills"] = True
    if st.button("Apply cover letter", use_container_width=True):
        accepted["cover_letter"] = True
    if st.button("Apply all", type="primary", use_container_width=True):
        for key in accepted:
            accepted[key] = True


def build_final_latex(original_tex: str, optimized_tex: str) -> str:
    accepted = st.session_state.accepted_changes
    if not any(accepted.values()):
        return optimized_tex

    final_tex = optimized_tex
    if not accepted.get("bullets", False):
        orig_bullets = re.findall(r"\\item\s*.+", original_tex)
        opt_bullets = re.findall(r"\\item\s*.+", final_tex)
        for old, new in zip(opt_bullets, orig_bullets):
            final_tex = final_tex.replace(old, new, 1)

    if not accepted.get("summary", False):
        orig_summary = extract_summary_from_tex(original_tex)
        opt_summary = extract_summary_from_tex(final_tex)
        if orig_summary and opt_summary:
            final_tex = final_tex.replace(opt_summary, orig_summary, 1)

    return final_tex


def render_resume_workspace(parsed: dict[str, Any], final_tex: str, pdf_bytes: bytes | None, pdf_error: str) -> None:
    st.markdown('<div class="section-wrap"><p class="section-title">Optimized Resume Workspace</p><p class="section-subtitle">Review accepted changes, inspect final LaTeX, and validate compile status.</p></div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="insight-card">
          <p class="section-title">Optimized Summary</p>
          <p class="helper-text">{parsed.get('optimized_summary', 'No explicit optimized summary parsed.')}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns([1, 1], gap="small")
    with left:
        st.markdown('<div class="muted-card"><p class="section-title">Acceptance Controls</p><p class="section-subtitle">Selections persist in session state.</p></div>', unsafe_allow_html=True)
        apply_selected_changes()
        st.caption(f"Accepted changes: {st.session_state.accepted_changes}")
    with right:
        status = "Compiled successfully" if pdf_bytes and not pdf_error else "PDF unavailable (see debug logs)"
        st.markdown(f'<div class="status-strip"><span class="helper-text">Compile status</span><span class="verdict-pill {"verdict-strong" if pdf_bytes and not pdf_error else "verdict-borderline"}">{status}</span></div>', unsafe_allow_html=True)

    st.markdown('<div class="code-wrap"><p class="section-title">Final LaTeX</p></div>', unsafe_allow_html=True)
    st.code(final_tex, language="latex")

    st.markdown("#### PDF Preview")
    if pdf_bytes:
        b64 = base64.b64encode(pdf_bytes).decode("utf-8")
        st.markdown(f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="780" type="application/pdf" style="border-radius:12px;border:1px solid rgba(147,168,213,.3);"></iframe>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="empty-state">PDF preview unavailable. You can still download the optimized .tex file.</div>', unsafe_allow_html=True)


def render_export_center(report: str, final_tex: str, pdf_bytes: bytes | None, cover_letter: str) -> None:
    st.markdown('<div class="section-wrap"><p class="section-title">Export Center</p><p class="section-subtitle">Download final artifacts and handoff-ready outputs.</p></div>', unsafe_allow_html=True)
    cards = st.columns(4, gap="small")

    with cards[0]:
        st.markdown('<div class="asset-card"><p class="section-title">ATS Report</p><p class="helper-text">Markdown report with ATS and recruiter insights.</p><p class="helper-text">Status: Ready</p></div>', unsafe_allow_html=True)
        st.download_button("Download .md", data=report.encode("utf-8"), file_name="ats_report.md", mime="text/markdown", use_container_width=True)
    with cards[1]:
        st.markdown('<div class="asset-card"><p class="section-title">Resume .tex</p><p class="helper-text">Accepted optimized LaTeX source.</p><p class="helper-text">Status: Ready</p></div>', unsafe_allow_html=True)
        st.download_button("Download .tex", data=final_tex.encode("utf-8"), file_name="optimized_resume.tex", mime="text/plain", use_container_width=True)
    with cards[2]:
        status = "Ready" if pdf_bytes else "Unavailable"
        st.markdown(f'<div class="asset-card"><p class="section-title">Resume .pdf</p><p class="helper-text">Compiled export from two-pass pdflatex.</p><p class="helper-text">Status: {status}</p></div>', unsafe_allow_html=True)
        if pdf_bytes:
            st.download_button("Download .pdf", data=pdf_bytes, file_name="optimized_resume.pdf", mime="application/pdf", use_container_width=True)
        else:
            st.button("PDF unavailable", disabled=True, use_container_width=True)
    with cards[3]:
        st.markdown('<div class="asset-card"><p class="section-title">Cover Letter</p><p class="helper-text">Plain-text tailored cover letter.</p><p class="helper-text">Status: Ready</p></div>', unsafe_allow_html=True)
        st.download_button("Download .txt", data=cover_letter.encode("utf-8"), file_name="cover_letter.txt", mime="text/plain", use_container_width=True)


def render_debug_panel(raw_output: str, report: str, pdf_error: str, parsing_issue: str) -> None:
    with st.expander("Debug / Raw Output", expanded=False):
        if parsing_issue:
            st.warning(parsing_issue)
        st.markdown("#### Parsed Report")
        st.code(report or "No parsed report")
        if pdf_error:
            st.markdown("#### PDF Compile Logs")
            st.text(pdf_error)
        st.markdown("#### Raw Model Output")
        st.code(raw_output or "No output")


def init_state() -> None:
    defaults: dict[str, Any] = {
        "api_key": os.getenv("OPENAI_API_KEY", ""),
        "model": DEFAULT_MODEL,
        "role_mode": ROLE_MODES[0],
        "job_description": "",
        "raw_output": "",
        "report": "",
        "optimized_tex": "",
        "final_tex": "",
        "pdf_bytes": load_cached_pdf(),
        "pdf_error": "",
        "parsed": {},
        "metrics": {},
        "recruiter": {},
        "strength_scores": {},
        "cover_letter_text": "",
        "active_cover_letter": "",
        "parsing_issue": "",
        "last_resume_source": "",
        "original_resume_tex": "",
        "uploaded_resume_name": "",
        "uploaded_resume_content": "",
        "use_base_if_missing": True,
        "show_resume_preview": False,
        "accepted_changes": {"summary": False, "bullets": False, "skills": False, "cover_letter": False},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def run_pipeline(api_key: str, model: str, jd: str, resume_tex: str, role_mode: str, resume_source: str) -> None:
    with st.status("Running analysis workflow...", expanded=True) as status:
        st.write("Parsing JD")
        st.write("Optimizing resume")
        raw_output, report, optimized_tex = run_agent(api_key, model, jd, resume_tex, role_mode)
        st.write("Generating recruiter evaluation")

        parsing_issue = ""
        if not report.strip():
            report = raw_output
            parsing_issue = "ATS report parsing fallback triggered: report section not explicitly detected."
        if not optimized_tex.strip():
            raise ValueError("Could not detect optimized LaTeX section in model output.")

        parsed = parse_ats_report(report)
        fallback = infer_lists_from_jd(jd)
        parsed["technical_skills"] = parsed.get("technical_skills") or fallback["technical_skills"]
        parsed["soft_skills"] = parsed.get("soft_skills") or fallback["soft_skills"]
        parsed["keywords"] = parsed.get("keywords") or fallback["keywords"]

        metrics = infer_metrics(parsed, report)
        recruiter = parse_recruiter_feedback(report)
        strength_scores = parse_strength_scores(report, metrics)
        cover_letter = parse_cover_letter(report)
        if not cover_letter:
            cover_letter = run_cover_letter_generation(api_key, model, jd, resume_tex, role_mode)

        final_tex = build_final_latex(resume_tex, optimized_tex)
        st.write("Compiling PDF")
        pdf_bytes, pdf_error = compile_pdf(final_tex)

        (OUTPUTS_DIR / "ats_report.md").write_text(report, encoding="utf-8")
        (OUTPUTS_DIR / "optimized_resume.tex").write_text(final_tex, encoding="utf-8")
        if pdf_bytes:
            OUTPUT_PDF_PATH.write_bytes(pdf_bytes)
        else:
            cached = load_cached_pdf()
            if cached:
                pdf_bytes = cached
                pdf_error = (pdf_error + "\n\n" if pdf_error else "") + "Using last successful PDF from outputs/optimized_resume.pdf."

        st.session_state.raw_output = raw_output
        st.session_state.report = report
        st.session_state.optimized_tex = optimized_tex
        st.session_state.final_tex = final_tex
        st.session_state.pdf_bytes = pdf_bytes
        st.session_state.pdf_error = pdf_error or ""
        st.session_state.parsed = parsed
        st.session_state.metrics = metrics
        st.session_state.recruiter = recruiter
        st.session_state.strength_scores = strength_scores
        st.session_state.cover_letter_text = cover_letter
        st.session_state.active_cover_letter = cover_letter
        st.session_state.parsing_issue = parsing_issue
        st.session_state.last_resume_source = resume_source
        st.session_state.original_resume_tex = resume_tex

        status.update(label="Analysis complete", state="complete")


def main() -> None:
    inject_css()
    init_state()
    render_top_shell()
    render_hero()

    api_key, model, role_mode, resume_tex, _, show_resume_preview, resume_source = render_sidebar()

    st.markdown("## Top Control Bar")
    st.markdown('<div class="section-wrap"><p class="section-title">Job Description Input</p><p class="section-subtitle">Paste complete requirements, responsibilities, and tech stack for highest-quality optimization.</p></div>', unsafe_allow_html=True)
    st.session_state.job_description = st.text_area(
        "Job Description",
        value=st.session_state.job_description,
        label_visibility="collapsed",
        height=280,
        placeholder="Paste job description text...",
    )

    meta1, meta2, meta3 = st.columns(3, gap="small")
    meta1.markdown(f"<div class='muted-card'><p class='helper-text'><strong>Model</strong><br>{model}</p></div>", unsafe_allow_html=True)
    meta2.markdown(f"<div class='muted-card'><p class='helper-text'><strong>Role mode</strong><br>{role_mode}</p></div>", unsafe_allow_html=True)
    meta3.markdown(f"<div class='muted-card'><p class='helper-text'><strong>Resume source</strong><br>{resume_source}</p></div>", unsafe_allow_html=True)

    if show_resume_preview:
        with st.expander("Resume Preview", expanded=False):
            st.code(resume_tex[:8000] if resume_tex else "No resume loaded.", language="latex")

    if st.button("Generate ATS + Recruiter + Resume Optimization", type="primary", use_container_width=True):
        if not api_key.strip():
            st.error("Missing API key. Please provide your OpenAI API key in the sidebar.")
            st.stop()
        if not st.session_state.job_description.strip():
            st.error("Missing job description.")
            st.stop()
        if not resume_tex.strip():
            st.error("Missing resume source. Upload `.tex` or enable bundled fallback.")
            st.stop()

        try:
            run_pipeline(api_key, model, st.session_state.job_description, resume_tex, role_mode, resume_source)
            st.success("Optimization complete. Review sections below.")
        except Exception as exc:
            st.exception(exc)
            st.stop()

    if st.session_state.optimized_tex:
        render_kpi_section(st.session_state.metrics)
        render_recruiter_panel(st.session_state.recruiter)
        render_strength_section(st.session_state.strength_scores)

        st.markdown("## Analysis Workspace")
        tabs = st.tabs(["JD Breakdown", "Skill Gap", "Diff Viewer", "Cover Letter", "Optimized Resume", "Downloads", "Debug"])
        with tabs[0]:
            render_jd_breakdown(st.session_state.parsed)
        with tabs[1]:
            render_skill_gap(st.session_state.parsed)
        with tabs[2]:
            render_diff_viewer(st.session_state.original_resume_tex, st.session_state.optimized_tex, st.session_state.parsed)
        with tabs[3]:
            render_cover_letter_workspace(api_key, model, role_mode, st.session_state.job_description, resume_tex)
        with tabs[4]:
            st.session_state.final_tex = build_final_latex(st.session_state.original_resume_tex, st.session_state.optimized_tex)
            st.session_state.pdf_bytes, st.session_state.pdf_error = compile_pdf(st.session_state.final_tex)
            render_resume_workspace(st.session_state.parsed, st.session_state.final_tex, st.session_state.pdf_bytes, st.session_state.pdf_error)
        with tabs[5]:
            render_export_center(st.session_state.report, st.session_state.final_tex, st.session_state.pdf_bytes, st.session_state.active_cover_letter)
        with tabs[6]:
            render_debug_panel(st.session_state.raw_output, st.session_state.report, st.session_state.pdf_error, st.session_state.parsing_issue)


if __name__ == "__main__":
    main()
