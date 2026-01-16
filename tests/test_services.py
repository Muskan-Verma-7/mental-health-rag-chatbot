"""Unit tests for service layer."""

from src.services.retrieval_service import (
    Document,
    RetrievalService,
    infer_topic_from_query,
)


def test_infer_topic_from_query():
    """Infer topics from typical mental health queries."""
    assert infer_topic_from_query("I feel depressed and hopeless") == "depression"
    assert infer_topic_from_query("I have anxiety and panic attacks") == "anxiety"
    assert infer_topic_from_query("I am stressed at work") == "stress"
    assert infer_topic_from_query("breathing exercises to calm down") == "breathing"
    assert infer_topic_from_query("cognitive behavioral therapy techniques") == "cbt"
    assert infer_topic_from_query("How can I feel better?") is None


def test_apply_topic_boosting():
    """Boost matching-topic documents and rerank."""
    service = RetrievalService()
    docs = [
        Document(content="stress doc", metadata={"topic": "stress"}, score=0.4),
        Document(content="cbt doc", metadata={"topic": "cbt"}, score=0.6),
    ]

    boosted = service._apply_topic_boosting(docs, "stress")

    stress_doc = next(d for d in boosted if d.metadata["topic"] == "stress")
    assert stress_doc.score > docs[0].score
    assert boosted[0].metadata["topic"] == "cbt"
    assert boosted[0].score == docs[1].score


def test_apply_topic_boosting_no_topic():
    """No boosting should occur when no topic is inferred."""
    service = RetrievalService()
    docs = [
        Document(content="doc", metadata={"topic": "stress"}, score=0.4),
        Document(content="doc2", metadata={"topic": "cbt"}, score=0.6),
    ]

    boosted = service._apply_topic_boosting(docs, None)
    assert [d.score for d in boosted] == [0.4, 0.6]
