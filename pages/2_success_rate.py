import streamlit as st
import matplotlib.pyplot as plt
import numpy as np

from utils.store import load_sessions
from utils.charts import cumulative_success_chart, diff_histogram

st.set_page_config(page_title="Success Rate Dashboard", layout="wide")
st.title("Success Rate Dashboard")

all_sessions = load_sessions()

if not all_sessions:
    st.info("No sessions yet. Upload JSON files on the Upload page.")
    st.stop()

# ── Filters ───────────────────────────────────────────────────
col_f1, col_f2 = st.columns(2)

with col_f1:
    devices = sorted({s.get("device_name") or "Unknown" for s in all_sessions})
    selected_device = st.selectbox("Device", ["All"] + devices)

with col_f2:
    def interval_bucket(days):
        if days is None:
            return "Unknown"
        if days <= 1:
            return "Daily (1 day)"
        elif days <= 2:
            return "Every 2 days"
        elif days <= 4:
            return "Every 3–4 days"
        elif days <= 7:
            return "Every 5–7 days"
        else:
            return "Weekly+"

    buckets_present = sorted({
        interval_bucket(s.get("feeding_interval_days")) for s in all_sessions
    })
    selected_feeding = st.selectbox("Feeding frequency", ["All"] + buckets_present)

# apply filters
sessions = all_sessions
if selected_device != "All":
    sessions = [s for s in sessions if (s.get("device_name") or "Unknown") == selected_device]
if selected_feeding != "All":
    sessions = [s for s in sessions if interval_bucket(s.get("feeding_interval_days")) == selected_feeding]

if not sessions:
    st.info("No sessions match the selected filters.")
    st.stop()

st.caption(f"{len(sessions)} session(s) shown")
st.divider()

# ── Top metrics ───────────────────────────────────────────────
completed = [s for s in sessions if s["result"] != "no_peak"]
total = len(completed)
successes = sum(1 for s in completed if s["result"] == "success")
success_rate = successes / total * 100 if total else 0

diffs = [s["diff_h"] for s in completed if s["diff_h"] is not None]
median_diff = float(np.median(diffs)) if diffs else None

col1, col2, col3 = st.columns(3)
col1.metric("Sessions analyzed", total)
col2.metric("Success rate", f"{success_rate:.1f}%")
col3.metric("Median Δ", f"{median_diff:+.2f}h" if median_diff is not None else "—")

st.divider()

# ── Breakdown bar chart ───────────────────────────────────────
def breakdown_pcts(sessions):
    buckets = {
        "✅ Within 1h window": 0,
        "⚠️ Too early (>1h)": 0,
        "❌ Late <30min": 0,
        "❌ Late 30min–1h": 0,
        "❌ Late 1–2h": 0,
        "❌ Late >2h": 0,
    }
    n = 0
    for s in sessions:
        d = s.get("diff_h")
        if d is None:
            continue
        n += 1
        if 0 <= d <= 1.0:
            buckets["✅ Within 1h window"] += 1
        elif d > 1.0:
            buckets["⚠️ Too early (>1h)"] += 1
        elif d > -0.5:
            buckets["❌ Late <30min"] += 1
        elif d > -1.0:
            buckets["❌ Late 30min–1h"] += 1
        elif d > -2.0:
            buckets["❌ Late 1–2h"] += 1
        else:
            buckets["❌ Late >2h"] += 1
    if n == 0:
        return buckets, 0
    return {k: v / n * 100 for k, v in buckets.items()}, n

BUCKET_COLORS = ["#1D9E75", "#EF9F27", "#D85A30", "#D85A30", "#B03A20", "#7D2510"]

buckets, n = breakdown_pcts(sessions)

st.subheader("Result Breakdown")
fig, ax = plt.subplots(figsize=(8, 2.5))
labels = list(buckets.keys())
values = list(buckets.values())
bars = ax.barh(labels, values, color=BUCKET_COLORS)
ax.set_xlim(0, 100)
ax.set_xlabel("% of sessions")
for bar, val in zip(bars, values):
    if val > 0:
        ax.text(val + 0.5, bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}%", va="center", fontsize=8)
fig.tight_layout()
st.pyplot(fig)
plt.close(fig)

st.divider()

# ── Feeding frequency breakdown ───────────────────────────────
has_feeding_data = any(s.get("feeding_interval_days") is not None for s in sessions)
if has_feeding_data and selected_feeding == "All":
    st.subheader("Success Rate by Feeding Frequency")

    bucket_names = ["Daily (1 day)", "Every 2 days", "Every 3–4 days", "Every 5–7 days", "Weekly+", "Unknown"]
    feed_labels, feed_rates, feed_counts = [], [], []
    for bname in bucket_names:
        group = [s for s in completed if interval_bucket(s.get("feeding_interval_days")) == bname]
        if not group:
            continue
        rate = sum(1 for s in group if s["result"] == "success") / len(group) * 100
        feed_labels.append(bname)
        feed_rates.append(rate)
        feed_counts.append(len(group))

    if feed_labels:
        fig, ax = plt.subplots(figsize=(8, 2.5))
        bar_colors = ["#1D9E75" if r >= 50 else "#D85A30" for r in feed_rates]
        bars = ax.barh(feed_labels, feed_rates, color=bar_colors, alpha=0.85)
        ax.set_xlim(0, 105)
        ax.axvline(50, color="#888780", linewidth=0.8, linestyle="--")
        ax.set_xlabel("Success rate %")
        for bar, rate, count in zip(bars, feed_rates, feed_counts):
            ax.text(rate + 0.5, bar.get_y() + bar.get_height() / 2,
                    f"{rate:.0f}%  (n={count})", va="center", fontsize=8)
        fig.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

st.divider()
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Cumulative Success Rate")
    if len(completed) >= 2:
        fig = cumulative_success_chart(completed)
        st.pyplot(fig)
        plt.close(fig)
    else:
        st.info("Need at least 2 sessions.")

with col_b:
    st.subheader("Δ Distribution")
    if diffs:
        fig = diff_histogram(completed)
        st.pyplot(fig)
        plt.close(fig)
    else:
        st.info("No completed sessions with peak data.")
