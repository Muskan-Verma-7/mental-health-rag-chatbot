"""Retrieval service for vector search and reranking."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import re

from ..core.config import get_settings
from ..core.database import get_database
from ..core.exceptions import RetrievalException
from .embedding_service import get_embedding_service
from ..utils.logger import get_logger

logger = get_logger()


@dataclass
class Document:
    """Retrieved document chunk."""

    content: str
    metadata: Dict[str, Any]
    score: float


def infer_topic_from_query(query: str) -> Optional[str]:
    """Infer topic from user query text.
    
    Args:
        query: User's query text
        
    Returns:
        Inferred topic or None if no clear topic detected
    """
    query_lower = query.lower()
    
    # Topic patterns with keywords (ordered by specificity)
    topic_patterns = {
        "depression": [
            r"\b(depress(ed|ion|ive)?|sad(ness)?|hopeless(ness)?|suicid(al|e)?)\b",
            r"\bfeeling down\b",
            r"\bno motivation\b",
        ],
        "anxiety": [
            r"\b(anxious|anxiety|anxiet(y|ies)|panic|worried|worry(ing)?)\b",
            r"\bpanic attack\b",
            r"\bfeeling nervous\b",
        ],
        "stress": [
            r"\b(stress(ed|ful)?|overwhelm(ed|ing)?|pressure|tense|tension)\b",
            r"\bstressed out\b",
            r"\btoo much\b.*\b(work|responsibilities)\b",
        ],
        "breathing": [
            r"\b(breath(e|ing)?|respiratory)\b",
            r"\bbreathing (exercise|technique)\b",
            r"\bcalm(ing)? breath\b",
        ],
        "cbt": [
            r"\b(cbt|cognitive behavioral|thought pattern|negative thought)\b",
            r"\bchanging thoughts\b",
        ],
    }
    
    # Check each topic's patterns
    topic_scores = {}
    for topic, patterns in topic_patterns.items():
        score = 0
        for pattern in patterns:
            if re.search(pattern, query_lower):
                score += 1
        if score > 0:
            topic_scores[topic] = score
    
    # Return topic with highest score, or None if no match
    if topic_scores:
        best_topic = max(topic_scores.items(), key=lambda x: x[1])
        return best_topic[0]
    
    return None


class RetrievalService:
    """Service for retrieving relevant therapy documents."""

    def __init__(self):
        """Initialize retrieval service."""
        self.settings = get_settings()
        self._cache: Dict[str, List[Document]] = {}

    def _apply_topic_boosting(
        self, documents: List[Document], query_topic: Optional[str]
    ) -> List[Document]:
        """Apply topic-based score boosting and rerank documents.
        
        Args:
            documents: List of retrieved documents
            query_topic: Inferred topic from query (if any)
            
        Returns:
            Reranked documents with boosted scores
        """
        if not query_topic or not documents:
            return documents
        
        boost_factor = self.settings.TOPIC_BOOST_FACTOR
        boosted_docs = []
        
        for doc in documents:
            new_score = doc.score
            doc_topic = doc.metadata.get("topic")
            
            # Apply boost if topics match
            if doc_topic and doc_topic == query_topic:
                new_score = min(1.0, doc.score + boost_factor)
                logger.info(
                    "topic_boost_applied",
                    query_topic=query_topic,
                    doc_topic=doc_topic,
                    original_score=doc.score,
                    boosted_score=new_score,
                )
            
            boosted_docs.append(
                Document(
                    content=doc.content,
                    metadata=doc.metadata,
                    score=new_score,
                )
            )
        
        # Re-sort by boosted scores
        boosted_docs.sort(key=lambda d: d.score, reverse=True)
        return boosted_docs

    async def retrieve(self, query: str) -> List[Document]:
        """Retrieve relevant documents for query with topic-aware ranking.
        
        This implements hybrid search that:
        1. Infers topic from the query
        2. Retrieves candidate documents via vector similarity
        3. Boosts scores for documents matching the query topic
        4. Returns top-k reranked results
        """
        # Check cache
        cache_key = query.lower().strip()
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            # Infer topic from query
            query_topic = infer_topic_from_query(query)
            logger.info(
                "query_topic_inferred",
                query=query,
                inferred_topic=query_topic or "none",
            )
            
            # Embed query
            embedding_service = await get_embedding_service()
            query_embedding = await embedding_service.embed_single(query)
            
            # Fetch more candidates for reranking (N * top_k)
            candidate_count = (
                self.settings.RETRIEVAL_TOP_K 
                * self.settings.RETRIEVAL_CANDIDATE_MULTIPLIER
            )
            
            # Search database with expanded candidate pool
            database = get_database()
            results = await database.search_similar(
                embedding=query_embedding,
                top_k=candidate_count,
                threshold=self.settings.RETRIEVAL_THRESHOLD,
            )
            
            logger.info(
                "vector_search_complete",
                candidates_found=len(results),
                threshold=self.settings.RETRIEVAL_THRESHOLD,
            )

            # Convert to Document objects
            documents = [
                Document(
                    content=result["content"],
                    metadata=result.get("metadata", {}),
                    score=result.get("score", 0.0),
                )
                for result in results
            ]
            
            # Apply topic-based boosting and reranking
            if query_topic:
                documents = self._apply_topic_boosting(documents, query_topic)
            
            # Return top-k after reranking
            final_documents = documents[: self.settings.RETRIEVAL_TOP_K]
            
            logger.info(
                "retrieval_complete",
                query_topic=query_topic or "none",
                final_count=len(final_documents),
                scores=[round(d.score, 3) for d in final_documents],
                topics=[d.metadata.get("topic", "unknown") for d in final_documents],
            )

            # Cache results
            self._cache[cache_key] = final_documents
            return final_documents

        except Exception as e:
            logger.exception("retrieval_error", error=str(e))
            raise RetrievalException(f"Retrieval failed: {e}")


_retrieval_service: RetrievalService | None = None


def get_retrieval_service() -> RetrievalService:
    """Get or create retrieval service singleton."""
    global _retrieval_service
    if _retrieval_service is None:
        _retrieval_service = RetrievalService()
    return _retrieval_service
