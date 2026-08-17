"""Dimension scoring.

Produces, for each dimension, a 0-100 score and a 1-5 band, together with the
component values that produced it. Nothing is rounded away: the component
values are carried into the audit record so that a supervisor can see how a
client's answers became a band (ESMA GL12 para 111 - "how that information was
used and interpreted to define the client's risk profile").
"""

from __future__ import annotations

from typing import Any

from .config import Config
from .models import ComponentResult, DimensionResult


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _answered(answers: dict[str, Any], qid: str) -> bool:
    return qid in answers and answers[qid] not in (None, "", [])


def _option_scores(cfg: Config, answers: dict[str, Any], qid: str) -> list[float]:
    """All option scores selected for a question (single or multi)."""
    if not _answered(answers, qid):
        return []
    value = answers[qid]
    values = value if isinstance(value, list) else [value]
    out: list[float] = []
    for v in values:
        opt = cfg.option(qid, v)
        if opt is None:
            continue
        score = opt.get("score")
        if score is not None:
            out.append(float(score))
    return out


def _weight_override(cfg: Config, answers: dict[str, Any], qids: list[str]) -> bool:
    """True when every selected option in the component carries weight_override: 0."""
    seen = False
    for qid in qids:
        if not _answered(answers, qid):
            continue
        value = answers[qid]
        values = value if isinstance(value, list) else [value]
        for v in values:
            opt = cfg.option(qid, v) or {}
            if opt.get("weight_override") == 0:
                seen = True
            else:
                return False
    return seen


def _component_value(cfg: Config, answers: dict[str, Any], comp: dict[str, Any]) -> float | None:
    method = comp["method"]
    qids = comp["questions"]

    if _weight_override(cfg, answers, qids):
        return None  # component drops out and its weight is redistributed

    if method == "proportion_correct":
        total = 0
        correct = 0
        for qid in qids:
            opts = cfg.question(qid).get("options", [])
            if not any("correct" in o for o in opts):
                continue
            total += 1
            if not _answered(answers, qid):
                continue
            opt = cfg.option(qid, answers[qid]) or {}
            if opt.get("correct") is True:
                correct += 1
        return 0.0 if total == 0 else 100.0 * correct / total

    if method == "sum_capped":
        s = sum(sum(_option_scores(cfg, answers, qid)) for qid in qids)
        return min(100.0, s)

    if method == "mean":
        vals: list[float] = []
        for qid in qids:
            vals.extend(_option_scores(cfg, answers, qid))
        return sum(vals) / len(vals) if vals else None

    raise ValueError(f"unknown scoring method {method}")


def comprehension_correct(cfg: Config, answers: dict[str, Any]) -> tuple[int, int]:
    """(correct, total) across the objective comprehension items."""
    total = 0
    correct = 0
    for section in cfg.questionnaire["sections"]:
        for q in section.get("questions", []):
            if q.get("scoring_role") != "comprehension":
                continue
            total += 1
            if not _answered(answers, q["id"]):
                continue
            opt = cfg.option(q["id"], answers[q["id"]]) or {}
            if opt.get("correct") is True:
                correct += 1
    return correct, total


def self_rating(cfg: Config, answers: dict[str, Any]) -> int | None:
    for section in cfg.questionnaire["sections"]:
        for q in section.get("questions", []):
            if q.get("scoring_role") != "cross_check_only":
                continue
            if not _answered(answers, q["id"]):
                return None
            opt = cfg.option(q["id"], answers[q["id"]]) or {}
            return opt.get("self_rating")
    return None


def max_experienced_tier(cfg: Config, answers: dict[str, Any]) -> int:
    """Highest complexity tier the client has actually invested in (B2)."""
    value = answers.get("B2")
    if not value:
        return 0
    values = value if isinstance(value, list) else [value]
    tiers = [(cfg.option("B2", v) or {}).get("tier", 0) for v in values]
    return max([int(t) for t in tiers] or [0])


# ---------------------------------------------------------------------------
# scored dimensions
# ---------------------------------------------------------------------------

def score_dimension(cfg: Config, answers: dict[str, Any], name: str) -> DimensionResult:
    spec = cfg.scoring["dimensions"][name]
    components: list[ComponentResult] = []
    weighted_total = 0.0
    weight_used = 0.0

    for comp_name, comp in (spec.get("components") or {}).items():
        val = _component_value(cfg, answers, comp)
        components.append(
            ComponentResult(name=comp_name, weight=float(comp["weight"]), value=val, questions=list(comp["questions"]))
        )
        if val is None or comp["weight"] == 0:
            continue
        weighted_total += val * float(comp["weight"])
        weight_used += float(comp["weight"])

    score = weighted_total / weight_used if weight_used > 0 else None
    band = cfg.band_for_score(score) if score is not None else 1

    return DimensionResult(
        name=name,
        label=spec.get("label", name),
        score=score,
        band=band,
        raw_band=band,
        components=components,
    )


def band_from_source(cfg: Config, answers: dict[str, Any], name: str) -> DimensionResult:
    """Dimensions whose band comes directly from an answer attribute."""
    spec = cfg.scoring["dimensions"][name]
    src = spec["band_source"]
    opt = cfg.option(src["question"], answers.get(src["question"])) or {}
    band = int(opt.get(src["attribute"], 1))
    raw = band
    notes: list[str] = []

    for red in src.get("reductions", []) or []:
        cond = red["when"]
        if all(answers.get(q) == v for q, v in cond.items()):
            band = max(1, band - int(red["minus"]))
            notes.append(
                f"reduced by {red['minus']} because " + ", ".join(f"{q}={v}" for q, v in cond.items())
            )

    return DimensionResult(
        name=name,
        label=spec.get("label", name),
        score=None,
        band=band,
        raw_band=raw,
        notes=notes,
    )


def score_all(cfg: Config, answers: dict[str, Any]) -> dict[str, DimensionResult]:
    """Score every dimension defined in the configuration."""
    results: dict[str, DimensionResult] = {}
    for name, spec in cfg.scoring["dimensions"].items():
        if spec.get("band_source") and not spec.get("components"):
            results[name] = band_from_source(cfg, answers, name)
        elif spec.get("band_source"):
            results[name] = band_from_source(cfg, answers, name)
        else:
            results[name] = score_dimension(cfg, answers, name)

    # --- knowledge: objective comprehension ceiling (GL4 paras 46, 52) ------
    k = results.get("knowledge")
    if k is not None:
        ceiling_cfg = cfg.scoring["dimensions"]["knowledge"].get("comprehension_ceiling", {})
        if ceiling_cfg.get("enabled"):
            correct, _total = comprehension_correct(cfg, answers)
            ceiling = int(ceiling_cfg["map"].get(correct, 5))
            if k.band > ceiling:
                k.caps_applied.append(
                    f"knowledge band {k.band} capped at {ceiling}: {correct} of 6 comprehension items correct"
                )
                k.band = ceiling
        # experience ceiling: a client cannot be gated into a tier more than one
        # step above anything they have actually held
        tier = max_experienced_tier(cfg, answers)
        gate = cfg.scoring["complexity_gate"]
        if gate.get(k.band, 0) > tier + 1:
            for band in sorted(gate, reverse=True):
                if gate[band] <= tier + 1:
                    if band < k.band:
                        k.caps_applied.append(
                            f"knowledge band {k.band} capped at {band}: highest instrument tier actually held is {tier}"
                        )
                        k.band = band
                    break

    return results
