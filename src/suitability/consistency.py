"""Coherence controls and the combination rule.

The obligation sits in ESMA GL4 para 51: "Firms should view the information
collected as a whole. Firms should be alert to any relevant contradictions
between different pieces of information collected, and contact the client in
order to resolve any material potential inconsistencies or inaccuracies."

Para 49 describes how a tool can discharge it: where firms use tools, they should
ensure those tools are fit for purpose, and risk-profiling software "could
include some controls of coherence of the replies provided by clients in order to
highlight contradictions between different pieces of information collected". The
fourteen controls below are that mechanism.

The severity, regulatory basis and stated effect of every control live in
``config/scoring.yaml``. The *conditions* are implemented here in code rather
than evaluated from strings: a suitability control that can be changed by
editing a text expression is not a control. The two must be kept in step, and
``tests/test_consistency.py`` asserts that every control id in the
configuration is implemented here and vice versa.
"""

from __future__ import annotations

from typing import Any

from .config import Config
from .models import ClientCase, ControlHit, DimensionResult
from .scoring import comprehension_correct, self_rating

COMBINATION_DIMENSIONS = ("tolerance", "capacity", "objective", "horizon")


def _hit(cfg: Config, cid: str, detail: str = "") -> ControlHit:
    c = cfg.control(cid)
    return ControlHit(
        id=c["id"],
        name=c["name"],
        severity=c["severity"],
        basis=c["basis"],
        effect=c["effect"],
        detail=detail,
        client_message=c.get("client_message"),
    )


def _cap(dim: DimensionResult, band: int, reason: str) -> bool:
    if dim.band > band:
        dim.caps_applied.append(reason)
        dim.band = band
        return True
    return False


def _num(answers: dict[str, Any], qid: str, default: float = 0.0) -> float:
    v = answers.get(qid)
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _attr(cfg: Config, answers: dict[str, Any], qid: str, attr: str, default: Any = None) -> Any:
    opt = cfg.option(qid, answers.get(qid)) or {}
    return opt.get(attr, default)


# ---------------------------------------------------------------------------
# completeness (Art. 54(8) DR 2017/565)
# ---------------------------------------------------------------------------

def check_completeness(cfg: Config, answers: dict[str, Any]) -> list[ControlHit]:
    category = answers.get("A1", "retail")
    missing = [q for q in cfg.required_questions(category) if answers.get(q) in (None, "", [])]
    # conditional sustainability follow-ups
    if answers.get("F1") in ("yes", "undecided") and not answers.get("F2"):
        missing.append("F2")
    if answers.get("F2") and any(a in (answers.get("F2") or []) for a in ("taxonomy", "sfdr_sustainable")):
        if not answers.get("F3"):
            missing.append("F3")
    if not missing:
        return []
    return [_hit(cfg, "CC13", f"unanswered required questions: {', '.join(sorted(set(missing)))}")]


# ---------------------------------------------------------------------------
# controls applied before the dimensions are combined
# ---------------------------------------------------------------------------

