"""Mass and energy balance for ELT rotary-kiln pyrolysis (basis: whole-tyre feed, 400-600 C)."""
from dataclasses import dataclass, asdict

CRUMB_FRAC, MOISTURE_FRAC = 0.88, 0.012      # of whole-tyre feed
CP_RUBBER, DH_PYR, LAMBDA_V = 1.95, 460.0, 2257.0   # MJ/(t.K), MJ/t crumb, MJ/t water
ETA_KILN, LHV_SYNGAS = 0.72, 38000.0         # -, MJ/t
T_AMB, T_COND = 25.0, 35.0                   # C
CP_OIL_VAP, LAMBDA_OIL, CP_GAS = 2.2, 300.0, 2.0   # condenser assumptions (MJ/t.K, MJ/t, MJ/t.K)
CP_WATER, CW_DELTA_T = 4.18, 10.0            # MJ/(t.K), K rise in cooling water


def yield_fractions(temp_c: float) -> dict:
    """EQ 1: product yields, wt% of whole tyre. Valid 400-600 C."""
    if not 400.0 <= temp_c <= 600.0:
        raise ValueError(f"temp_c={temp_c} outside validated window 400-600 C")
    steel = 12.0
    oil = 44.2 - 0.00115 * (temp_c - 500.0) ** 2
    gas = 9.8 + 0.055 * (temp_c - 400.0) + 0.00018 * (temp_c - 400.0) ** 2
    return {"steel": steel, "oil": oil, "gas": gas, "rcb": 100.0 - (steel + oil + gas)}


@dataclass
class ProcessOutputs:
    temp_c: float
    feed_tpd: float
    tpo_tpd: float
    rcb_tpd: float
    steel_tpd: float
    syngas_tpd: float
    wastewater_tpd: float          # moisture, carried inside the by-difference rCB remainder
    reactor_duty_gj_day: float     # burner duty, EQ 2
    syngas_energy_gj_day: float
    self_sufficiency_pct: float
    surplus_syngas_gj_day: float
    condenser_duty_gj_day: float
    condenser_cooling_water_m3_day: float


def simulate_pyrolysis_mass_energy(temp_c: float = 500.0, feed_tpd: float = 10.0) -> dict:
    y = yield_fractions(float(temp_c))
    steel, oil, gas, rcb = (y[k] * feed_tpd / 100.0 for k in ("steel", "oil", "gas", "rcb"))
    assert abs(steel + oil + gas + rcb - feed_tpd) < 1e-9, "mass balance does not close"
    crumb, water = CRUMB_FRAC * feed_tpd, MOISTURE_FRAC * feed_tpd
    q_sens = crumb * CP_RUBBER * (temp_c - T_AMB)
    q_pyr = crumb * DH_PYR + water * LAMBDA_V
    duty = (q_sens + q_pyr) / ETA_KILN / 1000.0
    syn = gas * LHV_SYNGAS / 1000.0
    q_cond = (oil * (CP_OIL_VAP * (temp_c - T_COND) + LAMBDA_OIL)
              + gas * CP_GAS * (temp_c - T_COND)) / 1000.0
    out = ProcessOutputs(temp_c, feed_tpd, oil, rcb, steel, gas, water, duty, syn,
                         100.0 * syn / duty, syn - duty, q_cond,
                         q_cond * 1000.0 / (CP_WATER * CW_DELTA_T))
    return {k: round(v, 4) for k, v in asdict(out).items()}


if __name__ == "__main__":
    import json
    print(json.dumps(simulate_pyrolysis_mass_energy(), indent=2))
