from __future__ import annotations

import copy

from suitability import mapping
from suitability.engine import assess


def test_recommendation_never_exceeds_the_client_band(cfg, base_answers, case_factory):
    for c11 in ("l_5", "l_15", "l_30", "l_50"):
        for d2 in ("h_lt_2", "h_3_5", "h_5_7", "h_gt_10"):
            answers = copy.deepcopy(base_answers)
            answers["C11"] = c11
            answers["D2"] = d2
            outcome = assess(case_factory(answers), cfg)
            if outcome.recommendation.portfolio_id:
                p = cfg.portfolio(outcome.recommendation.portfolio_id)
                assert p["risk_band"] <= outcome.final_band
                assert p["min_horizon_years"] <= mapping.client_horizon_years(cfg, answers)


def test_complexity_gate_excludes_products_the_client_cannot_understand(cfg, base_answers, case_factory):
    answers = copy.deepcopy(base_answers)
    answers["B1"] = "none"
    answers["B2"] = ["deposits_mmf"]
    answers["B3"] = "t_none"
    answers["B4"] = "v_na"
    for qid in ("B5", "B6", "B7", "B8", "B9", "B10"):
        answers[qid] = "d"
    outcome = assess(case_factory(answers), cfg)
    assert outcome.complexity_gate_tier == 0
    if outcome.recommendation.portfolio_id:
        assert cfg.portfolio(outcome.recommendation.portfolio_id)["complexity_tier"] == 0


def test_professional_clients_clear_the_knowledge_gate(cfg):
    """Art. 54(3) DR 2017/565 permits the presumption of knowledge and experience."""
    assert mapping.complexity_gate_tier(cfg, 1, "per_se_professional") == 4
    assert mapping.complexity_gate_tier(cfg, 1, "retail") == 0


def test_sustainability_is_applied_after_the_suitability_assessment(cfg, base_answers, case_factory):
    """GL8 para 81: preferences narrow the suitable range, they never widen it."""
    neutral = copy.deepcopy(base_answers)
    neutral["F1"] = "no"
    neutral.pop("F2", None)
    neutral.pop("F3", None)
    neutral.pop("F4", None)
    neutral.pop("F5", None)
    with_prefs = copy.deepcopy(base_answers)

    a = assess(case_factory(neutral), cfg)
    b = assess(case_factory(with_prefs), cfg)
    assert b.final_band <= a.final_band
    assert b.recommendation.sustainability_status == "met"
    assert a.recommendation.sustainability_status == "neutral"


def test_unmeetable_preferences_block_the_recommendation(cfg, base_answers, case_factory):
    """Art. 54(10): a product that does not meet the preferences may not be
    presented as if it did. The client must adapt them first (GL8 paras 82-83)."""
    answers = copy.deepcopy(base_answers)
    answers["F2"] = ["taxonomy"]
    answers["F3"] = "p75"
    answers["F5"] = "s100"
    outcome = assess(case_factory(answers), cfg)
    assert outcome.recommendation.sustainability_status == "unmet"
    assert outcome.recommendation.portfolio_id is None
    assert outcome.status == "no_suitable_product"
    assert any("adapt" in r for r in outcome.recommendation.rationale)


def test_portfolio_share_scales_the_required_minimum(cfg, base_answers):
    answers = copy.deepcopy(base_answers)
    answers["F2"] = ["sfdr_sustainable"]
    answers["F3"] = "p50"
    answers["F5"] = "s50"
    req = mapping.sustainability_requirements(cfg, answers)
    assert abs(req["sfdr_sustainable_min"] - 0.25) < 1e-9


def test_least_costly_equivalent_is_selected(cfg, base_answers, case_factory):
    """GL9 paras 91-95 and Art. 54(9)."""
    answers = copy.deepcopy(base_answers)
    answers["F1"] = "no"
    for k in ("F2", "F3", "F4", "F5"):
        answers.pop(k, None)
    outcome = assess(case_factory(answers), cfg)
    chosen = cfg.portfolio(outcome.recommendation.portfolio_id)
    equivalents = [
        p
        for p in cfg.all_portfolios()
        if p["risk_band"] == chosen["risk_band"]
        and p["complexity_tier"] <= outcome.complexity_gate_tier
        and p["min_horizon_years"] <= mapping.client_horizon_years(cfg, answers)
    ]
    assert chosen["total_cost_bps"] == min(p["total_cost_bps"] for p in equivalents)


def test_every_considered_product_carries_a_reason_for_exclusion(cfg, base_answers, case_factory):
    outcome = assess(case_factory(base_answers), cfg)
    ids = {c.portfolio_id for c in outcome.recommendation.considered}
    assert ids == {p["id"] for p in cfg.all_portfolios()}
    for cand in outcome.recommendation.considered:
        p = cfg.portfolio(cand.portfolio_id)
        if p["risk_band"] > outcome.final_band:
            assert cand.excluded_reason


def test_early_withdrawal_shortens_the_effective_horizon(cfg, base_answers):
    answers = copy.deepcopy(base_answers)
    answers["D2"] = "h_gt_10"
    assert mapping.client_horizon_years(cfg, answers) == 15
    answers["C8"] = "small_early"
    assert mapping.client_horizon_years(cfg, answers) == 2
