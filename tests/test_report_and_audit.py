from __future__ import annotations

import copy
import json

from suitability import audit, report
from suitability.engine import assess
from suitability.switching import Position, assess_switch


# ---------------------------------------------------------------------------
# Suitability report - Art. 54(12) DR 2017/565
# ---------------------------------------------------------------------------

def test_report_covers_every_element_article_54_12_requires(cfg, base_answers, case_factory):
    outcome = assess(case_factory(base_answers), cfg)
    text = report.render(outcome, base_answers, cfg)
    for required in (
        "investment term",          # length of time
        "Knowledge and experience",
        "Attitude to risk",
        "Capacity for loss",
        "Sustainability preferences",
        "Review",
    ):
        assert required.lower() in text.lower(), required
    assert outcome.recommendation.name in text


def test_report_states_the_purpose_of_the_assessment(cfg, base_answers, case_factory):
    """Art. 54(1): the client must be told the assessment exists so the firm can
    act in their best interest, and must not be led to think they decide."""
    outcome = assess(case_factory(base_answers), cfg)
    text = report.render(outcome, base_answers, cfg)
    assert "best interest" in text
    assert "not being asked to decide" in text


def test_report_expresses_loss_in_money_not_only_percentages(cfg, base_answers, case_factory):
    """GL4 para 48."""
    outcome = assess(case_factory(base_answers), cfg)
    text = report.render(outcome, base_answers, cfg)
    assert "EUR" in text


def test_report_names_the_binding_constraint(cfg, base_answers, case_factory):
    outcome = assess(case_factory(base_answers), cfg)
    text = report.render(outcome, base_answers, cfg)
    assert "most restrictive" in text
    assert "cannot substitute" in text


def test_referred_report_does_not_present_advice(cfg, neutral_answers, case_factory):
    answers = copy.deepcopy(neutral_answers)
    answers.update({"E1": "p5", "E2": "buy_more", "E3": "d_35", "E4": "added", "E5": "s5"})
    answers.update({"C1": "variable", "C2": "i_lt_25k", "C6": "gt_60", "C7": "m_lt_3",
                    "C9": "significant", "C11": "l_5"})
    outcome = assess(case_factory(answers), cfg)
    assert outcome.status == "referred"
    text = report.render(outcome, answers, cfg)
    assert "No recommendation is issued at this point" in text
    assert "must not be acted on" in text


def test_report_records_an_unmet_sustainability_preference_correctly(cfg, base_answers, case_factory):
    answers = copy.deepcopy(base_answers)
    answers["F2"] = ["taxonomy"]
    answers["F3"] = "p75"
    outcome = assess(case_factory(answers), cfg)
    text = report.render(outcome, answers, cfg)
    assert "may not present a product as meeting your sustainability preferences" in text
    assert "applies to this recommendation and not" in text


def test_every_example_renders(cfg, load_example):
    import os

    for name in sorted(os.listdir(os.path.join(os.path.dirname(__file__), "..", "examples", "clients"))):
        if not name.endswith(".yaml"):
            continue
        case = load_example(name)
        outcome = assess(case, cfg)
        answers = case.answers if not case.group_members else {
            **case.group_members[0].answers, **case.answers
        }
        text = report.render(outcome, answers, cfg)
        assert text.startswith("# Suitability report")
        assert len(text) > 1500


# ---------------------------------------------------------------------------
# Audit - ESMA Guideline 12
# ---------------------------------------------------------------------------

def test_audit_record_is_json_serialisable_and_complete(cfg, base_answers, case_factory, tmp_path):
    case = case_factory(base_answers, adviser_ref="ADV-1")
    outcome = assess(case, cfg)
    text = report.render(outcome, base_answers, cfg)
    record = audit.build_record(outcome, base_answers, case.adviser_ref, text)

    encoded = json.dumps(record)
    assert json.loads(encoded)["client_ref"] == case.client_ref

    for key in ("answers", "assessment", "config_versions", "answers_digest",
                "suitability_report_markdown", "adviser_ref", "written_at"):
        assert key in record, key

    # how the information was used and interpreted (GL12 para 111)
    assert record["assessment"]["dimensions"]["capacity"]["components"]
    assert record["assessment"]["recommendation"]["considered"]

    path = audit.append(record, str(tmp_path / "log.jsonl"))
    with open(path, encoding="utf-8") as fh:
        assert json.loads(fh.readline())["record_type"] == "suitability_assessment"


