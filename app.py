"""Einstiegspunkt der Streamlit-App: Bootstrap der ML-Assets und Start der UI."""
import logging

import streamlit as st

from train_models import ensure_ml_assets

_FASTF1_LOGGER_NAMES = (
    'fastf1', 'fastf1.fastf1', 'fastf1.fastf1.core', 'fastf1.fastf1.req',
    'fastf1.fastf1.api', 'fastf1.fastf1.utils', 'fastf1.core',
    'fastf1.req', 'fastf1.api', 'fastf1.utils',
)

# Muss der allererste Streamlit-Aufruf sein.
st.set_page_config(
    layout="wide",
    page_title="F1 Race Strategy Simulator",
    page_icon="🏎️",
)

# UI erst nach set_page_config importieren, damit kein Streamlit-Aufruf beim Import ausgeführt wird.
from ui_redesign import inject_css, make_bootstrap_placeholder, render_app, show_bootstrap_result

inject_css()

if 'race_started' not in st.session_state:
    st.session_state.race_started = False

# ── Bootstrap (einmalig beim ersten Start) ───────────────────────────────────
if 'ml_bootstrap_done' not in st.session_state:
    for name in _FASTF1_LOGGER_NAMES:
        logging.getLogger(name).setLevel(logging.WARNING)

    placeholder = make_bootstrap_placeholder()

    def _progress_cb(msg: str):
        try:
            if msg == '__FASTF1_RATE_LIMIT_RECOVERED__':
                st.session_state.ml_bootstrap_rate_limit_context = None
                st.session_state.ml_bootstrap_rate_limit_retry = None
            elif msg.startswith('FastF1 API-Rate-Limit erreicht beim '):
                st.session_state.ml_bootstrap_rate_limit_context = msg
            elif msg.startswith('Wartezeit bis zum nächsten Retry: '):
                st.session_state.ml_bootstrap_rate_limit_retry = msg
        except Exception:
            pass

    with st.spinner('ML-Modelle werden vorbereitet – nur beim ersten Start…'):
        try:
            st.session_state.ml_bootstrap_status = ensure_ml_assets(progress_callback=_progress_cb)
        except TypeError as exc:
            if 'progress_callback' not in str(exc):
                raise
            st.session_state.ml_bootstrap_status = ensure_ml_assets()

    st.session_state.ml_bootstrap_done = True
    placeholder.empty()

    show_bootstrap_result(st.session_state.ml_bootstrap_status)

    bootstrap_status = st.session_state.ml_bootstrap_status
    if bootstrap_status.get('rate_limited'):
        wait_s = bootstrap_status.get('rate_limit_wait', 0)
        if wait_s >= 3600:
            wait_text = f"ca. {wait_s // 3600}h"
        elif wait_s >= 60:
            wait_text = f"ca. {wait_s // 60} min"
        else:
            wait_text = f"ca. {wait_s}s"
        st.warning(
            f"FastF1 Rate-Limit während Datenabruf erreicht – {wait_text} gewartet. "
            "Bootstrap erfolgreich abgeschlossen."
        )

    # MAE-Ergebnisse nur im Terminal ausgeben, nicht in der UI.
    try:
        logging.basicConfig(level=logging.INFO)
        for name in _FASTF1_LOGGER_NAMES:
            logging.getLogger(name).setLevel(logging.WARNING)
        results = bootstrap_status.get('results')
        if results:
            for track, mae in results.items():
                logging.info(f'MAE {track}: {mae:.3f}s')
    except Exception:
        pass

# ── Haupt-App ────────────────────────────────────────────────────────────────
render_app()
