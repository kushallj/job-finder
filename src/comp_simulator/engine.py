from __future__ import annotations

from datetime import datetime
from typing import List, Dict, Any, Optional

from .models import OfferPackage, YearlyCompBreakdown, CompSimulationResult

VESTING_PRESETS = {
    "standard_4yr_25": [0.25, 0.25, 0.25, 0.25],      # 25% 1-yr cliff, 25%/yr
    "amazon_5_15_40_40": [0.05, 0.15, 0.40, 0.40],    # Amazon style backloaded
    "snap_10_20_30_40": [0.10, 0.20, 0.30, 0.40],     # Progressive backloaded
    "even_quarterly": [0.25, 0.25, 0.25, 0.25],       # Linear
}


class CompensationSimulatorEngine:
    """
    Computes 4-year total compensation cash flows, equity vesting curves,
    tax projections, and counter-offer negotiation targets.
    """

    def simulate_package(self, offer: OfferPackage) -> CompSimulationResult:
        # Determine 4-year vesting percentage schedule
        if offer.custom_vesting_splits and len(offer.custom_vesting_splits) == 4:
            total_sum = sum(offer.custom_vesting_splits)
            splits = [s / total_sum for s in offer.custom_vesting_splits]
        else:
            splits = VESTING_PRESETS.get(offer.vesting_schedule, [0.25, 0.25, 0.25, 0.25])

        tax_mult = max(0.0, 1.0 - (offer.estimated_tax_rate / 100.0))
        effective_equity_grant = offer.equity_grant_usd * offer.startup_exit_multiple

        yearly_breakdowns: List[YearlyCompBreakdown] = []
        total_pre_tax = 0.0
        total_post_tax = 0.0

        for yr_idx in range(4):
            year_num = yr_idx + 1
            base = offer.base_salary
            perf_bonus = round(base * (offer.target_bonus_pct / 100.0), 2)
            signon = offer.signon_bonus if year_num == 1 else 0.0
            total_cash_bonus = round(perf_bonus + signon, 2)

            equity_vest = round(effective_equity_grant * splits[yr_idx], 2)
            yr_total_pre = round(base + total_cash_bonus + equity_vest, 2)
            yr_total_post = round(yr_total_pre * tax_mult, 2)

            total_pre_tax += yr_total_pre
            total_post_tax += yr_total_post

            yearly_breakdowns.append(YearlyCompBreakdown(
                year=year_num,
                base_salary=base,
                cash_bonus=total_cash_bonus,
                equity_vested=equity_vest,
                total_pre_tax=yr_total_pre,
                take_home_post_tax=yr_total_post,
            ))

        avg_annual = round(total_pre_tax / 4.0, 2)

        # Counter-offer lever logic (target 12-16% boost primarily on base + equity)
        counter_target = round(avg_annual * 1.14, 2)
        target_increase_usd = round(counter_target - avg_annual, 2)

        if offer.vesting_schedule == "amazon_5_15_40_40":
            advice = (
                f"Backloaded Equity Warning: Year 1 & 2 equity is only 5% & 15%. Counter by asking for a "
                f"${int(target_increase_usd * 0.7):,} Year-1 sign-on bonus bridge and +${int(target_increase_usd * 0.3):,} base salary increase."
            )
        elif offer.startup_exit_multiple > 1.5:
            advice = (
                f"High-Growth Scenario ({offer.startup_exit_multiple}x multiple): Your 4-year total upside expands to "
                f"${int(total_pre_tax):,}. Ask for standard 1-year cliff with accelerated vesting on change of control."
            )
        else:
            advice = (
                f"Standard Market Strategy: Counter at ${int(counter_target):,}/yr (+${int(target_increase_usd):,}). "
                f"Request an increase of +$15,000 on Base and +${int(target_increase_usd * 2):,} in total Equity grant."
            )

        return CompSimulationResult(
            company=offer.company,
            role_title=offer.role_title,
            four_year_total_pre_tax=round(total_pre_tax, 2),
            four_year_total_post_tax=round(total_post_tax, 2),
            average_annual_comp=avg_annual,
            yearly_breakdowns=yearly_breakdowns,
            negotiation_counter_target=counter_target,
            negotiation_advice=advice,
            timestamp=datetime.utcnow().isoformat(),
        )


comp_simulator_engine = CompensationSimulatorEngine()
