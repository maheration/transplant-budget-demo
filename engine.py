"""
engine.py
The Transplant Sustainability Calculation Engine.

Four-step subtract-to-solve logic:
  Step 1 – Locked Drain    : existing patients × cost/head (with discharge levers)
  Step 2 – Nuke Drain      : orphan meds (toggleable)
  Step 3 – Growth Cost     : new transplants × Year 1 protocol cost
  Step 4 – Available Room  : budget − locked − nukes − growth

Also runs multi-year projections (Year 0 → N) with carry-over logic:
  new patients in Year N become maintenance patients in Year N+1.
"""

from dataclasses import dataclass, field
from typing import Dict, List


# ─────────────────────────────────────────────────────────────────────────────
# Input params (everything the sidebar controls)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SimParams:
    # Budget
    budget_sar: float = 12_000_000

    # New transplant volumes (Year 0 absolute numbers)
    new_kidney_adult: int = 160
    new_kidney_ped:   int = 40
    new_liver_adult:  int = 64
    new_liver_ped:    int = 16

    # Annual growth rates for new transplants (0.0 – 0.25)
    kidney_growth_pct: float = 0.0
    liver_growth_pct:  float = 0.0

    # Discharge levers (fraction of existing patients discharged, 0.0 – 0.25)
    discharge_old_kidney_adult: float = 0.0
    discharge_old_kidney_ped:   float = 0.0
    discharge_old_liver_adult:  float = 0.0
    discharge_old_liver_ped:    float = 0.0
    discharge_gen_nephro:       float = 0.0
    discharge_gen_nephro_ped:   float = 0.0
    discharge_gn:               float = 0.0
    discharge_gen_hepato:       float = 0.0   # zero cost anyway but shown for completeness

    # General clinic growth (0.0 – 0.15)
    gen_nephro_growth_pct:  float = 0.0
    gen_hepato_growth_pct:  float = 0.0

    # Risk / sensitivity
    drug_price_change_pct:  float = 0.0   # –0.20 to +0.20
    rejection_uplift_pct:   float = 0.0   # 0.0 to 0.30 – applied to transplant costs only

    # Toggles
    include_nukes: bool = True

    # Projection horizon
    horizon: int = 3


# ─────────────────────────────────────────────────────────────────────────────
# Single-year result
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class YearResult:
    year: int

    # Maintenance costs (existing patients)
    cost_old_kidney_adult: float = 0.0
    cost_old_kidney_ped:   float = 0.0
    cost_old_liver_adult:  float = 0.0
    cost_old_liver_ped:    float = 0.0
    cost_gen_nephro:       float = 0.0
    cost_gen_nephro_ped:   float = 0.0
    cost_gn:               float = 0.0
    cost_gen_hepato:       float = 0.0

    # New transplant costs (Year 1 protocol)
    cost_new_kidney_adult: float = 0.0
    cost_new_kidney_ped:   float = 0.0
    cost_new_liver_adult:  float = 0.0
    cost_new_liver_ped:    float = 0.0

    # Orphan / nuke meds
    cost_nukes: float = 0.0

    # Volumes this year
    n_new_kidney_adult: int = 0
    n_new_kidney_ped:   int = 0
    n_new_liver_adult:  int = 0
    n_new_liver_ped:    int = 0

    @property
    def total_maintenance(self):
        # Nukes are fixed annual drain — part of locked/maintenance bucket
        return (self.cost_old_kidney_adult + self.cost_old_kidney_ped +
                self.cost_old_liver_adult  + self.cost_old_liver_ped  +
                self.cost_gen_nephro       + self.cost_gen_nephro_ped +
                self.cost_gn               + self.cost_gen_hepato     +
                self.cost_nukes)

    @property
    def total_new_transplants(self):
        return (self.cost_new_kidney_adult + self.cost_new_kidney_ped +
                self.cost_new_liver_adult  + self.cost_new_liver_ped)

    @property
    def total_spend(self):
        return self.total_maintenance + self.total_new_transplants

    @property
    def budget_remaining(self):
        return 11_000_000 - self.total_spend   # always vs fixed 11M for display clarity

    @property
    def pct_budget_used(self):
        return self.total_spend / 11_000_000 * 100


