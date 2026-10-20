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
            "temp_c": round(temp_c, 2),
            "pressure_kpa": round(pressure_kpa, 2),
            "o2_vol_pct": round(max(0.0, o2_vol_pct), 3),
            "ground_truth": true_label
        })
    return stream


def detect_anomalies(stream: list[dict], z_threshold: float = 3.2) -> dict:
    # Use initial 100 minutes of steady-state operation to calibrate baseline stats
    calib = stream[:100]
    
    def stats(key: str):
        vals = [r[key] for r in calib]
        mean = sum(vals) / len(vals)
        std = math.sqrt(sum((x - mean) ** 2 for x in vals) / len(vals))
        return mean, max(std, 1e-6)

    t_mean, t_std = stats("temp_c")
    p_mean, p_std = stats("pressure_kpa")
    o_mean, o_std = stats("o2_vol_pct")

    flagged_events = []
    tp = fp = fn = tn = 0

    for row in stream:
        z_t = (row["temp_c"] - t_mean) / t_std
        z_p = (row["pressure_kpa"] - p_mean) / p_std
        z_o = (row["o2_vol_pct"] - o_mean) / o_std

        # Composite Euclidean Z-distance across sensor dimensions
        anomaly_score = math.sqrt(z_t**2 + z_p**2 + z_o**2)
        is_anomaly = anomaly_score > z_threshold

        # Root-cause classification rules for engineering diagnostics
        predicted_class = "NORMAL"
        if is_anomaly:
            if z_o > 2.5 and z_t > 2.0:
                predicted_class = "ALARM_O2_SEAL_LEAK"
            elif z_p > 2.5:
                predicted_class = "ALARM_WAX_FOULING"
            else:
                predicted_class = "ALARM_PROCESS_DRIFT"

        row["anomaly_score"] = round(anomaly_score, 2)
        row["predicted_class"] = predicted_class

        actual_fault = row["ground_truth"] != "NORMAL"
        if is_anomaly and actual_fault:
            tp += 1
        elif is_anomaly and not actual_fault:
            fp += 1
        elif not is_anomaly and actual_fault:
            fn += 1
        else:
            tn += 1

        if is_anomaly:
            flagged_events.append(row)

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) else 0.0

    return {
        "metrics": {
            "total_minutes": len(stream),
            "anomalies_flagged": len(flagged_events),
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4)
        },
        "flagged_sample": flagged_events[:10]
    }


if __name__ == "__main__":
    data = generate_telemetry()
    report = detect_anomalies(data)
    print("=== KILN TELEMETRY ANOMALY DETECTION REPORT ===")
    print(json.dumps(report["metrics"], indent=2))
