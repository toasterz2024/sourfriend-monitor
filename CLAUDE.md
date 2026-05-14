# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**SourFriend Delayed Mode Monitor** — a local Streamlit app for analyzing sourdough fermentation session logs exported from a SourFriend device. Spec: [PRD_sourfriend_monitor.md](PRD_sourfriend_monitor.md).

Stack: Python, Streamlit, Pandas, Matplotlib.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

## Architecture

```
sourfriend_monitor/
├── app.py                  # Streamlit entry point + navigation
├── pages/
│   ├── 1_upload.py         # Upload JSON files, sessions history table
│   ├── 2_success_rate.py   # Success rate dashboard + charts
│   ├── 3_mftime_tracker.py # mftime convergence visualization
│   └── 4_session_detail.py # Per-session height + temperature charts
├── utils/
│   ├── parser.py           # JSON → session dict (see parse_session below)
│   ├── store.py            # load/save sessions_store.json
│   └── charts.py           # reusable Matplotlib chart functions
└── sessions_store.json     # flat-file persistence (one dict per session)
```

All session data lives in `sessions_store.json`. Deduplication is by `routineLog.id`. No database, no auth, no cloud.

## Domain Logic

### Step indices in measurements
| stepIndex | Phase |
|-----------|-------|
| 0 | CP (Cold Phase) |
| 1 | EP1 (warm-up) |
| 2 | EP2 |
| 3 | SP (Shaping) |
| 4 | DP (Dough Proof) |

CP duration = EP1 start time (first measurement with `stepIndex == 1`).

### Peak detection
Always use `heightAnalysis.peakElapsedSeconds` — **not** SP start time. Missing `peakElapsedSeconds` means `result = "no_peak"`.

### Success window (strict)
```
diff_h = target_h - peak_h
```
- `0 ≤ diff_h ≤ 0.5` → ✅ success
- `diff_h > 0.5`      → ⚠ too early
- `diff_h < 0`        → ❌ late

### mftime logic
The firmware sets `mftime = EP1→peak duration from the previous session` (default 7h on first run). The tracker page plots actual EP1→peak per session against the mftime the device used for the **next** session (i.e., the previous session's EP1→peak).

### Target end time
Prefer `routineLog.targetEndTime`; fall back to `routineLog.alarmTime`.

## parse_session output contract

The dict returned by `utils/parser.py:parse_session()` is the canonical session record stored in `sessions_store.json`:

```python
{
    "id", "startedAt", "status",
    "starterName", "starterAmount", "flourAmount", "waterAmount",
    "cp_dur_h",       # hours in cold phase (= ep1_start_h)
    "ep1_start_h",    # elapsed hours when EP1 began
    "ep1_to_peak_h",  # hours from EP1 start to real peak
    "peak_h",         # elapsed hours of real peak
    "sp_start_h",     # elapsed hours when SP began
    "target_h",       # elapsed hours of targetEndTime
    "diff_h",         # target_h - peak_h
    "result",         # "success" | "too_early" | "late" | "no_peak"
    "cp_avg_temp",    # mean containerTemp during CP
    "ep1_avg_temp",   # mean containerTemp during EP1
    "measurements",   # list of cleaned measurement dicts (outliers removed)
}
```

Measurements are filtered (`isOutlier == False`), sorted by `elapsedSeconds`, and stored as a list of dicts (not a DataFrame).
