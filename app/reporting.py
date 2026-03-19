from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import orjson
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.models import InterviewSession, ReportPayload


def aggregate_scores(session: InterviewSession) -> dict[str, float]:
    if not session.evaluations:
        return {
            "communication": 0.0,
            "technical_relevance": 0.0,
            "confidence": 0.0,
            "clarity": 0.0,
            "overall_quality": 0.0,
        }

    sums = defaultdict(float)
    for evaluation in session.evaluations:
        sums["communication"] += evaluation.scorecard.communication
        sums["technical_relevance"] += evaluation.scorecard.technical_relevance
        sums["confidence"] += evaluation.scorecard.confidence
        sums["clarity"] += evaluation.scorecard.clarity
        sums["overall_quality"] += evaluation.scorecard.overall_quality
    count = len(session.evaluations)
    return {key: round(value / count, 2) for key, value in sums.items()}


def build_transcript(session: InterviewSession) -> str:
    lines = []
    for turn in session.transcript:
        lines.append(f"[{turn.timestamp.isoformat()}] {turn.role.upper()}: {turn.content}")
    return "\n".join(lines)


def build_report_payload(session: InterviewSession, summary: list[str]) -> ReportPayload:
    all_answer_skills = sorted({skill for item in session.evaluations for skill in item.skills_answer})
    avg_relevance = (
        round(sum(item.relevance_score for item in session.evaluations) / len(session.evaluations), 4)
        if session.evaluations
        else 0.0
    )
    return ReportPayload(
        transcript=build_transcript(session),
        scores=aggregate_scores(session),
        skills_resume=session.resume_profile.skills,
        skills_answer=all_answer_skills,
        relevance_score=avg_relevance,
        summary=summary,
    )


def write_report_files(
    session: InterviewSession,
    report_payload: ReportPayload,
    report_dir: Path,
    template_dir: Path,
) -> tuple[Path, Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    report_json = report_dir / f"{session.session_id}.json"
    report_html = report_dir / f"{session.session_id}.html"
    report_json.write_bytes(orjson.dumps(report_payload.model_dump(), option=orjson.OPT_INDENT_2))

    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("report.html")
    rendered = template.render(
        session=session,
        report=report_payload,
        question_count=len(session.questions),
    )
    report_html.write_text(rendered, encoding="utf-8")
    return report_json, report_html
