"""Haupt-UI des F1 Race Strategy Simulators: Einstellungsseite, Rennseite und Live-Daten."""

import time

import pandas as pd
import streamlit as st
from strategy_optimizer import find_best_overall_strategy, find_optimal_pit_lap, optimize_hybrid_strategy

from car import Car
from opponents import advance_opponents, build_opponent_table, create_opponents
from racelogic import (
    apply_safety_event_effect,
    compress_sc_field,
    get_safety_event_lap_multiplier,
    get_safety_event_pitstop_multiplier,
    resolve_safety_event,
    roll_safety_event,
)

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


# ─── Hilfsfunktionen ─────────────────────────────────────────────────────────

def _fmt_time(seconds: float) -> str:
    """Formatiert Sekunden als M:SS.mmm (z.B. 1:32.300)."""
    if not seconds or seconds <= 0:
        return "–"
    m = int(seconds // 60)
    s = seconds % 60
    return f"{m}:{s:06.3f}"


def _calculate_position(player, opponents) -> int:
    """Berechnet aktuelle Position des Spielers anhand der Gesamtzeiten."""
    ahead = sum(1 for opp in opponents if opp.car.total_time < player.total_time)
    return ahead + 1


def _build_live_standings(player, opponents) -> pd.DataFrame:
    """Erstellt Live-Rangliste mit Spieler + Gegnern, sortiert nach Gesamtzeit."""
    rows = []

    # Spieler
    p_last = player.race_history[-1]["Rundenzeit"] if player.race_history else 0.0
    rows.append({
        "team_display": f"► {player.team}",
        "tire": player.tire,
        "tire_age": player.tire_age,
        "last_lap": p_last,
        "pit_stops": player.pitstop_counter,
        "total": player.total_time,
    })

    # Gegner
    for opp in opponents:
        car = opp.car
        last = car.race_history[-1]["Rundenzeit"] if car.race_history else car.lap_time
        rows.append({
            "team_display": opp.team,
            "tire": car.tire,
            "tire_age": car.tire_age,
            "last_lap": last,
            "pit_stops": car.pitstop_counter,
            "total": car.total_time,
        })

    rows.sort(key=lambda r: r["total"])

    result = []
    prev_total = None
    for i, r in enumerate(rows):
        delta = "–" if prev_total is None else f"+{r['total'] - prev_total:.3f}s"
        prev_total = r["total"]
        result.append({
            "Rang": i + 1,
            "Team": r["team_display"],
            "Reifen": r["tire"],
            "Alter": r["tire_age"],
            "Letzte Runde": _fmt_time(r["last_lap"]),
            "Stops": r["pit_stops"],
            "Rückstand": delta,
        })

    return pd.DataFrame(result)


# ─── CSS ──────────────────────────────────────────────────────────────────────

def inject_css():
    """Injiziert globales CSS für das dunkle F1-Theme."""
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

    /* ── Reifenauswahl-Karte ── */
    .tire-card {
        border-radius: 8px;
        padding: 0.7rem 0.4rem;
        text-align: center;
        margin-bottom: 0.4rem;
        cursor: pointer;
    }
    .tire-icon {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 36px;
        height: 36px;
        border-radius: 50%;
        border: 2.5px solid;
        font-weight: 900;
        font-size: 0.85rem;
        margin: 0 auto 0.35rem;
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
    """Zeigt einen Ladebildschirm beim ersten Start und gibt den Placeholder zurück."""
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
    """Zeigt eine Statuszeile nach erfolgreichem Bootstrap (DB + Modelle)."""
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
    """Zeigt die fünf Team-Kacheln und gibt das gewählte Team zurück."""
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
                st.button("✓ Ausgewählt", key=f"tbtn_{team}", disabled=True, width='stretch')
            else:
                if st.button("Wählen", key=f"tbtn_{team}", width='stretch'):
                    st.session_state.team_player = team
                    st.rerun()

    return st.session_state.team_player


def _tire_selector(session_key: str, default: str = "SOFT", disabled_tire: str = None) -> str:
    """Visueller Reifenauswähler mit farbigen Badge-Karten."""
    current = st.session_state.get(session_key)
    if current is None or current == disabled_tire:
        available = [t for t in ["SOFT", "MEDIUM", "HARD"] if t != disabled_tire]
        st.session_state[session_key] = available[0] if available else default

    cols = st.columns(3)
    for col, tire in zip(cols, ["SOFT", "MEDIUM", "HARD"]):
        color    = TIRE_COLORS[tire]
        lbl      = TIRE_LABELS[tire]
        disabled = tire == disabled_tire
        selected = st.session_state[session_key] == tire
        border   = f"2px solid {color}" if selected else ("2px solid #1a1a1a" if disabled else "2px solid #2a2a2a")
        glow     = f"box-shadow:0 0 10px {color}44;" if selected else ""
        bg       = "#1a1a1a" if selected else ("#0d0d0d" if disabled else "#111111")
        opacity  = "opacity:0.35;" if disabled else ""

        with col:
            st.markdown(f"""
            <div class="tire-card" style="border:{border};background:{bg};{glow}{opacity}">
                <div class="tire-icon" style="color:{color};border-color:{color};">{lbl}</div>
                <div style="color:{color};font-size:0.72rem;font-weight:700;letter-spacing:1px;">
                    {tire}
                </div>
            </div>
            """, unsafe_allow_html=True)
            if disabled:
                st.button("–", key=f"{session_key}_btn_{tire}", disabled=True, width='stretch')
            elif selected:
                st.button("✓", key=f"{session_key}_btn_{tire}", disabled=True, width='stretch')
            else:
                if st.button("Wählen", key=f"{session_key}_btn_{tire}", width='stretch'):
                    st.session_state[session_key] = tire
                    st.rerun()

    return st.session_state[session_key]


def render_setup_page():
    """Rendert die Einstellungsseite (Team, Strecke, Startreifen, KI-Briefing)."""
    # Kopfzeile
    st.markdown('<div class="f1-logo">F1</div>', unsafe_allow_html=True)
    st.markdown('<div class="f1-eyebrow">Race Strategy Simulator</div>', unsafe_allow_html=True)
    st.markdown('<div class="f1-heading">Neue Simulation</div>', unsafe_allow_html=True)
    st.markdown('<div class="f1-sub">Triff die richtigen Entscheidungen. Schlage die Konkurrenz. Führe dein Team zum Sieg.</div>', unsafe_allow_html=True)
    st.markdown("---")

    team = _team_selector()
    st.markdown("---")

    st.markdown('<div class="section-label">RENNPARAMETER</div>', unsafe_allow_html=True)

    col_track, col_start, col_temp = st.columns([2, 1.5, 1])

    with col_track:
        st.markdown('<div class="section-label">STRECKE WÄHLEN</div>', unsafe_allow_html=True)
        track = st.selectbox(
            "Strecke", TRACKS,
            format_func=lambda t: f"{TRACK_FLAGS.get(t, '')} {t}",
            label_visibility="collapsed",
            key="track_select",
        )
        laps = TRACK_LAP_COUNTS.get(track, 52)
        st.markdown(f'<div class="f1-sub">{laps} Runden</div>', unsafe_allow_html=True)

    with col_start:
        st.markdown('<div class="section-label">STARTREIFEN</div>', unsafe_allow_html=True)
        tire_start = _tire_selector("start_tire_sel", default="SOFT")

    with col_temp:
        st.markdown('<div class="section-label">LUFTTEMPERATUR</div>', unsafe_allow_html=True)
        t_range = TRACK_TEMP_RANGES.get(track, {"min": 15, "max": 30, "default": 22})
        air_temp = st.slider(
            "Temperatur", t_range["min"], t_range["max"], t_range["default"],
            step=1, format="%d°C", label_visibility="collapsed",
            key="air_temp_select",
        )

    st.markdown("---")

    st.info("💡 **FIA Reglement:** Bei trockenen Bedingungen müssen während des Rennens mindestens zwei verschiedene Reifenmischungen verwendet werden.")

    # KI-Stratege Briefing
    st.markdown('<div class="section-label">KI-STRATEGE BRIEFING</div>', unsafe_allow_html=True)

    with st.expander("🏎  KI: Smarte Strategie-Vorhersage", expanded=False):
        st.markdown(
            '<div class="f1-sub">Die KI simuliert alle Reifenkombinationen und empfiehlt automatisch die schnellste Gesamtstrategie.</div>',
            unsafe_allow_html=True,
        )

        if st.button("Optimale Strategie berechnen", width='stretch'):
            with st.spinner("KI simuliert alle Rennszenarien…"):
                try:
                    result = find_best_overall_strategy(
                        track_name=track, total_laps=laps, team=team,
                        start_compound=tire_start, air_temp=air_temp,
                    )

                    def _fmt(sec):
                        m, s = divmod(sec, 60)
                        return f"{int(m)}m {s:.2f}s"

                    st.success(f"### 🏁 KI empfiehlt eine **{result['recommendation']}** Strategie!")
                    st.write(f"⏱️ **Geschätzte Gesamtzeit:** {_fmt(result['total_time'])}")

                    if result['recommendation'] == "2-Stop":
                        st.info(f"💡 Ein 2-Stopp ist voraussichtlich **{result['time_saved']:.2f} Sek. schneller** als ein 1-Stopp.")
                        st.write(f"🛞 **Start:** {tire_start}")
                        st.write(f"🛑 **Stopp 1 (Runde {result['pit1_lap']}):** Wechsel auf {result['pit1_tyre']}")
                        st.write(f"🛑 **Stopp 2 (Runde {result['pit2_lap']}):** Wechsel auf {result['pit2_tyre']} 🤖 *(KI-Wahl)*")
                    else:
                        st.info(f"💡 Ein 1-Stopp ist voraussichtlich **{result['time_saved']:.2f} Sek. schneller** als ein 2-Stopp.")
                        st.write(f"🛞 **Start:** {tire_start}")
                        st.write(f"🛑 **Stopp 1 (Runde {result['pit1_lap']}):** Wechsel auf {result['pit1_tyre']}")
                        st.write("🏁 Durchfahren bis ins Ziel.")
                except Exception as exc:
                    st.error(f"Simulationsfehler: {exc}")

    st.markdown("---")

    if st.button("🏁  SIMULATION STARTEN", type="primary", width='stretch'):
        st.session_state.track    = track
        st.session_state.air_temp = air_temp
        st.session_state.race_started = True
        st.session_state.player   = Car(team, track, tire_start)
        st.session_state.total_laps = laps
        st.session_state.opponents  = create_opponents(team, track, laps)
        # Strategie für Startreifen vorberechnen (gecacht → bei späteren Abrufen sofort verfügbar).
        try:
            st.session_state.ki_strategy = find_best_overall_strategy(track, laps, team, tire_start, air_temp)
        except Exception:
            st.session_state.ki_strategy = None
        st.rerun()

# ─── Seite 2 — Rennen ─────────────────────────────────────────────────────────


# ─── Seite 2 — Rennen ─────────────────────────────────────────────────────────

def _tire_html(compound, age=None):
    """Gibt ein HTML-Reifenabzeichen mit optionalem Alter zurück."""
    c   = TIRE_COLORS.get(compound, "#fff")
    lbl = TIRE_LABELS.get(compound, compound[0])
    age_str = f"&nbsp;·&nbsp;{age} Rdn." if age is not None else ""
    return (
        f'<span class="tire-badge" style="color:{c};border-color:{c};">{lbl}</span>'
        f'&nbsp;<span style="color:{c};font-weight:700;">{compound}</span>'
        f'<span style="color:#555;font-size:0.78rem;">{age_str}</span>'
    )



def _do_pit(player, total_laps):
    """Führt einen Boxenstopp für den Spieler durch und lässt Gegner gleichzeitig weiterfahren."""
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
        if st.session_state.safety_event_status == 'SAFETYCAR':
            compress_sc_field(player, st.session_state.opponents)
    resolve_safety_event()
    # Strategie für neuen Reifen nachladen (gecacht → sofort verfügbar).
    try:
        st.session_state.ki_strategy = find_best_overall_strategy(
            st.session_state.track, total_laps, player.team,
            new_tire, st.session_state.air_temp,
        )
    except Exception:
        st.session_state.ki_strategy = None
    st.session_state.lap_start_time  = time.time()
    st.session_state.lap_started_for = player.lap
    st.rerun(scope="app")


def _race_summary(player, total_laps, opponents):
    """Zeigt Rennergebnis, Rundenzeitendiagramm und Endrangliste nach Rennende."""
    history = player.race_history
    total_s = player.total_time
    m   = int(total_s // 60)
    s   = total_s % 60
    avg = total_s / max(1, len(history))
    best = min(r["Rundenzeit"] for r in history) if history else 0.0
    final_pos = _calculate_position(player, opponents)

    col_stats, col_chart = st.columns([1, 2])
    with col_stats:
        st.markdown(f"""
        <div class="f1-card">
            <div class="section-label">RENNERGEBNIS</div>
            <div style="margin-top:0.6rem;">
                <div class="metric-tile" style="margin-bottom:0.6rem;">
                    <div class="mlabel">ENDPLATZIERUNG</div>
                    <div class="mval" style="font-size:3rem;line-height:1;">{"DQ" if len({r["Reifen"] for r in history}) < 2 else f"P{final_pos}"}</div>
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.6rem;">
                    <div class="metric-tile">
                        <div class="mlabel">Ø RUNDENZEIT</div>
                        <div class="mval" style="font-size:1.1rem;">{_fmt_time(avg)}</div>
                    </div>
                    <div class="metric-tile">
                        <div class="mlabel">BESTE RUNDE</div>
                        <div class="mval" style="font-size:1.1rem;">{_fmt_time(best)}</div>
                    </div>
                    <div class="metric-tile" style="grid-column:1/-1;">
                        <div class="mlabel">BOXENSTOPPS</div>
                        <div class="mval" style="font-size:1.25rem;">{player.pitstop_counter}</div>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_chart:
        if history:
            import altair as alt
            df = pd.DataFrame(history)
            st.markdown('<div class="section-label">RUNDENZEITENENTWICKLUNG</div>', unsafe_allow_html=True)
            chart = (
                alt.Chart(df)
                .mark_line(color="#e10600", strokeWidth=2, point=alt.OverlayMarkDef(color="#e10600", size=40))
                .encode(
                    x=alt.X("Runde:Q", scale=alt.Scale(domain=[1, total_laps], clamp=True), title="Runde"),
                    y=alt.Y("Rundenzeit:Q", scale=alt.Scale(zero=False), title="Zeit (s)"),
                    tooltip=["Runde:Q", alt.Tooltip("Rundenzeit:Q", format=".3f", title="Zeit (s)"), "Reifen:N"],
                )
                .properties(width="container", height=220)
                .interactive(bind_y=False)
            )
            st.altair_chart(chart, width='stretch')

    # Endrangliste
    st.markdown('<div class="section-label" style="margin-top:0.5rem;">ENDRANGLISTE</div>', unsafe_allow_html=True)
    st.dataframe(_build_live_standings(player, opponents), width='stretch', hide_index=True)

    # Vollständiger Rundenverlauf (eingeklappt)
    with st.expander("Vollständiger Rundenverlauf", expanded=False):
        if history:
            hist_df = pd.DataFrame(history, columns=["Runde", "Rundenzeit", "Reifen", "Reifenalter", "Kommentar"])
            hist_df["Rundenzeit"] = hist_df["Rundenzeit"].apply(_fmt_time)
            st.dataframe(hist_df, width='stretch', hide_index=True)


@st.fragment(run_every=1)
def _race_fragment():
    """Sekündlich aktualisiertes Fragment: Rennsteuerung, Live-Daten und automatisches Weiterschalten."""
    player     = st.session_state.player
    total_laps = st.session_state.total_laps
    opponents  = st.session_state.get("opponents", [])
    event      = st.session_state.get("safety_event_status")
    track      = st.session_state.track
    air_temp   = st.session_state.air_temp

    # Safety-Car-Banner
    if event == "SAFETYCAR":
        st.markdown('<div class="banner-sc">🚨&nbsp; SAFETY CAR EINGESETZT</div>', unsafe_allow_html=True)
    elif event == "VSC":
        st.markdown('<div class="banner-vsc">⚠&nbsp; VIRTUELLES SAFETY CAR</div>', unsafe_allow_html=True)

    # Rennende
    if player.lap == total_laps + 1:
        compounds_used = {r["Reifen"] for r in player.race_history}
        if len(compounds_used) < 2:
            st.markdown('<div class="banner-dsq">❌&nbsp; DISQUALIFIZIERT — Weniger als 2 verschiedene Reifenmischungen gefahren</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="banner-end">🏁&nbsp; RENNEN BEENDET — Glückwunsch!</div>', unsafe_allow_html=True)
        _race_summary(player, total_laps, opponents)
        return

    # Rundenzeit berechnen
    player.predict_lap_time(air_temp=air_temp)

    # Rundentimer
    current_lap = player.lap
    if st.session_state.get("lap_started_for") != current_lap:
        st.session_state.lap_start_time  = time.time()
        st.session_state.lap_started_for = current_lap

    sim_speed = st.session_state.get("sim_speed", 5)
    elapsed   = time.time() - st.session_state.lap_start_time
    remaining = max(0.0, sim_speed - elapsed)

    if remaining <= 0:
        roll_safety_event()
        apply_safety_event_effect(player)
        player.advance_lap(st.session_state.safety_event_status)
        if opponents:
            advance_opponents(
                opponents, total_laps,
                st.session_state.safety_event_status,
                get_safety_event_lap_multiplier(),
                get_safety_event_pitstop_multiplier(),
            )
            if st.session_state.safety_event_status == 'SAFETYCAR':
                compress_sc_field(player, opponents)
        resolve_safety_event()
        st.session_state.lap_start_time  = time.time()
        st.session_state.lap_started_for = player.lap
        st.rerun()

    # ── Zweispaltiges Layout ──────────────────────────────────────────────
    left, right = st.columns([1, 2], gap="medium")

    # ── LINKS: Statuskacheln + Pitstop-Steuerung ─────────────────────────
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

        # Geschwindigkeitsregler + Countdown
        st.markdown('<div class="section-label">SIMULATIONSGESCHWINDIGKEIT</div>', unsafe_allow_html=True)
        st.slider(
            "Simulationsgeschwindigkeit",
            min_value=1, max_value=15, value=5, step=1,
            format="%ds",
            key="sim_speed",
            label_visibility="collapsed",
        )
        st.info(f"⏱  Automatisch weiter in **{remaining:.1f}s**")

        st.markdown('<div class="section-label">REIFEN FÜR PITSTOP</div>', unsafe_allow_html=True)
        _tire_selector("pitstop_tire_choice", default="SOFT")

        # KI-Empfehlung aus vorberechneter Gesamtstrategie
        ki = st.session_state.get("ki_strategy")
        if ki:
            t1c = TIRE_COLORS.get(ki.get('pit1_tyre', ''), '#fff')
            line = (
                f'<b>{ki["recommendation"]}</b>: '
                f'Stopp R{ki["pit1_lap"]} → <span style="color:{t1c};font-weight:900;">{ki["pit1_tyre"]}</span>'
            )
            if ki["recommendation"] == "2-Stop":
                t2c = TIRE_COLORS.get(ki.get('pit2_tyre', ''), '#fff')
                line += (
                    f' · R{ki["pit2_lap"]} → '
                    f'<span style="color:{t2c};font-weight:900;">{ki["pit2_tyre"]}</span> 🤖'
                )
            st.markdown(
                f'<div class="f1-card" style="padding:0.6rem 0.9rem;margin-bottom:0.5rem;">'
                f'<div style="color:#fff;font-size:0.85rem;">{line}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        if st.button("🔧  PIT NOW", key="pit_btn", type="primary", width='stretch'):
            _do_pit(player, total_laps)

    # ── RECHTS: Datenpanels ───────────────────────────────────────────────
    with right:
        # Obere Metrik-Reihe: Letzte Runde | Platz | Team
        pos = _calculate_position(player, opponents)
        team_color = TEAM_COLORS.get(player.team, "#e10600")

        if player.lap > 1:
            last = player.race_history[-1]["Rundenzeit"]
            prev = player.race_history[-2]["Rundenzeit"] if player.lap > 2 else None
            delta_color, delta_str = "#555", ""
            if prev is not None:
                diff = last - prev
                delta_color = "#00cc66" if diff < 0 else "#ff4444"
                delta_str   = f"{diff:+.3f}s"

            m1, m2, m3 = st.columns(3)
            with m1:
                st.markdown(f"""
                <div class="metric-tile" style="text-align:left;padding:0.9rem 1.1rem;">
                    <div class="mlabel">LETZTE RUNDENZEIT</div>
                    <div class="mval" style="font-size:1.4rem;">{_fmt_time(last)}
                        <span style="font-size:0.85rem;color:{delta_color};margin-left:6px;">{delta_str}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            with m2:
                st.markdown(f"""
                <div class="metric-tile">
                    <div class="mlabel">PLATZ</div>
                    <div class="mval">P{pos}</div>
                </div>
                """, unsafe_allow_html=True)
            with m3:
                st.markdown(f"""
                <div class="metric-tile">
                    <div class="mlabel">TEAM</div>
                    <div style="margin-top:0.3rem;">
                        <span style="background:{team_color};color:#fff;font-weight:700;
                              font-size:0.72rem;padding:3px 8px;border-radius:4px;
                              letter-spacing:0.5px;">{player.team}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown(
                '<div class="f1-card"><div class="f1-sub">Rundenzeiten erscheinen nach der ersten Runde.</div></div>',
                unsafe_allow_html=True,
            )

        # Rundenzeit-Verlauf (einzelne Rundenzeiten)
        if player.lap > 1:
            import altair as alt
            history_df = pd.DataFrame(player.race_history)
            st.markdown('<div class="section-label" style="margin-top:0.25rem;">RUNDENZEITENENTWICKLUNG</div>', unsafe_allow_html=True)
            chart = (
                alt.Chart(history_df)
                .mark_line(color="#e10600", strokeWidth=2, point=alt.OverlayMarkDef(color="#e10600", size=40))
                .encode(
                    x=alt.X("Runde:Q", scale=alt.Scale(domain=[1, total_laps], clamp=True), title="Runde"),
                    y=alt.Y("Rundenzeit:Q", scale=alt.Scale(zero=False), title="Zeit (s)"),
                    tooltip=["Runde:Q", alt.Tooltip("Rundenzeit:Q", format=".3f", title="Zeit (s)"), "Reifen:N"],
                )
                .properties(width="container", height=160)
                .interactive(bind_y=False)
            )
            st.altair_chart(chart, width='stretch')

        # Live-Rangliste (Spieler + Gegner, nach Gesamtzeit sortiert)
        st.markdown('<div class="section-label" style="margin-top:0.5rem;">LIVE-RANGLISTE</div>', unsafe_allow_html=True)
        standings = _build_live_standings(player, opponents)
        st.dataframe(standings, width='stretch', hide_index=True)

    # ── Rundenverlauf (eingeklappt, ganz unten) ───────────────────────────
    with st.expander("Rundenverlauf", expanded=False):
        if player.lap > 1:
            hist = pd.DataFrame(
                player.race_history,
                columns=["Runde", "Rundenzeit", "Reifen", "Reifenalter", "Kommentar"],
            )
            hist["Rundenzeit"] = hist["Rundenzeit"].apply(_fmt_time)
            st.dataframe(hist, width='stretch', hide_index=True)
        else:
            st.markdown('<div class="f1-sub">Noch keine Runden absolviert.</div>', unsafe_allow_html=True)


def render_race_page():
    """Rendert die Rennseite mit Header, Zurück-Button und dem Live-Renn-Fragment."""
    hdr_l, hdr_r = st.columns([4, 1])
    with hdr_l:
        st.markdown('<div class="f1-logo">F1</div>', unsafe_allow_html=True)
        track = st.session_state.get("track", "")
        team  = st.session_state.player.team if "player" in st.session_state else ""
        color = TEAM_COLORS.get(team, "#e10600")
        flag  = TRACK_FLAGS.get(track, "")
        st.markdown(
            f'<div class="f1-eyebrow">Rennen läuft</div>'
            f'<div style="font-size:1.35rem;font-weight:900;color:#fff;margin:0.1rem 0;">'
            f'{flag}&nbsp;{track}'
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
    """Hauptrouter: leitet zur Rennseite oder Einstellungsseite weiter."""
    if st.session_state.get("race_started"):
        render_race_page()
    else:
        render_setup_page()