def test_audit_is_append_only(cfg, base_answers, case_factory, tmp_path):
    outcome = assess(case_factory(base_answers), cfg)
    path = str(tmp_path / "log.jsonl")
    for _ in range(3):
        audit.append(audit.build_record(outcome, base_answers), path)
    with open(path, encoding="utf-8") as fh:
        assert len(fh.readlines()) == 3


def test_profile_change_record_states_the_direction(cfg):
    rec = audit.profile_change_record("C1", 2, 4, "inheritance received", {"C3": 500000}, "ADV-1")
    assert rec["direction"] == "riskier"
    assert rec["client_informed"] is True


def test_sustainability_adaptation_is_scoped_to_one_recommendation(cfg):
    rec = audit.sustainability_adaptation_record(
        "C1", {"taxonomy_min": 0.75}, {"taxonomy_min": 0.25}, "no product available", "accepted", "ADV-1"
    )
    assert rec["scope"] == "this_recommendation_only"
    assert rec["explanation_given"]


def test_the_digest_changes_when_an_answer_changes(cfg, base_answers, case_factory):
    a = assess(case_factory(copy.deepcopy(base_answers)), cfg)
    changed = copy.deepcopy(base_answers)
    changed["E3"] = "d_5"
    b = assess(case_factory(changed), cfg)
    assert a.answers_digest != b.answers_digest


# ---------------------------------------------------------------------------
# Switching - Art. 54(11), ESMA Guideline 10
# ---------------------------------------------------------------------------

def test_switch_is_refused_when_costs_exceed_benefits(cfg):
    existing = Position("Fund A", 100000, ongoing_cost_bps=60, exit_cost_bps=100, expected_gross_return_pct=5.0)
    proposed = Position("Fund B", 100000, ongoing_cost_bps=55, entry_cost_bps=100, expected_gross_return_pct=5.0)
    result = assess_switch(existing, proposed, horizon_years=4, cfg=cfg)
    assert result.permitted is False
    assert "cannot be demonstrated" in result.reasons[0]


def test_switch_is_permitted_when_it_pays_back_inside_the_horizon(cfg):
    existing = Position("Fund A", 200000, ongoing_cost_bps=150, exit_cost_bps=0, expected_gross_return_pct=5.0)
    proposed = Position("Fund B", 200000, ongoing_cost_bps=40, entry_cost_bps=50, expected_gross_return_pct=5.0)
    result = assess_switch(existing, proposed, horizon_years=10, cfg=cfg)
    assert result.permitted is True
    assert result.breakeven_years is not None and result.breakeven_years < 3


def test_qualitative_grounds_must_be_stated(cfg):
    existing = Position("Concentrated holding", 100000, ongoing_cost_bps=20, exit_cost_bps=50)
    proposed = Position("Diversified fund", 100000, ongoing_cost_bps=45, entry_cost_bps=0)
    refused = assess_switch(existing, proposed, horizon_years=8, cfg=cfg)
    assert refused.permitted is False
    allowed = assess_switch(
        existing, proposed, horizon_years=8, cfg=cfg,
        qualitative_benefits=["removes a 40% single-issuer concentration"],
    )
    assert allowed.permitted is True
    assert "must be evidenced on file" in allowed.reasons[0]


def test_rebalancing_within_bands_is_not_a_switch(cfg):
    p = Position("Model", 100000, ongoing_cost_bps=40)
    result = assess_switch(p, p, horizon_years=5, cfg=cfg, is_rebalancing_within_bands=True)
    assert result.permitted is True
    assert "not a switch" in result.reasons[0]
