# PRD — SourFriend Delayed Mode Monitor
**Version:** 1.0  
**Stack:** Python, Streamlit, Pandas, Matplotlib  
**Run:** locally via VS Code + Claude Code

---

## 1. Goal

A local Streamlit app to track daily fermentation experiments and evaluate how well the current firmware mftime logic performs. No ML models. No database. Pure analysis of JSON session logs.

---

## 2. Core Concept

The firmware calculates CP duration as:
```
CP duration = targetEndTime - routineStartTime - mftime
```
Where mftime = EP1→peak duration from the previous session (default 7h on first run).

**The app answers one question:** how often does the real peak land within the success window (≤ 30 minutes before targetEndTime)?

**Success definition (strict):**
```
0h ≤ (targetEndTime - real_peak) ≤ 0.5h
```

---

## 3. Data Source

- Input: JSON files exported from SourFriend device (one file per session)
- JSON structure: `routineLog`, `heightAnalysis`, `measurements`, `manualInput`
- Key fields used:
  - `heightAnalysis.peakElapsedSeconds` → real peak time
  - `routineLog.startedAt` → session start
  - `routineLog.alarmTime` or `routineLog.targetEndTime` → user target
  - `measurements` → height + temperature time series
  - `manualInput.starterAmount/flourAmount/waterAmount` → recipe

---

## 4. Data Storage

- Sessions stored as a local JSON file (`sessions_store.json`) in the app directory
- On upload: parse JSON → extract key fields → append to store
- Duplicate detection: by `routineLog.id`
- No external database required

---

## 5. Pages & Features

---

### Page 1 — Upload & History

**Upload**
- Drag & drop one or multiple JSON files
- Auto-parse on upload
- Show success/error message per file
- Skip duplicates silently

**Sessions table**
Columns:
| Column | Description |
|--------|-------------|
| Date | startedAt |
| Starter | starterName |
| Ratio | flour/starter |
| CP dur | hours in cold phase |
| EP1→peak | hours from warm-up to real peak |
| Peak at | elapsed hours when peak occurred |
| Target at | elapsed hours of targetEndTime |
| Δ (diff) | target − peak in hours |
| Result | ✅ success / ⚠ too early / ❌ late / — no peak |

- Sortable by date
- Color-coded Result column
- Download table as CSV button

**Result categories:**
- ✅ success: `0h ≤ diff ≤ 0.5h`
- ⚠ too early: `diff > 0.5h`
- ❌ late: `diff < 0h`
- — no peak: `peakElapsedSeconds` missing or session not completed

---

### Page 2 — Success Rate Dashboard

**Top metric row (3 columns):**
- Total sessions analyzed
- Success rate % (strict ≤30min window)
- Median Δ (how far off on average)

**Breakdown bar chart:**
Horizontal bar showing % of sessions in each category:
- ✅ within 30min window
- ⚠ too early (> 30min early)
- ❌ < 30min late
- ❌ 30min–1h late
- ❌ 1–2h late
- ❌ > 2h late

**Success rate over time (line chart):**
- X axis: session number (chronological)
- Y axis: cumulative success rate %
- Shows whether the firmware is improving as mftime learns

**Δ distribution (histogram):**
- X axis: diff in hours (target − peak)
- Vertical lines at 0 and 0.5h marking the success window
- Shows the spread of errors

---

### Page 3 — mftime Tracker

**Purpose:** visualize how mftime evolves session by session and whether it converges.

**Chart 1 — EP1→peak per session (scatter + line):**
- X axis: session number
- Y axis: hours
- Blue line: actual EP1→peak of each session
- Orange dashed line: mftime the device used for the NEXT session (= previous EP1→peak)
- Gray horizontal band: ±30min around the median EP1→peak (stability zone)

**Chart 2 — mftime error per session (bar chart):**
- Bar height = |actual EP1→peak − mftime used|
- Color: green if error < 0.5h, yellow if 0.5–1h, red if > 1h
- Shows how quickly mftime calibrates

