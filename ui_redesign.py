"""Redesigned F1 Race Strategy Simulator UI — dark F1-inspired theme, German UI."""

import time

import pandas as pd
import streamlit as st

from car import Car
from opponents import advance_opponents, build_opponent_table, create_opponents
from racelogic import (
    apply_safety_event_effect,
    get_safety_event_lap_multiplier,
    get_safety_event_pitstop_multiplier,
    resolve_safety_event,
    roll_safety_event,
)
from strategy_optimizer import find_optimal_pit_lap

# ─── Konstanten ───────────────────────────────────────────────────────────────

TEAM_COLORS = {
    "Ferrari":  "#DC0000",
    "Red Bull": "#1E3A6E",
    "Mercedes": "#00A19C",
    "McLaren":  "#FF8000",
    "Williams": "#005AFF",
}

TRACK_TEMP_RANGES = {
    "Belgian Grand Prix": {"min": 10, "max": 22, "default": 16},
    "British Grand Prix": {"min": 14, "max": 26, "default": 20},
    "Italian Grand Prix": {"min": 14, "max": 28, "default": 21},
}

TRACK_LAP_COUNTS = {
    "Belgian Grand Prix": 44,
    "British Grand Prix": 52,
    "Italian Grand Prix": 53,
}

TRACK_FLAGS = {
    "Belgian Grand Prix": "🇧🇪",
    "British Grand Prix": "🇬🇧",
    "Italian Grand Prix": "🇮🇹",
}

TIRE_COLORS = {"SOFT": "#FF3333", "MEDIUM": "#FFD700", "HARD": "#CCCCCC"}
TIRE_LABELS  = {"SOFT": "S",      "MEDIUM": "M",       "HARD": "H"}

TRACKS = list(TRACK_LAP_COUNTS.keys())


# ─── CSS ──────────────────────────────────────────────────────────────────────

