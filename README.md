# Interview Analyzer

Production-style AI interview application with:

- Resume upload and parsing
- AI-generated technical interview questions based on resume skills
- Clarification handling without leaking answers
- Per-answer scoring for communication, technical relevance, confidence, clarity, and overall quality
- Resume-vs-answer skill similarity scoring in `[0, 1]`
- Final JSON report plus a styled HTML report
- Optional voice input via browser recording and Faster-Whisper transcription

## Recommended model stack

Two deployment profiles are supported by configuration:

### Accuracy-first profile

- STT: `openai/whisper-large-v3` via `faster-whisper`
- LLM: `Qwen/Qwen3-235B-A22B-Instruct-2507` served behind an OpenAI-compatible endpoint
- Embeddings: `BAAI/bge-m3`
- Reranker: `BAAI/bge-reranker-v2-m3`

### Practical local profile

- STT: `openai/whisper-large-v3` via `faster-whisper`
- LLM: `meta-llama/Llama-3.3-70B-Instruct` or `Qwen/Qwen2.5-32B-Instruct`
- Embeddings: `BAAI/bge-m3`
- Reranker: `BAAI/bge-reranker-v2-m3`

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## Environment

Copy `.env.example` to `.env` and adjust values:

```bash
cp .env.example .env
```

## Notes

- For the best experience, point `LLM_BASE_URL` to a local or remote OpenAI-compatible inference server such as vLLM.
- The app stores uploads, interview sessions, and reports in `storage/`.
- Only three interview questions are asked for the test flow, as requested.
- See `MODEL_SELECTION.md` for the current open-model recommendation and deployment rationale.
# HireSense-AI
An AI-powered interview system that analyzes resumes, conducts adaptive technical interviews, and generates structured, unbiased candidate evaluation reports.  Built with a focus on fairness, consistency, and explainability. 
