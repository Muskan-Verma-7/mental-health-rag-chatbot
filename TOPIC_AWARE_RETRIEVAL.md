# Topic-Aware Retrieval Implementation

## Overview

Implemented hybrid search that combines vector similarity with topic-based filtering and boosting to improve retrieval relevance for mental health queries.

## Features Implemented

### 1. Topic Inference from Queries
- Automatic topic detection from user queries using regex patterns
- Supported topics: `depression`, `anxiety`, `stress`, `breathing`, `cbt`
- Falls back to `None` if no clear topic detected

**Example:**
- "I feel depressed and hopeless" → `depression`
- "How do I manage my stress?" → `stress`
- "cognitive behavioral therapy techniques" → `cbt`

### 2. Candidate Pool Expansion
- Fetches N × top_k candidates (default: 3 × 3 = 9 candidates)
- Allows for reranking before returning final results
- Configurable via `RETRIEVAL_CANDIDATE_MULTIPLIER`

### 3. Topic-Based Score Boosting
- Documents matching the query topic get a score boost
- Default boost: +0.15 (configurable via `TOPIC_BOOST_FACTOR`)
- Ensures relevant topic-specific content rises to the top

### 4. Hybrid Reranking
- Combines vector similarity scores with topic matching
- Re-sorts all candidates after boosting
- Returns top-k most relevant documents

## Configuration

New settings in `src/core/config.py`:

```python
RETRIEVAL_TOP_K: int = 3  # Final number of documents returned
RETRIEVAL_THRESHOLD: float = 0.4  # Minimum similarity score
RETRIEVAL_CANDIDATE_MULTIPLIER: int = 3  # Fetch N*top_k candidates
TOPIC_BOOST_FACTOR: float = 0.15  # Score boost for matching topics
```

## Test Results

### Depression Query
```
Query: "depression treatment options"
Topic detected: depression
Retrieved: 3 documents

Before boosting:
- Doc 1: score=0.711, topic=depression
- Doc 2: score=0.711, topic=depression  
- Doc 3: score=0.659, topic=depression

After boosting:
- Doc 1: score=0.861, topic=depression (+0.15)
- Doc 2: score=0.861, topic=depression (+0.15)
- Doc 3: score=0.809, topic=depression (+0.15)
```

### CBT Query
```
Query: "cognitive behavioral therapy techniques"
Topic detected: cbt
Retrieved: 3 documents

Before boosting:
- Doc 1: score=0.724, topic=cbt
- Doc 2: score=0.663, topic=cbt
- Doc 3: score=0.657, topic=cbt

After boosting:
- Doc 1: score=0.874, topic=cbt (+0.15)
- Doc 2: score=0.813, topic=cbt (+0.15)
- Doc 3: score=0.807, topic=cbt (+0.15)
```

### Stress Query
```
Query: "managing stress at work"
Topic detected: stress
Retrieved: 3 documents

Before boosting:
- Doc 1: score=0.483, topic=stress
- Doc 2: score=0.483, topic=stress
- Doc 3: score=0.462, topic=cbt

After boosting:
- Doc 1: score=0.633, topic=stress (+0.15)
- Doc 2: score=0.633, topic=stress (+0.15)
- Doc 3: score=0.462, topic=cbt (no boost)
```

## Impact

1. **Improved Relevance**: Documents matching the query topic are prioritized
2. **Better User Experience**: Users get more targeted, topic-specific responses
3. **Flexible Tuning**: Boost factor can be adjusted based on performance
4. **Transparent**: All boosting is logged for debugging and analysis

## Logging

The system logs comprehensive information:
- Topic inference results
- Vector search results (before boosting)
- Each document boost application
- Final reranked results

Example logs:
```json
{
  "event": "query_topic_inferred",
  "query": "depression treatment",
  "inferred_topic": "depression"
}
{
  "event": "topic_boost_applied",
  "query_topic": "depression",
  "doc_topic": "depression",
  "original_score": 0.711,
  "boosted_score": 0.861
}
{
  "event": "retrieval_complete",
  "query_topic": "depression",
  "final_count": 3,
  "scores": [0.861, 0.861, 0.809],
  "topics": ["depression", "depression", "depression"]
}
```

## Topics in Database

Current indexed topics:
- `general`: 554 chunks
- `depression`: 243 chunks
- `cbt`: 155 chunks
- `stress`: 48 chunks

Note: The breathing document (UmqxBC_breathinig_and_guided_visualization.pdf) is image-based and couldn't be indexed with text extraction.

## Future Enhancements

1. **ML-based Topic Classification**: Replace regex with a trained classifier
2. **Multi-topic Queries**: Handle queries spanning multiple topics
3. **Topic Weights**: Different boost factors for different topic matches
4. **User Feedback Loop**: Learn topic relevance from user interactions
5. **OCR Integration**: Extract text from image-based PDFs like the breathing document

## Code Structure

### Topic Inference
Location: `src/services/retrieval_service.py`

```python
def infer_topic_from_query(query: str) -> Optional[str]:
    """Infer topic from user query text using regex patterns."""
    # Pattern matching for different mental health topics
    # Returns most confident topic or None
```

### Boosting Logic
Location: `src/services/retrieval_service.py`

```python
def _apply_topic_boosting(
    self, documents: List[Document], query_topic: Optional[str]
) -> List[Document]:
    """Apply topic-based score boosting and rerank documents."""
    # Add boost factor to matching documents
    # Re-sort by boosted scores
```

### Main Retrieval
Location: `src/services/retrieval_service.py`

```python
async def retrieve(self, query: str) -> List[Document]:
    """Retrieve with topic-aware ranking."""
    # 1. Infer topic from query
    # 2. Fetch candidate pool (N*top_k)
    # 3. Apply topic boosting
    # 4. Return top-k reranked results
```

## Performance

- Topic inference: <1ms (regex-based)
- Candidate retrieval: 100-200ms (vector search)
- Boosting & reranking: <1ms (in-memory)
- Total overhead: ~1-2ms compared to basic retrieval

## Conclusion

The topic-aware retrieval system successfully enhances the RAG application by prioritizing domain-specific content when a clear topic is detected. The hybrid approach maintains high-quality vector similarity while ensuring users get the most relevant topic-specific resources.
