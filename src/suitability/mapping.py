"""Matching the client profile to a model portfolio.

Order of operations, per ESMA GL8 para 81: the Art. 25(2) assessment is
completed first - knowledge and experience, financial situation, and the other
investment objectives - and only then are sustainability preferences applied to
the range of products already found suitable. Sustainability preferences can
never widen that range.

Selection among the products that survive both filters follows GL9 paras 91-95
and Art. 54(9): the least costly and least complex equivalent is taken unless a
reasoned justification is recorded.
"""

from __future__ import annotations

from typing import Any

from .config import Config
from .models import PortfolioCandidate, Recommendation


def complexity_gate_tier(cfg: Config, knowledge_band: int, client_category: str = "retail") -> int:
    presumption = cfg.scoring["professional_presumptions"].get(client_category, {})
    if presumption.get("assume_knowledge"):
        # Art. 54(3) DR 2017/565 - the firm may assume the necessary knowledge
        # and experience for products for which the client is so classified.
        return max(cfg.scoring["complexity_gate"].values())
    return int(cfg.scoring["complexity_gate"].get(knowledge_band, 0))


def client_horizon_years(cfg: Config, answers: dict[str, Any]) -> float:
    opt = cfg.option("D2", answers.get("D2")) or {}
    years = float(opt.get("horizon_years", 0))
    # A withdrawal expected inside the first two years shortens the effective
    # holding period regardless of the stated horizon (GL3 para 37).
    if answers.get("C8") in ("small_early", "large_early"):
        years = min(years, 2.0)
    return years


def sustainability_requirements(cfg: Config, answers: dict[str, Any]) -> dict[str, Any]:
    """The client's Art. 2(7) requirements, scaled to the portfolio level.

    ESMA GL8 para 88 permits the minimum proportions to be applied on average at
    portfolio level, or to the share of the portfolio the client specifies
    (GL2 para 29 - question F5).
    """
    if answers.get("F1") not in ("yes", "undecided"):
        return {"has_preferences": False}

    aspects = answers.get("F2") or []
    if isinstance(aspects, str):
        aspects = [aspects]
    min_prop = float((cfg.option("F3", answers.get("F3")) or {}).get("min_proportion", 0.0))
    share = float((cfg.option("F5", answers.get("F5")) or {}).get("portfolio_share", 1.0))

    return {
        "has_preferences": True,
        "undecided": answers.get("F1") == "undecided",
        "aspects": list(aspects),
        "taxonomy_min": min_prop * share if "taxonomy" in aspects else 0.0,
        "sfdr_sustainable_min": min_prop * share if "sfdr_sustainable" in aspects else 0.0,
        "pai_required": "pai" in aspects,
        "pai_categories": answers.get("F4") or [],
        "portfolio_share": share,
        "stated_min_proportion": min_prop,
    }


def _meets_sustainability(p: dict[str, Any], req: dict[str, Any]) -> tuple[bool, str]:
    if not req.get("has_preferences"):
        return True, "client is sustainability-neutral (GL8 para 85)"
    s = p.get("sustainability", {}) or {}
    reasons: list[str] = []
    ok = True
    if req["taxonomy_min"] > 0:
        if float(s.get("taxonomy_min", 0.0)) + 1e-9 < req["taxonomy_min"]:
            ok = False
            reasons.append(
                f"Taxonomy-aligned {float(s.get('taxonomy_min', 0.0)):.0%} < required {req['taxonomy_min']:.0%}"
            )
    if req["sfdr_sustainable_min"] > 0:
        if float(s.get("sfdr_sustainable_min", 0.0)) + 1e-9 < req["sfdr_sustainable_min"]:
            ok = False
            reasons.append(
                f"SFDR sustainable {float(s.get('sfdr_sustainable_min', 0.0)):.0%} < required "
                f"{req['sfdr_sustainable_min']:.0%}"
            )
    if req["pai_required"]:
        if not s.get("pai_considered"):
            ok = False
            reasons.append("principal adverse impacts not considered")
        else:
            missing = [c for c in req["pai_categories"] if c not in (s.get("pai_categories") or [])]
            if missing:
                ok = False
                reasons.append("PAI categories not covered: " + ", ".join(missing))
    return ok, "; ".join(reasons) if reasons else "meets the stated sustainability preferences"


