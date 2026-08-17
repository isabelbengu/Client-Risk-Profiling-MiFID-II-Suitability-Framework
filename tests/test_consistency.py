from __future__ import annotations

import copy

from suitability import consistency
from suitability.engine import assess


def _ids(outcome) -> set[str]:
    return {c.id for c in outcome.controls}


def test_every_configured_control_is_implemented(cfg):
    """The configuration lists the controls; this file's tests exercise them.
    A control that exists on paper but never fires is worse than no control."""
    configured = {c["id"] for c in cfg.scoring["coherence_controls"]}
    exercised = {
        "CC01", "CC02", "CC03", "CC04", "CC05", "CC06", "CC07",
        "CC08", "CC09", "CC10", "CC11", "CC12", "CC13", "CC14",
    }
    assert configured == exercised


def test_cc13_blocks_on_missing_information(cfg, base_answers, case_factory):
    answers = copy.deepcopy(base_answers)
    del answers["C7"]
    outcome = assess(case_factory(answers), cfg)
    assert "CC13" in _ids(outcome)
    assert outcome.status == "blocked"
    assert outcome.final_band == 0
    assert outcome.recommendation.portfolio_id is None


def test_cc10_blocks_borrowing_to_invest(cfg, base_answers, case_factory):
    answers = copy.deepcopy(base_answers)
    answers["C10"] = True
    outcome = assess(case_factory(answers), cfg)
    assert "CC10" in _ids(outcome)
    assert outcome.status == "blocked"


def test_cc01_flags_and_caps_over_estimation(cfg, base_answers, case_factory):
    answers = copy.deepcopy(base_answers)
    answers["B0"] = "advanced"
    for qid in ("B7", "B8", "B9", "B10"):
        answers[qid] = "d"
    outcome = assess(case_factory(answers), cfg)
    assert "CC01" in _ids(outcome)
    assert outcome.dimensions["knowledge"].caps_applied


def test_cc02_refers_low_knowledge_high_appetite(cfg, neutral_answers, case_factory):
    answers = copy.deepcopy(neutral_answers)
    answers["B1"] = "none"
    answers["B2"] = ["none"]
    answers["B3"] = "t_none"
    answers["B4"] = "v_na"
    for qid in ("B5", "B6", "B7", "B8", "B9", "B10"):
        answers[qid] = "d"
    answers.update({"E1": "p5", "E2": "buy_more", "E3": "d_35", "E4": "added", "E5": "s5"})
    outcome = assess(case_factory(answers), cfg)
    assert "CC02" in _ids(outcome)
    assert outcome.status == "referred"


def test_cc03_refers_when_tolerance_outruns_capacity(cfg, base_answers, case_factory):
    answers = copy.deepcopy(base_answers)
    answers.update({"E1": "p5", "E2": "buy_more", "E3": "d_35", "E4": "added", "E5": "s5"})
    answers.update({"C1": "variable", "C2": "i_lt_25k", "C6": "gt_60", "C7": "m_lt_3",
                    "C9": "significant", "C11": "l_5"})
    outcome = assess(case_factory(answers), cfg)
    assert "CC03" in _ids(outcome)
    assert outcome.final_band <= outcome.dimensions["capacity"].band


def test_cc04_caps_the_band_at_the_absorbable_loss(cfg, base_answers, case_factory):
    """The decisive test of the whole framework: a client who is willing to lose
    35% but can only absorb 5% must not be put in a portfolio that can lose 15%."""
    answers = copy.deepcopy(base_answers)
    answers["C11"] = "l_5"
    answers.update({"E1": "p5", "E3": "d_35", "E4": "added", "E5": "s5", "E2": "buy_more"})
    outcome = assess(case_factory(answers), cfg)
    assert "CC04" in _ids(outcome)
    assert cfg.stress_loss(outcome.final_band) <= 5


def test_zero_absorbable_loss_leaves_no_suitable_portfolio(cfg, base_answers, case_factory):
    answers = copy.deepcopy(base_answers)
    answers["C11"] = "l_0"
    outcome = assess(case_factory(answers), cfg)
    assert outcome.final_band == 0
    assert outcome.recommendation.portfolio_id is None
    assert outcome.status == "no_suitable_product"


def test_cc05_flags_a_long_objective_on_a_short_horizon(cfg, base_answers, case_factory):
    answers = copy.deepcopy(base_answers)
    answers["D1"] = "max_growth"
    answers["D2"] = "h_lt_2"
    outcome = assess(case_factory(answers), cfg)
    assert "CC05" in _ids(outcome)
    assert outcome.final_band <= 2