# ─────────────────────────────────────────────────────────────────────────────
# Main engine
# ─────────────────────────────────────────────────────────────────────────────

def run_simulation(data: dict, params: SimParams) -> List[YearResult]:
    """
    Runs a multi-year simulation.
    Returns a list of YearResult objects, one per year (Year 0 = current year).
    """
    census    = data["census"]
    protocols = data["protocols"]
    nuke_total = data["orphan_drugs"]["total"] if params.include_nukes else 0.0

    # Price multiplier (drug inflation/deflation)
    price_mult = 1.0 + params.drug_price_change_pct
    # Rejection uplift applies to transplant patients only
    reject_mult = 1.0 + params.rejection_uplift_pct

    # ── Base patient counts (after discharge levers) ──────────────────────────
    def discharged(category_key, discharge_frac):
        base = census[category_key]["patients"]
        return max(0, int(base * (1 - discharge_frac)))

    base_old_kidney_adult = discharged("Adult_Kidney",          params.discharge_old_kidney_adult)
    base_old_kidney_ped   = discharged("Ped_Kidney",            params.discharge_old_kidney_ped)
    base_old_liver_adult  = discharged("Adult_Liver",           params.discharge_old_liver_adult)
    base_old_liver_ped    = discharged("Ped_Liver",             params.discharge_old_liver_ped)
    base_gen_nephro       = discharged("adult_gen_Nephrology",  params.discharge_gen_nephro)
    base_gen_nephro_ped   = discharged("ped_gen_Nephrology",    params.discharge_gen_nephro_ped)
    base_gn               = discharged("GN_Specialized_Group",  params.discharge_gn)
    base_gen_hepato_adult = discharged("adult_gen_Hepatology",  params.discharge_gen_hepato)
    base_gen_hepato_ped   = discharged("ped_gen_Hepatology",    params.discharge_gen_hepato)

    # Cost per head after price adjustment (and rejection uplift for transplant categories)
    cph = lambda cat: census[cat]["cost_per_head"] * price_mult
    cph_tx = lambda cat: census[cat]["cost_per_head"] * price_mult * reject_mult

    # Protocol costs per new patient (Year 1) after price + rejection
    proto = lambda key: protocols[key] * price_mult * reject_mult

    # ── Cumulative carry-over pools (new → old in subsequent years) ───────────
    carry_kidney_adult = 0
    carry_kidney_ped   = 0
    carry_liver_adult  = 0
    carry_liver_ped    = 0

    results = []

    for yr in range(params.horizon + 1):
        year_label = data["assumptions"]["current_year"] + yr

        # New transplant volumes this year (growth applied from Year 1 onwards)
        growth_k = (1 + params.kidney_growth_pct) ** yr
        growth_l = (1 + params.liver_growth_pct)  ** yr

        n_nka = round(params.new_kidney_adult * growth_k)
        n_nkp = round(params.new_kidney_ped   * growth_k)
        n_nla = round(params.new_liver_adult  * growth_l)
        n_nlp = round(params.new_liver_ped    * growth_l)

        # General clinic growth
        gen_nephro_mult  = (1 + params.gen_nephro_growth_pct)  ** yr
        gen_hepato_mult  = (1 + params.gen_hepato_growth_pct)  ** yr

        # ── STEP 1: Maintenance (existing + carry-over from prior years) ──────
        eff_old_ka = base_old_kidney_adult + carry_kidney_adult
        eff_old_kp = base_old_kidney_ped   + carry_kidney_ped
        eff_old_la = base_old_liver_adult  + carry_liver_adult
        eff_old_lp = base_old_liver_ped    + carry_liver_ped

        cost_old_ka  = eff_old_ka * cph_tx("Adult_Kidney")
        cost_old_kp  = eff_old_kp * cph_tx("Ped_Kidney")
        cost_old_la  = eff_old_la * cph_tx("Adult_Liver")
        cost_old_lp  = eff_old_lp * cph_tx("Ped_Liver")

        cost_gen_ne  = base_gen_nephro     * gen_nephro_mult * cph("adult_gen_Nephrology")
        cost_gen_nep = base_gen_nephro_ped * gen_nephro_mult * cph("ped_gen_Nephrology")
        cost_gn      = base_gn             * cph("GN_Specialized_Group")
        cost_gen_h   = (base_gen_hepato_adult + base_gen_hepato_ped) * gen_hepato_mult * cph("adult_gen_Hepatology")

        # ── STEP 2: Nuke drain ────────────────────────────────────────────────
        cost_nukes = nuke_total * price_mult

        # ── STEP 3: New transplant costs (Year 1 protocol) ───────────────────
        cost_nka = n_nka * proto("new_kidney_adult")
        cost_nkp = n_nkp * proto("new_kidney_ped")
        cost_nla = n_nla * proto("new_liver_adult")
        cost_nlp = n_nlp * proto("new_liver_ped")

        yr_result = YearResult(
            year               = year_label,
            cost_old_kidney_adult = cost_old_ka,
            cost_old_kidney_ped   = cost_old_kp,
            cost_old_liver_adult  = cost_old_la,
            cost_old_liver_ped    = cost_old_lp,
            cost_gen_nephro       = cost_gen_ne,
            cost_gen_nephro_ped   = cost_gen_nep,
            cost_gn               = cost_gn,
            cost_gen_hepato       = cost_gen_h,
            cost_new_kidney_adult = cost_nka,
            cost_new_kidney_ped   = cost_nkp,
            cost_new_liver_adult  = cost_nla,
            cost_new_liver_ped    = cost_nlp,
            cost_nukes            = cost_nukes,
            n_new_kidney_adult    = n_nka,
            n_new_kidney_ped      = n_nkp,
            n_new_liver_adult     = n_nla,
            n_new_liver_ped       = n_nlp,
        )
        results.append(yr_result)

        # ── Carry-over: this year's new patients become next year's maintenance
        carry_kidney_adult += n_nka
        carry_kidney_ped   += n_nkp
        carry_liver_adult  += n_nla
        carry_liver_ped    += n_nlp

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Derived analytics (answer the 13 clinical questions)
# ─────────────────────────────────────────────────────────────────────────────