def apply_pre_combination(
    cfg: Config, answers: dict[str, Any], dims: dict[str, DimensionResult]
) -> list[ControlHit]:
    hits: list[ControlHit] = []

    # CC10 - borrowing to invest: hard stop
    if answers.get("C10") is True:
        hits.append(_hit(cfg, "CC10", "client is funding the investment with borrowed or pledged assets"))

    # CC01 - knowledge over-estimation (the cap itself is applied in scoring.py)
    rating = self_rating(cfg, answers)
    correct, total = comprehension_correct(cfg, answers)
    if rating is not None and rating >= 4 and correct <= 3:
        hits.append(
            _hit(cfg, "CC01", f"self-rating {rating}/5 against {correct}/{total} comprehension items correct")
        )

    # CC08 - no emergency reserve caps capacity at band 2
    if answers.get("C7") == "m_0" and "capacity" in dims:
        bound = _cap(dims["capacity"], 2, "CC08: no cash reserve outside the invested amount")
        hits.append(
            _hit(
                cfg,
                "CC08",
                "client holds no cash reserve outside the invested amount"
                + ("" if bound else "; the cap was not binding on the assessed band"),
            )
        )

    # CC09 - concentration overlay
    if "capacity" in dims:
        overlay = cfg.scoring["dimensions"]["capacity"].get("concentration_overlay", {})
        if overlay.get("enabled"):
            total_assets = _num(answers, overlay["basis"]["total_financial_assets"])
            invested = _num(answers, overlay["basis"]["invested"])
            if total_assets > 0:
                share = invested / total_assets
                cap_band = 5
                for rule in overlay["caps"]:
                    if share <= float(rule["max_share"]):
                        cap_band = int(rule["max_band"])
                        break
                else:
                    cap_band = int(overlay["caps"][-1]["max_band"])
                bound = _cap(
                    dims["capacity"],
                    cap_band,
                    f"CC09: mandate is {share:.0%} of net financial assets",
                )
                if share > 0.50:
                    hits.append(
                        _hit(
                            cfg,
                            "CC09",
                            f"mandate is {share:.0%} of net financial assets; overlay caps capacity at "
                            f"band {cap_band}" + ("" if bound else " (not binding on the assessed band)"),
                        )
                    )

    # CC06 - liquidity need inside the horizon shortens the effective horizon
    if answers.get("C8") in ("small_early", "large_early") and "horizon" in dims:
        if _cap(dims["horizon"], 2, "CC06: capital needed within the first two years"):
            hits.append(_hit(cfg, "CC06", "client expects to withdraw capital within the first two years"))

    # CC05 - long-term objective over a short horizon
    if "objective" in dims and "horizon" in dims:
        if dims["objective"].band >= 4 and dims["horizon"].band <= 2:
            hits.append(
                _hit(
                    cfg,
                    "CC05",
                    f"objective band {dims['objective'].band} against horizon band {dims['horizon'].band}",
                )
            )

    # CC02 - low knowledge with high risk appetite
    if "knowledge" in dims and "tolerance" in dims:
        if dims["knowledge"].band <= 2 and dims["tolerance"].band >= 4:
            hits.append(
                _hit(
                    cfg,
                    "CC02",
                    f"knowledge band {dims['knowledge'].band} against risk tolerance band {dims['tolerance'].band}",
                )
            )

    # CC03 - tolerance materially exceeds capacity
    if "tolerance" in dims and "capacity" in dims:
        gap = dims["tolerance"].band - dims["capacity"].band
        if gap >= 2:
            hits.append(
                _hit(
                    cfg,
                    "CC03",
                    f"risk tolerance band {dims['tolerance'].band} exceeds capacity band "
                    f"{dims['capacity'].band} by {gap}",
                )
            )

    return hits


# ---------------------------------------------------------------------------
# combination: the binding constraint
# ---------------------------------------------------------------------------

def combine(cfg: Config, dims: dict[str, DimensionResult]) -> tuple[int, str]:
    """Return (final band, name of the binding dimension).

    ``min`` rather than a weighted average: Art. 25(2) MiFID II makes risk
    tolerance and the ability to bear losses cumulative conditions, and ESMA
    GL6 para 70 rejects averaging divergent inputs.
    """
    inputs = [d for d in cfg.scoring["combination"]["inputs"] if d in dims]
    if not inputs:
        return 1, "none"
    binding = min(inputs, key=lambda n: (dims[n].band, n))
    return dims[binding].band, binding


# ---------------------------------------------------------------------------
# controls applied to the combined band
# ---------------------------------------------------------------------------

