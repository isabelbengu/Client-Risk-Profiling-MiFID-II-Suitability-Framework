from __future__ import annotations

import copy

from suitability import scoring


def test_comprehension_drives_the_knowledge_ceiling(cfg, base_answers):
    """A confident client who fails the worked examples is capped (GL4 para 52)."""
    answers = copy.deepcopy(base_answers)
    answers["B0"] = "professional"
    for qid in ("B5", "B6", "B7", "B8", "B9", "B10"):
        answers[qid] = "d"  # "I do not know" on every item
    dims = scoring.score_all(cfg, answers)
    assert dims["knowledge"].band == 1
    assert any("comprehension" in c for c in dims["knowledge"].caps_applied)


def test_self_rating_alone_cannot_raise_knowledge(cfg, base_answers):
    low = copy.deepcopy(base_answers)
    low["B0"] = "none"
    high = copy.deepcopy(base_answers)
    high["B0"] = "professional"
    assert scoring.score_all(cfg, low)["knowledge"].score == scoring.score_all(cfg, high)["knowledge"].score


def test_experience_ceiling_limits_the_gate(cfg, base_answers):
    """Answering the quiz well does not qualify a client for products they have
    never held: the gate cannot exceed one tier above actual experience."""
    answers = copy.deepcopy(base_answers)
    answers["B2"] = ["deposits_mmf"]          # tier 0 only
    answers["B3"] = "t_none"
    answers["B4"] = "v_na"
    dims = scoring.score_all(cfg, answers)
    assert dims["knowledge"].band <= 2
    assert any("instrument tier" in c for c in dims["knowledge"].caps_applied)


def test_never_invested_drops_the_revealed_behaviour_component(cfg, base_answers):
    """E4 = 'I was not invested at the time' must not score as zero tolerance;
    its weight is redistributed across the remaining components."""
    answers = copy.deepcopy(base_answers)
    answers["E4"] = "never_invested"
    dims = scoring.score_all(cfg, answers)
    comp = next(c for c in dims["tolerance"].components if c.name == "revealed_behaviour")
    assert comp.value is None
    sold = copy.deepcopy(base_answers)
    sold["E4"] = "sold"
    assert dims["tolerance"].score > scoring.score_all(cfg, sold)["tolerance"].score


def test_objective_band_is_reduced_by_a_fixed_commitment(cfg, base_answers):
    answers = copy.deepcopy(base_answers)
    answers["D1"] = "growth"
    answers["D3"] = "none"
    without = scoring.score_all(cfg, answers)["objective"].band
    answers["D3"] = "fixed_date"
    with_commitment = scoring.score_all(cfg, answers)["objective"].band
    assert with_commitment == without - 1


def test_high_withdrawals_reduce_the_objective_band(cfg, base_answers):
    answers = copy.deepcopy(base_answers)
    answers["D1"] = "max_growth"
    answers["D4"] = "gt_5"
    assert scoring.score_all(cfg, answers)["objective"].band == 4


def test_horizon_band_comes_straight_from_the_stated_term(cfg, base_answers):
    for value, expected in (("h_lt_2", 1), ("h_3_5", 2), ("h_5_7", 3), ("h_7_10", 4), ("h_gt_10", 5)):
        answers = copy.deepcopy(base_answers)
        answers["D2"] = value
        assert scoring.score_all(cfg, answers)["horizon"].band == expected


def test_capacity_falls_when_the_client_can_absorb_less(cfg, base_answers):
    scores = []
    for value in ("l_0", "l_5", "l_15", "l_30", "l_50", "l_gt_50"):
        answers = copy.deepcopy(base_answers)
        answers["C11"] = value
        scores.append(scoring.score_all(cfg, answers)["capacity"].score)
    assert scores == sorted(scores)


def test_tolerance_is_monotonic_in_the_drawdown_answer(cfg, base_answers):
    scores = []
    for value in ("d_0", "d_5", "d_10", "d_20", "d_35", "d_gt_35"):
        answers = copy.deepcopy(base_answers)
        answers["E3"] = value
        scores.append(scoring.score_all(cfg, answers)["tolerance"].score)
    assert scores == sorted(scores)


def test_every_dimension_is_produced(cfg, base_answers):
    dims = scoring.score_all(cfg, base_answers)
    assert set(dims) == {"knowledge", "capacity", "objective", "tolerance", "horizon"}
    for d in dims.values():
        assert 1 <= d.band <= 5
