## RAG Pipeline Demo

This is a quick demo I built to showcase my ability to design and implement RAG systems. Built in a few hours to demonstrate the kind of work I can bring to Aumio.

### What This Demonstrates

**RAG Pipeline Thinking:**
- Built a complete RAG system from scratch: embeddings → vector search → retrieval → LLM generation
- Implemented topic-aware retrieval as an experiment (not claiming it's perfect, just showing I can think through the problem)
- Clean architecture with proper separation of concerns

**Production Mindset:**
- Safety-first approach with crisis detection (critical for mental health domain)
- Structured logging, error handling, rate limiting
- Docker-ready, deployable to Render

**Technical Skills:**
- FastAPI with async/await patterns
- Supabase pgvector for vector storage
- Groq LLM integration
- Service layer with dependency injection

### Quick Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set up .env with:
# SUPABASE_URL, SUPABASE_KEY, GROQ_API_KEY

# Set up Supabase schema (run scripts/supabase_schema.sql)
# Index demo documents
python scripts/index_data.py

# Run
uvicorn src.main:app --reload
```

### Key Files

- `src/services/retrieval_service.py` - RAG retrieval logic with topic-aware boosting experiment
- `src/services/safety_service.py` - Crisis detection and safety filtering
- `src/api/routes.py` - Main chat endpoint
- `src/services/llm_service.py` - LLM integration with context

### Important Notes

- **Demo documents only** - The PDFs in `data/therapy_docs/` are just for demonstration purposes, not real therapy documents
- **Quick prototype** - This was built to show capability, not production quality
- **Topic-aware retrieval** - Implemented as a proof of concept to show I can think through retrieval improvements, not claiming it's optimal

### What I'd Build at Aumio

Given more time and real requirements, I'd focus on:
- Better retrieval strategies (cross-encoders, hybrid search)
- Conversation memory and context management
- User feedback loops to improve retrieval
- A/B testing framework for different approaches
- Proper evaluation metrics and monitoring

This demo shows I can move fast, think through RAG problems, and write clean, maintainable code. I'm excited to apply these skills to real problems at Aumio.