def apply_post_combination(
    cfg: Config,
    case: ClientCase,
    dims: dict[str, DimensionResult],
    final_band: int,
) -> tuple[int, list[ControlHit]]:
    answers = case.answers
    hits: list[ControlHit] = []

    # CC04 - the recommended band's stress loss must fit inside the loss the
    # client can absorb (Art. 25(2): ability to bear losses)
    capacity_loss = _attr(cfg, answers, "C11", "capacity_loss_pct")
    tolerance_loss = _attr(cfg, answers, "E3", "tolerance_loss_pct")
    if capacity_loss is not None:
        allowed = 0
        for band in range(1, 6):
            if cfg.stress_loss(band) <= float(capacity_loss):
                allowed = band
        if allowed < final_band:
            detail = (
                f"band {final_band} carries a {cfg.stress_loss(final_band):.0f}% adverse-scenario loss "
                f"against an absorbable loss of {capacity_loss:.0f}%"
            )
            hits.append(_hit(cfg, "CC04", detail))
            final_band = allowed
        elif tolerance_loss is not None and float(tolerance_loss) > float(capacity_loss):
            hits.append(
                _hit(
                    cfg,
                    "CC04",
                    f"stated loss tolerance {tolerance_loss:.0f}% exceeds absorbable loss {capacity_loss:.0f}%",
                )
            )

    # CC11 - vulnerability overlay
    flags = answers.get("A7") or []
    if isinstance(flags, str):
        flags = [flags]
    age = _num(answers, "A4", 0)
    triggers = [f for f in flags if f in ("sole_income_source", "first_time_investor")]
    if age >= 75:
        triggers.append(f"age {int(age)}")
    if triggers:
        binding_here = final_band > 3
        hits.append(
            _hit(
                cfg,
                "CC11",
                "vulnerability indicators: "
                + ", ".join(triggers)
                + ("" if binding_here else "; the band 3 cap was not binding on the assessed band"),
            )
        )
        if binding_here:
            final_band = 3

    # CC07 - return expectation not achievable at the accepted risk level
    expectation_band = _attr(cfg, answers, "D5", "implied_band")
    if expectation_band is not None and int(expectation_band) - final_band >= 2:
        hits.append(
            _hit(
                cfg,
                "CC07",
                f"client expects a band {expectation_band} return from a band {final_band} portfolio",
            )
        )

    # CC12 - profile upgraded immediately before a recommendation (GL5 para 58)
    if (
        case.profile_updated_days_ago is not None
        and case.profile_updated_days_ago <= 5
        and case.previous_final_band is not None
        and final_band > case.previous_final_band
    ):
        hits.append(
            _hit(
                cfg,
                "CC12",
                f"profile moved from band {case.previous_final_band} to {final_band} "
                f"{case.profile_updated_days_ago} day(s) before this recommendation",
            )
        )

    return final_band, hits


# ---------------------------------------------------------------------------
# groups and legal persons (ESMA GL6 paras 69-70)
# ---------------------------------------------------------------------------

def most_prudent(
    cfg: Config, member_results: list[tuple[str, dict[str, DimensionResult], int]]
) -> tuple[dict[str, DimensionResult], int, list[ControlHit]]:
    """Combine several individually assessed persons under the prudent rule.

    ESMA GL6 para 69: "the firm should adopt the most prudent approach by taking
    into account, accordingly, the information on the person with the least
    knowledge and experience, the weakest financial situation or the most
    conservative investment objectives."

    Para 70 rejects the alternative in terms: considering "an average profile of
    the level of knowledge and competence of all of them, would unlikely be
    compliant with the MiFID II overarching principle of acting in the clients'
    best interests." This function therefore never averages.
    """
    hits: list[ControlHit] = []
    combined: dict[str, DimensionResult] = {}
    names = [n for n, _d, _b in member_results]

    all_dims = {k for _n, d, _b in member_results for k in d}
    for dim in all_dims:
        candidates = [(n, d[dim]) for n, d, _b in member_results if dim in d]
        who, weakest = min(candidates, key=lambda t: (t[1].band, t[0]))
        clone = DimensionResult(
            name=weakest.name,
            label=weakest.label,
            score=weakest.score,
            band=weakest.band,
            components=weakest.components,
            caps_applied=list(weakest.caps_applied),
            raw_band=weakest.raw_band,
            notes=list(weakest.notes) + [f"most prudent of {len(candidates)} persons: taken from {who}"],
        )
        combined[dim] = clone

    bands = [b for _n, _d, b in member_results]
    if bands and max(bands) - min(bands) >= 2:
        hits.append(
            _hit(
                cfg,
                "CC14",
                f"final bands across {', '.join(names)} range from {min(bands)} to {max(bands)}",
            )
        )
    return combined, min(bands) if bands else 1, hits
