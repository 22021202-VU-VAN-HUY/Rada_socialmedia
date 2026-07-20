from talent_radar.schemas import ClassificationRequest
from talent_radar.services.query_pack import QueryPack, QueryPackMatcher
from talent_radar.services.rule_classifier import RuleClassifier


def classifier() -> RuleClassifier:
    pack = QueryPack(
        entity="VSF",
        version="test",
        exact=["VSF"],
        context_anchors=["dang ky", "deadline"],
    )
    return RuleClassifier(QueryPackMatcher(pack))


def test_question_becomes_content_action() -> None:
    result = classifier().classify(ClassificationRequest(text="VSF deadline dang ky khi nao?"))
    assert result.relevance["label"] == "relevant"
    assert result.voice["signal_type"] == "question"
    assert result.recommendation["actions"][0]["type"] == "content_creation"


def test_risk_becomes_needs_review() -> None:
    result = classifier().classify(ClassificationRequest(text="VSF bi to cao lua dao"))
    assert result.voice["signal_type"] == "risk"
    assert result.risk["danger_level"] == "high"
    assert result.review_status == "needs_review"
