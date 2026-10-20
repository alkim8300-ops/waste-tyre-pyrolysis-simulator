"""Writes the verification matrix (420-580 C, 10 TPD, 300 d/yr) used by the web dashboard's self-check."""
import json, shutil
from pathlib import Path
from models.tea_financials import evaluate_plant_economics

ROOT = Path(__file__).resolve().parent.parent
rows = [evaluate_plant_economics(t, 10.0, 300) for t in range(420, 581, 20)]
assumptions = rows[0]["assumptions"]
for r in rows:
    r.pop("assumptions")
payload = {"basis": "10 TPD whole ELT, 300 d/yr, Nairobi", "scenarios": rows, "assumptions": assumptions}
out = ROOT / "data" / "baseline_10tpd_nairobi.json"
out.write_text(json.dumps(payload, indent=2))
shutil.copy(out, ROOT / "web" / "baseline_10tpd_nairobi.json")   # build copy served with the site
print(f"wrote {len(rows)} scenarios -> {out}")
