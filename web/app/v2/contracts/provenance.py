"""Estruturas canônicas mínimas de provenance do V2."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

OriginKind = Literal["human", "ai_assisted", "ai_generated", "system", "legacy_unknown"]
ProvenanceConfidence = Literal["confirmed", "derived", "legacy_unknown"]
ProvenanceMixKind = Literal[
    "human_only",
    "ai_generated_only",
    "ai_assisted_only",
    "system_only",
    "legacy_unknown_only",
    "human_ai_mix",
    "human_with_unknown",
    "ai_with_unknown",
    "mixed",
    "unclassified",
]
ProvenanceQuality = Literal["confirmed", "partial", "legacy_unknown", "system_only", "unclassified"]

_PRIMARY_ORIGIN_PRIORITY: dict[str, int] = {
    "human": 5,
    "ai_generated": 4,
    "ai_assisted": 3,
    "legacy_unknown": 2,
    "system": 1,
}


class ProvenanceEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    origin_kind: OriginKind
    source: str
    confidence: ProvenanceConfidence = "confirmed"
    signal_count: int = Field(default=1, ge=0)
    details: str | None = None


class ContentOriginSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_name: Literal["ContentOriginSummaryV1"] = "ContentOriginSummaryV1"
    contract_version: str = "v1"
    primary_origin: OriginKind = "legacy_unknown"
    mix_kind: ProvenanceMixKind = "unclassified"
    quality: ProvenanceQuality = "unclassified"
    has_human_inputs: bool = False
    has_ai_outputs: bool = False
    has_ai_assisted_content: bool = False
    has_system_content: bool = False
    has_legacy_unknown_content: bool = False
    human_signal_count: int = Field(default=0, ge=0)
    ai_generated_signal_count: int = Field(default=0, ge=0)
    ai_assisted_signal_count: int = Field(default=0, ge=0)
    system_signal_count: int = Field(default=0, ge=0)
    legacy_unknown_signal_count: int = Field(default=0, ge=0)
    total_signal_count: int = Field(default=0, ge=0)
    sources: list[str] = Field(default_factory=list)
    entries: list[ProvenanceEntry] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


def _aggregate_signal_counts(entries: list[ProvenanceEntry]) -> dict[str, int]:
    counts: dict[str, int] = {
        "human": 0,
        "ai_generated": 0,
        "ai_assisted": 0,
        "system": 0,
        "legacy_unknown": 0,
    }
    for entry in entries:
        counts[entry.origin_kind] = counts.get(entry.origin_kind, 0) + max(0, int(entry.signal_count))
    return counts


def _resolve_primary_origin(counts: dict[str, int]) -> OriginKind:
    ranked = sorted(
        counts.items(),
        key=lambda item: (int(item[1]), _PRIMARY_ORIGIN_PRIORITY.get(item[0], 0)),
        reverse=True,
    )
    top_kind, top_count = ranked[0]
    if top_count <= 0:
        return "legacy_unknown"
    return top_kind  # type: ignore[return-value]


def _resolve_mix_kind(counts: dict[str, int]) -> ProvenanceMixKind:
    present = {kind for kind, count in counts.items() if count > 0}
    if not present:
        return "unclassified"
    if present == {"human"}:
        return "human_only"
    if present == {"ai_generated"}:
        return "ai_generated_only"
    if present == {"ai_assisted"}:
        return "ai_assisted_only"
    if present == {"system"}:
        return "system_only"
    if present == {"legacy_unknown"}:
        return "legacy_unknown_only"

    ai_present = bool({"ai_generated", "ai_assisted"} & present)
    if present == {"human", "ai_generated"} or present == {"human", "ai_assisted"} or present == {"human", "ai_generated", "ai_assisted"}:
        return "human_ai_mix"
    if present == {"human", "legacy_unknown"}:
        return "human_with_unknown"
    if ai_present and present <= {"ai_generated", "ai_assisted", "legacy_unknown"} and "legacy_unknown" in present:
        return "ai_with_unknown"
    return "mixed"


def _resolve_quality(counts: dict[str, int]) -> ProvenanceQuality:
    total = sum(counts.values())
    if total <= 0:
        return "unclassified"
    if counts["legacy_unknown"] > 0 and counts["human"] == 0 and counts["ai_generated"] == 0 and counts["ai_assisted"] == 0 and counts["system"] == 0:
        return "legacy_unknown"
    if counts["system"] > 0 and total == counts["system"]:
        return "system_only"
    if counts["legacy_unknown"] > 0:
        return "partial"
    return "confirmed"


def build_content_origin_summary(
    *,
    entries: list[ProvenanceEntry],
    notes: list[str] | None = None,
) -> ContentOriginSummary:
    counts = _aggregate_signal_counts(entries)
    total_signal_count = sum(counts.values())
    sources = sorted({entry.source for entry in entries if entry.source})

    return ContentOriginSummary(
        primary_origin=_resolve_primary_origin(counts),
        mix_kind=_resolve_mix_kind(counts),
        quality=_resolve_quality(counts),
        has_human_inputs=counts["human"] > 0,
        has_ai_outputs=counts["ai_generated"] > 0,
        has_ai_assisted_content=counts["ai_assisted"] > 0,
        has_system_content=counts["system"] > 0,
        has_legacy_unknown_content=counts["legacy_unknown"] > 0,
        human_signal_count=counts["human"],
        ai_generated_signal_count=counts["ai_generated"],
        ai_assisted_signal_count=counts["ai_assisted"],
        system_signal_count=counts["system"],
        legacy_unknown_signal_count=counts["legacy_unknown"],
        total_signal_count=total_signal_count,
        sources=sources,
        entries=list(entries),
        notes=list(notes or []),
    )


__all__ = [
    "ContentOriginSummary",
    "OriginKind",
    "ProvenanceConfidence",
    "ProvenanceEntry",
    "ProvenanceMixKind",
    "ProvenanceQuality",
    "build_content_origin_summary",
]
