from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.audio import transcribe_audio
from app.config import get_settings
from app.interview_engine import InterviewEngine
from app.llm import LLMClient
from app.models import ResumeProfile
from app.resume_parser import parse_resume
import orjson

settings = get_settings()
llm_client = LLMClient(settings)
engine = InterviewEngine(settings, llm_client)

app = FastAPI(title=settings.app_name)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/storage", StaticFiles(directory="storage"), name="storage")
templates = Jinja2Templates(directory="templates")


def resume_payload_path(upload_id: str) -> Path:
    return settings.uploads_dir / f"{upload_id}.resume.json"


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request, "app_name": settings.app_name})


@app.post("/api/resume/analyze")
async def analyze_resume(resume: UploadFile = File(...)):
    extension = Path(resume.filename or "resume.pdf").suffix.lower() or ".pdf"
    upload_id = uuid.uuid4().hex
    file_name = f"{upload_id}{extension}"
    destination = settings.uploads_dir / file_name
    with destination.open("wb") as buffer:
        shutil.copyfileobj(resume.file, buffer)

    resume_profile = await parse_resume(destination, llm_client)
    payload = {
        "upload_id": upload_id,
        "resume_path": str(destination),
        "resume_profile": resume_profile.model_dump(),
    }
    resume_payload_path(upload_id).write_bytes(orjson.dumps(payload, option=orjson.OPT_INDENT_2))
    return payload


@app.post("/api/interview/start")
async def start_interview(upload_id: str = Form(...)):
    payload_path = resume_payload_path(upload_id)
    if not payload_path.exists():
        raise HTTPException(status_code=404, detail="Uploaded resume analysis was not found.")

    payload = orjson.loads(payload_path.read_bytes())
    resume_profile = ResumeProfile.model_validate(payload["resume_profile"])
    session = await engine.create_session(resume_profile)

    return {
        "session_id": session.session_id,
        "resume_profile": session.resume_profile.model_dump(),
        "question": session.questions[0].model_dump(),
        "message": session.questions[0].question,
    }


@app.post("/api/interview/respond")
async def respond(session_id: str = Form(...), answer: str = Form(...)):
    if not answer.strip():
        raise HTTPException(status_code=400, detail="Answer is required.")
    return (await engine.handle_answer(session_id, answer)).model_dump()


@app.post("/api/interview/respond-audio")
async def respond_audio(session_id: str = Form(...), audio: UploadFile = File(...)):
    extension = Path(audio.filename or "answer.webm").suffix.lower() or ".webm"
    audio_path = settings.uploads_dir / f"{uuid.uuid4().hex}{extension}"
    with audio_path.open("wb") as buffer:
        shutil.copyfileobj(audio.file, buffer)
    transcript = transcribe_audio(settings, audio_path)
    if not transcript:
        raise HTTPException(status_code=400, detail="Audio could not be transcribed.")
    reply = await engine.handle_answer(session_id, transcript)
    payload = reply.model_dump()
    payload["transcribed_answer"] = transcript
    return payload
