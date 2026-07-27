from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class TopicFilterConfigError(ValueError):
    pass


@dataclass(frozen=True)
class TopicMatch:
    topic_id: str
    topic_label: str
    matched_terms: tuple[str, ...]
    matched_groups: tuple[str, ...]

    @property
    def matched(self) -> bool:
        return bool(self.matched_terms)

    def as_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic_id,
            "topic_label": self.topic_label,
            "matched_terms": list(self.matched_terms),
            "matched_groups": list(self.matched_groups),
        }


@dataclass(frozen=True)
class _Keyword:
    group: str
    display: str
    normalized: str


class TopicKeywordFilter:
    def __init__(
        self,
        *,
        topic_id: str,
        topic_label: str,
        keywords: tuple[_Keyword, ...],
    ) -> None:
        if not topic_id or not topic_label or not keywords:
            raise TopicFilterConfigError("Topic filter requires an id, label, and keywords.")
        self.topic_id = topic_id
        self.topic_label = topic_label
        self._keywords = keywords

    @classmethod
    def from_yaml(cls, path: Path) -> TopicKeywordFilter:
        if not path.is_file():
            raise TopicFilterConfigError(f"Khong tim thay cau hinh bo loc: {path}")
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = yaml.safe_load(handle) or {}
        except (OSError, yaml.YAMLError) as exc:
            raise TopicFilterConfigError(f"Khong doc duoc cau hinh bo loc: {path}") from exc

        topic = payload.get("topic")
        if not isinstance(topic, dict):
            raise TopicFilterConfigError("Cau hinh bo loc phai co object topic.")
        groups = topic.get("keyword_groups")
        if not isinstance(groups, dict):
            raise TopicFilterConfigError("Cau hinh bo loc phai co keyword_groups.")

        keywords: list[_Keyword] = []
        seen: set[str] = set()
        for group, terms in groups.items():
            if not isinstance(group, str) or not isinstance(terms, list):
                raise TopicFilterConfigError("Moi nhom tu khoa phai la mot danh sach.")
            for term in terms:
                if not isinstance(term, str):
                    raise TopicFilterConfigError("Tu khoa phai la chuoi.")
                normalized = normalize_topic_text(term)
                if not normalized or normalized in seen:
                    continue
                seen.add(normalized)
                keywords.append(
                    _Keyword(
                        group=group,
                        display=term.strip(),
                        normalized=normalized,
                    )
                )

        return cls(
            topic_id=str(topic.get("id") or "").strip(),
            topic_label=str(topic.get("label") or "").strip(),
            keywords=tuple(keywords),
        )

    def match(self, text: str | None) -> TopicMatch:
        normalized_text = normalize_topic_text(text or "")
        searchable = f" {normalized_text} "
        matched_terms: list[str] = []
        matched_groups: list[str] = []
        for keyword in self._keywords:
            if f" {keyword.normalized} " not in searchable:
                continue
            matched_terms.append(keyword.display)
            if keyword.group not in matched_groups:
                matched_groups.append(keyword.group)
        return TopicMatch(
            topic_id=self.topic_id,
            topic_label=self.topic_label,
            matched_terms=tuple(matched_terms),
            matched_groups=tuple(matched_groups),
        )

    def describe(self) -> dict[str, str]:
        return {"topic": self.topic_id, "topic_label": self.topic_label}


def normalize_topic_text(value: str) -> str:
    folded = unicodedata.normalize("NFD", value.casefold().replace("đ", "d"))
    without_marks = "".join(
        character
        for character in folded
        if unicodedata.category(character) != "Mn"
    )
    words = re.sub(r"[^a-z0-9]+", " ", without_marks)
    return " ".join(words.split())
