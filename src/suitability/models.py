"""Domain objects for the suitability assessment.

Every object here is deliberately serialisable: the audit record required by
ESMA GL12 para 111 is built by dumping these structures, so nothing that
influences the outcome may live only in local variables.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


Severity = str  # "block" | "refer" | "cap" | "note"


@dataclass
class ClientCase:
    """The raw input to an assessment."""

    client_ref: str
    answers: dict[str, Any]
    assessed_at: str
    adviser_ref: str | None = None
    previous_final_band: int | None = None
    profile_updated_days_ago: int | None = None
    # For groups: a list of ClientCase-like answer sets, assessed individually
    # and combined under the most-prudent rule (ESMA GL6 paras 69-70).
    group_members: list["ClientCase"] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


@dataclass
class ComponentResult:
    name: str
    weight: float
    value: float | None
    questions: list[str]


@dataclass
class DimensionResult:
    name: str
    label: str
    score: float | None
    band: int
    components: list[ComponentResult] = field(default_factory=list)
    caps_applied: list[str] = field(default_factory=list)
    raw_band: int | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "label": self.label,
            "score": None if self.score is None else round(self.score, 2),
            "raw_band": self.raw_band,
            "band": self.band,
            "caps_applied": self.caps_applied,
            "notes": self.notes,
            "components": [
                {
                    "name": c.name,
                    "weight": c.weight,
                    "value": None if c.value is None else round(c.value, 2),
                    "questions": c.questions,
                }
                for c in self.components
            ],
        }


@dataclass
class ControlHit:
    id: str
    name: str
    severity: Severity
    basis: str
    effect: str
    detail: str = ""
    client_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PortfolioCandidate:
    portfolio_id: str
    name: str
    risk_band: int
    total_cost_bps: int
    complexity_tier: int
    meets_sustainability: bool
    excluded_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Recommendation:
    portfolio_id: str | None
    name: str | None
    risk_band: int
    rationale: list[str] = field(default_factory=list)
    considered: list[PortfolioCandidate] = field(default_factory=list)
    sustainability_status: str = "not_applicable"
    sustainability_detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "portfolio_id": self.portfolio_id,
            "name": self.name,
            "risk_band": self.risk_band,
            "rationale": self.rationale,
            "sustainability_status": self.sustainability_status,
            "sustainability_detail": self.sustainability_detail,
            "considered": [c.to_dict() for c in self.considered],
        }


@dataclass
class Outcome:
    """The complete, auditable result of one assessment."""

    client_ref: str
    assessed_at: str
    status: str  # "recommended" | "referred" | "blocked" | "no_suitable_product"
    dimensions: dict[str, DimensionResult]
    binding_constraint: str
    final_band: int
    complexity_gate_tier: int
    controls: list[ControlHit]
    recommendation: Recommendation
    config_versions: dict[str, str]
    answers_digest: str = ""
    messages: list[str] = field(default_factory=list)

    @property
    def blocking(self) -> list[ControlHit]:
        return [c for c in self.controls if c.severity == "block"]

    @property
    def referrals(self) -> list[ControlHit]:
        return [c for c in self.controls if c.severity == "refer"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "client_ref": self.client_ref,
            "assessed_at": self.assessed_at,
            "status": self.status,
            "final_band": self.final_band,
            "binding_constraint": self.binding_constraint,
            "complexity_gate_tier": self.complexity_gate_tier,
            "dimensions": {k: v.to_dict() for k, v in self.dimensions.items()},
            "controls": [c.to_dict() for c in self.controls],
            "recommendation": self.recommendation.to_dict(),
            "config_versions": self.config_versions,
            "answers_digest": self.answers_digest,
            "messages": self.messages,
        }