def select(
    cfg: Config,
    answers: dict[str, Any],
    final_band: int,
    knowledge_band: int,
) -> Recommendation:
    category = answers.get("A1", "retail")
    gate = complexity_gate_tier(cfg, knowledge_band, category)
    horizon = client_horizon_years(cfg, answers)
    req = sustainability_requirements(cfg, answers)

    considered: list[PortfolioCandidate] = []
    rationale: list[str] = []

    if final_band < 1:
        return Recommendation(
            portfolio_id=None,
            name=None,
            risk_band=0,
            rationale=[
                "No model portfolio may be recommended: the client cannot absorb any "
                "permanent loss of the amount concerned."
            ],
            considered=[],
            sustainability_status="not_assessed",
            sustainability_detail="the Art. 25(2) assessment did not produce a suitable range",
        )

    # --- step 1: the Art. 25(2) filter -------------------------------------
    suitable: list[dict[str, Any]] = []
    for p in cfg.all_portfolios():
        reasons: list[str] = []
        if p["risk_band"] > final_band:
            reasons.append(f"risk band {p['risk_band']} above the client's band {final_band}")
        if p["complexity_tier"] > gate:
            reasons.append(
                f"complexity tier {p['complexity_tier']} above the client's knowledge gate tier {gate}"
            )
        if float(p["min_horizon_years"]) > horizon:
            reasons.append(
                f"minimum holding period {p['min_horizon_years']}y exceeds the client's {horizon:g}y horizon"
            )
        meets, detail = _meets_sustainability(p, req)
        considered.append(
            PortfolioCandidate(
                portfolio_id=p["id"],
                name=p["name"],
                risk_band=p["risk_band"],
                total_cost_bps=p["total_cost_bps"],
                complexity_tier=p["complexity_tier"],
                meets_sustainability=meets,
                excluded_reason="; ".join(reasons) if reasons else None,
            )
        )
        if not reasons:
            suitable.append(p)

    if not suitable:
        return Recommendation(
            portfolio_id=None,
            name=None,
            risk_band=final_band,
            rationale=[
                "No model portfolio satisfies the client's risk band, knowledge gate and "
                "holding period simultaneously. No recommendation may be made "
                "(Art. 54(10) DR 2017/565)."
            ],
            considered=considered,
            sustainability_status="not_assessed",
            sustainability_detail="no product survived the Art. 25(2) filter",
        )

    # the highest band the client may hold, given the filters above
    achievable_band = max(p["risk_band"] for p in suitable)
    if achievable_band < final_band:
        rationale.append(
            f"Profile band {final_band} was reduced to {achievable_band} in product terms: "
            f"knowledge gate tier {gate} and a {horizon:g}-year horizon rule out the higher band."
        )
    at_band = [p for p in suitable if p["risk_band"] == achievable_band]

    # --- step 2: the sustainability filter (GL8 para 81, applied last) -----
    matching = [p for p in at_band if _meets_sustainability(p, req)[0]]

    if req.get("has_preferences") and not matching:
        # GL8 para 82 / Art. 54(10): the firm may not present a non-matching
        # product as meeting the preferences. It may only be recommended after
        # the client adapts their preferences, with the reason recorded.
        fallback = _cheapest(at_band)
        return Recommendation(
            portfolio_id=None,
            name=None,
            risk_band=achievable_band,
            rationale=rationale
            + [
                "The suitable product range contains nothing that meets the client's stated "
                "sustainability preferences.",
                "Under Art. 54(10) DR 2017/565 and ESMA GL8 paras 82-83 no recommendation may be "
                "made unless the client adapts those preferences for this advice only. The "
                "explanation given and the client's decision must be recorded.",
                f"Were the preferences adapted, the suitable alternative would be "
                f"{fallback['id']} ({fallback['name']}).",
            ],
            considered=considered,
            sustainability_status="unmet",
            sustainability_detail=_meets_sustainability(at_band[0], req)[1],
        )

    pool = matching if matching else at_band

    # --- step 3: cost and complexity among equivalents (GL9) ---------------
    chosen = _cheapest(pool)
    if len(pool) > 1:
        rationale.append(
            "Equivalent products at the same risk band and sustainability classification were "
            "compared on ongoing cost and complexity; the least costly was selected "
            "(Art. 54(9) DR 2017/565, ESMA GL9 paras 91-95)."
        )

    # --- step 4: portfolio-size constraint (GL8 para 89) -------------------
    invested = float(answers.get("C4") or 0)
    threshold = float(cfg.portfolios["construction_constraints"]["small_portfolio_threshold_eur"])
    if invested < threshold:
        rationale.append(
            f"The mandate of EUR {invested:,.0f} is below the EUR {threshold:,.0f} threshold at which "
            "direct holdings can be effectively diversified; the model is implemented through pooled "
            "instruments only (ESMA GL8 para 89)."
        )

    status = "met" if req.get("has_preferences") and matching else (
        "neutral" if not req.get("has_preferences") else "unmet"
    )
    _, detail = _meets_sustainability(chosen, req)

    return Recommendation(
        portfolio_id=chosen["id"],
        name=chosen["name"],
        risk_band=achievable_band,
        rationale=rationale,
        considered=considered,
        sustainability_status=status,
        sustainability_detail=detail,
    )


def _cheapest(pool: list[dict[str, Any]]) -> dict[str, Any]:
    return sorted(pool, key=lambda p: (p["total_cost_bps"], p["complexity_tier"], p["id"]))[0]
