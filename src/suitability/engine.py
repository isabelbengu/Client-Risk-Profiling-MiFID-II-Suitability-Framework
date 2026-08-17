"""The assessment pipeline.

    completeness  ->  score  ->  coherence  ->  combine  ->  coherence  ->  match

Each stage records what it did. The pipeline never silently upgrades a client:
every control can only hold a profile still or move it down, and any upward
movement has to come from a documented change to an answer (see ``overrides`` in
``config/scoring.yaml``).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from . import consistency, mapping, scoring
from .config import Config, load_config
from .models import ClientCase, ControlHit, Outcome, Recommendation


def _digest(answers: dict) -> str:
    payload = json.dumps(answers, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def assess(case: ClientCase, cfg: Config | None = None) -> Outcome:
    cfg = cfg or load_config()

    if case.group_members:
        return _assess_group(case, cfg)

    answers = case.answers
    controls: list[ControlHit] = []
    messages: list[str] = []

    # -- 0. completeness (Art. 54(8) DR 2017/565) ---------------------------
    completeness = consistency.check_completeness(cfg, answers)
    controls.extend(completeness)

    # -- 1. dimension scores ------------------------------------------------
    dims = scoring.score_all(cfg, answers)

    # -- 2. coherence controls before combination ---------------------------
    controls.extend(consistency.apply_pre_combination(cfg, answers, dims))

    # -- 3. the binding constraint ------------------------------------------
    final_band, binding = consistency.combine(cfg, dims)

    # -- 4. coherence controls on the combined band -------------------------
    final_band, post = consistency.apply_post_combination(cfg, case, dims, final_band)
    controls.extend(post)

    if any(c.severity == "block" for c in controls):
        final_band = 0

    # -- 5. product match ---------------------------------------------------
    knowledge_band = dims["knowledge"].band if "knowledge" in dims else 5
    gate = mapping.complexity_gate_tier(cfg, knowledge_band, answers.get("A1", "retail"))

    if final_band == 0:
        recommendation = Recommendation(
            portfolio_id=None,
            name=None,
            risk_band=0,
            rationale=[c.effect for c in controls if c.severity == "block"]
            or ["No investment portfolio may be recommended."],
        )
    else:
        recommendation = mapping.select(cfg, answers, final_band, knowledge_band)

    # -- 6. status ----------------------------------------------------------
    if any(c.severity == "block" for c in controls):
        status = "blocked"
        messages.append(
            "No investment service or financial instrument may be recommended until the "
            "blocking control is resolved (Art. 54(8) and 54(10) DR 2017/565)."
        )
    elif recommendation.portfolio_id is None:
        status = "no_suitable_product"
    elif any(c.severity == "refer" for c in controls):
        status = "referred"
        messages.append(
            "A material inconsistency was found in the information collected. The client must be "
            "contacted to resolve it before the recommendation is issued (ESMA GL4 para 51)."
        )
    else:
        status = "recommended"

    if recommendation.risk_band and recommendation.risk_band < final_band:
        final_band_effective = recommendation.risk_band
    else:
        final_band_effective = final_band

    return Outcome(
        client_ref=case.client_ref,
        assessed_at=case.assessed_at or _now(),
        status=status,
        dimensions=dims,
        binding_constraint=binding,
        final_band=final_band_effective,
        complexity_gate_tier=gate,
        controls=controls,
        recommendation=recommendation,
        config_versions=cfg.versions,
        answers_digest=_digest(answers),
        messages=messages,
    )


def _assess_group(case: ClientCase, cfg: Config) -> Outcome:
    """Two or more natural persons, assessed individually then combined.

    ESMA GL6 paras 69-70: the most prudent of the individual profiles governs,
    and profiles are not averaged.
    """
    member_outcomes = [assess(m, cfg) for m in case.group_members]
    member_results = [(o.client_ref, o.dimensions, o.final_band) for o in member_outcomes]
    dims, _band, hits = consistency.most_prudent(cfg, member_results)

    controls: list[ControlHit] = list(hits)
    for o in member_outcomes:
        for c in o.controls:
            c.detail = f"[{o.client_ref}] {c.detail}".strip()
            controls.append(c)

    final_band, binding = consistency.combine(cfg, dims)
    final_band = min([final_band] + [o.final_band for o in member_outcomes])

    if any(c.severity == "block" for c in controls):
        final_band = 0

    # The representative's knowledge governs where one is designated
    # (GL6 para 67); otherwise the least knowledgeable person's does.
    knowledge_band = dims["knowledge"].band if "knowledge" in dims else 1
    # Mandate-level answers (amount invested, horizon, sustainability preferences)
    # are taken from the group case; anything absent falls back to the first
    # member so that the product filters still have inputs.
    answers = dict(case.group_members[0].answers)
    answers.update({k: v for k, v in (case.answers or {}).items() if v not in (None, "", [])})

    if final_band == 0:
        recommendation = Recommendation(portfolio_id=None, name=None, risk_band=0,
                                        rationale=["No investment portfolio may be recommended."])
        status = "blocked"
    else:
        recommendation = mapping.select(cfg, answers, final_band, knowledge_band)
        status = (
            "no_suitable_product"
            if recommendation.portfolio_id is None
            else ("referred" if any(c.severity == "refer" for c in controls) else "recommended")
        )

    return Outcome(
        client_ref=case.client_ref,
        assessed_at=case.assessed_at or _now(),
        status=status,
        dimensions=dims,
        binding_constraint=binding,
        final_band=recommendation.risk_band or final_band,
        complexity_gate_tier=mapping.complexity_gate_tier(cfg, knowledge_band, answers.get("A1", "retail")),
        controls=controls,
        recommendation=recommendation,
        config_versions=cfg.versions,
        answers_digest=_digest({m.client_ref: m.answers for m in case.group_members}),
        messages=[
            "Assessed as a group. The most prudent individual profile governs each dimension; "
            "profiles were not averaged (ESMA GL6 paras 69-70)."
        ],
    )