def months_until_collapse(results: List[YearResult], budget: float) -> str:
    """Q1: When does the budget run out?"""
    for r in results:
        if r.total_spend > budget:
            overage_frac = (r.total_spend - budget) / (r.total_spend / 12)
            months_in = 12 - overage_frac
            return f"Year {r.year} (~month {max(1, int(months_in))})"
    return "Within projection horizon ✅"


def max_sustainable_transplants(data: dict, params: SimParams) -> dict:
    """
    Q2: What is the max sustainable new transplant volume?
    Solves: budget - locked_drain - nukes = new_tx_cost × N

    Always uses a fixed default ratio (80% adult / 20% ped, 71% kidney / 29% liver)
    so the answer is independent of sidebar volume inputs — it answers the question
    'given the locked drain, how many transplants COULD fit?' regardless of what
    the user typed for planned volumes.
    """
    from copy import deepcopy
    base = deepcopy(params)
    base.new_kidney_adult  = 0
    base.new_kidney_ped    = 0
    base.new_liver_adult   = 0
    base.new_liver_ped     = 0
    base.kidney_growth_pct = 0
    base.liver_growth_pct  = 0

    zero_results = run_simulation(data, base)
    locked    = zero_results[0].total_maintenance + zero_results[0].cost_nukes
    available = params.budget_sar - locked

    proto       = data["protocols"]
    price_mult  = 1 + params.drug_price_change_pct
    reject_mult = 1 + params.rejection_uplift_pct

    # Fixed default ratios: kidney 80% adult / 20% ped; liver 80% adult / 20% ped
    # kidney:liver split = 71:29 (matches 200 kidney / 80 liver default target)
    adult_ped_ratio = 0.80          # 80% adult within each organ
    kl_ratio        = 200 / 280     # kidney share of total transplants

    avg_k_cost = (adult_ped_ratio * proto["new_kidney_adult"] +
                  (1 - adult_ped_ratio) * proto["new_kidney_ped"]) * price_mult * reject_mult
    avg_l_cost = (adult_ped_ratio * proto["new_liver_adult"] +
                  (1 - adult_ped_ratio) * proto["new_liver_ped"]) * price_mult * reject_mult

    blended_cost = kl_ratio * avg_k_cost + (1 - kl_ratio) * avg_l_cost

    if available <= 0 or blended_cost <= 0:
        return {
            "available_sar": available,
            "max_kidney": 0,
            "max_liver":  0,
            "max_total":  0,
        }

    max_total = int(available / blended_cost)
    max_k     = int(max_total * kl_ratio)
    max_l     = max_total - max_k

    return {
        "available_sar": available,
        "max_kidney":    max_k,
        "max_liver":     max_l,
        "max_total":     max_total,
    }


