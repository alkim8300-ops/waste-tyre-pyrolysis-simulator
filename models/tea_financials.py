"""Techno-economic analysis and emissions-compliance maths, calibrated for Nairobi (USD, 1 USD ~ 129 KES)."""
from dataclasses import dataclass, asdict
from models.mass_energy_balance import simulate_pyrolysis_mass_energy

MW_H2S, MW_NAOH, MW_SO2 = 34.08, 40.00, 64.07


@dataclass
class Assumptions:
    capex_base: float = 280_000.0     # USD at 10 TPD
    capex_exp: float = 0.65           # capacity-exponent rule (0.6-0.7 typical)
    elt_cost: float = 25.0            # USD/t tyres delivered
    power_kwh_t: float = 115.0
    power_tariff: float = 0.14        # USD/kWh (KPLC CI1)
    naoh_cost_t: float = 4.50         # USD per t feed
    labour_base: float = 78_000.0     # USD/yr at 10 TPD, scaled by (feed/10)^0.5
    maint_base: float = 22_200.0      # USD/yr at base CAPEX, scaled with CAPEX
    
    # Revenue pricing
    tpo_price: float = 550.0
    rcb_price: float = 380.0          # Price if upgraded/milled
    raw_char_price: float = 120.0     # Price for raw high-ash pyrolysis char (fuel/filler)
    steel_price: float = 220.0
    
    # Process Reality Toggles
    upgrade_char_to_rcb: bool = True  # Defaults True to maintain baseline JSON parity
    rcb_upgrade_capex: float = 65_000.0 # Additional CAPEX for milling/demineralization plant
    
    tax: float = 0.30
    discount: float = 0.14
    horizon_yr: int = 5
    dep_years: int = 10               # straight-line
    co2e_per_t_elt: float = 0.85      # tCO2e avoided per t ELT (uncontrolled burning/landfill)
    h2s_wt: float = 0.0115            # H2S in raw syngas, wt fraction
    
    # Optional realism levers. Defaults reproduce the original model exactly.
    ramp: tuple = (1.0, 1.0, 1.0, 1.0, 1.0)  # utilisation by year; realistically (0.6, 0.85, 1.0, 1.0, 1.0)
    salvage_frac: float = 0.0         # share of remaining book value recovered at end of horizon
    capex_contingency: float = 0.0    # e.g. 0.25 adds 25% to CAPEX
    other_opex_pct_capex: float = 0.0 # insurance etc., share of CAPEX per year
    other_opex_fixed: float = 0.0     # admin, logistics, effluent disposal, USD/yr
    tpo_realisation: float = 1.0      # share of reference TPO price achieved (sulfur discount)
    rcb_sell_through: float = 1.0     # share of char actually sold


def scrubber_stoichiometry(syngas_tpd: float, h2s_wt: float = 0.0115) -> dict:
    """H2S + 2NaOH -> Na2S + 2H2O (conservative design basis; at pH ~9 mostly NaHS forms, needing ~1 NaOH);
    2H2S + 3O2 -> 2SO2 + 2H2O if left unscrubbed."""
    h2s = syngas_tpd * 1000.0 * h2s_wt
    return {"h2s_kg_day": round(h2s, 2),
            "naoh_kg_day_stoich": round(h2s / MW_H2S * 2 * MW_NAOH, 2),
            "so2_kg_day_if_unscrubbed": round(h2s / MW_H2S * MW_SO2, 2)}


def irr(cashflows, lo=-0.99, hi=100.0):
    f = lambda r: sum(c / (1 + r) ** t for t, c in enumerate(cashflows))
    if f(lo) * f(hi) > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if f(lo) * f(mid) > 0 else (lo, mid)
    return (lo + hi) / 2


