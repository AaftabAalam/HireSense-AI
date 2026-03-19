from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from pypdf import PdfReader

from app.llm import LLMClient
from app.models import ResumeProfile
from app.prompts import RESUME_EXTRACTION_PROMPT

COMMON_SKILLS = [
    "python",
    "java",
    "javascript",
    "typescript",
    "react",
    "next.js",
    "node.js",
    "fastapi",
    "django",
    "flask",
    "sql",
    "postgresql",
    "mysql",
    "mongodb",
    "redis",
    "docker",
    "kubernetes",
    "aws",
    "azure",
    "gcp",
    "machine learning",
    "deep learning",
    "nlp",
    "pytorch",
    "tensorflow",
    "llm",
    "rag",
    "ci/cd",
]


def extract_text_from_file(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(str(file_path))
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    if suffix == ".docx":
        doc = Document(str(file_path))
        return "\n".join(paragraph.text for paragraph in doc.paragraphs).strip()
    return file_path.read_text(encoding="utf-8", errors="ignore").strip()


def extract_skills_fallback(text: str) -> list[str]:
    normalized = text.lower()
    found = []
    for skill in COMMON_SKILLS:
        if re.search(rf"\b{re.escape(skill.lower())}\b", normalized):
            found.append(skill)
    return sorted(set(found))


async def parse_resume(file_path: Path, llm_client: LLMClient) -> ResumeProfile:
    raw_text = extract_text_from_file(file_path)
    if not raw_text:
        return ResumeProfile(raw_text="", skills=[])

    try:
        payload = await llm_client.chat_json(
            RESUME_EXTRACTION_PROMPT,
            f"Resume text:\n{raw_text[:30000]}",
        )
        return ResumeProfile(
            candidate_name=payload.get("candidate_name"),
            title=payload.get("title"),
            summary=payload.get("summary"),
            skills=payload.get("skills") or extract_skills_fallback(raw_text),
            experience_highlights=payload.get("experience_highlights") or [],
            projects=payload.get("projects") or [],
            raw_text=raw_text,
        )
    except Exception:
        return ResumeProfile(
            summary=raw_text[:500],
            skills=extract_skills_fallback(raw_text),
            experience_highlights=[],
            projects=[],
            raw_text=raw_text,
        )
