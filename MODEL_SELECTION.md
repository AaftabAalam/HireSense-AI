# Model Selection Notes

## Recommendation

There is no honest way to guarantee "95%+ accuracy" for every resume, role, accent, and interview style. What we can do is choose a stack that is strong, current, and production-ready for this workflow.

### Accuracy-first stack

- Speech-to-text: `openai/whisper-large-v3` through `faster-whisper`
- Interview and scoring LLM: `Qwen/Qwen3-235B-A22B-Instruct-2507`
- Embeddings and first-pass skill matching: `BAAI/bge-m3`
- Final relevance reranker: `BAAI/bge-reranker-v2-m3`

### Why this stack

- `faster-whisper` is a fast Whisper implementation using CTranslate2 and states it is up to 4x faster than `openai/whisper` at the same accuracy while using less memory.
- `Qwen3-235B-A22B-Instruct-2507` is one of the strongest open-weight instruct models currently available, with 22B active parameters, native 262,144-token context, and documented agentic/tool-calling support.
- `BAAI/bge-m3` is designed for dense, sparse, and multi-vector retrieval together, supports more than 100 languages, and handles long inputs up to 8192 tokens.
- `BAAI/bge-reranker-v2-m3` is a multilingual lightweight reranker designed to output relevance directly and can be normalized to `[0,1]`.

### Practical local fallback

If the 235B model is too expensive for your hardware, use:

- `meta-llama/Llama-3.3-70B-Instruct`
- or `Qwen/Qwen2.5-32B-Instruct`

The application is already written so the LLM is configurable behind an OpenAI-compatible endpoint, which means you can switch models without rewriting the app.

## Official sources

- [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- [Qwen3-235B-A22B-Instruct-2507](https://huggingface.co/Qwen/Qwen3-235B-A22B-Instruct-2507)
- [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3)
- [BAAI/bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3)