def inject_css():
    st.markdown("""
    <style>
    /* ── Globaler dunkler Hintergrund ── */
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    section.main > div,
    .block-container {
        background-color: #0a0a0a !important;
        color: #ffffff;
    }
    [data-testid="stHeader"]   { background: transparent !important; }
    [data-testid="stToolbar"]  { display: none; }
    footer                     { display: none !important; }

    /* ── Typografie ── */
    .f1-eyebrow {
        font-size: 0.65rem;
        font-weight: 700;
        letter-spacing: 3px;
        text-transform: uppercase;
        color: #555;
        margin-bottom: 0.3rem;
    }
    .f1-heading {
        font-size: 2.8rem;
        font-weight: 900;
        text-transform: uppercase;
        line-height: 1;
        color: #ffffff;
        margin-bottom: 0.5rem;
    }
    .f1-sub {
        font-size: 0.82rem;
        color: #666;
        margin-top: 0.25rem;
    }
    .section-label {
        font-size: 0.62rem;
        font-weight: 700;
        letter-spacing: 3px;
        text-transform: uppercase;
        color: #555;
        margin-bottom: 0.6rem;
        padding-bottom: 0.35rem;
        border-bottom: 1px solid #1e1e1e;
    }

    /* ── F1-Logo-Pille ── */
    .f1-logo {
        display: inline-block;
        background: #e10600;
        color: #fff;
        font-weight: 900;
        font-size: 0.85rem;
        padding: 2px 9px 2px 8px;
        border-radius: 3px;
        letter-spacing: -0.5px;
        font-style: italic;
        margin-bottom: 0.6rem;
    }

    /* ── Karten ── */
    .f1-card {
        background: #141414;
        border: 1px solid #1e1e1e;
        border-radius: 8px;
        padding: 1.1rem 1.25rem;
        margin-bottom: 0.75rem;
    }

    /* ── Metrikkacheln ── */
    .metric-tile {
        background: #141414;
        border: 1px solid #1e1e1e;
        border-radius: 8px;
        padding: 0.9rem 1rem;
        text-align: center;
        margin-bottom: 0.75rem;
    }
    .metric-tile .mlabel {
        font-size: 0.58rem;
        letter-spacing: 3px;
        text-transform: uppercase;
        color: #555;
        margin-bottom: 0.3rem;
    }
    .metric-tile .mval {
        font-size: 2rem;
        font-weight: 900;
        color: #ffffff;
        line-height: 1.05;
    }
    .metric-tile .msub {
        font-size: 0.72rem;
        color: #555;
        margin-top: 0.15rem;
    }

    /* ── Teamkacheln ── */
    .team-tile {
        border-radius: 8px;
        height: 62px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #fff;
        font-weight: 800;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.4rem;
    }

    /* ── Reifenabzeichen ── */
    .tire-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        border-radius: 50%;
        border: 2px solid;
        font-weight: 900;
        font-size: 0.72rem;
        vertical-align: middle;
    }

    /* ── Safety-Car-Banner ── */
    .banner-sc {
        background: linear-gradient(90deg, #c45000, #ff7800);
        color: #fff;
        text-align: center;
        padding: 0.55rem 1rem;
        border-radius: 6px;
        font-weight: 800;
        font-size: 0.85rem;
        letter-spacing: 2px;
        margin-bottom: 0.75rem;
    }
    .banner-vsc {
        background: linear-gradient(90deg, #b89000, #ffd700);
        color: #000;
        text-align: center;
        padding: 0.55rem 1rem;
        border-radius: 6px;
        font-weight: 800;
        font-size: 0.85rem;
        letter-spacing: 2px;
        margin-bottom: 0.75rem;
    }
    .banner-end {
        background: #141414;
        border: 2px solid #e10600;
        color: #fff;
        text-align: center;
        padding: 1.5rem;
        border-radius: 8px;
        font-weight: 800;
        font-size: 1.1rem;
        letter-spacing: 2px;
        margin-bottom: 1rem;
    }
    .banner-dsq {
        background: #1a0000;
        border: 2px solid #880000;
        color: #ff4444;
        text-align: center;
        padding: 1.5rem;
        border-radius: 8px;
        font-weight: 800;
        font-size: 1.1rem;
        letter-spacing: 2px;
        margin-bottom: 1rem;
    }

    /* ── Primärer Button → F1-Rot ── */
    div[data-testid="stButton"] > button[kind="primary"] {
        background: #e10600 !important;
        color: #fff !important;
        border: none !important;
        font-weight: 700 !important;
        letter-spacing: 0.5px !important;
    }
    div[data-testid="stButton"] > button[kind="primary"]:hover {
        background: #ff1a10 !important;
    }
    div[data-testid="stButton"] > button[kind="secondary"] {
        background: #1e1e1e !important;
        color: #ccc !important;
        border: 1px solid #333 !important;
    }
    div[data-testid="stButton"] > button[kind="secondary"]:hover {
        background: #2a2a2a !important;
        color: #fff !important;
    }

    /* ── Radio + Select ── */
    [data-testid="stRadio"]     label { color: #aaa !important; font-size: 0.85rem !important; }
    [data-testid="stSelectbox"] label { color: #555 !important; font-size: 0.62rem !important;
                                        letter-spacing: 2px !important; text-transform: uppercase !important; }

    /* ── Dataframe dunkel ── */
    [data-testid="stDataFrame"] thead th {
        background: #1a1a1a !important;
        color: #555 !important;
        font-size: 0.65rem !important;
        letter-spacing: 2px !important;
        text-transform: uppercase !important;
    }
    [data-testid="stDataFrame"] tbody td {
        background: #0f0f0f !important;
        color: #ccc !important;
        font-size: 0.82rem !important;
    }

    /* ── Trennlinien ── */
    hr { border-color: #1e1e1e !important; margin: 0.75rem 0; }

    /* ── Bootstrap-Konsole ── */
    .boot-console {
        font-family: 'Courier New', monospace;
        font-size: 0.78rem;
        color: #00cc66;
        background: #050f05;
        border: 1px solid #0d3b0d;
        border-radius: 6px;
        padding: 1rem 1.2rem;
        min-height: 120px;
    }

    /* ── Expander ── */
    [data-testid="stExpander"] {
        background: #141414 !important;
        border: 1px solid #1e1e1e !important;
        border-radius: 8px !important;
    }
    [data-testid="stExpander"] summary {
        color: #aaa !important;
        font-size: 0.85rem !important;
    }
    </style>
    """, unsafe_allow_html=True)


# ─── Bootstrap-Hilfsfunktionen ────────────────────────────────────────────────