def evaluate_plant_economics(temp_c=500.0, feed_tpd=10.0, op_days=300, a: Assumptions = None) -> dict:
    a = a or Assumptions()
    mb = simulate_pyrolysis_mass_energy(temp_c, feed_tpd)
    feed_yr = feed_tpd * op_days
    
    # Apply char upgrading CAPEX logic
    base_capex = a.capex_base * (feed_tpd / 10.0) ** a.capex_exp
    extra_capex = a.rcb_upgrade_capex if a.upgrade_char_to_rcb else 0.0
    capex = (base_capex + extra_capex) * (1.0 + a.capex_contingency)
    
    # Apply dual-tier char pricing logic
    active_char_price = a.rcb_price if a.upgrade_char_to_rcb else a.raw_char_price
    
    rev = {"tpo": mb["tpo_tpd"] * op_days * a.tpo_price * a.tpo_realisation,
           "rcb": mb["rcb_tpd"] * op_days * active_char_price * a.rcb_sell_through,
           "steel": mb["steel_tpd"] * op_days * a.steel_price}
           
    variable = {"feedstock": feed_yr * a.elt_cost,
                "power_naoh": feed_yr * (a.power_kwh_t * a.power_tariff + a.naoh_cost_t)}
                
    fixed = {"labour": a.labour_base * (feed_tpd / 10.0) ** 0.5,
             "maintenance": a.maint_base * capex / (a.capex_base + extra_capex),
             "other": a.other_opex_fixed + a.other_opex_pct_capex * capex}
             
    opex = {**variable, **fixed}
    revenue, total_opex = sum(rev.values()), sum(opex.values())
    ebitda = revenue - total_opex                        # full-utilisation (steady-state) year
    dep = capex / a.dep_years
    tax = a.tax * max(0.0, ebitda - dep)
    cf = ebitda - tax
    
    flows = [-capex]
    for t in range(1, a.horizon_yr + 1):
        u = a.ramp[min(t, len(a.ramp)) - 1]
        e = u * (revenue - sum(variable.values())) - sum(fixed.values())
        flows.append(e - a.tax * max(0.0, e - (dep if t <= a.dep_years else 0.0)))
        
    flows[-1] += a.salvage_frac * capex * max(0.0, 1.0 - a.horizon_yr / a.dep_years)
    npv = sum(c / (1 + a.discount) ** t for t, c in enumerate(flows))
    r = irr(flows)
    
    cum, payback = -capex, None
    for t, c in enumerate(flows[1:], 1):
        if cum + c >= 0:
            payback = t - 1 + (-cum) / c
            break
        cum += c
    if payback is None and cf > 0:
        payback = a.horizon_yr + (-cum) / cf
        
    return {**mb, "capex_usd": round(capex), "revenue_usd_yr": round(revenue),
            "opex_usd_yr": round(total_opex), "ebitda_usd_yr": round(ebitda),
            "net_profit_usd_yr": round(ebitda - dep - tax), "after_tax_cashflow_usd_yr": round(cf),
            "payback_yr": None if payback is None else round(payback, 3),
            "npv_usd": round(npv), "irr_pct": None if r is None else round(r * 100, 1),
            "co2e_avoided_t_yr": round(feed_yr * a.co2e_per_t_elt),
            "revenue_breakdown": {k: round(v) for k, v in rev.items()},
            "opex_breakdown": {k: round(v) for k, v in opex.items()},
            "scrubber": scrubber_stoichiometry(mb["syngas_tpd"], a.h2s_wt),
            "assumptions": asdict(a)}


if __name__ == "__main__":
    import json
    
    print("=== BASELINE (100% Day-1 Capacity, Upgraded rCB) ===")
    print(json.dumps(evaluate_plant_economics(), indent=2))
    
    print("\n=== REALISTIC SCENARIO (Raw Char Only, 60% Year 1 Ramp, 10% Contingency) ===")
    realistic_assumptions = Assumptions(
        upgrade_char_to_rcb=False, 
        ramp=(0.60, 0.85, 1.0, 1.0, 1.0),
        capex_contingency=0.10
    )
    print(json.dumps(evaluate_plant_economics(a=realistic_assumptions), indent=2))
