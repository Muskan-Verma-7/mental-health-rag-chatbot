## Aumio RAG Demo

Production-ready RAG mental health chatbot with FastAPI, Supabase pgvector, Groq LLM, safety filtering, and observability.

### Features
- Retrieval-augmented generation with topic-aware ranking
- Safety filtering with crisis resources
- Structured logging and metrics
- Async service layer and caching
- Supabase pgvector storage and search

### Architecture
API → Safety → Embeddings → Vector Search → Topic Boosting → LLM → Response

### Requirements
- Python 3.11+
- Supabase project with pgvector enabled
- Groq API key

### Setup
1. Create a `.env` from the template:
   ```bash
   cp .env.example .env
   ```
2. Fill in `SUPABASE_URL`, `SUPABASE_KEY`, `GROQ_API_KEY`.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Apply Supabase schema:
   - Run the SQL in `scripts/supabase_schema.sql` in the Supabase SQL editor.
5. Download and index documents:
   ```bash
   python scripts/download_docs.py
   python scripts/index_data.py
   ```
6. Run the API:
   ```bash
   uvicorn src.main:app --reload
   ```

### API Endpoints
- `POST /chat` — main chat endpoint
- `GET /health` — health check
- `GET /metrics` — request metrics

Example request:
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"I am feeling stressed at work"}'
```

### Tracing (Langfuse)
Langfuse tracing is optional. Add these keys to `.env` to enable:

```
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_SECRET_KEY=your_langfuse_secret_key
LANGFUSE_HOST=https://cloud.langfuse.com
```

Traces include spans for safety checks, retrieval, and LLM generation.

### Testing
```bash
pytest
```

### Docker
```bash
docker build -t aumio-rag-demo .
docker run --env-file .env -p 8000:8000 aumio-rag-demo
```

### Docker Compose (Dev)
```bash
docker-compose up --build
```

### Deployment (Render)
Use `render.yaml` and set environment variables in the Render dashboard:
`SUPABASE_URL`, `SUPABASE_KEY`, `GROQ_API_KEY`.

### Notes
- The breathing PDF in `data/therapy_docs` is image-based and requires OCR to index.
- Topic-aware retrieval is documented in `TOPIC_AWARE_RETRIEVAL.md`.
