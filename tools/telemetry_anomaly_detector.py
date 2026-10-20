"""
Synthetic Kiln Telemetry Generator & Unsupervised Anomaly Detection Pipeline.
Simulates 10-TPD rotary kiln sensor streams (Temp, Pressure, O2) and flags 
wax blockages and seal leaks using multi-variate statistical thresholding.
"""

import json
import math
import random
from pathlib import Path

def generate_telemetry(n_minutes: int = 500, seed: int = 42) -> list[dict]:
    random.seed(seed)
    stream = []
    
    for minute in range(n_minutes):
        # Normal steady-state operating baselines
        temp_c = random.gauss(500.0, 4.5)       # Target: 500 °C
        pressure_kpa = random.gauss(104.0, 0.8) # Slight positive pressure
        o2_vol_pct = random.gauss(0.35, 0.05)   # Anaerobic (< 0.5% O2)
        true_label = "NORMAL"

        # Inject synthetic fault 1: Condenser Wax Fouling (Minutes 140-155)
        if 140 <= minute <= 155:
            pressure_kpa += (minute - 139) * 1.8  # Rapid backpressure buildup
            temp_c -= (minute - 139) * 1.2        # Endothermic dip
            true_label = "FAULT_WAX_BLOCKAGE"

        # Inject synthetic fault 2: Rotary Seal Air Leak / Thermal Runaway (Minutes 340-352)
        elif 340 <= minute <= 352:
            o2_vol_pct += (minute - 339) * 0.25   # Air ingress
            temp_c += (minute - 339) * 7.5        # Exothermic oxidation spike
            pressure_kpa += (minute - 339) * 0.9
            true_label = "FAULT_O2_RUNAWAY"

        stream.append({
            "minute": minute,
            "temp_c": round(