def make_bootstrap_placeholder():
    """Zeigt F1-Startbildschirm während des Bootstrappings."""
    ph = st.empty()
    ph.markdown("""
    <div style="min-height:75vh;display:flex;flex-direction:column;
                align-items:center;justify-content:center;text-align:center;
                background:#0a0a0a;">
        <div class="f1-logo" style="font-size:1.4rem;padding:4px 14px;">F1</div>
        <div class="f1-heading" style="font-size:3.5rem;margin:0.6rem 0 0.4rem;">
            RACE STRATEGY<br>SIMULATOR
        </div>
        <div class="f1-sub" style="font-size:0.9rem;">
            Daten und ML-Modelle werden vorbereitet — beim ersten Start kann dies einige Minuten dauern…
        </div>
        <div class="boot-console" style="margin-top:1.5rem;width:min(520px,90vw);text-align:left;">
            &gt; Datenbank wird geprüft…<br>
            &gt; FastF1-Sessiondaten werden geladen…<br>
            &gt; Random-Forest-Modelle werden pro Strecke trainiert…
        </div>
    </div>
    """, unsafe_allow_html=True)
    return ph


def show_bootstrap_result(bootstrap_status):
    """Zeigt kurze Statuskarte nach abgeschlossenem Bootstrap."""
    import os
    from train_models import TRACK_LIST

    lines = []
    if bootstrap_status.get("created_db"):
        lines.append("✓ Datenbank erstellt")
    elif os.path.exists("f1_project.db"):
        lines.append("✓ Datenbank bereit")

    if bootstrap_status.get("trained_models"):
        lines.append("✓ ML-Modelle trainiert")
    else:
        all_ok = all(
            os.path.exists(f"models/dry/rf_{t.replace(' ', '_')}.pkl")
            for t in TRACK_LIST
        )
        if all_ok:
            lines.append("✓ ML-Modelle bereit")

    if lines:
        body = "  ·  ".join(lines)
        st.markdown(f"""
        <div class="f1-card" style="text-align:center;padding:0.6rem 1.2rem;">
            <span style="color:#00cc66;font-size:0.8rem;letter-spacing:1px;">{body}</span>
        </div>
        """, unsafe_allow_html=True)


# ─── Seite 1 — Einstellungen ──────────────────────────────────────────────────

def _team_selector():
    """Teamauswahl-Kacheln. Gibt ausgewählten Teamnamen zurück."""
    if "team_player" not in st.session_state:
        st.session_state.team_player = "Ferrari"

    st.markdown('<div class="section-label">TEAM WÄHLEN</div>', unsafe_allow_html=True)

    cols = st.columns(5)
    for i, (team, color) in enumerate(TEAM_COLORS.items()):
        selected = st.session_state.team_player == team
        border = "2px solid #ffffff" if selected else "2px solid transparent"
        shadow = "box-shadow:0 0 14px rgba(255,255,255,0.12);" if selected else ""
        with cols[i]:
            st.markdown(
                f'<div class="team-tile" style="background:{color};border:{border};{shadow}">'
                f"{team}</div>",
                unsafe_allow_html=True,
            )
            if selected:
                st.button("✓ Ausgewählt", key=f"tbtn_{team}", disabled=True,
                          width='stretch')
            else:
                if st.button("Wählen", key=f"tbtn_{team}", width='stretch'):
                    st.session_state.team_player = team
                    st.rerun()

    return st.session_state.team_player


