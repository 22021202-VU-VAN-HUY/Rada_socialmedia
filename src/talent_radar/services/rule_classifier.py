from datetime import datetime
from typing import Any

from talent_radar.schemas import ClassificationRequest, ClassificationResult, Evidence
from talent_radar.services.query_pack import QueryPackMatcher


POSITIVE_TERMS = [
    "hay",
    "bo ich",
    "dang tham gia",
    "recommend",
    "truyen cam hung",
    "tot",
    "thich",
]
QUESTION_TERMS = ["deadline", "dang ky", "dieu kien", "khi nao", "o dau", "tham gia", "chi phi"]
COMPLAINT_TERMS = ["kho dung", "cham", "te", "khong ro", "that vong", "phan nan"]
RISK_TERMS = ["lua dao", "to cao", "tay chay", "phot", "scam", "kien", "lo thong tin"]
CRITICAL_TERMS = ["du lieu ca nhan", "phap ly", "de doa", "quay roi", "bao mat"]


def _contains_any(text: str, terms: list[str]) -> list[str]:
    lowered = text.casefold()
    return [term for term in terms if term.casefold() in lowered]


class RuleClassifier:
    def __init__(self, matcher: QueryPackMatcher):
        self.matcher = matcher

    def classify(self, request: ClassificationRequest) -> ClassificationResult:
        text = request.text.strip()
        relevance = self.matcher.match(text)

        positive = _contains_any(text, POSITIVE_TERMS)
        questions = _contains_any(text, QUESTION_TERMS)
        complaints = _contains_any(text, COMPLAINT_TERMS)
        risks = _contains_any(text, RISK_TERMS)
        criticals = _contains_any(text, CRITICAL_TERMS)

        sentiment_label = "neutral"
        if positive and not complaints and not risks:
            sentiment_label = "positive"
        elif complaints or risks or criticals:
            sentiment_label = "negative"
        elif positive and (complaints or risks):
            sentiment_label = "mixed"

        signal_type = "noise"
        if risks or criticals:
            signal_type = "risk"
        elif complaints:
            signal_type = "complaint"
        elif questions:
            signal_type = "question"
        elif positive:
            signal_type = "praise"
        elif relevance["label"] in {"relevant", "possibly_relevant"}:
            signal_type = "opportunity"

        danger_score = 0
        danger_level = "none"
        risk_type = None
        if complaints:
            danger_score = 35
            danger_level = "low"
            risk_type = "service_quality"
        if risks:
            danger_score = 72
            danger_level = "high"
            risk_type = "misinformation"
        if criticals:
            danger_score = 92
            danger_level = "critical"
            risk_type = "policy_legal"

        review_status = "auto_accepted"
        if relevance["needs_review"] or danger_level in {"medium", "high", "critical"}:
            review_status = "needs_review"

        action_type = "monitoring"
        priority = "low"
        instruction = "Theo doi them trong daily digest."
        if signal_type == "question":
            action_type = "content_creation"
            priority = "medium"
            instruction = "Dua cau hoi lap lai vao FAQ hoac noi dung giai thich."
        elif signal_type == "praise":
            action_type = "amplification"
            priority = "low"
            instruction = "Can nhac khai thac tin hieu tich cuc neu quote policy cho phep."
        elif danger_level in {"high", "critical"}:
            action_type = "escalation"
            priority = "high"
            instruction = "Chuyen nguoi phu trach review bang chung truoc khi hanh dong."
        elif signal_type == "complaint":
            action_type = "product_fix"
            priority = "medium"
            instruction = "Tong hop phan nan va gan owner xu ly."

        safe_excerpt = text[:240]
        evidence = Evidence(
            item_id=request.item_id,
            source_id=request.source_id,
            platform=request.platform,
            item_type=request.item_type,
            published_at=request.published_at,
            permalink=request.permalink,
            import_batch_id=request.import_batch_id,
            safe_excerpt=safe_excerpt,
        )

        return ClassificationResult(
            relevance=relevance,
            sentiment={"label": sentiment_label, "confidence": 0.65},
            voice={
                "signal_type": signal_type,
                "signal_polarity": sentiment_label,
                "topic": "general",
                "audience_need": " ".join(questions) if questions else None,
                "opportunity_score": 70 if signal_type in {"praise", "opportunity"} else 0,
                "summary": self._summary(signal_type),
            },
            risk={
                "danger_level": danger_level,
                "danger_score": danger_score,
                "risk_type": risk_type,
                "velocity": "stable",
                "evidence": ", ".join(risks + criticals) or "Khong co tin hieu rui ro manh.",
            },
            recommendation={
                "summary": instruction,
                "actions": [
                    {
                        "type": action_type,
                        "priority": priority,
                        "owner_suggestion": "Comms",
                        "deadline_suggestion": "24h" if priority == "high" else "3 ngay",
                        "instruction": instruction,
                    }
                ],
            },
            evidence=evidence,
            review_status=review_status,
        )

    @staticmethod
    def _summary(signal_type: str) -> str:
        return {
            "risk": "Noi dung co dau hieu rui ro can review.",
            "complaint": "Noi dung phan nan hoac gop y trai nghiem.",
            "question": "Nguoi ngoai dang hoi thong tin ve VSF.",
            "praise": "Noi dung co tin hieu tich cuc ve VSF.",
            "opportunity": "Noi dung co the la co hoi insight hoac truyen thong.",
            "noise": "Noi dung chua du tin hieu lien quan VSF.",
        }.get(signal_type, "Tin hieu can theo doi.")
