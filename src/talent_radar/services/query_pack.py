from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class QueryPack:
    entity: str
    version: str
    exact: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    ecosystem_slang: list[str] = field(default_factory=list)
    location_indirect: list[str] = field(default_factory=list)
    program_indirect: list[str] = field(default_factory=list)
    context_anchors: list[str] = field(default_factory=list)
    exclusions: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QueryPack":
        return cls(
            entity=str(data.get("entity", "VSF")),
            version=str(data.get("version", "1.0")),
            exact=list(data.get("exact") or []),
            aliases=list(data.get("aliases") or []),
            ecosystem_slang=list(data.get("ecosystem_slang") or []),
            location_indirect=list(data.get("location_indirect") or []),
            program_indirect=list(data.get("program_indirect") or []),
            context_anchors=list(data.get("context_anchors") or []),
            exclusions=list(data.get("exclusions") or []),
        )


def load_query_pack(path: Path) -> QueryPack:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return QueryPack.from_dict(data)


def _contains(text: str, terms: list[str]) -> list[str]:
    lowered = text.casefold()
    return [term for term in terms if term.casefold() in lowered]


class QueryPackMatcher:
    def __init__(self, pack: QueryPack):
        self.pack = pack

    def match(self, text: str) -> dict[str, Any]:
        exact = _contains(text, self.pack.exact)
        aliases = _contains(text, self.pack.aliases)
        slang = _contains(text, self.pack.ecosystem_slang)
        locations = _contains(text, self.pack.location_indirect)
        indirect = _contains(text, self.pack.program_indirect)
        anchors = _contains(text, self.pack.context_anchors)
        exclusions = _contains(text, self.pack.exclusions)

        matched_terms = exact + aliases + slang + locations + indirect
        reasons: list[str] = []
        score = 0.0
        label = "irrelevant"
        needs_review = False

        if exclusions and not exact:
            reasons.append("exclusion matched without a strong VSF anchor")
            return {
                "label": "irrelevant",
                "score": 0.0,
                "matched_terms": matched_terms,
                "exclusions": exclusions,
                "context_anchors": anchors,
                "reasons": reasons,
                "needs_review": False,
            }

        if exact:
            score += 0.8
            label = "relevant"
            reasons.append("official name or exact entity term matched")

        if aliases:
            score += 0.45
            reasons.append("alias matched")
            if not anchors and not exact:
                label = "possibly_relevant"
                needs_review = True

        if slang or locations or indirect:
            score += 0.25
            reasons.append("slang, ecosystem, location, or indirect term matched")
            if anchors or exact:
                score += 0.2
                label = "possibly_relevant" if not exact else label
            else:
                label = "possibly_relevant"
                needs_review = True

        if anchors:
            score += 0.1
            reasons.append("context anchor matched")

        if not matched_terms:
            reasons.append("no query pack terms matched")

        score = min(score, 1.0)
        if score >= 0.75 and exact:
            label = "relevant"
        elif score >= 0.25 and label == "irrelevant":
            label = "possibly_relevant"
            needs_review = True

        return {
            "label": label,
            "score": round(score, 3),
            "matched_terms": matched_terms,
            "exclusions": exclusions,
            "context_anchors": anchors,
            "reasons": reasons,
            "needs_review": needs_review,
        }
