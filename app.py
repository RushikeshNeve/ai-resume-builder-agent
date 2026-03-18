from __future__ import annotations

import base64
import os
import re
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
            --bg-main: #05070d;
            --bg-elev: #0b1322;
            --bg-card: rgba(13, 22, 39, 0.84);
            --bg-card-2: rgba(19, 30, 50, 0.9);
            --text-main: #ecf2ff;
            --text-subtle: #9eb0cb;
            --line: rgba(168, 189, 255, 0.22);
            --line-strong: rgba(168, 189, 255, 0.35);
            --accent: #7c8cff;
            --accent-2: #56d7ff;
            --danger: #ff6f7d;
            --warning: #ffc96e;
            --success: #50d890;
            --shadow: 0 18px 38px rgba(0, 0, 0, 0.38);
          }

          .stApp {
            background:
              radial-gradient(circle at 7% 2%, rgba(56, 80, 164, 0.28), transparent 32%),
              radial-gradient(circle at 90% 5%, rgba(69, 173, 255, 0.18), transparent 34%),
              linear-gradient(180deg, #05070d 0%, #0b1321 52%, #05070d 100%);
            color: var(--text-main);
          }

          .block-container {
            max-width: 1450px;
            padding-top: 1.35rem;
            padding-bottom: 2.4rem;
          }

          [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #060d19 0%, #0b1425 100%);
            border-right: 1px solid rgba(142, 169, 235, 0.2);
          }

          [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
          [data-testid="stSidebar"] label { color: #dbe6ff; }

          .hero-banner {
            position: relative;
            overflow: hidden;
            padding: 1.85rem 2.2rem;
            margin-bottom: 1rem;
            border: 1px solid var(--line-strong);
            border-radius: 22px;
            background:
              radial-gradient(circle at 85% 15%, rgba(91, 145, 255, 0.35), transparent 39%),
              linear-gradient(135deg, rgba(26, 40, 70, 0.95) 0%, rgba(33, 60, 122, 0.9) 47%, rgba(17, 135, 175, 0.88) 100%);
            box-shadow: var(--shadow);
          }

          .hero-title { margin: 0; font-size: 2.1rem; color: #f4f8ff; letter-spacing: -0.02em; }
          .app-subtitle { margin-top: .45rem; color: #d6e3ff; font-size: 1.02rem; margin-bottom: 0; }
          .badge-row { display: flex; flex-wrap: wrap; gap: .45rem; margin-top: .95rem; }
          .feature-badge {
            border-radius: 999px;
            padding: .32rem .8rem;
            background: rgba(255, 255, 255, 0.11);
            border: 1px solid rgba(255, 255, 255, 0.26);
            color: #f4f9ff;
            font-size: .78rem;
          }

          .glass-card, .section-card, .status-card, .download-card, .summary-card, .code-card,
          .metric-card, .diff-card, .before-card, .after-card, .recruiter-card, .radar-card, .cover-letter-card {
            border-radius: 18px;
            border: 1px solid var(--line);
            box-shadow: var(--shadow);
            backdrop-filter: blur(6px);
          }

          .glass-card, .section-card, .status-card, .summary-card, .download-card,
          .code-card, .diff-card, .before-card, .after-card, .recruiter-card, .radar-card, .cover-letter-card {
            background: linear-gradient(160deg, var(--bg-card) 0%, var(--bg-card-2) 100%);
            padding: 1rem 1.05rem;
            margin-bottom: .9rem;
          }

          .card-title { margin: 0 0 .55rem 0; color: #f2f7ff; font-size: 1rem; }
          .card-subtitle { color: var(--text-subtle); margin: 0; font-size: .86rem; }

          .metric-card {
            min-height: 116px;
            padding: .9rem .98rem;
            background: linear-gradient(165deg, rgba(19, 32, 58, 0.95), rgba(29, 49, 88, 0.88));
          }
          .metric-value { margin-top: .25rem; font-size: 1.84rem; font-weight: 700; color: #fff; }
          .metric-label { margin: 0; color: #cfddff; font-size: .8rem; font-weight: 600; text-transform: uppercase; letter-spacing: .06em; }
          .metric-helper { margin-top: .24rem; color: #9db3d9; font-size: .74rem; }

          .chip {
            display: inline-block;
            border: 1px solid rgba(156, 186, 245, 0.42);
            color: #e8f1ff;
            background: rgba(71, 97, 152, 0.35);
            margin: .18rem .26rem .2rem 0;
            border-radius: 999px;
            padding: .24rem .64rem;
            font-size: .77rem;
          }
          .chip-danger { background: rgba(221, 94, 113, 0.2); border-color: rgba(255, 128, 148, 0.55); }
          .chip-warning { background: rgba(244, 177, 70, 0.17); border-color: rgba(255, 206, 126, 0.5); }
          .chip-success { background: rgba(65, 175, 109, 0.2); border-color: rgba(109, 232, 159, 0.54); }

          .verdict-badge {
            display: inline-block;
            border-radius: 999px;
            padding: .32rem .76rem;
            font-size: .79rem;
            font-weight: 700;
            letter-spacing: .03em;
          }
          .verdict-reject { color: #ffdce2; background: rgba(224, 75, 104, 0.25); border: 1px solid rgba(255, 128, 148, 0.6); }
          .verdict-borderline { color: #ffecc8; background: rgba(229, 156, 43, 0.23); border: 1px solid rgba(255, 199, 117, 0.55); }
          .verdict-shortlist { color: #d7f0ff; background: rgba(69, 158, 255, 0.24); border: 1px solid rgba(112, 194, 255, 0.6); }
          .verdict-strong { color: #d5ffe9; background: rgba(65, 175, 109, 0.24); border: 1px solid rgba(109, 232, 159, 0.6); }

          .recruiter-card.reject { border-color: rgba(255, 128, 148, 0.56); }
          .recruiter-card.borderline { border-color: rgba(255, 206, 126, 0.55); }
          .recruiter-card.shortlist, .recruiter-card.stronghire { border-color: rgba(110, 221, 175, 0.58); }

          .diff-label { font-size: .78rem; font-weight: 700; letter-spacing: .05em; margin-bottom: .35rem; }
          .before-card { border-color: rgba(255, 199, 117, 0.42); }
          .after-card { border-color: rgba(109, 232, 159, 0.42); }

          .download-card { min-height: 158px; }
          .status-card.success { border-color: rgba(80, 216, 144, 0.55); }
          .status-card.error { border-color: rgba(255, 111, 125, 0.58); }
          .status-card.warning { border-color: rgba(255, 196, 111, 0.58); }

          .pdf-frame {
            border-radius: 14px;
            border: 1px solid rgba(157, 186, 244, 0.28);
            overflow: hidden;
            box-shadow: inset 0 0 0 1px rgba(157, 186, 244, 0.1);
          }

          [data-testid="stTabs"] [data-baseweb="tab-list"] {
            gap: .26rem;
            background: rgba(9, 15, 26, 0.72);
            padding: .3rem;
            border: 1px solid rgba(159, 186, 244, 0.22);
            border-radius: 12px;
          }
          [data-testid="stTabs"] [data-baseweb="tab"] {
            color: #c3d5fa;
            border-radius: 9px;
            border: 1px solid transparent;
            padding-top: .42rem; padding-bottom: .42rem;
          }
          [data-testid="stTabs"] [aria-selected="true"] {
            background: rgba(54, 82, 140, 0.58) !important;
            color: #f2f7ff !important;
            border-color: rgba(159, 186, 244, 0.35) !important;
          }

          .stDownloadButton > button, .stButton > button {
            border-radius: 10px;
            border: 1px solid rgba(140, 172, 243, 0.42);
            background: linear-gradient(180deg, rgba(58, 87, 146, 0.95), rgba(40, 68, 121, 0.96));
            color: #f0f6ff;
            font-weight: 600;
          }

          .stTextArea textarea, .stTextInput input,
          .stSelectbox [data-baseweb="select"] > div,
          .stFileUploader > div {
            background: rgba(7, 13, 24, 0.75) !important;
            color: #e4efff !important;
            border-radius: 10px !important;
            border-color: rgba(130, 161, 226, 0.35) !important;
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
    summary = extract_section(text, [r"Professional\s*Summary", r"Summary", r"Rewritten\s*Summary", r"Optimized\s*Summary"])
    return summary.strip()


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
    block = extract_section(
        report,
        [r"Recruiter\s*Simulation(?:\s*Engine)?", r"Recruiter\s*Review", r"Hiring\s*Manager\s*Assessment"],
    )
    target = block or report

    verdict_match = re.search(r"verdict\s*[:\-]\s*(Reject|Borderline|Shortlist|Strong\s*Hire)", target, flags=re.IGNORECASE)
    confidence_match = re.search(r"confidence\s*(?:score)?\s*[:\-]\s*(\d{1,3})", target, flags=re.IGNORECASE)
    reasons = parse_marked_list(extract_section(target, [r"Reasons", r"Why\s*this\s*verdict"]))
    working = parse_marked_list(extract_section(target, [r"What\s*is\s*working\s*well", r"Strengths", r"Working\s*well"]))
    fixing = parse_marked_list(extract_section(target, [r"What\s*needs\s*fixing", r"Needs\s*fixing", r"Risks", r"Concerns"]))
    recs = parse_marked_list(extract_section(target, [r"Top\s*Recommendations", r"Recommendations", r"Next\s*actions"]))

    verdict = verdict_match.group(1).replace("  ", " ").title() if verdict_match else "Borderline"
    verdict = "Strong Hire" if verdict.lower().replace(" ", "") == "stronghire" else verdict
    confidence = int(confidence_match.group(1)) if confidence_match else 68

    if not reasons and target:
        reasons = parse_marked_list(extract_section(target, [r"Rationale"]))
    return {
        "verdict": verdict,
        "confidence": max(0, min(100, confidence)),
        "reasons": reasons,
        "working": working,
        "fixing": fixing,
        "recommendations": recs,
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
        pattern = rf"{re.escape(key)}\s*[:\-]\s*(\d{{1,3}})"
        match = re.search(pattern, search_text, flags=re.IGNORECASE)
        if match:
            base[key] = int(match.group(1))

    technical_count = len(metrics.get("technical_skills", []))
    weak_count = len(metrics.get("weak_skills", []))
    missing_count = len(metrics.get("missing_skills", []))
    keyword_match = metrics.get("keyword_match", 65)

    if base["Technical Depth"] is None:
        base["Technical Depth"] = int(max(35, min(95, 55 + technical_count * 3 - weak_count * 2)))
    if base["Impact"] is None:
        impact_match = re.search(r"\b(led|scaled|increased|improved|reduced|delivered|launched|optimized)\b", report, flags=re.IGNORECASE)
        base["Impact"] = 76 if impact_match else 64
    if base["Keywords"] is None:
        base["Keywords"] = int(max(30, min(98, keyword_match)))
    if base["Clarity"] is None:
        summary_len = len(parse_summary(report).split())
        base["Clarity"] = 82 if summary_len >= 30 else 70
    if base["ATS Score"] is None:
        base["ATS Score"] = 100 - min(45, missing_count * 4)

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

    technical = parse_marked_list(
        extract_section(
            report,
            [
                r"Top\s*10\s*Technical\s*Skills",
                r"Technical\s*Skills",
                r"Core\s*Technical\s*Skills",
                r"Required\s*Technical\s*Skills",
            ],
        )
    )
    soft = parse_marked_list(
        extract_section(
            report,
            [
                r"Top\s*5\s*Soft\s*Skills",
                r"Soft\s*Skills",
                r"Behavioral\s*Skills",
                r"Collaboration\s*Skills",
            ],
        )
    )
    responsibilities = parse_marked_list(extract_section(report, [r"Key\s*Responsibilities", r"Responsibilities"]))
    keywords = parse_marked_list(extract_section(report, [r"ATS\s*Keywords", r"Keywords", r"Keyword\s*Targets"]))

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


def infer_lists_from_jd(jd: str) -> dict[str, list[str]]:
    if not jd.strip():
        return {"technical_skills": [], "soft_skills": [], "keywords": []}

    lower = jd.lower()
    tech_candidates = [
        "python",
        "java",
        "go",
        "node",
        "typescript",
        "javascript",
        "react",
        "sql",
        "postgres",
        "mysql",
        "redis",
        "kafka",
        "aws",
        "gcp",
        "azure",
        "docker",
        "kubernetes",
        "airflow",
        "spark",
        "llm",
        "rag",
        "etl",
        "api",
        "microservices",
    ]
    soft_candidates = [
        "communication",
        "collaboration",
        "leadership",
        "mentoring",
        "ownership",
        "stakeholder",
        "problem solving",
        "adaptability",
        "teamwork",
    ]

    technical = [s for s in tech_candidates if re.search(rf"\b{re.escape(s)}\b", lower)]
    soft = [s.title() for s in soft_candidates if re.search(rf"\b{re.escape(s)}\b", lower)]

    keyword_pattern = re.compile(r"\b[A-Za-z][A-Za-z0-9+\-#/]{2,}\b")
    raw_tokens = keyword_pattern.findall(jd)
    stop_words = {
        "the",
        "and",
        "for",
        "with",
        "you",
        "our",
        "will",
        "this",
        "that",
        "are",
        "from",
        "have",
        "your",
        "years",
        "experience",
        "required",
        "preferred",
        "ability",
    }
    keywords: list[str] = []
    for token in raw_tokens:
        lower_token = token.lower()
        if lower_token in stop_words:
            continue
        if lower_token not in [k.lower() for k in keywords]:
            keywords.append(token)
        if len(keywords) >= 20:
            break

    return {
        "technical_skills": technical[:12],
        "soft_skills": soft[:8],
        "keywords": keywords,
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
        total = max(1, len(parsed.get("technical_skills", [])) + len(parsed.get("soft_skills", [])))
        weak = parsed.get("weak_skills", [])
        missing = parsed.get("missing_skills", [])
        impact = min(total, len(missing) + max(0, len(weak) // 2))
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
    pattern = r"\\section\*?\{(?:Summary|Professional\s*Summary)\}(.*?)(?=\\section\*?\{|\\end\{document\})"
    match = re.search(pattern, tex_content, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    summary = re.sub(r"\\[a-zA-Z]+(?:\[[^\]]*\])?(?:\{[^}]*\})?", "", match.group(1))
    return re.sub(r"\s+", " ", summary).strip()


def compute_diff_pairs(before: list[str], after: list[str]) -> list[tuple[str, str]]:
    size = max(len(before), len(after))
    pairs: list[tuple[str, str]] = []
    for idx in range(size):
        b = before[idx] if idx < len(before) else ""
        a = after[idx] if idx < len(after) else ""
        pairs.append((b, a))
    return pairs


def compile_pdf(tex_content: str) -> tuple[bytes | None, str | None]:
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            tex_path = tmp_path / "optimized_resume.tex"
            tex_path.write_text(tex_content, encoding="utf-8")
            cmd = ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex_path.name]
            logs: list[str] = []
            for run_number in (1, 2):
                result = subprocess.run(cmd, cwd=tmp_path, capture_output=True, text=True, timeout=90)
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
    prompt = user_prompt + "\n" + extension

    response = client.chat.completions.create(
        model=model,
        temperature=0.25,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
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
            {
                "role": "system",
                "content": "You are an expert career coach and recruiter. Produce concise, high-impact, personalized cover letters.",
            },
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


def render_hero() -> None:
    st.markdown(
        """
        <div class="hero-banner">
          <h1 class="hero-title">Resume Optimizer Agent</h1>
          <p class="app-subtitle">Premium AI Career Copilot for recruiter simulation, ATS optimization, role-tailored resume rewrites, and export-ready outputs.</p>
          <div class="badge-row">
            <span class="feature-badge">ATS Score</span>
            <span class="feature-badge">Recruiter Review</span>
            <span class="feature-badge">Diff Viewer</span>
            <span class="feature-badge">Cover Letter</span>
            <span class="feature-badge">PDF Export</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander("How it works", expanded=False):
        st.markdown(
            """
            1. Choose role mode and model in sidebar.
            2. Paste a Job Description.
            3. Upload a `.tex` resume or use bundled `base_resume.tex`.
            4. Generate ATS report, recruiter simulation, optimized LaTeX, cover letter, and radar insights.
            5. Selectively apply improvements, preview PDF, and download final artifacts.
            """
        )


def render_sidebar() -> tuple[str, str, str, bytes | None, bool, bool, str]:
    with st.sidebar:
        st.markdown("### ⚙️ Workspace Controls")
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        api_key = st.text_input("OpenAI API Key", type="password", value=os.getenv("OPENAI_API_KEY", ""))
        model = st.selectbox("Model", options=MODEL_OPTIONS, index=MODEL_OPTIONS.index(DEFAULT_MODEL))
        role_mode = st.radio("Role-specific optimization mode", ROLE_MODES, index=0, horizontal=False)
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

        ready = bool(api_key.strip() and resume_tex.strip())
        readiness = "Ready" if ready else "Not ready"
        st.markdown(
            f"""
            <div class="status-card {'success' if ready else 'warning'}">
              <p class="card-title">App status</p>
              <p class="card-subtitle"><strong>Active role mode:</strong> {role_mode}</p>
              <p class="card-subtitle"><strong>Resume source:</strong> {resume_icon} {resume_source}</p>
              <p class="card-subtitle"><strong>Selected model:</strong> {model}</p>
              <p class="card-subtitle"><strong>Status:</strong> {readiness}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return api_key, model, role_mode, uploaded_tex, use_base_if_missing, show_resume_preview, resume_source


def render_input_section(job_description: str, resume_source: str, resume_tex: str, role_mode: str) -> str:
    st.markdown("## Input Workspace")
    left, right = st.columns([1.65, 1], gap="large")
    with left:
        st.markdown(
            """
            <div class="section-card">
              <p class="card-title">Job Description (Required)</p>
              <p class="card-subtitle">Paste full JD context (requirements, stack, responsibilities, and priorities).</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        jd_value = st.text_area(
            "JD",
            value=job_description,
            label_visibility="collapsed",
            height=350,
            placeholder="Paste job description, requirements, tools, skills, and responsibilities...",
        )

    with right:
        st.markdown(
            f"""
            <div class="status-card">
              <p class="card-title">Resume Source Card</p>
              <p class="card-subtitle"><strong>Source:</strong> {resume_source}</p>
              <p class="card-subtitle"><strong>Role mode:</strong> {role_mode}</p>
              <p class="card-subtitle"><strong>Resume size:</strong> {len(resume_tex)} chars</p>
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
        ("ATS Score", f"{metrics['ats_score']}/100", "Model + parser score", "ats_score"),
        ("Keyword Match %", f"{metrics['keyword_match']}%", "Coverage of extracted ATS keywords", "keyword_match"),
        ("Skills Match %", f"{metrics['skills_match']}%", "Alignment across technical + soft skills", "skills_match"),
        ("Missing Skills Count", str(metrics["missing_skills_count"]), "Critical requirements not represented", "missing_skills_count"),
    ]
    cols = st.columns(4)
    for idx, (label, value, helper, key) in enumerate(labels):
        estimate = metrics.get("estimate_flags", {}).get(key, False)
        cols[idx].markdown(
            f"""
            <div class="metric-card">
              <p class="metric-label">{label}</p>
              <div class="metric-value">{value}</div>
              <div class="metric-helper">{helper}{' • estimated' if estimate else ''}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_chip_group(items: list[str], variant: str = "") -> None:
    if not items:
        st.caption("No items detected")
        return
    klass = "chip" if not variant else f"chip {variant}"
    html = "".join(f'<span class="{klass}">{i.replace("<", "&lt;").replace(">", "&gt;")}</span>' for i in items)
    st.markdown(html, unsafe_allow_html=True)


def render_recruiter_card(data: dict[str, Any]) -> None:
    verdict = data.get("verdict", "Borderline")
    verdict_key = verdict.lower().replace(" ", "")
    verdict_class_map = {
        "reject": ("reject", "verdict-reject"),
        "borderline": ("borderline", "verdict-borderline"),
        "shortlist": ("shortlist", "verdict-shortlist"),
        "stronghire": ("stronghire", "verdict-strong"),
    }
    card_class, badge_class = verdict_class_map.get(verdict_key, ("borderline", "verdict-borderline"))
    st.markdown(
        f"""
        <div class="recruiter-card {card_class}">
          <p class="card-title">Recruiter Simulation Engine</p>
          <span class="verdict-badge {badge_class}">{verdict.upper()}</span>
          <p class="card-subtitle" style="margin-top:.45rem;"><strong>Confidence:</strong> {data.get('confidence', 0)}/100</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3, gap="medium")
    with c1:
        st.markdown('<div class="section-card"><p class="card-title">Reasons for Verdict</p>', unsafe_allow_html=True)
        for item in data.get("reasons", []) or ["No explicit reasons were parsed."]:
            st.markdown(f"- {item}")
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="section-card"><p class="card-title">What is Working Well</p>', unsafe_allow_html=True)
        for item in data.get("working", []) or ["No strengths were explicitly listed."]:
            st.markdown(f"- {item}")
        st.markdown("</div>", unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="section-card"><p class="card-title">Needs Fixing + Top Recommendations</p>', unsafe_allow_html=True)
        combined = (data.get("fixing", []) or []) + (data.get("recommendations", []) or [])
        for item in combined or ["No explicit fixes/recommendations were parsed."]:
            st.markdown(f"- {item}")
        st.markdown("</div>", unsafe_allow_html=True)


def render_jd_breakdown(parsed: dict[str, Any]) -> None:
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown('<div class="section-card"><p class="card-title">Technical Skills</p>', unsafe_allow_html=True)
        render_chip_group(parsed.get("technical_skills", []))
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown('<div class="section-card"><p class="card-title">Responsibilities</p>', unsafe_allow_html=True)
        for item in parsed.get("responsibilities", []) or ["No responsibilities parsed."]:
            st.markdown(f"- {item}")
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
        st.markdown('<div class="section-card"><p class="card-title">Weakly Represented Skills</p>', unsafe_allow_html=True)
        render_chip_group(parsed.get("weak_skills", []), "chip-warning")
        st.markdown("</div>", unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="section-card"><p class="card-title">Strong Matches</p>', unsafe_allow_html=True)
        render_chip_group(parsed.get("strong_skills", []), "chip-success")
        st.markdown("</div>", unsafe_allow_html=True)


def render_diff_tab(original_tex: str, optimized_tex: str, parsed: dict[str, Any]) -> None:
    original_summary = extract_summary_from_tex(original_tex)
    optimized_summary = parsed.get("optimized_summary", "") or extract_summary_from_tex(optimized_tex)
    before_bullets = extract_latex_bullets(original_tex)
    after_bullets = extract_latex_bullets(optimized_tex) or parsed.get("optimized_bullets", [])

    st.markdown('<div class="diff-card"><p class="card-title">Summary Diff (Before vs After)</p></div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown('<div class="before-card"><p class="diff-label">BEFORE</p>', unsafe_allow_html=True)
        st.write(original_summary or "No original summary extracted.")
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="after-card"><p class="diff-label">AFTER</p>', unsafe_allow_html=True)
        st.write(optimized_summary or "No optimized summary extracted.")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="diff-card"><p class="card-title">Bullet Diff (Before vs After)</p></div>', unsafe_allow_html=True)
    pairs = compute_diff_pairs(before_bullets, after_bullets)
    if not pairs:
        st.caption("No bullet pairs were parsed. Showing grouped highlights instead.")
        c3, c4 = st.columns(2, gap="large")
        with c3:
            st.markdown('<div class="before-card"><p class="diff-label">ORIGINAL HIGHLIGHTS</p>', unsafe_allow_html=True)
            for b in before_bullets or ["No original bullets extracted."]:
                st.markdown(f"- {b}")
            st.markdown("</div>", unsafe_allow_html=True)
        with c4:
            st.markdown('<div class="after-card"><p class="diff-label">OPTIMIZED HIGHLIGHTS</p>', unsafe_allow_html=True)
            for b in after_bullets or ["No optimized bullets extracted."]:
                st.markdown(f"- {b}")
            st.markdown("</div>", unsafe_allow_html=True)
        return

    for before, after in pairs[:12]:
        d1, d2 = st.columns(2, gap="large")
        with d1:
            st.markdown('<div class="before-card"><p class="diff-label">BEFORE</p>', unsafe_allow_html=True)
            st.write(before or "—")
            st.markdown("</div>", unsafe_allow_html=True)
        with d2:
            st.markdown('<div class="after-card"><p class="diff-label">AFTER</p>', unsafe_allow_html=True)
            st.write(after or "—")
            st.markdown("</div>", unsafe_allow_html=True)


def render_cover_letter_tab(api_key: str, model: str, role_mode: str, jd: str, resume_tex: str) -> None:
    st.markdown('<div class="cover-letter-card"><p class="card-title">JD-Aligned Cover Letter Generator</p><p class="card-subtitle">Edit, accept, regenerate, and export cover letter text.</p></div>', unsafe_allow_html=True)

    letter = st.text_area(
        "Cover Letter",
        value=st.session_state.cover_letter_text,
        height=420,
        key="cover_letter_editor",
        label_visibility="collapsed",
    )
    st.session_state.cover_letter_text = letter

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Use this", use_container_width=True, key="cover_use_this"):
            st.session_state.active_cover_letter = st.session_state.cover_letter_text
            st.session_state.accepted_changes["cover_letter"] = True
            st.success("Stored as active cover letter.")
    with c2:
        if st.button("Regenerate", use_container_width=True, key="cover_regenerate"):
            if not api_key.strip() or not jd.strip() or not resume_tex.strip():
                st.warning("Need API key + JD + resume source to regenerate cover letter.")
            else:
                with st.spinner("Regenerating cover letter..."):
                    try:
                        new_letter = run_cover_letter_generation(api_key, model, jd, resume_tex, role_mode)
                        st.session_state.cover_letter_text = new_letter
                        st.session_state.cover_letter_editor = new_letter
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Cover letter regeneration failed: {exc}")
    with c3:
        if st.button("Copy-ready", use_container_width=True, key="cover_copy_ready"):
            st.code(st.session_state.cover_letter_text.strip() or "No cover letter text available.", language="text")

    st.download_button(
        "Download cover_letter.txt",
        data=(st.session_state.cover_letter_text or "").encode("utf-8"),
        file_name="cover_letter.txt",
        mime="text/plain",
        use_container_width=True,
        key="cover_tab_download_txt",
    )
    st.download_button(
        "Download cover_letter.md",
        data=(st.session_state.cover_letter_text or "").encode("utf-8"),
        file_name="cover_letter.md",
        mime="text/markdown",
        use_container_width=True,
        key="cover_tab_download_md",
    )


def render_radar_chart(scores: dict[str, int]) -> None:
    labels = list(scores.keys())
    values = [scores[label] for label in labels]
    values += values[:1]
    angles = [n / float(len(labels)) * 2 * 3.1415926 for n in range(len(labels))]
    angles += angles[:1]

    fig = plt.figure(figsize=(5.5, 5.2), facecolor="#0b1322")
    ax = fig.add_subplot(111, polar=True)
    ax.set_facecolor("#101a2f")
    ax.plot(angles, values, linewidth=2.2, color="#56d7ff")
    ax.fill(angles, values, color="#56d7ff", alpha=0.24)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, color="#dbe6ff", fontsize=9)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"], color="#9eb0cb", fontsize=8)
    ax.set_ylim(0, 100)
    ax.grid(color="#314666", alpha=0.5)
    ax.spines["polar"].set_color("#38527b")
    st.markdown('<div class="radar-card"><p class="card-title">Resume Strength Radar Chart</p></div>', unsafe_allow_html=True)
    st.pyplot(fig, use_container_width=False)
    plt.close(fig)


def apply_selected_changes() -> None:
    accepted = st.session_state.accepted_changes
    if st.button("Apply optimized summary", use_container_width=True, key="apply_summary"):
        accepted["summary"] = True
    if st.button("Apply optimized bullets", use_container_width=True, key="apply_bullets"):
        accepted["bullets"] = True
    if st.button("Apply optimized skills", use_container_width=True, key="apply_skills"):
        accepted["skills"] = True
    if st.button("Apply cover letter", use_container_width=True, key="apply_cover_letter"):
        accepted["cover_letter"] = True
    if st.button("Apply all changes", use_container_width=True, type="primary", key="apply_all"):
        for key in accepted.keys():
            accepted[key] = True


def build_final_latex(original_tex: str, optimized_tex: str) -> str:
    accepted = st.session_state.accepted_changes
    if not any(accepted.values()):
        return optimized_tex

    final_tex = optimized_tex

    if not accepted.get("bullets", False):
        orig_bullets = re.findall(r"\\item\s*.+", original_tex)
        opt_bullets = re.findall(r"\\item\s*.+", final_tex)
        if orig_bullets and opt_bullets:
            for old, new in zip(opt_bullets, orig_bullets):
                final_tex = final_tex.replace(old, new, 1)

    if not accepted.get("summary", False):
        orig_summary = extract_summary_from_tex(original_tex)
        opt_summary = extract_summary_from_tex(final_tex)
        if orig_summary and opt_summary:
            final_tex = final_tex.replace(opt_summary, orig_summary, 1)

    return final_tex


def render_resume_tab(parsed: dict[str, Any], final_tex: str, pdf_bytes: bytes | None, pdf_error: str) -> None:
    st.markdown('<div class="summary-card"><p class="card-title">Optimized Summary</p>', unsafe_allow_html=True)
    st.write(parsed.get("optimized_summary", "No explicit optimized summary parsed."))
    st.markdown("</div>", unsafe_allow_html=True)

    left, right = st.columns([1, 1], gap="medium")
    with left:
        st.markdown('<div class="section-card"><p class="card-title">Apply / Accept Changes</p><p class="card-subtitle">Selective acceptance uses session state and survives regeneration when possible.</p></div>', unsafe_allow_html=True)
        apply_selected_changes()
        st.caption(f"Accepted state: {st.session_state.accepted_changes}")

    with right:
        status_class = "success" if pdf_bytes and not pdf_error else "warning"
        status_text = "PDF compiled successfully." if pdf_bytes and not pdf_error else "PDF unavailable or cached fallback in use."
        st.markdown(
            f'<div class="status-card {status_class}"><p class="card-title">Compile Status</p><p class="card-subtitle">{status_text}</p></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="code-card"><p class="card-title">Final Export LaTeX (Accepted Changes Applied)</p>', unsafe_allow_html=True)
    st.code(final_tex, language="latex")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("#### PDF Preview")
    if pdf_bytes:
        b64 = base64.b64encode(pdf_bytes).decode("utf-8")
        st.markdown(
            f'<div class="pdf-frame"><iframe src="data:application/pdf;base64,{b64}" width="100%" height="760" type="application/pdf"></iframe></div>',
            unsafe_allow_html=True,
        )
    else:
        st.info("PDF preview unavailable because compilation did not succeed.")


def render_downloads(report: str, final_tex: str, pdf_bytes: bytes | None, cover_letter: str) -> None:
    c1, c2, c3, c4 = st.columns(4, gap="medium")
    with c1:
        st.markdown('<div class="download-card"><p class="card-title">ATS Report</p><p class="card-subtitle">Markdown ATS and analysis report.</p></div>', unsafe_allow_html=True)
        st.download_button(
            "Download ats_report.md",
            data=report.encode("utf-8"),
            file_name="ats_report.md",
            mime="text/markdown",
            use_container_width=True,
            key="download_ats_md",
        )
    with c2:
        st.markdown('<div class="download-card"><p class="card-title">Optimized LaTeX</p><p class="card-subtitle">Final accepted resume in `.tex` format.</p></div>', unsafe_allow_html=True)
        st.download_button(
            "Download optimized_resume.tex",
            data=final_tex.encode("utf-8"),
            file_name="optimized_resume.tex",
            mime="text/plain",
            use_container_width=True,
            key="download_resume_tex",
        )
    with c3:
        st.markdown('<div class="download-card"><p class="card-title">Compiled PDF</p><p class="card-subtitle">Two-pass `pdflatex` output when available.</p></div>', unsafe_allow_html=True)
        if pdf_bytes:
            st.download_button(
                "Download optimized_resume.pdf",
                data=pdf_bytes,
                file_name="optimized_resume.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="download_resume_pdf",
            )
        else:
            st.button("PDF unavailable", disabled=True, use_container_width=True, key="download_pdf_unavailable")
    with c4:
        st.markdown('<div class="download-card"><p class="card-title">Cover Letter</p><p class="card-subtitle">Active cover letter export.</p></div>', unsafe_allow_html=True)
        st.download_button(
            "Download cover_letter.txt",
            data=cover_letter.encode("utf-8"),
            file_name="cover_letter.txt",
            mime="text/plain",
            use_container_width=True,
            key="download_cover_txt",
        )


def render_debug_panel(raw_output: str, report: str, pdf_error: str, parsing_issue: str) -> None:
    st.markdown('<div class="section-card"><p class="card-title">Debug</p><p class="card-subtitle">Low-priority troubleshooting panel.</p></div>', unsafe_allow_html=True)
    with st.expander("Debug / Logs", expanded=False):
        if parsing_issue:
            st.error(parsing_issue)
        st.markdown("#### Parsed report snapshot")
        st.code(report or "No parsed report")
        if pdf_error:
            st.markdown("#### LaTeX compilation logs")
            st.text(pdf_error)
        st.markdown("#### Raw model output")
        st.code(raw_output or "No output")


def init_state() -> None:
    cached_pdf = load_cached_pdf()
    defaults: dict[str, Any] = {
        "job_description": "",
        "raw_output": "",
        "report": "",
        "optimized_tex": "",
        "final_tex": "",
        "pdf_bytes": cached_pdf,
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
        "accepted_changes": {
            "summary": False,
            "bullets": False,
            "skills": False,
            "cover_letter": False,
        },
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def main() -> None:
    inject_css()
    init_state()
    render_hero()

    api_key, model, role_mode, uploaded_tex, use_base_if_missing, show_resume_preview, resume_source = render_sidebar()

    if uploaded_tex is not None:
        resume_tex = uploaded_tex.getvalue().decode("utf-8", errors="ignore")
    elif use_base_if_missing:
        resume_tex = BASE_RESUME_PATH.read_text(encoding="utf-8")
    else:
        resume_tex = ""

    jd = render_input_section(st.session_state.job_description, resume_source, resume_tex, role_mode)
    st.session_state.job_description = jd

    if show_resume_preview:
        with st.expander("Resume preview", expanded=False):
            st.code(resume_tex[:8000] if resume_tex else "No resume source loaded.", language="latex")

    generate = st.button("Generate ATS + Recruiter Review + Optimized Resume", type="primary", use_container_width=True)

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

        with st.spinner("Running role-specific ATS optimization pipeline..."):
            try:
                raw_output, report, optimized_tex = run_agent(api_key, model, jd, resume_tex, role_mode)
            except Exception as exc:
                st.exception(exc)
                st.stop()

            parsing_issue = ""
            if not report.strip():
                report = raw_output
                parsing_issue = "ATS report parsing fallback triggered: report section not explicitly detected."
            if not optimized_tex.strip():
                st.error("Could not detect optimized LaTeX section in model output.")
                st.session_state.raw_output = raw_output
                st.session_state.report = report
                st.session_state.parsing_issue = (parsing_issue + " LaTeX split failed.").strip()
                st.stop()

            parsed = parse_ats_report(report)
            inferred_from_jd = infer_lists_from_jd(jd)
            if not parsed.get("technical_skills"):
                parsed["technical_skills"] = inferred_from_jd["technical_skills"]
            if not parsed.get("soft_skills"):
                parsed["soft_skills"] = inferred_from_jd["soft_skills"]
            if not parsed.get("keywords"):
                parsed["keywords"] = inferred_from_jd["keywords"]
            metrics = infer_metrics(parsed, report)
            recruiter = parse_recruiter_feedback(report)
            strength_scores = parse_strength_scores(report, metrics)
            cover_letter = parse_cover_letter(report)
            if not cover_letter:
                try:
                    cover_letter = run_cover_letter_generation(api_key, model, jd, resume_tex, role_mode)
                except Exception:
                    cover_letter = ""

            final_tex = build_final_latex(resume_tex, optimized_tex)
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

        st.success("Optimization complete. Explore ATS, recruiter simulation, diffs, cover letter, and downloads below.")

    if st.session_state.optimized_tex:
        st.markdown("## ATS Metrics + Recruiter Simulation")
        render_metric_cards(st.session_state.metrics)
        render_recruiter_card(st.session_state.recruiter)
        render_radar_chart(st.session_state.strength_scores)

        tabs = st.tabs(["JD Breakdown", "Skill Gap", "Diff Viewer", "Cover Letter", "Optimized Resume", "Downloads", "Debug"])
        with tabs[0]:
            render_jd_breakdown(st.session_state.parsed)
        with tabs[1]:
            render_skill_gap(st.session_state.parsed)
        with tabs[2]:
            render_diff_tab(st.session_state.original_resume_tex, st.session_state.optimized_tex, st.session_state.parsed)
        with tabs[3]:
            render_cover_letter_tab(api_key, model, role_mode, jd, resume_tex)
        with tabs[4]:
            st.session_state.final_tex = build_final_latex(st.session_state.original_resume_tex, st.session_state.optimized_tex)
            st.session_state.pdf_bytes, st.session_state.pdf_error = compile_pdf(st.session_state.final_tex)
            render_resume_tab(st.session_state.parsed, st.session_state.final_tex, st.session_state.pdf_bytes, st.session_state.pdf_error)
        with tabs[5]:
            render_downloads(st.session_state.report, st.session_state.final_tex, st.session_state.pdf_bytes, st.session_state.active_cover_letter)
        with tabs[6]:
            render_debug_panel(st.session_state.raw_output, st.session_state.report, st.session_state.pdf_error, st.session_state.parsing_issue)


if __name__ == "__main__":
    main()
