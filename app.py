import logging

import streamlit as st

from train_models import ensure_ml_assets

_FASTF1_LOGGER_NAMES = (
    'fastf1', 'fastf1.fastf1', 'fastf1.fastf1.core', 'fastf1.fastf1.req',
    'fastf1.fastf1.api', 'fastf1.fastf1.utils', 'fastf1.core',
    'fastf1.req', 'fastf1.api', 'fastf1.utils',
)

# Must be the very first Streamlit call.
st.set_page_config(
    layout="wide",
    page_title="F1 Race Strategy Simulator",
    page_icon="🏎️",
)

# Import UI after set_page_config so no Streamlit calls run at import time.
from ui_redesign import inject_css, make_bootstrap_placeholder, render_app, show_bootstrap_result

inject_css()

if 'race_started' not in st.session_state:
    st.session_state.race_started = False

# ── Bootstrap (runs once on first launch) ────────────────────────────────────
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

    with st.spinner('Preparing ML models — first launch only…'):
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
            f"FastF1 rate limit hit during data fetch — waited {wait_text}. "
            "Bootstrapping completed successfully."
        )

    # Log MAE results to terminal only.
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

# ── Main app ─────────────────────────────────────────────────────────────────
render_app()