def render_setup_page():
    """Rennkonfigurationsseite."""
    # Kopfzeile
    st.markdown('<div class="f1-logo">F1</div>', unsafe_allow_html=True)
    st.markdown('<div class="f1-eyebrow">Race Strategy Simulator</div>', unsafe_allow_html=True)
    st.markdown('<div class="f1-heading">Neue Simulation</div>', unsafe_allow_html=True)
    st.markdown('<div class="f1-sub">Triff die richtigen Entscheidungen. Schlage die Konkurrenz. Führe dein Team zum Sieg.</div>', unsafe_allow_html=True)
    st.markdown("---")

    # Teamauswahl
    team = _team_selector()
    st.markdown("---")

    # Rennparameter
    st.markdown('<div class="section-label">RENNPARAMETER</div>', unsafe_allow_html=True)

    col_track, col_start, col_target, col_temp = st.columns([2, 1, 1, 1])

    with col_track:
        st.markdown('<div class="section-label">STRECKE WÄHLEN</div>', unsafe_allow_html=True)
        # Widget-Key "track_select" ist bewusst ANDERS als der persistierte Key "track",
        # damit kein Konflikt zwischen Widget-Verwaltung und manuellem Setzen entsteht.
        track = st.selectbox(
            "Strecke",
            TRACKS,
            format_func=lambda t: f"{TRACK_FLAGS.get(t, '')} {t}",
            label_visibility="collapsed",
            key="track_select",
        )
        laps = TRACK_LAP_COUNTS.get(track, 52)
        st.markdown(f'<div class="f1-sub">{laps} Runden</div>', unsafe_allow_html=True)

    with col_start:
        st.markdown('<div class="section-label">STARTREIFEN</div>', unsafe_allow_html=True)
        tire_start = st.radio(
            "Startreifen", ["SOFT", "MEDIUM", "HARD"],
            label_visibility="collapsed", key="start_tire",
        )

    with col_target:
        st.markdown('<div class="section-label">ZIELREIFEN FÜR PITSTOP</div>', unsafe_allow_html=True)
        target_tire = st.radio(
            "Zielreifen", ["SOFT", "MEDIUM", "HARD"],
            index=2, label_visibility="collapsed", key="target_tire",
        )

    with col_temp:
        st.markdown('<div class="section-label">LUFTTEMPERATUR</div>', unsafe_allow_html=True)
        t_range = TRACK_TEMP_RANGES.get(track, {"min": 15, "max": 30, "default": 22})
        air_temp = st.slider(
            "Temperatur", t_range["min"], t_range["max"], t_range["default"],
            step=1, format="%d°C", label_visibility="collapsed",
            key="air_temp_select",
        )
        st.markdown(
            f'<div class="f1-sub">{air_temp}°C &nbsp;·&nbsp; {t_range["min"]}–{t_range["max"]}°C</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # KI-Stratege Briefing
    st.markdown('<div class="section-label">KI-STRATEGE BRIEFING</div>', unsafe_allow_html=True)

    with st.expander("🏎  KI nach optimalem Boxenstoppfenster fragen", expanded=True):
        st.markdown(
            '<div class="f1-sub">Lass die KI Rundenzeiten mit verschiedenen Reifenmischungen simulieren, um deine mathematisch schnellste Strategie zu finden.</div>',
            unsafe_allow_html=True,
        )
        if st.button("Optimale Boxenstopprunde berechnen", width='stretch'):
            with st.spinner("Strategie wird simuliert…"):
                try:
                    best_lap = find_optimal_pit_lap(
                        track_name=track,
                        total_laps=laps,
                        team=team,
                        start_compound=tire_start,
                        next_compound=target_tire,
                        air_temp=air_temp,
                    )
                    st.success(
                        f"**Optimale Strategie:** Boxenstopp in Runde **{best_lap}** — "
                        f"{tire_start} → {target_tire}"
                    )
                    if team in ("Red Bull", "Mercedes"):
                        st.info(
                            f"{team} zeigt historisch starkes Reifenmanagement. Die KI empfiehlt, "
                            f"bis Runde {best_lap} zu fahren, da das Auto das Tempo auch auf "
                            f"verschlissenen Reifen hält."
                        )
                    elif team in ("Ferrari", "McLaren"):
                        st.info(
                            f"{team} erreicht früh seinen Höchstleistung, fällt aber schneller ab. "
                            f"Ein Boxenstopp in Runde {best_lap} vermeidet die Klippe, "
                            f"wo die {tire_start}-Reifen stark nachlassen."
                        )
                    else:
                        st.info(
                            f"Für {team} minimiert Runde {best_lap} die Zeit auf verschlissenen "
                            f"Reifen und schützt gleichzeitig die Streckenposition."
                        )
                except FileNotFoundError:
                    st.error("Modell nicht gefunden — App neu starten, um das Bootstrap abzuschließen.")
                except Exception as exc:
                    st.error(f"Simulationsfehler: {exc}")

    st.markdown("---")

    if st.button("🏁  SIMULATION STARTEN", type="primary", width='stretch'):
        # Werte explizit in einfache Session-State-Keys schreiben (nicht widget-verwaltet),
        # damit sie auf der Rennseite verfügbar bleiben wenn die Widgets nicht mehr rendern.
        st.session_state.track = track
        st.session_state.air_temp = air_temp
        st.session_state.race_started = True
        st.session_state.player = Car(team, track, tire_start)
        st.session_state.total_laps = laps
        st.session_state.opponents = create_opponents(team, track, laps)
        st.rerun()


# ─── Seite 2 — Rennen ─────────────────────────────────────────────────────────

def _tire_html(compound, age=None):
    """Gibt ein inline-HTML-Reifenabzeichen zurück."""
    c   = TIRE_COLORS.get(compound, "#fff")
    lbl = TIRE_LABELS.get(compound, compound[0])
    age_str = f"&nbsp;·&nbsp;{age} Runden" if age is not None else ""
    return (
        f'<span class="tire-badge" style="color:{c};border-color:{c};">{lbl}</span>'
        f'&nbsp;<span style="color:{c};font-weight:700;">{compound}</span>'
        f'<span style="color:#555;font-size:0.78rem;">{age_str}</span>'
    )


def _do_continue(player, total_laps):
    roll_safety_event()
    apply_safety_event_effect(player)
    player.advance_lap(st.session_state.safety_event_status)
    if hasattr(st.session_state, "opponents"):
        advance_opponents(
            st.session_state.opponents, total_laps,
            st.session_state.safety_event_status,
            get_safety_event_lap_multiplier(),
            get_safety_event_pitstop_multiplier(),
        )
    resolve_safety_event()
    st.session_state.lap_start_time  = time.time()
    st.session_state.lap_started_for = player.lap
    st.rerun(scope="app")


def _do_pit(player, total_laps):
    new_tire = st.session_state.pitstop_tire_choice
    roll_safety_event()
    apply_safety_event_effect(player)
    player.box(
        new_tire,
        st.session_state.safety_event_status,
        pitstop_multiplier=get_safety_event_pitstop_multiplier(),
    )
    if hasattr(st.session_state, "opponents"):
        advance_opponents(
            st.session_state.opponents, total_laps,
            st.session_state.safety_event_status,
            get_safety_event_lap_multiplier(),
            get_safety_event_pitstop_multiplier(),
        )
    resolve_safety_event()
    st.session_state.lap_start_time  = time.time()
    st.session_state.lap_started_for = player.lap
    st.rerun(scope="app")


def _race_summary(player, total_laps):
    """Ergebnisanzeige nach Rennende."""
    history = player.race_history
    total_s = player.total_time
    m   = int(total_s // 60)
    s   = total_s % 60
    avg = total_s / max(1, len(history))
    best = min(r["Rundenzeit"] for r in history) if history else 0.0

    col_stats, col_chart = st.columns([1, 2])
    with col_stats:
        st.markdown(f"""
        <div class="f1-card">
            <div class="section-label">RENNERGEBNIS</div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.6rem;margin-top:0.6rem;">
                <div class="metric-tile">
                    <div class="mlabel">GESAMTZEIT</div>
                    <div class="mval" style="font-size:1.25rem;">{m}:{s:05.2f}</div>
                </div>
                <div class="metric-tile">
                    <div class="mlabel">Ø RUNDENZEIT</div>
                    <div class="mval" style="font-size:1.25rem;">{avg:.2f}s</div>
                </div>
                <div class="metric-tile">
                    <div class="mlabel">BOXENSTOPPS</div>
                    <div class="mval" style="font-size:1.25rem;">{player.pitstop_counter}</div>
                </div>
                <div class="metric-tile">
                    <div class="mlabel">BESTE RUNDE</div>
                    <div class="mval" style="font-size:1.25rem;">{best:.2f}s</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_chart:
        if history:
            df = pd.DataFrame(history)
            st.markdown('<div class="section-label">RUNDENZEITENENTWICKLUNG</div>', unsafe_allow_html=True)
            st.line_chart(df.set_index("Runde")["Rundenzeit"], color="#e10600", height=220)

    if history:
        st.markdown('<div class="section-label" style="margin-top:0.5rem;">VOLLSTÄNDIGER RUNDENVERLAUF</div>', unsafe_allow_html=True)
        hist_df = pd.DataFrame(
            history, columns=["Runde", "Rundenzeit", "Reifen", "Reifenalter", "Kommentar"]
        )
        st.dataframe(hist_df, width='stretch', hide_index=True)

    opponents = st.session_state.get("opponents")
    if opponents:
        st.markdown('<div class="section-label" style="margin-top:0.5rem;">ENDFELD</div>', unsafe_allow_html=True)
        st.dataframe(
            pd.DataFrame(build_opponent_table(opponents, total_laps)),
            width='stretch', hide_index=True,
        )


@st.fragment(run_every=1)
def _race_fragment():
    player     = st.session_state.player
    total_laps = st.session_state.total_laps
    event      = st.session_state.get("safety_event_status")
    # "track" und "air_temp" wurden beim Rennstart explizit als einfache Keys gespeichert.
    track      = st.session_state.track
    air_temp   = st.session_state.air_temp

    # Safety-Car-Banner
    if event == "SAFETYCAR":
        st.markdown('<div class="banner-sc">🚨&nbsp; SAFETY CAR EINGESETZT</div>', unsafe_allow_html=True)
    elif event == "VSC":
        st.markdown('<div class="banner-vsc">⚠&nbsp; VIRTUELLES SAFETY CAR</div>', unsafe_allow_html=True)

    # Rennende
    if player.lap == total_laps + 1:
        if player.pitstop_counter == 0:
            st.markdown(
                '<div class="banner-dsq">❌&nbsp; DISQUALIFIZIERT — Kein Boxenstopp absolviert</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="banner-end">🏁&nbsp; RENNEN BEENDET — Glückwunsch!</div>',
                unsafe_allow_html=True,
            )
        _race_summary(player, total_laps)
        return

    # Rundenzeit für diese Runde berechnen
    player.predict_lap_time(air_temp=air_temp)

    # Rundentimer
    current_lap = player.lap
    if st.session_state.get("lap_started_for") != current_lap:
        st.session_state.lap_start_time  = time.time()
        st.session_state.lap_started_for = current_lap

    elapsed   = time.time() - st.session_state.lap_start_time
    timeout   = 5.0
    remaining = max(0.0, timeout - elapsed)

    # Auto-Weiterschaltung
    if remaining <= 0:
        roll_safety_event()
        apply_safety_event_effect(player)
        player.advance_lap(st.session_state.safety_event_status)
        if hasattr(st.session_state, "opponents"):
            advance_opponents(
                st.session_state.opponents, total_laps,
                st.session_state.safety_event_status,
                get_safety_event_lap_multiplier(),
                get_safety_event_pitstop_multiplier(),
            )
        resolve_safety_event()
        st.session_state.lap_start_time  = time.time()
        st.session_state.lap_started_for = player.lap
        st.rerun()

    # ── Zweispaltiges Layout ──────────────────────────────────────────────
    left, right = st.columns([1, 2], gap="medium")

    # ── LINKS: Statuskacheln + Steuerung ─────────────────────────────────
    with left:
        st.markdown(f"""
        <div class="metric-tile">
            <div class="mlabel">RUNDE</div>
            <div class="mval">{player.lap}
                <span style="font-size:1rem;color:#444;">/ {total_laps}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="f1-card">
            <div class="section-label">AKTUELLE REIFEN</div>
            <div style="margin-top:0.4rem;">{_tire_html(player.tire, player.tire_age)}</div>
        </div>
        """, unsafe_allow_html=True)

        c_pit, c_temp = st.columns(2)
        with c_pit:
            st.markdown(f"""
            <div class="metric-tile">
                <div class="mlabel">BOXENSTOPPS</div>
                <div class="mval">{player.pitstop_counter}</div>
            </div>
            """, unsafe_allow_html=True)
        with c_temp:
            st.markdown(f"""
            <div class="metric-tile">
                <div class="mlabel">LUFTTEMP.</div>
                <div class="mval">{air_temp}<span style="font-size:1rem;color:#444;">°C</span></div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<div class="section-label" style="margin-top:0.25rem;">BOXENSTRATEGIE</div>', unsafe_allow_html=True)
        st.info(f"⏱  Automatisch weiter in **{remaining:.1f}s**")

        st.radio(
            "Reifen für Boxenstopp:",
            ["SOFT", "MEDIUM", "HARD"],
            key="pitstop_tire_choice",
            horizontal=True,
        )

        btn_l, btn_r = st.columns(2)
        with btn_l:
            if st.button("▶  Weiter", key="continue_btn", width='stretch'):
                _do_continue(player, total_laps)
        with btn_r:
            if st.button("🔧  PIT NOW", key="pit_btn", type="primary", width='stretch'):
                _do_pit(player, total_laps)

    # ── RECHTS: Datenpanels ───────────────────────────────────────────────
    with right:
        if player.lap > 1:
            last = player.race_history[-1]["Rundenzeit"]
            prev = player.race_history[-2]["Rundenzeit"] if player.lap > 2 else None
            if prev is not None:
                diff = last - prev
                delta_color = "#00cc66" if diff < 0 else "#ff4444"
                delta_str   = f"{diff:+.3f}s"
            else:
                delta_color, delta_str = "#555", ""

            st.markdown(f"""
            <div class="metric-tile" style="text-align:left;padding:1rem 1.25rem;">
                <div class="mlabel">LETZTE RUNDENZEIT</div>
                <div class="mval">{last:.3f}<span style="font-size:1rem;color:#444;">s</span>
                    &nbsp;<span style="font-size:0.85rem;color:{delta_color};">{delta_str}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            history_df = pd.DataFrame(player.race_history)
            st.markdown('<div class="section-label" style="margin-top:0.25rem;">RUNDENZEITENENTWICKLUNG</div>', unsafe_allow_html=True)
            st.line_chart(
                history_df.set_index("Runde")["Rundenzeit"],
                color="#e10600",
                height=180,
            )
        else:
            st.markdown(
                '<div class="f1-card"><div class="f1-sub">Der Rundenverlauf erscheint nach deiner ersten Runde.</div></div>',
                unsafe_allow_html=True,
            )

        # Live-KI-Stratege
        st.markdown('<div class="section-label">LIVE KI-STRATEGE</div>', unsafe_allow_html=True)
        advisor_col, result_col = st.columns([1, 2])
        with advisor_col:
            live_target = st.selectbox(
                "Strategie auswerten für:",
                ["SOFT", "MEDIUM", "HARD"],
                key="live_target_tire",
            )
        with result_col:
            try:
                best = find_optimal_pit_lap(
                    track_name=track,
                    total_laps=total_laps,
                    team=player.team,
                    start_compound=player.tire,
                    next_compound=live_target,
                    air_temp=air_temp,
                )
                st.markdown("<br>", unsafe_allow_html=True)
                st.success(f"Boxenstopp in Runde **{best}** → {live_target}")
            except Exception as _e:
                st.markdown("<br>", unsafe_allow_html=True)
                st.warning(f"KI-Stratege Fehler: {_e}")

    # ── Rundenverlauf ──────────────────────────────────────────────────────
    if player.lap > 1:
        st.markdown('<div class="section-label" style="margin-top:0.5rem;">RUNDENVERLAUF</div>', unsafe_allow_html=True)
        hist = pd.DataFrame(
            player.race_history,
            columns=["Runde", "Rundenzeit", "Reifen", "Reifenalter", "Kommentar"],
        )
        st.dataframe(hist, width='stretch', hide_index=True)

    # ── Gegner ────────────────────────────────────────────────────────────
    opponents = st.session_state.get("opponents")
    if opponents:
        st.markdown('<div class="section-label" style="margin-top:0.5rem;">GEGNER</div>', unsafe_allow_html=True)
        opp_df = pd.DataFrame(build_opponent_table(opponents, total_laps))
        st.dataframe(opp_df, width='stretch', hide_index=True)


def render_race_page():
    """Rennseite: Kopfzeile + Fragment."""
    hdr_l, hdr_r = st.columns([4, 1])
    with hdr_l:
        st.markdown('<div class="f1-logo">F1</div>', unsafe_allow_html=True)
        track  = st.session_state.get("track", "")
        team   = st.session_state.player.team if "player" in st.session_state else ""
        color  = TEAM_COLORS.get(team, "#e10600")
        flag   = TRACK_FLAGS.get(track, "")
        st.markdown(
            f'<div class="f1-eyebrow">Rennen läuft</div>'
            f'<div style="font-size:1.35rem;font-weight:900;color:#fff;margin:0.1rem 0;">'
            f'{flag}&nbsp;{track}'
            f'&nbsp;<span style="background:{color};padding:2px 10px;border-radius:4px;'
            f'font-size:0.8rem;vertical-align:middle;">{team}</span>'
            f"</div>",
            unsafe_allow_html=True,
        )
    with hdr_r:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("← Menü", key="back_btn"):
            st.session_state.race_started = False
            if "player" in st.session_state:
                del st.session_state["player"]
            st.rerun()

    st.markdown("---")

    if "player" in st.session_state:
        _race_fragment()
    else:
        st.error("Keine Renndaten gefunden. Bitte zum Menü zurückkehren und eine neue Simulation starten.")


# ─── App-Router ───────────────────────────────────────────────────────────────

def render_app():
    """Hauptfunktion — wird von app.py aufgerufen."""
    if st.session_state.get("race_started"):
        render_race_page()
    else:
        render_setup_page()
