"""Configuration loading and validation.

The engine holds no hard-coded questions, scores, bands or portfolios. Everything
that determines an outcome lives in ``config/*.yaml`` and is version-stamped, so
that a past decision can be reproduced from the version recorded in its audit
entry (ESMA GL8 para 90 on algorithm documentation and change management, and
GL12 para 111 on recording how client information was interpreted).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import yaml

DEFAULT_CONFIG_DIR = os.environ.get(
    "SUITABILITY_CONFIG_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "config"),
)


class ConfigError(ValueError):
    """Raised when the configuration is internally inconsistent."""


@dataclass
class Config:
    questionnaire: dict[str, Any]
    scoring: dict[str, Any]
    portfolios: dict[str, Any]

    # ---- indexes -----------------------------------------------------------
    def __post_init__(self) -> None:
        self._questions: dict[str, dict[str, Any]] = {}
        self._section_of: dict[str, str] = {}
        for section in self.questionnaire["sections"]:
            for q in section.get("questions", []):
                if q["id"] in self._questions:
                    raise ConfigError(f"duplicate question id {q['id']}")
                self._questions[q["id"]] = q
                self._section_of[q["id"]] = section["id"]
        self._portfolios = {p["id"]: p for p in self.portfolios["portfolios"]}
        self._validate()

    # ---- accessors ---------------------------------------------------------
    @property
    def versions(self) -> dict[str, str]:
        return {
            "questionnaire": self.questionnaire["meta"]["version"],
            "scoring": self.scoring["meta"]["version"],
            "portfolios": self.portfolios["meta"]["version"],
        }

    def question(self, qid: str) -> dict[str, Any]:
        try:
            return self._questions[qid]
        except KeyError as exc:  # pragma: no cover - defensive
            raise ConfigError(f"unknown question {qid}") from exc

    def option(self, qid: str, value: Any) -> dict[str, Any] | None:
        for opt in self.question(qid).get("options", []) or []:
            if opt["value"] == value:
                return opt
        return None

    def required_questions(self, client_category: str = "retail") -> list[str]:
        """Questions that must be answered for this client category.

        Art. 54(3) DR 2017/565 lets a firm presume knowledge and experience for
        professional clients, and the ability to bear risk for per se
        professional clients; ESMA GL3 para 41 keeps investment objectives in
        scope regardless.
        """
        presumption = self.scoring["professional_presumptions"].get(client_category, {})
        needed_dims = set(presumption.get("still_required", []))
        out: list[str] = []
        for section in self.questionnaire["sections"]:
            dim = section.get("dimension")
            if section.get("scored") and dim and dim not in needed_dims:
                continue
            for q in section.get("questions", []):
                if not q.get("required"):
                    continue
                if q.get("depends_on"):
                    continue  # conditional questions are checked at answer time
                out.append(q["id"])
        return out

    def portfolio(self, pid: str) -> dict[str, Any]:
        return self._portfolios[pid]

    def all_portfolios(self) -> list[dict[str, Any]]:
        return list(self.portfolios["portfolios"])

    def band_for_score(self, score: float) -> int:
        for band in self.scoring["bands"]:
            if band["min_score"] <= score <= band["max_score"]:
                return int(band["band"])
        raise ConfigError(f"score {score} outside band table")

    def band_label(self, band: int) -> str:
        rb = self.portfolios["risk_bands"].get(band)
        if rb:
            return rb["label"]
        return str(band)

    def stress_loss(self, band: int) -> float:
        rb = self.portfolios["risk_bands"].get(band, {})
        return float(rb.get("stress_loss_pct", 0.0))

    def control(self, cid: str) -> dict[str, Any]:
        for c in self.scoring["coherence_controls"]:
            if c["id"] == cid:
                return c
        raise ConfigError(f"unknown control {cid}")

    # ---- validation --------------------------------------------------------
    def _validate(self) -> None:
        # every scored dimension's component questions must exist
        for dim_name, dim in self.scoring["dimensions"].items():
            for comp_name, comp in (dim.get("components") or {}).items():
                for qid in comp["questions"]:
                    if qid not in self._questions:
                        raise ConfigError(
                            f"dimension {dim_name}.{comp_name} references unknown question {qid}"
                        )
            weights = [c["weight"] for c in (dim.get("components") or {}).values()]
            if weights and abs(sum(weights) - 1.0) > 1e-6:
                raise ConfigError(f"dimension {dim_name} weights sum to {sum(weights)}, expected 1.0")

        # bands must be contiguous and cover 0-100
        bands = sorted(self.scoring["bands"], key=lambda b: b["min_score"])
        if bands[0]["min_score"] != 0 or bands[-1]["max_score"] != 100:
            raise ConfigError("band table must cover 0-100")

        # every risk band with portfolios must have a stress loss defined
        for p in self.portfolios["portfolios"]:
            rb = self.portfolios["risk_bands"].get(p["risk_band"])
            if rb is None or "stress_loss_pct" not in rb:
                raise ConfigError(f"portfolio {p['id']} has no stress loss for band {p['risk_band']}")
            if p["complexity_tier"] not in self.portfolios["complexity_tiers"]:
                raise ConfigError(f"portfolio {p['id']} has unknown complexity tier")

        # the complexity gate must map every band
        gate = self.scoring["complexity_gate"]
        for band in range(1, 6):
            if band not in gate:
                raise ConfigError(f"complexity gate missing band {band}")


def load_config(config_dir: str | None = None) -> Config:
    d = config_dir or DEFAULT_CONFIG_DIR
    def _read(name: str) -> dict[str, Any]:
        with open(os.path.join(d, name), "r", encoding="utf-8") as fh:
            return yaml.safe_load(fh)

    return Config(
        questionnaire=_read("questionnaire.yaml"),
        scoring=_read("scoring.yaml"),
        portfolios=_read("portfolios.yaml"),
    )
