import json
import streamlit as st
import pandas as pd

from utils.store import load_sessions, load_metadata

st.set_page_config(page_title="History", layout="wide")
st.title("Session History")

RESULT_EMOJI = {
    "success": "✅",
    "too_early": "⚠️",
    "late": "❌",
    "no_peak": "—",
}

# ── How to add sessions ───────────────────────────────────────
with st.expander("📂 How to add sessions"):
    st.markdown("""
**Add a session log:**
1. Download the JSON file from your SourFriend device
2. Go to the `data/` folder in the GitHub repository
3. Click **Add file → Upload files**, drag your JSON, commit

The app redeploys automatically in ~30 seconds.

---

**Add device name or feeding date** — edit `metadata.json` in GitHub:
```json
{
  "your-session-id": {
    "device_name": "SourFriend-A1",
    "last_feeding_date": "2026-05-13"
  }
}
```

**Delete a session** — delete the JSON file from the `data/` folder on GitHub.
""")

# ── Load ──────────────────────────────────────────────────────
sessions = load_sessions()

if st.button("🔄 Refresh"):
    st.cache_data.clear()
    st.rerun()

if not sessions:
    st.info("No sessions yet. Add JSON files to the `data/` folder on GitHub.")
    st.stop()

# ── Missing metadata warning ──────────────────────────────────
metadata = load_metadata()
missing = [s for s in sessions if s["id"] not in metadata]
if missing:
    with st.expander(f"⚠️ {len(missing)} session(s) have no metadata (device / feeding date)"):
        snippet = {
            s["id"]: {"device_name": "", "last_feeding_date": ""}
            for s in missing
        }
        st.markdown("Copy this into `metadata.json` on GitHub and fill in the values:")
        st.code(json.dumps(snippet, indent=2), language="json")

# ── Table ─────────────────────────────────────────────────────
st.divider()

rows = []
for s in sorted(sessions, key=lambda x: x["startedAt"], reverse=True):
    started = pd.to_datetime(s["startedAt"]).strftime("%Y-%m-%d %H:%M")
    flour = s.get("flourAmount")
    starter = s.get("starterAmount")
    ratio = f"{flour/starter:.1f}" if flour and starter else "—"
    interval = s.get("feeding_interval_days")
    rows.append({
        "Date": started,
        "Device": s.get("device_name") or "—",
        "Fed (days ago)": str(interval) if interval is not None else "—",
        "Starter": s.get("starterName") or "—",
        "Ratio": ratio,
        "CP dur (h)": f"{s['cp_dur_h']:.2f}" if s.get("cp_dur_h") else "—",
        "EP1→peak (h)": f"{s['ep1_to_peak_h']:.2f}" if s.get("ep1_to_peak_h") else "—",
        "Peak at (h)": f"{s['peak_h']:.2f}" if s.get("peak_h") else "—",
        "Target at (h)": f"{s['target_h']:.2f}" if s.get("target_h") else "—",
        "Δ (h)": f"{s['diff_h']:+.2f}" if s.get("diff_h") is not None else "—",
        "Result": RESULT_EMOJI.get(s["result"], "—"),
    })

display_df = pd.DataFrame(rows)
st.dataframe(display_df, use_container_width=True, hide_index=True)

csv = display_df.to_csv(index=False)
st.download_button("Download CSV", csv, "sessions.csv", "text/csv")
