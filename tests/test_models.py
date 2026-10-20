import unittest
from models.mass_energy_balance import simulate_pyrolysis_mass_energy as mb, yield_fractions
from models.tea_financials import evaluate_plant_economics as tea, scrubber_stoichiometry


class ModelTests(unittest.TestCase):
    def test_mass_closure_across_window(self):
        for t in range(400, 601, 5):
            for f in (5, 10, 50):
                o = mb(t, f)
                self.assertAlmostEqual(o["tpo_tpd"] + o["rcb_tpd"] + o["steel_tpd"] + o["syngas_tpd"], f, places=2)

    def test_oil_peaks_at_500(self):
        self.assertAlmostEqual(yield_fractions(500)["oil"], 44.2)
        self.assertLess(yield_fractions(450)["oil"], 44.2)

    def test_window_enforced(self):
        with self.assertRaises(ValueError):
            mb(650, 10)

    def test_baseline_is_self_sufficient(self):
        self.assertGreater(mb(500, 10)["self_sufficiency_pct"], 100)

    def test_baseline_economics_consistent(self):
        e = tea(500, 10, 300)
        self.assertEqual(e["revenue_usd_yr"] - e["opex_usd_yr"], e["ebitda_usd_yr"])
        self.assertEqual(e["opex_usd_yr"], 237_000)

    def test_h2s_baseline(self):
        self.assertAlmostEqual(scrubber_stoichiometry(1.71)["h2s_kg_day"], 19.67, places=1)


if __name__ == "__main__":
    unittest.main()