def freeze_scenario(data: dict, params: SimParams) -> List[YearResult]:
    """Q3: If we stop all new transplants tomorrow."""
    from copy import deepcopy
    p = deepcopy(params)
    p.new_kidney_adult = 0
    p.new_kidney_ped   = 0
    p.new_liver_adult  = 0
    p.new_liver_ped    = 0
    p.kidney_growth_pct = 0
    p.liver_growth_pct  = 0
    return run_simulation(data, p)


def existing_only_annual_cost(data: dict, params: SimParams) -> float:
    """Q3 helper: what existing patients cost per year with zero new transplants."""
    r = freeze_scenario(data, params)
    return r[0].total_spend


# ─────────────────────────────────────────────────────────────────────────────
# Sanity check
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from data_loader import load_all
    data = load_all()

    params = SimParams(
        budget_sar        = data["assumptions"]["budget_sar"],
        horizon           = data["assumptions"]["projection_horizon"],
        new_kidney_adult  = 160,
        new_kidney_ped    = 40,
        new_liver_adult   = 64,
        new_liver_ped     = 16,
        include_nukes     = True,
    )

    results = run_simulation(data, params)

    print("\n=== SIMULATION RESULTS (Base Scenario) ===")
    print(f"{'Year':<6} {'Total Spend':>15} {'Maintenance':>15} {'New Tx':>12} {'Nukes':>12} {'vs Budget':>12}")
    print("-" * 75)
    for r in results:
        diff = r.total_spend - params.budget_sar
        flag = "🚨" if diff > 0 else "✅"
        print(f"{r.year:<6} {r.total_spend:>15,.0f} {r.total_maintenance:>15,.0f} "
              f"{r.total_new_transplants:>12,.0f} {r.cost_nukes:>12,.0f} "
              f"{diff:>+12,.0f} {flag}")

    print(f"\n→ Budget collapse: {months_until_collapse(results, params.budget_sar)}")

    cap = max_sustainable_transplants(data, params)
    print(f"→ Available for new Tx: {cap['available_sar']:,.0f} SAR")
    print(f"→ Max sustainable: {cap['max_kidney']} kidney + {cap['max_liver']} liver = {cap.get('max_total',0)} total")

    freeze = freeze_scenario(data, params)
    print(f"\n→ Existing patients alone cost: {freeze[0].total_spend:,.0f} SAR/year")
