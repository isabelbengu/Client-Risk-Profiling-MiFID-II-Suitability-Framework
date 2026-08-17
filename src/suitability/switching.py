"""Cost-benefit analysis of a switch.

Article 54(11) DR 2017/565 requires a firm advising on, or carrying out, a
switch to collect the necessary information on both the existing and the
proposed investments and to undertake an analysis of the costs and benefits of
the switch, "such that they are reasonably able to demonstrate that the benefits
of switching are greater than the costs".

ESMA GL10 adds: rebalancing inside the tolerance bands of an agreed strategy is
not a switch (para 97); the analysis must take account of expected net returns,
changed circumstances, changed product features and portfolio-level benefits
such as diversification, liquidity and reduced credit risk (para 98); the
suitability report must explain the conclusion before the transaction (para 99);
and a sale and a related purchase advised days apart are one switch (para 100).
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class Position:
    name: str
    value_eur: float
    ongoing_cost_bps: float
    exit_cost_bps: float = 0.0
    entry_cost_bps: float = 0.0
    expected_gross_return_pct: float = 0.0


@dataclass
class SwitchAssessment:
    permitted: bool
    one_off_cost_eur: float
    annual_cost_change_eur: float
    expected_annual_net_gain_eur: float
    breakeven_years: float | None
    horizon_years: float
    qualitative_benefits: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def assess_switch(
    existing: Position,
    proposed: Position,
    horizon_years: float,
    cfg: Any,
    qualitative_benefits: list[str] | None = None,
    is_rebalancing_within_bands: bool = False,
) -> SwitchAssessment:
    benefits = list(qualitative_benefits or [])
    reasons: list[str] = []

    if is_rebalancing_within_bands:
        return SwitchAssessment(
            permitted=True,
            one_off_cost_eur=0.0,
            annual_cost_change_eur=0.0,
            expected_annual_net_gain_eur=0.0,
            breakeven_years=0.0,
            horizon_years=horizon_years,
            qualitative_benefits=benefits,
            reasons=["Rebalancing within the tolerance bands of the agreed strategy is not a switch "
                     "(ESMA GL10 para 97)."],
        )

    value = existing.value_eur
    one_off = value * (existing.exit_cost_bps + proposed.entry_cost_bps) / 10000.0
    annual_cost_change = value * (proposed.ongoing_cost_bps - existing.ongoing_cost_bps) / 10000.0

    net_existing = existing.expected_gross_return_pct - existing.ongoing_cost_bps / 100.0
    net_proposed = proposed.expected_gross_return_pct - proposed.ongoing_cost_bps / 100.0
    annual_net_gain = value * (net_proposed - net_existing) / 100.0

    if annual_net_gain > 0:
        breakeven = one_off / annual_net_gain
    else:
        breakeven = None

    cap = float(cfg.portfolios["switching"]["breakeven_horizon_cap_years"])

    permitted = False
    if breakeven is not None and breakeven <= min(cap, horizon_years):
        permitted = True
        reasons.append(
            f"Expected net return improvement of EUR {annual_net_gain:,.0f} a year recovers the "
            f"EUR {one_off:,.0f} one-off cost in {breakeven:.1f} years, inside both the "
            f"{cap:.0f}-year policy cap and the client's {horizon_years:g}-year horizon."
        )
    elif benefits:
        permitted = True
        reasons.append(
            "The switch is not justified on expected net return alone. It is justified on the "
            "following non-financial grounds, which must be evidenced on file: "
            + "; ".join(benefits)
            + f". One-off cost EUR {one_off:,.0f}; annual cost change EUR {annual_cost_change:,.0f}."
        )
    else:
        reasons.append(
            f"The benefits of the switch cannot be demonstrated to exceed its costs. One-off cost "
            f"EUR {one_off:,.0f}"
            + (f", breakeven {breakeven:.1f} years against a {horizon_years:g}-year horizon."
               if breakeven is not None
               else ", with no expected net return improvement.")
            + " Art. 54(11) DR 2017/565 is not satisfied."
        )

    return SwitchAssessment(
        permitted=permitted,
        one_off_cost_eur=round(one_off, 2),
        annual_cost_change_eur=round(annual_cost_change, 2),
        expected_annual_net_gain_eur=round(annual_net_gain, 2),
        breakeven_years=None if breakeven is None else round(breakeven, 2),
        horizon_years=horizon_years,
        qualitative_benefits=benefits,
        reasons=reasons,
    )
