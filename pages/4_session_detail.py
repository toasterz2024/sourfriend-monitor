import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from utils.store import load_sessions
from utils.charts import height_chart, temperature_chart

st.set_page_config(page_title="Session Detail", layout="wide")
st.title("Session Detail")

sessions = load_sessions()

if not sessions:
    st.info("No sessions yet. Upload JSON files on the Upload page.")
    st.stop()

RESULT_EMOJI = {
    "success": "✅",
    "too_early": "⚠️",
    "late": "❌",
    "no_peak": "—",
}

def session_label(s):
    date = pd.to_datetime(s["startedAt"]).strftime("%Y-%m-%d %H:%M")
    device = s.get("device_name") or "—"
    name = s.get("starterName") or "—"
    result = RESULT_EMOJI.get(s["result"], "—")
    return f"{date}  |  {device}  |  {name}  |  {result}"

# device filter
devices = sorted({s.get("device_name") or "Unknown" for s in sessions})
selected_device = st.selectbox("Device", ["All"] + devices)
if selected_device != "All":
    sessions = [s for s in sessions if (s.get("device_name") or "Unknown") == selected_device]

if not sessions:
    st.info(f"No sessions for device '{selected_device}'.")
    st.stop()

options = list(reversed(sessions))
labels = [session_label(s) for s in options]
choice = st.selectbox("Select session", range(len(labels)), format_func=lambda i: labels[i])
session = options[choice]

# info cards in sidebar
with st.sidebar:
    st.subheader("Session Info")
    started = pd.to_datetime(session["startedAt"]).strftime("%Y-%m-%d %H:%M")
    st.write(f"**Started at:** {started}")

    target_h = session.get("target_h")
    if target_h:
        from datetime import timedelta
        target_dt = pd.to_datetime(session["startedAt"]) + timedelta(hours=target_h)
        st.write(f"**Target end:** {target_dt.strftime('%H:%M')}")

    cp = session.get("cp_dur_h")
    st.write(f"**CP duration:** {cp:.2f}h" if cp else "**CP duration:** —")

    cp_temp = session.get("cp_avg_temp")
    st.write(f"**CP avg temp:** {cp_temp:.1f}°C" if cp_temp else "**CP avg temp:** —")

    ep1 = session.get("ep1_to_peak_h")
    st.write(f"**EP1→peak:** {ep1:.2f}h" if ep1 else "**EP1→peak:** —")

    peak_h = session.get("peak_h")
    st.write(f"**Real peak:** {peak_h:.2f}h" if peak_h else "**Real peak:** —")

    diff = session.get("diff_h")
    st.write(f"**Δ from target:** {diff:+.2f}h" if diff is not None else "**Δ from target:** —")

    result = RESULT_EMOJI.get(session["result"], "—")
    st.write(f"**Result:** {result}")

    device = session.get("device_name")
    if device:
        st.write(f"**Device:** {device}")

    interval = session.get("feeding_interval_days")
    if interval is not None:
        st.write(f"**Fed:** {interval} day(s) before session")

# height chart
st.subheader("Height")
if session.get("measurements"):
    fig = height_chart(session)
    st.pyplot(fig)
    plt.close(fig)
else:
    st.info("No measurement data.")

# temperature chart
st.subheader("Temperature")
if session.get("measurements"):
    fig = temperature_chart(session)
    st.pyplot(fig)
    plt.close(fig)
