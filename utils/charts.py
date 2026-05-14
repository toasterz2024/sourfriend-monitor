import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

plt.rcParams.update({
    "figure.facecolor":   "white",
    "axes.facecolor":     "#f8f8f6",
    "axes.grid":          True,
    "grid.color":         "white",
    "grid.linewidth":     1.0,
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "axes.spines.left":   False,
    "axes.spines.bottom": False,
    "font.family":        "sans-serif",
    "font.size":          11,
    "axes.titlesize":     12,
    "axes.titleweight":   "bold",
})

STEP_COLORS  = {0: "#378ADD", 1: "#EF9F27", 2: "#1D9E75", 3: "#D85A30", 4: "#7F77DD"}
STEP_LABELS  = {0: "CP (cold)", 1: "EP1 (warm-up)", 2: "EP2 (ferment)", 3: "SP (peak)", 4: "DP (cold2)"}
SESSION_COLORS = ["#D85A30", "#1D9E75", "#378ADD", "#EF9F27", "#7F77DD"]

RESULT_COLORS = {
    "success":   "#1D9E75",
    "too_early": "#EF9F27",
    "late":      "#D85A30",
    "no_peak":   "#888780",
}


def height_chart(session: dict) -> plt.Figure:
    meas = pd.DataFrame(session["measurements"])
    meas["elapsed_h"] = meas["elapsedSeconds"] / 3600
    meas["height_smooth"] = meas["height"].rolling(10, center=True, min_periods=1).median()

    fig, ax = plt.subplots(figsize=(10, 4))

    for step_idx in sorted(STEP_COLORS):
        rows = meas[meas["stepIndex"] == step_idx]
        if rows.empty:
            continue
        ax.axvspan(rows["elapsed_h"].iloc[0], rows["elapsed_h"].iloc[-1],
                   alpha=0.12, color=STEP_COLORS[step_idx])

    ax.plot(meas["elapsed_h"], meas["height_smooth"], color="#333", linewidth=1.5)

    target_h = session.get("target_h")
    if target_h:
        ax.axvline(target_h, color="black", linestyle="--", linewidth=1.5, label="Target end")
        ax.axvspan(target_h - 1.0, target_h, alpha=0.08, color="#1D9E75", label="Success window (1h)")

    peak_h = session.get("peak_h")
    if peak_h:
        peak_row = meas.iloc[(meas["elapsed_h"] - peak_h).abs().argmin()]
        ax.scatter(peak_h, peak_row["height_smooth"],
                   color="black", s=100, zorder=5, edgecolors="white", linewidths=1.5, label="Real peak")

    patches = [mpatches.Patch(color=STEP_COLORS[i], alpha=0.5, label=STEP_LABELS[i])
               for i in STEP_COLORS if not meas[meas["stepIndex"] == i].empty]
    extra = [Line2D([0], [0], color="black", ls="--", label="Target end"),
             Line2D([0], [0], marker="o", color="black", ls="", markersize=7, label="Real peak")]
    ax.legend(handles=patches + extra, loc="upper left", fontsize=8, ncol=3)

    ax.set_xlabel("Elapsed hours")
    ax.set_ylabel("Height (mm)")
    fig.tight_layout()
    return fig


def temperature_chart(session: dict) -> plt.Figure:
    meas = pd.DataFrame(session["measurements"])
    meas["elapsed_h"] = meas["elapsedSeconds"] / 3600
    t_smooth = meas["containerTemp"].rolling(10, center=True, min_periods=1).median()
    a_smooth = meas["ambientTemp"].rolling(10, center=True, min_periods=1).median()

    fig, ax = plt.subplots(figsize=(10, 2.5))
    ax.plot(meas["elapsed_h"], t_smooth, color="#D85A30", linewidth=1.5, label="Container")
    ax.plot(meas["elapsed_h"], a_smooth, color="#378ADD", linewidth=1.0, linestyle="--", label="Ambient")
    ax.axhline(27, color="#D85A30", linewidth=0.8, linestyle=":", alpha=0.7, label="27°C target")
    ax.axhline(5,  color="#378ADD", linewidth=0.8, linestyle=":", alpha=0.7, label="5°C target")

    target_h = session.get("target_h")
    if target_h:
        ax.axvline(target_h, color="black", linestyle="--", linewidth=1.5, alpha=0.7)

    ax.set_xlabel("Elapsed hours")
    ax.set_ylabel("Temp (°C)")
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    return fig