**Key stats:**
- Sessions until first successful prediction
- Mean mftime error after session N (for N = 1, 2, 3, 5)
- Current mftime (last session's EP1→peak)

---

### Page 4 — Session Detail

**Session selector:** dropdown with date + starter + result

**Height chart:**
- Full height time series (smoothed with rolling median, window=10)
- Color-shaded background per step: CP (blue) / EP1 (orange) / EP2 (green) / SP (red) / DP (purple)
- Vertical dashed line: targetEndTime
- Green shaded band: success window (targetEndTime − 0.5h to targetEndTime)
- Black dot: real peak (peakElapsedSeconds)
- X axis: elapsed hours from session start

**Temperature chart (below height):**
- Container temp (solid line)
- Ambient temp (dashed line)
- Horizontal reference lines: 27°C (target warm) and 5°C (target cold)
- Same X axis as height chart

**Session info panel (sidebar or cards):**
- Started at
- Target end time
- CP duration
- CP avg temperature
- EP1→peak
- Real peak time
- Δ from target
- Result

---

## 6. File Structure

```
sourfriend_monitor/
├── app.py                  # main Streamlit entry point
├── pages/
│   ├── 1_upload.py
│   ├── 2_success_rate.py
│   ├── 3_mftime_tracker.py
│   └── 4_session_detail.py
├── utils/
│   ├── parser.py           # JSON → session dict
│   ├── store.py            # load/save sessions_store.json
│   └── charts.py           # reusable chart functions
├── sessions_store.json     # local persistent storage
└── requirements.txt
```

---

## 7. Parser Logic

`parser.py` must extract:

```python
def parse_session(json_data: dict) -> dict:
    rl   = json_data["routineLog"]
    ha   = json_data["heightAnalysis"]
    mi   = json_data["manualInput"]
    meas = pd.DataFrame(json_data["measurements"])

    # clean measurements
    meas["elapsedSeconds"] = pd.to_numeric(meas["elapsedSeconds"])
    meas["height"]         = pd.to_numeric(meas["height"], errors="coerce")
    meas["containerTemp"]  = pd.to_numeric(meas["containerTemp"], errors="coerce")
    meas["ambientTemp"]    = pd.to_numeric(meas["ambientTemp"], errors="coerce")
    meas = meas[meas["isOutlier"] == False].sort_values("elapsedSeconds")

    # step timing
    steps = {}
    for step in meas["stepIndex"].unique():
        s = meas[meas["stepIndex"] == step]
        steps[int(step)] = {
            "start_h": s["elapsedSeconds"].iloc[0] / 3600,
            "end_h":   s["elapsedSeconds"].iloc[-1] / 3600,
            "avg_temp": s["containerTemp"].mean(),
        }

    ep1_start_h = steps.get(1, {}).get("start_h", None)
    cp_dur_h    = ep1_start_h  # CP = 0 to EP1 start

    # IMPORTANT: use peakElapsedSeconds, NOT SP start
    peak_sec    = ha.get("peakElapsedSeconds")
    peak_h      = peak_sec / 3600 if peak_sec else None

    ep1_to_peak_h = (peak_h - ep1_start_h) if (peak_h and ep1_start_h) else None

    # target
    started_at     = pd.to_datetime(rl["startedAt"])
    target_end_str = rl.get("targetEndTime") or rl.get("alarmTime")
    target_end     = pd.to_datetime(target_end_str) if target_end_str else None
    target_h       = (target_end - started_at).total_seconds() / 3600 if target_end else None

    diff_h = (target_h - peak_h) if (target_h and peak_h) else None

    if diff_h is None:
        result = "no_peak"
    elif 0 <= diff_h <= 0.5:
        result = "success"
    elif diff_h > 0.5:
        result = "too_early"
    else:
        result = "late"

    return {
        "id":              rl["id"],
        "startedAt":       rl["startedAt"],
        "status":          rl["status"],
        "starterName":     mi.get("starterName"),
        "starterAmount":   mi.get("starterAmount"),
        "flourAmount":     mi.get("flourAmount"),
        "waterAmount":     mi.get("waterAmount"),
        "cp_dur_h":        cp_dur_h,
        "ep1_start_h":     ep1_start_h,
        "ep1_to_peak_h":   ep1_to_peak_h,
        "peak_h":          peak_h,
        "sp_start_h":      steps.get(3, {}).get("start_h"),
        "target_h":        target_h,
        "diff_h":          diff_h,
        "result":          result,
        "cp_avg_temp":     steps.get(0, {}).get("avg_temp"),
        "ep1_avg_temp":    steps.get(1, {}).get("avg_temp"),
        "measurements":    meas.to_dict(orient="records"),
    }
```

---

## 8. Requirements

```
streamlit>=1.35
pandas>=2.0
matplotlib>=3.7
numpy>=1.24
```

---

## 9. Out of Scope

- No ML models or predictions
- No user authentication
- No cloud deployment (local only)
- No database (flat JSON file)
- No real-time device connection

---

## 10. Success Criteria

The app is done when:
1. Can upload a JSON and see it appear in the table
2. Success rate is calculated correctly using `peakElapsedSeconds` (not SP start)
3. mftime tracker shows EP1→peak trend across sessions
4. Session detail shows height + temperature with correct peak marker
