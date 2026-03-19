from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ResumeProfile(BaseModel):
    candidate_name: str | None = None
    title: str | None = None
    summary: str | None = None
    skills: list[str] = Field(default_factory=list)
    experience_highlights: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    raw_text: str = ""


class InterviewQuestion(BaseModel):
    id: int
    skill_focus: str
    question: str
    guidance: str


class ScoreCard(BaseModel):
    communication: float
    technical_relevance: float
    confidence: float
    clarity: float
    overall_quality: float


class AnswerEvaluation(BaseModel):
    answer: str
    scorecard: ScoreCard
    skills_answer: list[str] = Field(default_factory=list)
    relevance_score: float
    feedback_summary: list[str] = Field(default_factory=list)
    clarification_response: str | None = None
    answer_status: Literal["answered", "clarification_needed"] = "answered"


class TranscriptTurn(BaseModel):
    role: Literal["system", "assistant", "user"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class InterviewSession(BaseModel):
    session_id: str
    status: Literal["created", "in_progress", "completed"] = "created"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resume_profile: ResumeProfile
    questions: list[InterviewQuestion]
    current_question_index: int = 0
    transcript: list[TranscriptTurn] = Field(default_factory=list)
    evaluations: list[AnswerEvaluation] = Field(default_factory=list)


class ReportPayload(BaseModel):
    transcript: str
    scores: dict[str, float]
    skills_resume: list[str]
    skills_answer: list[str]
    relevance_score: float
    summary: list[str]


class ChatReply(BaseModel):
    session_id: str
    status: Literal["in_progress", "completed"]
    current_question_index: int
    assistant_message: str
    latest_evaluation: AnswerEvaluation | None = None
    report_path: str | None = None
    report_json_path: str | None = None