def cumulative_success_chart(sessions: list[dict]) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(8, 3))
    successes = 0
    xs, ys = [], []
    for i, s in enumerate(sessions, 1):
        if s["result"] == "success":
            successes += 1
        xs.append(i)
        ys.append(successes / i * 100)

    ax.plot(xs, ys, color="#1D9E75", linewidth=2, marker="o", markersize=4)
    ax.axhline(50, color="#888780", linewidth=0.8, linestyle="--")
    ax.set_xlabel("Session #")
    ax.set_ylabel("Cumulative success %")
    ax.set_ylim(0, 105)
    fig.tight_layout()
    return fig


def diff_histogram(sessions: list[dict]) -> plt.Figure:
    diffs = [s["diff_h"] for s in sessions if s["diff_h"] is not None]
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.hist(diffs, bins=20, color="#378ADD", edgecolor="white")
    ax.axvline(0,   color="#D85A30", linewidth=1.5, linestyle="--", label="0h (on time)")
    ax.axvline(1.0, color="#1D9E75", linewidth=1.5, linestyle="--", label="1h (window edge)")
    ax.axvspan(0, 1.0, alpha=0.08, color="#1D9E75")
    ax.set_xlabel("Δ = target − peak (hours)")
    ax.set_ylabel("Sessions")
    ax.legend(fontsize=8)
    fig.tight_layout()
    return fig


def mftime_evolution_chart(sessions: list[dict]) -> plt.Figure:
    ep1_vals = [s["ep1_to_peak_h"] for s in sessions]
    xs = list(range(1, len(sessions) + 1))
    mftime_used = [None] + ep1_vals[:-1]

    fig, ax = plt.subplots(figsize=(10, 3.5))

    valid = [(x, v) for x, v in zip(xs, ep1_vals) if v is not None]
    if valid:
        vx, vy = zip(*valid)
        ax.plot(vx, vy, color="#378ADD", marker="o", markersize=5, linewidth=1.5, label="Actual EP1→peak")

    valid_m = [(x, v) for x, v in zip(xs, mftime_used) if v is not None]
    if valid_m:
        mx, my = zip(*valid_m)
        ax.plot(mx, my, color="#EF9F27", marker="x", markersize=5, linewidth=1.5,
                linestyle="--", label="mftime used")

    all_vals = [v for v in ep1_vals if v is not None]
    if len(all_vals) >= 2:
        median = np.median(all_vals)
        ax.axhspan(median - 0.5, median + 0.5, alpha=0.1, color="#888780", label="±30min stability zone")

    ax.set_xlabel("Session #")
    ax.set_ylabel("Hours")
    ax.legend(fontsize=8)
    fig.tight_layout()
    return fig


def mftime_error_chart(sessions: list[dict]) -> plt.Figure:
    ep1_vals = [s["ep1_to_peak_h"] for s in sessions]
    mftime_used = [None] + ep1_vals[:-1]
    xs = list(range(1, len(sessions) + 1))

    errors, colors_list, bar_xs = [], [], []
    for x, actual, used in zip(xs, ep1_vals, mftime_used):
        if actual is None or used is None:
            continue
        err = abs(actual - used)
        errors.append(err)
        bar_xs.append(x)
        colors_list.append("#1D9E75" if err < 0.5 else "#EF9F27" if err < 1.0 else "#D85A30")

    fig, ax = plt.subplots(figsize=(10, 3))
    ax.bar(bar_xs, errors, color=colors_list, edgecolor="white")
    ax.axhline(0.5, color="#888780", linewidth=0.8, linestyle="--")
    patches = [
        mpatches.Patch(color="#1D9E75", label="< 0.5h"),
        mpatches.Patch(color="#EF9F27", label="0.5–1h"),
        mpatches.Patch(color="#D85A30", label="> 1h"),
    ]
    ax.legend(handles=patches, fontsize=8)
    ax.set_xlabel("Session #")
    ax.set_ylabel("|actual − mftime| (h)")
    fig.tight_layout()
    return fig
