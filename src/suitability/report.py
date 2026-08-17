"""Suitability report (Art. 54(12) DR 2017/565).

Article 54(12) requires a firm giving investment advice to a retail client to
provide a report that gives "an outline of the advice given and how the
recommendation provided is suitable for the retail client, including how it meets
the client's objectives and personal circumstances" - with reference to the
investment term required, the client's knowledge and experience, and the client's
attitude to risk and capacity for loss. Where sustainability preferences were
expressed, Art. 54(12) as amended by DR (EU) 2021/1253 also requires the report to
explain how the recommendation meets them. The report must state whether the
recommended service or instrument is likely to require the retail client to seek a
periodic review.

This module generates that report from the outcome object, so every sentence in
it is traceable to a recorded input.
"""

from __future__ import annotations

from typing import Any

from .config import Config
from .models import Outcome

_DIM_SENTENCE = {
    "tolerance": "your attitude to risk",
    "capacity": "your capacity for loss",
    "objective": "the objective you set for this money",
    "horizon": "the length of time you intend to invest for",
}


def _answer_label(cfg: Config, answers: dict[str, Any], qid: str) -> str:
    opt = cfg.option(qid, answers.get(qid))
    return opt["label"] if opt else str(answers.get(qid, "not answered"))


def render(outcome: Outcome, answers: dict[str, Any], cfg: Config) -> str:
    d = outcome.dimensions
    lines: list[str] = []
    a = lines.append

    a("# Suitability report")
    a("")
    a(f"**Client reference:** {outcome.client_ref}  ")
    a(f"**Date of assessment:** {outcome.assessed_at}  ")
    a(f"**Service:** {_answer_label(cfg, answers, 'A3')}  ")
    a(f"**Client categorisation:** {_answer_label(cfg, answers, 'A1')}  ")
    a(
        f"**Framework version:** questionnaire {outcome.config_versions['questionnaire']}, "
        f"scoring {outcome.config_versions['scoring']}, portfolios {outcome.config_versions['portfolios']}"
    )
    a("")
    a("*The purpose of this assessment is to enable us to act in your best interest. "
      "It is our assessment, not yours: you are not being asked to decide whether an "
      "investment is suitable for you (Art. 54(1) DR 2017/565).*")
    a("")

    # ---- outcome ----------------------------------------------------------
    a("## 1. The advice")
    a("")
    if outcome.status == "recommended":
        a(f"We recommend the **{outcome.recommendation.name}** model portfolio "
          f"(`{outcome.recommendation.portfolio_id}`), a **band {outcome.final_band} - "
          f"{cfg.band_label(outcome.final_band)}** strategy.")
        p = cfg.portfolio(outcome.recommendation.portfolio_id)
        a("")
        a(f"- Summary risk indicator: **{p['sri']}/7**")
        a(f"- Loss in an adverse twelve-month scenario: around **{p['stress_loss_pct']}%** "
          f"of the amount invested")
        a(f"- Recommended minimum holding period: **{p['min_horizon_years']} years**")
        a(f"- Ongoing costs and charges: **{p['total_cost_bps']} bps a year**")
        invested = float(answers.get("C4") or 0)
        if invested:
            a(f"- On EUR {invested:,.0f}, that adverse scenario is a fall of roughly "
              f"**EUR {invested * p['stress_loss_pct'] / 100:,.0f}**, and the annual cost is "
              f"about **EUR {invested * p['total_cost_bps'] / 10000:,.0f}**")
    elif outcome.status == "referred":
        a("**No recommendation is issued at this point.** The information you gave contains a "
          "material inconsistency that we need to resolve with you first. This is set out in "
          "section 4.")
        if outcome.recommendation.portfolio_id:
            p = cfg.portfolio(outcome.recommendation.portfolio_id)
            a("")
            a(f"For discussion only, and subject to that conversation, your answers as they stand "
              f"point to the **{outcome.recommendation.name}** model portfolio "
              f"(`{outcome.recommendation.portfolio_id}`, band {outcome.final_band}, summary risk "
              f"indicator {p['sri']}/7, around {p['stress_loss_pct']}% loss in an adverse "
              f"twelve-month scenario). This is not advice and must not be acted on.")
    elif outcome.status == "blocked":
        a("**We are unable to make a recommendation.** See section 4.")
    else:
        a("**No model portfolio in our range is suitable for you on the basis of the information "
          "collected.** See section 4.")
    a("")

    # ---- how it meets the client's circumstances --------------------------
    a("## 2. How this meets your objectives and personal circumstances")
    a("")
    a(f"**Investment term.** You told us you intend to hold this investment for "
      f"{_answer_label(cfg, answers, 'D2').lower()}. "
      f"{_answer_label(cfg, answers, 'D3')}. "
      f"{_answer_label(cfg, answers, 'D4')}.")
    a("")
    k = d.get("knowledge")
    if k:
        correct_line = ""
        for cap in k.caps_applied:
            correct_line = f" {cap}."
        a(f"**Knowledge and experience.** We assessed this at band {k.band} of 5. It is based on "
          f"the instruments you have actually held, how often you have transacted, your background, "
          f"and the worked examples you answered - not on how you rated yourself.{correct_line} "
          f"This determines which types of product we may recommend to you (complexity tier "
          f"{outcome.complexity_gate_tier} and below), because you must be able to understand the "
          f"risks involved.")
        a("")
    t = d.get("tolerance")
    c = d.get("capacity")
    if t and c:
        a(f"**Attitude to risk.** Band {t.band} of 5. You said the largest twelve-month fall you "
          f"would accept without changing your plan is {_answer_label(cfg, answers, 'E3').lower()}, "
          f"and that in a 20% market fall you would "
          f"{_answer_label(cfg, answers, 'E2').lower()}.")
        a("")
        a(f"**Capacity for loss.** Band {c.band} of 5. This is a different question from your "
          f"attitude: it is what your finances can absorb, not what you would be comfortable with. "
          f"You told us you could absorb a permanent loss of "
          f"{_answer_label(cfg, answers, 'C11').lower()}, that your reserve outside this "
          f"investment covers {_answer_label(cfg, answers, 'C7').lower()}, and that your regular "
          f"commitments take {_answer_label(cfg, answers, 'C6').lower()} of your income.")
        for cap in c.caps_applied:
            a(f"  - {cap}")
        a("")
    binding = outcome.binding_constraint
    a(f"**Which of these decided the outcome.** We do not average these assessments against one "
      f"another: a willingness to take risk cannot substitute for the ability to bear a loss. We "
      f"take the most restrictive. Here that was **{_DIM_SENTENCE.get(binding, binding)}** "
      f"(band {d[binding].band}), which is why the recommendation sits at band "
      f"{outcome.final_band}.")
    a("")
    for line in outcome.recommendation.rationale:
        a(f"- {line}")
    if outcome.recommendation.rationale:
        a("")

    # ---- sustainability ---------------------------------------------------
    a("## 3. Sustainability preferences")
    a("")
    status = outcome.recommendation.sustainability_status
    if status == "neutral":
        a("You told us you have no sustainability preferences for this portfolio. We may therefore "
          "recommend products with or without sustainability features, and this recommendation is "
          "not presented as meeting any sustainability preference.")
    elif status == "met":
        a(f"You asked for: {_sustainability_summary(cfg, answers)}. The recommended portfolio meets "
          f"this: {outcome.recommendation.sustainability_detail}.")
    elif status == "unmet":
        a(f"You asked for: {_sustainability_summary(cfg, answers)}. Nothing in the range that is "
          f"otherwise suitable for you meets that. We may not present a product as meeting your "
          f"sustainability preferences when it does not. You may choose to adapt your preferences "
          f"for this advice only - that choice is yours, it applies to this recommendation and not "
          f"to your general profile, and we will record it.")
    else:
        a("Sustainability preferences were not reached, because no suitable product range was "
          "identified.")
    a("")

    # ---- controls and next steps -----------------------------------------
    a("## 4. Points we need to raise with you")
    a("")
    visible = [ct for ct in outcome.controls if ct.severity in ("block", "refer", "cap")]
    if not visible:
        a("None. Your answers were internally consistent.")
    for ct in visible:
        a(f"- **{ct.name}.** {ct.client_message or ct.effect}")
        a(f"  <small>Control {ct.id} ({ct.severity}); {ct.basis}. Recorded detail: {ct.detail}.</small>")
    a("")

    # ---- review -----------------------------------------------------------
    a("## 5. Review")
    a("")
    months = cfg.questionnaire["meta"]["review_cycle_months"]
    a(f"This assessment should be reviewed at least every {months} months, and sooner if your "
      f"circumstances change - in particular your income, your commitments, the date you need the "
      f"money, or your plans for retirement. Tell us when something changes; we will also ask you "
      f"periodically.")
    a("")
    if outcome.status == "recommended":
        p = cfg.portfolio(outcome.recommendation.portfolio_id)
        if p["min_horizon_years"] >= 5 or p["risk_band"] >= 3:
            a("Given the holding period and the level of fluctuation involved, this recommendation "
              "is likely to require a periodic review of its continuing suitability.")
    a("")
    a("---")
    a("")
    a(f"*Prepared from questionnaire responses digest `{outcome.answers_digest}`. "
      f"This report and the underlying assessment are retained under the firm's record-keeping "
      f"arrangements (ESMA Guideline 12).*")

    return "\n".join(lines)


def _sustainability_summary(cfg: Config, answers: dict[str, Any]) -> str:
    aspects = answers.get("F2") or []
    if isinstance(aspects, str):
        aspects = [aspects]
    parts: list[str] = []
    prop = cfg.option("F3", answers.get("F3")) or {}
    share = cfg.option("F5", answers.get("F5")) or {}
    if "taxonomy" in aspects:
        parts.append(f"at least {prop.get('min_proportion', 0):.0%} in environmentally sustainable "
                     f"activities under the Taxonomy Regulation")
    if "sfdr_sustainable" in aspects:
        parts.append(f"at least {prop.get('min_proportion', 0):.0%} in sustainable investments under "
                     f"the SFDR")
    if "pai" in aspects:
        cats = answers.get("F4") or []
        parts.append("consideration of principal adverse impacts"
                     + (f" ({', '.join(cats)})" if cats else ""))
    summary = "; ".join(parts) if parts else "sustainability features, without specifying which"
    if share:
        summary += f", applied to {share.get('portfolio_share', 1):.0%} of the portfolio"
    return summary
