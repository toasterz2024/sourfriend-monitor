import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from utils.store import load_sessions
from utils.charts import mftime_evolution_chart, mftime_error_chart

st.set_page_config(page_title="mftime Tracker", layout="wide")
st.title("mftime Tracker")

all_sessions = load_sessions()

if not all_sessions:
    st.info("No sessions yet. Upload JSON files on the Upload page.")
    st.stop()

# ── Device filter ─────────────────────────────────────────────
devices = sorted({s.get("device_name") or "Unknown" for s in all_sessions})
selected_device = st.selectbox(
    "Device",
    options=["All"] + devices,
    index=0,
)

if selected_device == "All":
    sessions = all_sessions
else:
    sessions = [
        s for s in all_sessions
        if (s.get("device_name") or "Unknown") == selected_device
    ]

if not sessions:
    st.info(f"No sessions for device '{selected_device}'.")
    st.stop()

st.caption(f"{len(sessions)} session(s) shown")
st.divider()

# ── Stats ─────────────────────────────────────────────────────
ep1_vals = [s.get("ep1_to_peak_h") for s in sessions]
mftime_used = [None] + ep1_vals[:-1]

valid_ep1 = [v for v in ep1_vals if v is not None]
current_mftime = ep1_vals[-1] if ep1_vals else None

first_good = None
for i, (actual, used) in enumerate(zip(ep1_vals, mftime_used), 1):
    if actual is not None and used is not None and abs(actual - used) < 0.5:
        first_good = i
        break

pairs = [(a, u) for a, u in zip(ep1_vals, mftime_used) if a is not None and u is not None]
mean_err_all = np.mean([abs(a - u) for a, u in pairs]) if pairs else None

col1, col2, col3 = st.columns(3)
col1.metric("Current mftime", f"{current_mftime:.2f}h" if current_mftime else "—")
col2.metric("Sessions until first good prediction", str(first_good) if first_good else "Not yet")
col3.metric("Mean error (all sessions)", f"{mean_err_all:.2f}h" if mean_err_all is not None else "—")

st.divider()
st.subheader("EP1→peak per Session")
if len(valid_ep1) >= 1:
    fig = mftime_evolution_chart(sessions)
    st.pyplot(fig)
    plt.close(fig)
else:
    st.info("No EP1→peak data yet.")

st.divider()
st.subheader("mftime Prediction Error per Session")
if pairs:
    fig = mftime_error_chart(sessions)
    st.pyplot(fig)
    plt.close(fig)

    def mean_error_after(n):
        tail_pairs = [(a, u) for a, u in zip(ep1_vals[n:], mftime_used[n:])
                      if a is not None and u is not None]
        return np.mean([abs(a - u) for a, u in tail_pairs]) if tail_pairs else None

    st.subheader("Mean Error After N Sessions")
    rows = []
    for n in [1, 2, 3, 5]:
        err = mean_error_after(n)
        rows.append({"After session N": n, "Mean mftime error (h)": f"{err:.2f}" if err is not None else "—"})
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=False)
else:
    st.info("Need at least 2 sessions to compute mftime error.")
