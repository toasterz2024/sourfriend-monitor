import pandas as pd

def parse_session(json_data: dict) -> dict:
    rl = json_data["routineLog"]
    ha = json_data["heightAnalysis"]
    mi = json_data["manualInput"]

    meas = pd.DataFrame(json_data["measurements"])
    meas["elapsedSeconds"] = pd.to_numeric(meas["elapsedSeconds"])
    meas["height"]         = pd.to_numeric(meas["height"], errors="coerce")
    meas["containerTemp"]  = pd.to_numeric(meas["containerTemp"], errors="coerce")
    meas["ambientTemp"]    = pd.to_numeric(meas["ambientTemp"], errors="coerce")
    meas = meas[meas["isOutlier"] == False].sort_values("elapsedSeconds")

    steps = {}
    for step in meas["stepIndex"].unique():
        s = meas[meas["stepIndex"] == step]
        steps[int(step)] = {
            "start_h": s["elapsedSeconds"].iloc[0] / 3600,
            "end_h":   s["elapsedSeconds"].iloc[-1] / 3600,
            "avg_temp": s["containerTemp"].mean(),
        }

    ep1_start_h = steps.get(1, {}).get("start_h")
    cp_dur_h    = ep1_start_h

    # ── Peak detection ─────────────────────────────────────────
    # Primary: peakElapsedSeconds from heightAnalysis (firmware)
    # Fallback: smoothed max height in EP2 (step 2) + SP (step 3) only
    # EP1 excluded — it's the growth phase up to 100%, not the peak.
    # If EP2/SP not reached → no peak.
    peak_sec = ha.get("peakElapsedSeconds")

    if not peak_sec:
        active = meas[meas["stepIndex"].isin([2, 3])]
        if len(active) > 0 and not active["height"].isna().all():
            h_smooth = active["height"].rolling(10, center=True, min_periods=1).median()
            peak_idx = h_smooth.idxmax()
            peak_h   = float(active.loc[peak_idx, "elapsedSeconds"]) / 3600
        else:
            peak_h = None
    else:
        peak_h = peak_sec / 3600

    ep1_to_peak_h = (peak_h - ep1_start_h) if (peak_h and ep1_start_h) else None

    started_at     = pd.to_datetime(rl["startedAt"])
    target_end_str = rl.get("targetEndTime")
    target_end     = pd.to_datetime(target_end_str) if target_end_str else None
    target_h       = (target_end - started_at).total_seconds() / 3600 if target_end else None
    diff_h         = (target_h - peak_h) if (target_h is not None and peak_h is not None) else None

    if diff_h is None:
        result = "no_peak"
    elif 0 <= diff_h <= 1.0:
        result = "success"
    elif diff_h > 1.0:
        result = "too_early"
    else:
        result = "late"

    return {
        "id":            rl["id"],
        "startedAt":     rl["startedAt"],
        "status":        rl.get("status"),
        "starterName":   mi.get("starterName"),
        "starterAmount": mi.get("starterAmount"),
        "flourAmount":   mi.get("flourAmount"),
        "waterAmount":   mi.get("waterAmount"),
        "cp_dur_h":      cp_dur_h,
        "ep1_start_h":   ep1_start_h,
        "ep1_to_peak_h": ep1_to_peak_h,
        "peak_h":        peak_h,
        "sp_start_h":    steps.get(3, {}).get("start_h"),
        "target_h":      target_h,
        "diff_h":        diff_h,
        "result":        result,
        "cp_avg_temp":   steps.get(0, {}).get("avg_temp"),
        "ep1_avg_temp":  steps.get(1, {}).get("avg_temp"),
        "measurements":  meas.to_dict(orient="records"),
    }