def test_cc06_shortens_the_horizon_for_an_early_withdrawal(cfg, base_answers, case_factory):
    answers = copy.deepcopy(base_answers)
    answers["D2"] = "h_gt_10"
    answers["C8"] = "large_early"
    outcome = assess(case_factory(answers), cfg)
    assert "CC06" in _ids(outcome)
    assert outcome.dimensions["horizon"].band <= 2


def test_cc07_flags_an_unachievable_return_expectation(cfg, base_answers, case_factory):
    answers = copy.deepcopy(base_answers)
    answers["D1"] = "preserve"
    answers["D5"] = "r_gt_9"
    outcome = assess(case_factory(answers), cfg)
    assert "CC07" in _ids(outcome)


def test_cc08_caps_capacity_without_a_reserve(cfg, base_answers, case_factory):
    answers = copy.deepcopy(base_answers)
    answers["C7"] = "m_0"
    outcome = assess(case_factory(answers), cfg)
    assert "CC08" in _ids(outcome)
    assert outcome.dimensions["capacity"].band <= 2


def test_cc09_caps_a_concentrated_mandate(cfg, base_answers, case_factory):
    answers = copy.deepcopy(base_answers)
    answers["C3"] = 100000
    answers["C4"] = 95000
    outcome = assess(case_factory(answers), cfg)
    assert "CC09" in _ids(outcome)
    assert outcome.dimensions["capacity"].band <= 3


def test_cc11_caps_a_vulnerable_client(cfg, base_answers, case_factory):
    answers = copy.deepcopy(base_answers)
    answers["A4"] = 80
    answers.update({"D1": "max_growth", "D2": "h_gt_10", "C11": "l_50"})
    answers.update({"E1": "p5", "E2": "buy_more", "E3": "d_35", "E4": "added", "E5": "s5"})
    outcome = assess(case_factory(answers), cfg)
    assert "CC11" in _ids(outcome)
    assert outcome.final_band <= 3


def test_cc12_flags_a_last_minute_upgrade(cfg, base_answers, case_factory):
    case = case_factory(copy.deepcopy(base_answers), previous_final_band=1, profile_updated_days_ago=1)
    outcome = assess(case, cfg)
    assert "CC12" in _ids(outcome)
    assert outcome.status in ("referred", "recommended")


def test_cc14_fires_on_divergent_group_profiles(cfg, load_example):
    outcome = assess(load_example("06-joint-group.yaml"), cfg)
    assert "CC14" in _ids(outcome)


def test_the_group_takes_the_most_prudent_profile_not_the_average(cfg, load_example):
    case = load_example("06-joint-group.yaml")
    group = assess(case, cfg)
    from suitability.engine import assess as assess_one

    members = [assess_one(m, cfg) for m in case.group_members]
    bands = [m.final_band for m in members]
    assert group.final_band == min(bands)
    assert group.final_band != round(sum(bands) / len(bands))
    for dim in ("knowledge", "capacity", "tolerance", "objective"):
        assert group.dimensions[dim].band == min(m.dimensions[dim].band for m in members)


def test_binding_constraint_is_the_minimum(cfg, base_answers, case_factory):
    outcome = assess(case_factory(base_answers), cfg)
    inputs = cfg.scoring["combination"]["inputs"]
    lowest = min(outcome.dimensions[d].band for d in inputs)
    assert outcome.dimensions[outcome.binding_constraint].band == lowest


def test_no_control_can_raise_the_band(cfg, base_answers, case_factory):
    """Every control is one-way: it holds a profile or moves it down."""
    import itertools

    from suitability import scoring

    baseline = assess(case_factory(copy.deepcopy(base_answers)), cfg)
    for qid, values in itertools.chain(
        [("C7", ["m_0"])], [("C10", [True])], [("A4", [80])], [("C8", ["large_early"])]
    ):
        for value in values:
            answers = copy.deepcopy(base_answers)
            answers[qid] = value
            outcome = assess(case_factory(answers), cfg)
            assert outcome.final_band <= baseline.final_band, (qid, value)
    assert scoring is not None


def test_completeness_respects_professional_presumptions(cfg, base_answers):
    answers = copy.deepcopy(base_answers)
    answers["A1"] = "per_se_professional"
    for qid in ("B5", "B6", "B7", "B8", "B9", "B10", "C7"):
        answers.pop(qid, None)
    hits = consistency.check_completeness(cfg, answers)
    assert hits == [], [h.detail for h in hits]
