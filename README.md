# Waste Tyre Pyrolysis Simulator (10 TPD, Nairobi)

Coupled mass balance, energy balance and techno-economic model of a rotary-kiln plant converting end-of-life tyres (ELT) to tyre pyrolysis oil (TPO), recovered carbon black (rCB), steel and syngas. A Python engine produces the reference numbers; a zero-build web dashboard re-implements the same equations and verifies itself against them on load.

**Live demo:** `https://<your-username>.github.io/waste-tyre-pyrolysis-simulator/`

## Model

Yields, % of whole tyre, valid for 400 °C ≤ T ≤ 600 °C (15 °C/min, 45 min residence):

$$Y_{oil}=44.2-0.00115\,(T-500)^2 \qquad Y_{gas}=9.8+0.055\,(T-400)+0.00018\,(T-400)^2$$

$$Y_{steel}=12 \qquad Y_{rCB}=100-(Y_{steel}+Y_{oil}+Y_{gas})$$

Kiln burner duty, with $\dot m_{crumb}=0.88\,M_{feed}$, $\dot m_w=0.012\,M_{feed}$, $C_{p}=1.95$ MJ/(t·K), $\Delta H_{pyr}=460$ MJ/t, $\lambda_v=2257$ MJ/t, $\eta=0.72$:

$$Q_{burner}=\frac{\dot m_{crumb}C_p(T-25)+\dot m_{crumb}\Delta H_{pyr}+\dot m_w\lambda_v}{\eta}$$

Syngas self-sufficiency is $\dot m_{gas}\times 38{,}000\ \text{MJ/t}$ divided by $Q_{burner}$. CAPEX scales as $C_2=C_1(S_2/S_1)^{0.65}$.

## Layout

```
models/        mass_energy_balance.py, tea_financials.py, export_lookup.py
tests/         unittest suite (mass closure, window limits, economics identities)
data/          baseline_10tpd_nairobi.json (generated)
web/           index.html, style.css, app.js (+ build copy of the baseline JSON)
.github/       CI: tests, baseline drift check, GitHub Pages deploy
```

## Run

```bash
python -m unittest discover -s tests      # tests
python -m models.tea_financials           # baseline KPIs as JSON
python -m models.export_lookup            # regenerate baseline (data/ and web/)
python -m http.server -d web 8000         # dashboard at http://localhost:8000
```

Python needs only the standard library (3.9+).

## Deploy

GitHub Pages cannot publish from `/web`, only from `/` or `/docs`, so this repo deploys with the included Actions workflow. In the repository go to Settings → Pages → Source and choose **GitHub Actions**, then push to `main`.

## Assumptions and limits

- Yield polynomials are empirical fits, not a kinetic model. Prices, ELT cost and CAPEX are project inputs; stress-test them with the dashboard's price sliders.
- Moisture (1.2 wt%) is carried inside the by-difference rCB remainder, so mass closes exactly to the feed.
- Cash flow is EBITDA less tax on (EBITDA − 10-year straight-line depreciation). No ramp-up, working capital or financing.
- Condenser duty uses assumed vapour heat capacities and a 10 K cooling-water rise (constants at the top of `mass_energy_balance.py`).
- The CO₂e factor (0.85 t/t ELT) is a placeholder and needs a source. NEMA stack limits are not encoded; add them from the Environmental Management and Co-ordination (Air Quality) Regulations before claiming compliance.

## Sharing with an AI assistant

`python -m tools.bundle` writes two files to `dist/` (git-ignored):

- `waste-tyre-pyrolysis-simulator_bundle.md`: every source file in one text file, with a briefing header (commands, baseline numbers, invariants, open items). Upload this one file to Gemini, ChatGPT or Claude when you want help changing the code.
- `waste-tyre-pyrolysis-simulator.html`: the dashboard as a single self-contained file that opens by double-click or can be pasted into Gemini Canvas. Only Chart.js still loads from a CDN.
