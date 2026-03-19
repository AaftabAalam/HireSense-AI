from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

import orjson

from app.config import Settings
from app.llm import LLMClient
from app.models import (
    AnswerEvaluation,
    ChatReply,
    InterviewQuestion,
    InterviewSession,
    ReportPayload,
    ResumeProfile,
    ScoreCard,
    TranscriptTurn,
)
from app.prompts import ANSWER_EVALUATION_PROMPT, QUESTION_GENERATION_PROMPT, SUMMARY_PROMPT
from app.reporting import build_report_payload, write_report_files
from app.similarity import compute_skill_relevance


CLARIFICATION_PATTERNS = [
    r"\bcan you clarify\b",
    r"\bwhat do you mean\b",
    r"\bcould you repeat\b",
    r"\bi do not understand\b",
    r"\bplease explain the question\b",
    r"\bcan you explain\b",
]


class InterviewEngine:
    def __init__(self, settings: Settings, llm_client: LLMClient) -> None:
        self.settings = settings
        self.llm_client = llm_client

    def session_path(self, session_id: str) -> Path:
        return self.settings.sessions_dir / f"{session_id}.json"

    def load_session(self, session_id: str) -> InterviewSession:
        data = orjson.loads(self.session_path(session_id).read_bytes())
        return InterviewSession.model_validate(data)

    def save_session(self, session: InterviewSession) -> None:
        self.session_path(session.session_id).write_bytes(orjson.dumps(session.model_dump(), option=orjson.OPT_INDENT_2))

    async def create_session(self, resume_profile: ResumeProfile) -> InterviewSession:
        questions = await self.generate_questions(resume_profile)
        session = InterviewSession(
            session_id=uuid.uuid4().hex,
            status="in_progress",
            resume_profile=resume_profile,
            questions=questions,
            transcript=[
                TranscriptTurn(role="system", content="Interview session initialized."),
                TranscriptTurn(role="assistant", content=questions[0].question),
            ],
        )
        self.save_session(session)
        return session

    async def generate_questions(self, resume_profile: ResumeProfile) -> list[InterviewQuestion]:
        try:
            payload = await self.llm_client.chat_json(
                QUESTION_GENERATION_PROMPT.format(max_questions=self.settings.max_questions),
                json.dumps(
                    {
                        "candidate_name": resume_profile.candidate_name,
                        "title": resume_profile.title,
                        "summary": resume_profile.summary,
                        "skills": resume_profile.skills,
                        "experience_highlights": resume_profile.experience_highlights,
                        "projects": resume_profile.projects,
                    }
                ),
            )
            questions = [InterviewQuestion.model_validate(item) for item in payload["questions"][: self.settings.max_questions]]
            if questions:
                return questions
        except Exception:
            pass

        skills = resume_profile.skills[: self.settings.max_questions] or ["software engineering", "problem solving", "system design"]
        return [
            InterviewQuestion(
                id=index + 1,
                skill_focus=skill,
                question=f"Explain a real project or task where you used {skill}. What problem were you solving, what decisions did you make, and what was the outcome?",
                guidance="Focus on your own hands-on contribution, architecture or logic, and measurable impact.",
            )
            for index, skill in enumerate(skills[: self.settings.max_questions])
        ]

    async def evaluate_answer(self, session: InterviewSession, answer_text: str) -> AnswerEvaluation:
        current_question = session.questions[session.current_question_index]
        relevance_score = compute_skill_relevance(self.settings, session.resume_profile.skills, answer_text)
        answer_skills = self.extract_answer_skills(session.resume_profile.skills, answer_text)

        if self.looks_like_clarification_request(answer_text):
            return AnswerEvaluation(
                answer=answer_text,
                scorecard=ScoreCard(
                    communication=0.0,
                    technical_relevance=0.0,
                    confidence=0.0,
                    clarity=0.0,
                    overall_quality=0.0,
                ),
                skills_answer=[],
                relevance_score=0.0,
                feedback_summary=["Candidate requested clarification before giving a substantive answer."],
                clarification_response=current_question.guidance,
                answer_status="clarification_needed",
            )

        fallback = AnswerEvaluation(
            answer=answer_text,
            scorecard=ScoreCard(
                communication=self.fallback_score(answer_text, "communication"),
                technical_relevance=self.fallback_score(answer_text, "technical_relevance", answer_skills),
                confidence=self.fallback_score(answer_text, "confidence"),
                clarity=self.fallback_score(answer_text, "clarity"),
                overall_quality=self.fallback_score(answer_text, "overall_quality", answer_skills),
            ),
            skills_answer=answer_skills,
            relevance_score=relevance_score,
            feedback_summary=[
                "Response captured and scored in fallback mode.",
                f"Detected answer skills: {', '.join(answer_skills) if answer_skills else 'none explicitly matched'}.",
            ],
        )
        try:
            payload = await self.llm_client.chat_json(
                ANSWER_EVALUATION_PROMPT,
                json.dumps(
                    {
                        "current_question": current_question.model_dump(),
                        "resume_skills": session.resume_profile.skills,
                        "resume_summary": session.resume_profile.summary,
                        "candidate_answer": answer_text,
                    }
                ),
            )
            return AnswerEvaluation(
                answer=answer_text,
                scorecard=ScoreCard.model_validate(payload["scorecard"]),
                skills_answer=payload.get("skills_answer") or answer_skills,
                relevance_score=relevance_score,
                feedback_summary=payload.get("feedback_summary") or [],
                clarification_response=payload.get("clarification_response"),
                answer_status=payload.get("answer_status", "answered"),
            )
        except Exception:
            return fallback

    @staticmethod
    def looks_like_clarification_request(answer_text: str) -> bool:
        normalized = answer_text.strip().lower()
        if len(normalized.split()) <= 12 and "?" in normalized:
            return True
        return any(re.search(pattern, normalized) for pattern in CLARIFICATION_PATTERNS)

    @staticmethod
    def extract_answer_skills(resume_skills: list[str], answer_text: str) -> list[str]:
        normalized = answer_text.lower()
        return [skill for skill in resume_skills if skill.lower() in normalized]

    def fallback_score(self, answer_text: str, category: str, matched_skills: list[str] | None = None) -> float:
        words = len(answer_text.split())
        matched_skills = matched_skills or []
        if category == "communication":
            return min(9.0, round(4.5 + min(words, 180) / 40, 2))
        if category == "technical_relevance":
            return min(9.5, round(4.0 + (len(matched_skills) * 1.35), 2))
        if category == "confidence":
            boost = 0.8 if re.search(r"\b(i implemented|i built|i designed|i optimized|i led)\b", answer_text.lower()) else 0.0
            return min(9.0, round(4.8 + boost + min(words, 160) / 70, 2))
        if category == "clarity":
            boost = 0.9 if re.search(r"\b(first|then|because|result|finally|impact)\b", answer_text.lower()) else 0.0
            return min(9.0, round(4.7 + boost + min(words, 140) / 85, 2))
        return min(9.2, round((self.fallback_score(answer_text, "communication") + self.fallback_score(answer_text, "technical_relevance", matched_skills) + self.fallback_score(answer_text, "confidence") + self.fallback_score(answer_text, "clarity")) / 4, 2))

    async def finalize_summary(self, session: InterviewSession) -> list[str]:
        report_payload = build_report_payload(session, [])
        try:
            payload = await self.llm_client.chat_json(
                SUMMARY_PROMPT,
                json.dumps(
                    {
                        "scores": report_payload.scores,
                        "skills_resume": report_payload.skills_resume,
                        "skills_answer": report_payload.skills_answer,
                        "relevance_score": report_payload.relevance_score,
                        "transcript_excerpt": report_payload.transcript[-12000:],
                    }
                ),
            )
            summary = payload.get("summary") or []
            if summary:
                return summary[:5]
        except Exception:
            pass

        return [
            "The candidate demonstrated part of the claimed skill set, but further depth validation would help.",
            "Communication remained understandable, though some answers may need stronger structure and evidence.",
            "Resume-to-answer relevance was calculated from the actual interview responses.",
        ]

    async def handle_answer(self, session_id: str, answer_text: str) -> ChatReply:
        session = self.load_session(session_id)
        session.transcript.append(TranscriptTurn(role="user", content=answer_text))

        evaluation = await self.evaluate_answer(session, answer_text)
        if evaluation.answer_status == "clarification_needed":
            clarification = evaluation.clarification_response or (
                f"Please answer the question directly. {session.questions[session.current_question_index].guidance}"
            )
            session.transcript.append(TranscriptTurn(role="assistant", content=clarification))
            self.save_session(session)
            return ChatReply(
                session_id=session.session_id,
                status="in_progress",
                current_question_index=session.current_question_index,
                assistant_message=clarification,
                latest_evaluation=evaluation,
            )

        session.evaluations.append(evaluation)
        session.current_question_index += 1

        if session.current_question_index >= len(session.questions):
            session.status = "completed"
            summary = await self.finalize_summary(session)
            report_payload: ReportPayload = build_report_payload(session, summary)
            report_json, report_html = write_report_files(
                session,
                report_payload,
                self.settings.reports_dir,
                Path("templates"),
            )
            closing_message = "The interview is complete. Your final report has been generated."
            session.transcript.append(TranscriptTurn(role="assistant", content=closing_message))
            self.save_session(session)
            return ChatReply(
                session_id=session.session_id,
                status="completed",
                current_question_index=len(session.questions),
                assistant_message=closing_message,
                latest_evaluation=evaluation,
                report_path=str(report_html),
                report_json_path=str(report_json),
            )

        next_question = session.questions[session.current_question_index].question
        session.transcript.append(TranscriptTurn(role="assistant", content=next_question))
        self.save_session(session)
        return ChatReply(
            session_id=session.session_id,
            status="in_progress",
            current_question_index=session.current_question_index,
            assistant_message=next_question,
            latest_evaluation=evaluation,
        )
