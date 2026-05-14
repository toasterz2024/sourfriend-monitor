import json
import os
import pandas as pd
import streamlit as st

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
METADATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "metadata.json")


def load_metadata() -> dict:
    if not os.path.exists(METADATA_PATH):
        return {}
    try:
        with open(METADATA_PATH) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        st.error(f"metadata.json is invalid JSON: {e}. Fix it on GitHub and redeploy.")
        return {}


@st.cache_data
def load_sessions() -> list[dict]:
    from utils.parser import parse_session

    if not os.path.isdir(DATA_DIR):
        return []

    metadata = load_metadata()
    sessions = []

    for fname in sorted(os.listdir(DATA_DIR)):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(DATA_DIR, fname)
        try:
            with open(path) as f:
                raw = json.load(f)
            session = parse_session(raw)

            meta = metadata.get(session["id"], {})
            session["device_name"] = meta.get("device_name")
            session["last_feeding_date"] = meta.get("last_feeding_date")

            if meta.get("last_feeding_date"):
                session_date = pd.to_datetime(session["startedAt"]).date()
                last_feeding = pd.to_datetime(meta["last_feeding_date"]).date()
                session["feeding_interval_days"] = (session_date - last_feeding).days
            else:
                session["feeding_interval_days"] = None

            sessions.append(session)
        except Exception:
            pass

    return sorted(sessions, key=lambda s: s["startedAt"])
