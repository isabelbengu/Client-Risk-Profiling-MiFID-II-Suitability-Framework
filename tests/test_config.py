"""The configuration is the control. These tests are the control's control."""

from __future__ import annotations

import pytest

from suitability.config import ConfigError


def test_versions_present(cfg):
    for key, value in cfg.versions.items():
        assert value, f"{key} has no version"


def test_component_weights_sum_to_one(cfg):
    for name, dim in cfg.scoring["dimensions"].items():
        comps = dim.get("components") or {}
        if not comps:
            continue
        total = sum(c["weight"] for c in comps.values())
        assert abs(total - 1.0) < 1e-9, f"{name} weights sum to {total}"


def test_every_component_question_exists(cfg):
    for dim in cfg.scoring["dimensions"].values():
        for comp in (dim.get("components") or {}).values():
            for qid in comp["questions"]:
                assert cfg.question(qid) is not None


def test_bands_are_contiguous_and_cover_the_range(cfg):
    bands = sorted(cfg.scoring["bands"], key=lambda b: b["min_score"])
    assert bands[0]["min_score"] == 0
    assert bands[-1]["max_score"] == 100
    for lower, upper in zip(bands, bands[1:]):
        assert upper["min_score"] - lower["max_score"] < 0.01


def test_stress_loss_is_monotonic_in_band(cfg):
    losses = [cfg.stress_loss(b) for b in range(1, 6)]
    assert losses == sorted(losses)
    assert len(set(losses)) == 5


def test_every_band_has_at_least_one_portfolio(cfg):
    bands = {p["risk_band"] for p in cfg.all_portfolios()}
    assert bands == {1, 2, 3, 4, 5}


def test_every_band_has_a_core_and_a_sustainable_variant(cfg):
    for band in range(1, 6):
        variants = [p for p in cfg.all_portfolios() if p["risk_band"] == band]
        assert any(not p["sustainability"]["has_features"] for p in variants), band
        assert any(p["sustainability"].get("sfdr_sustainable_min", 0) >= 0.3 for p in variants), band


def test_min_horizon_increases_with_risk_band(cfg):
    by_band: dict[int, list[float]] = {}
    for p in cfg.all_portfolios():
        by_band.setdefault(p["risk_band"], []).append(float(p["min_horizon_years"]))
    mins = [min(by_band[b]) for b in sorted(by_band)]
    assert mins == sorted(mins)


def test_options_have_unique_values(cfg):
    for section in cfg.questionnaire["sections"]:
        for q in section.get("questions", []):
            values = [o["value"] for o in q.get("options", []) or []]
            assert len(values) == len(set(values)), q["id"]


def test_scored_options_are_within_range(cfg):
    for section in cfg.questionnaire["sections"]:
        for q in section.get("questions", []):
            for opt in q.get("options", []) or []:
                if opt.get("score") is None:
                    continue
                assert 0 <= opt["score"] <= 100, (q["id"], opt["value"])


def test_comprehension_questions_have_exactly_one_correct_answer(cfg):
    for section in cfg.questionnaire["sections"]:
        for q in section.get("questions", []):
            if q.get("scoring_role") != "comprehension":
                continue
            correct = [o for o in q["options"] if o.get("correct")]
            assert len(correct) == 1, q["id"]


def test_self_rating_question_is_not_scored(cfg):
    """GL4 para 46: self-assessment must be counterbalanced, not relied on."""
    q = cfg.question("B0")
    assert q["scoring_role"] == "cross_check_only"
    for opt in q["options"]:
        assert opt.get("score") is None
    used = {
        qid
        for dim in cfg.scoring["dimensions"].values()
        for comp in (dim.get("components") or {}).values()
        for qid in comp["questions"]
    }
    assert "B0" not in used


def test_knowledge_is_not_an_input_to_the_risk_band(cfg):
    """Knowledge gates complexity; it never raises the risk band."""
    assert "knowledge" not in cfg.scoring["combination"]["inputs"]
    assert cfg.scoring["combination"]["knowledge_treatment"] == "complexity_gate_only"


def test_combination_method_is_the_binding_constraint(cfg):
    assert cfg.scoring["combination"]["method"] == "binding_constraint"


def test_bad_config_is_rejected(cfg):
    import copy

    from suitability.config import Config

    broken = copy.deepcopy(cfg.scoring)
    broken["dimensions"]["tolerance"]["components"]["attitude_statement"]["weight"] = 0.99
    with pytest.raises(ConfigError):
        Config(questionnaire=cfg.questionnaire, scoring=broken, portfolios=cfg.portfolios)
