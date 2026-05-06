"""
InterfaceDM.py — Full-featured F1 Race Strategy Simulator interface.

Handles lap time calculation, tire degradation, weather effects,
pit stop strategy, interactive charts, and CSV export via Streamlit.
"""
#DON'T USE THIS FILE DIRECTLY, IT'S JUST A TEMPLATE WITH OWN AI RACELOGIC (NOT LINKED WITH OUR OWN
#RACELOGIC IN THE BACKEND). IT'S JUST LEFT HERE FOR INSPIRATION!

import streamlit as st
import plotly.graph_objects as go
import random
import pandas as pd
import io

st.set_page_config(page_title="F1 Race Strategy Simulator", layout="wide", initial_sidebar_state="collapsed")

# ── CONSTANTS ─────────────────────────────────────────────────────────────────

# Constructor names mapped to their official hex brand color
TEAMS = {
    "Ferrari":  "#DC0000",
    "Red Bull": "#3671C6",
    "Mercedes": "#00D2BE",
    "McLaren":  "#FF8000",
    "Williams": "#005AFF",
}

# Each track stores the base lap time (seconds) and total race laps
TRACKS = {
    "Monaco":      {"base_time": 75,  "laps": 78},
    "Monza":       {"base_time": 81,  "laps": 53},
    "Silverstone": {"base_time": 87,  "laps": 52},
    "Spa":         {"base_time": 104, "laps": 44},
    "Suzuka":      {"base_time": 91,  "laps": 53},
    "Bahrain":     {"base_time": 93,  "laps": 57},
    "Melbourne":   {"base_time": 80,  "laps": 58},
}

# Seconds added/subtracted from the base lap time per team (performance delta)
TEAM_DELTA = {
    "Ferrari": -0.1, "Red Bull": -0.3, "Mercedes": 0.0,
    "McLaren": -0.2, "Williams": 0.8,
}

# Each compound stores its display color, per-lap degradation rate,
# and a lap-time offset relative to the base time
COMPOUNDS = {
    "SOFT":   {"color": "#E8001C", "deg": 2.5, "offset": -1.5},  # fastest, wears quickest
    "MEDIUM": {"color": "#FFF200", "deg": 1.5, "offset":  0.0},  # balanced
    "HARD":   {"color": "#CCCCCC", "deg": 0.8, "offset":  1.0},  # slowest, most durable
}

# ── STATE ─────────────────────────────────────────────────────────────────────

def init_state():
    """Seed st.session_state with default values on first load.

    Only sets keys that are not already present, so existing race
    progress is preserved across Streamlit reruns.
    """
    defs = dict(
        phase="setup",       # "setup" | "racing" | "finished"
        team="Ferrari",
        track="Monaco",
        compound="SOFT",
        weather="Clear",     # "Clear" | "Wet"
        lap=1,
        lap_times=[],        # recorded lap time for each completed lap
        tire_life=100.0,     # percentage of tyre remaining (0–100)
        stints=[],           # list of {"compound", "start_lap", "end_lap"} dicts
        pit_times=[],        # pit-stop durations in seconds
        pit_count=0,
        pit_compound=None,   # compound selected for the next pit stop
        message="",          # transient status message shown after pit
        temp=25,             # air temperature in °C
        humidity=45,
        wind=12,             # wind speed in km/h
        last_session=None,   # summary dict from the most recently finished race
    )
    for k, v in defs.items():
        if k not in st.session_state:
            st.session_state[k] = v

# ── SIMULATION ────────────────────────────────────────────────────────────────

def calc_lap_time():
    """Return a simulated lap time (seconds) for the current state.

    Formula:
        base_time                      — circuit constant
        + compound offset              — tyre speed advantage/penalty
        + team delta                   — constructor performance gap
        + degradation penalty          — increases as tyre_life drops toward 0
        + wet penalty (if applicable)  — 4–10 s random addition
        + random variance              — ±0.4 s natural lap-to-lap variation
    """
    s = st.session_state
    return round(
        TRACKS[s.track]["base_time"]
        + COMPOUNDS[s.compound]["offset"]
        + TEAM_DELTA.get(s.team, 0.0)
        + (1 - s.tire_life / 100) * 6          # max +6 s when tyres are fully worn
        + (random.uniform(4, 10) if s.weather == "Wet" else 0)
        + random.uniform(-0.4, 0.4),
        2,
    )


def degrade_tires():
    """Reduce tyre life by one lap's worth of wear, with ±15 % randomness."""
    s = st.session_state
    s.tire_life = max(0.0, round(
        s.tire_life - COMPOUNDS[s.compound]["deg"] * random.uniform(0.85, 1.15), 1
    ))


def get_pit_window():
    """Calculate the recommended pit-stop window (two lap numbers).

    Estimates how many more laps the current tyre can run before
    dropping below 20 % life, then returns that lap and the one
    five laps later as the outer edge of the window.

    Returns:
        (window_start, window_end) — both clamped to the race distance.
    """
    s = st.session_state
    # Laps left before tyre drops under the 20 % threshold
    n = max(0, int((s.tire_life - 20) / COMPOUNDS[s.compound]["deg"]))
    ws = min(s.lap + n, TRACKS[s.track]["laps"] - 1)
    return ws, min(ws + 5, TRACKS[s.track]["laps"] - 1)


def do_lap(pit: bool):
    """Advance the race by one lap, optionally performing a pit stop first.

    If pitting:
      - Closes the current stint and opens a new one.
      - Resets tyre life to 100 % on the chosen compound.
      - Adds a random pit-stop duration (2.0–4.5 s) to pit_times.

    After the optional pit stop:
      - Records the lap time and degrades tyres.
      - Increments the lap counter.
      - Transitions phase to "finished" when the final lap is completed.
    """
    s = st.session_state
    if pit:
        dur = round(random.uniform(2.0, 4.5), 2)
        if s.stints:
            s.stints[-1]["end_lap"] = s.lap - 1     # close out the stint we just ended
        cmp = s.pit_compound or s.compound           # fall back to current if none chosen
        s.stints.append({"compound": cmp, "start_lap": s.lap, "end_lap": None})
        s.compound, s.tire_life = cmp, 100.0
        s.pit_count += 1
        s.pit_times.append(dur)
        s.pit_compound = None
        s.message = f"Pit stop: {dur:.2f}s — Now on {cmp} tires."
    else:
        s.message = ""

    s.lap_times.append(calc_lap_time())
    degrade_tires()
    s.lap += 1

    if s.lap > TRACKS[s.track]["laps"]:
        if s.stints:
            s.stints[-1]["end_lap"] = s.lap - 1
        s.phase = "finished"
        # Persist a minimal summary for the "Last Session" card
        s.last_session = dict(
            team=s.team, track=s.track,
            compound=s.stints[0]["compound"] if s.stints else s.compound,
            best_lap=min(s.lap_times), laps=len(s.lap_times),
        )


def start_race():
    """Reset all in-race state and transition from setup to racing.

    Randomises weather-dependent environmental conditions so that
    wet races feel genuinely different from dry ones.
    """
    s = st.session_state
    wet = s.weather == "Wet"
    s.temp     = random.randint(12, 22) if wet else random.randint(20, 35)
    s.humidity = random.randint(75, 95) if wet else random.randint(35, 65)
    s.wind     = random.randint(15, 35) if wet else random.randint(5, 25)
    s.lap, s.lap_times, s.tire_life = 1, [], 100.0
    s.pit_count, s.pit_times, s.message = 0, [], ""
    s.pit_compound = None
    s.stints = [{"compound": s.compound, "start_lap": 1, "end_lap": None}]
    s.phase = "racing"

# ── CSS ───────────────────────────────────────────────────────────────────────

# Dark F1-themed stylesheet injected via st.markdown.
# Uses Orbitron (display/numbers) and Rajdhani (body) from Google Fonts.
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@500;600&display=swap');

[data-testid="stAppViewContainer"] { background: #050810; }
[data-testid="stHeader"], [data-testid="stToolbar"] { display: none !important; }
#MainMenu, footer { visibility: hidden; }
[data-testid="block-container"] { padding: 1rem 1.5rem; max-width: 100%; }
[data-testid="stVerticalBlock"] { gap: 0.6rem; }

.panel {
    background: #0d1117;
    border: 1px solid #1c2333;
    border-radius: 12px;
    padding: 18px 20px;
    margin-bottom: 12px;
}
.panel-hdr {
    font-family: 'Orbitron', monospace;
    font-size: 0.65rem;
    letter-spacing: 3px;
    color: #4a6888;
    text-transform: uppercase;
    border-bottom: 1px solid #1c2333;
    padding-bottom: 10px;
    margin-bottom: 14px;
}
.panel-hdr span { color: #3a5a78; margin-right: 6px; }

.f1-logo {
    font-family: 'Orbitron', monospace;
    font-weight: 900;
    font-size: 0.75rem;
    color: #E8001C;
    letter-spacing: 4px;
    border: 2px solid #E8001C;
    padding: 2px 7px;
    display: inline-block;
    margin-bottom: 10px;
}
.hero-title {
    font-family: 'Orbitron', monospace;
    font-size: 1.5rem;
    font-weight: 900;
    color: white;
    line-height: 1.2;
    letter-spacing: 2px;
    margin-bottom: 8px;
}
.hero-sub {
    color: #4a6888;
    font-size: 0.78rem;
    line-height: 1.5;
    margin-bottom: 16px;
}

.info-card {
    background: #080c14;
    border: 1px solid #1c2333;
    border-radius: 8px;
    padding: 12px 14px;
    margin-bottom: 8px;
}
.lbl { font-family:'Orbitron',monospace; font-size:0.52rem; letter-spacing:2px; color:#3a5878; margin-bottom:3px; }
.val { font-family:'Orbitron',monospace; font-size:1.4rem; font-weight:700; color:white; }
.val-sm { font-family:'Orbitron',monospace; font-size:0.85rem; font-weight:700; color:white; }

.section-lbl { font-family:'Orbitron',monospace; font-size:0.55rem; letter-spacing:2px; color:#3a5878; margin:10px 0 6px; }

.team-card {
    border-radius: 8px;
    padding: 10px;
    text-align: center;
    cursor: pointer;
    margin-bottom: 4px;
}
.tire-row {
    display: flex;
    align-items: center;
    gap: 10px;
    border-radius: 8px;
    padding: 10px 12px;
    margin-bottom: 4px;
}

.pit-box {
    background: #0c0900;
    border: 1px solid #2a1f00;
    border-radius: 8px;
    padding: 12px;
    margin: 8px 0;
}
.pit-box .lbl { color: #886633; }

.weather-strip {
    display: flex;
    gap: 16px;
    align-items: center;
    padding: 8px 12px;
    background: #080c14;
    border-radius: 8px;
    border: 1px solid #1c2333;
    margin-top: 10px;
    font-size: 0.72rem;
    color: #4a6888;
}

.strategy-bar { display: flex; gap: 3px; border-radius: 4px; overflow: hidden; height: 22px; margin-bottom: 4px; }
.strategy-seg {
    display: flex; align-items: center; justify-content: center;
    font-size: 0.5rem; font-weight: 700; color: #111;
    font-family: 'Orbitron', monospace;
}

.stat-mini { text-align: center; }
.stat-mini .lbl { font-size: 0.48rem; }
.stat-mini .val-sm { font-size: 0.72rem; }

/* Buttons */
.stButton > button {
    font-family: 'Orbitron', monospace !important;
    font-weight: 700 !important;
    letter-spacing: 1.5px !important;
    border-radius: 8px !important;
    font-size: 0.78rem !important;
    border: none !important;
    transition: all 0.15s !important;
}
button[data-testid="baseButton-primary"] {
    background: linear-gradient(135deg, #8a0000, #cc1000) !important;
    color: white !important;
    box-shadow: 0 0 18px #cc100044 !important;
}
button[data-testid="baseButton-primary"]:hover {
    background: linear-gradient(135deg, #aa0000, #ee1200) !important;
    box-shadow: 0 0 28px #cc100077 !important;
}
button[data-testid="baseButton-secondary"] {
    background: #0d1520 !important;
    color: #8899bb !important;
    border: 1px solid #1c2a3f !important;
    box-shadow: none !important;
}
button[data-testid="baseButton-secondary"]:hover {
    background: #121d2e !important;
    color: white !important;
}
[data-testid="stProgress"] > div > div { background: #00e676 !important; }
[data-testid="stDownloadButton"] > button {
    font-family: 'Orbitron', monospace !important;
    font-size: 0.6rem !important;
    letter-spacing: 1px !important;
    background: #0d1520 !important;
    color: #4a88cc !important;
    border: 1px solid #1c3a5f !important;
}
</style>
"""

# ── PANELS ────────────────────────────────────────────────────────────────────

def hero_panel():
    """Render the top-left branding panel.

    Shows the simulator title and tagline. Displays a START button
    during setup, and a summary card of the most recently finished
    race session if one exists.
    """
    s = st.session_state
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-hdr"><span>◀</span> F1 RACE STRATEGY SIMULATOR</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="f1-logo">F1</div>
    <div class="hero-title">F1 RACE<br>STRATEGY<br>SIMULATOR</div>
    <div class="hero-sub">Make the right calls. Beat the competition.<br>Lead your team to victory!</div>
    """, unsafe_allow_html=True)

    # Only show the start button when no race is in progress
    if s.phase == "setup":
        if st.button("▶  START SIMULATION", key="hero_start", use_container_width=True, type="primary"):
            start_race()
            st.rerun()

    # Last-session summary card — shown after at least one race is completed
    if s.last_session:
        ls = s.last_session
        tc = TEAMS.get(ls["team"], "#ff0000")
        cmp_c = COMPOUNDS.get(ls["compound"], {}).get("color", "#fff")
        st.markdown(f"""
        <div class="info-card" style="margin-top:12px;">
            <div class="lbl">LAST SESSION</div>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-top:8px;">
                <div style="display:flex;flex-direction:column;gap:4px;">
                    <div style="display:flex;align-items:center;gap:6px;">
                        <div style="width:12px;height:12px;border-radius:50%;background:{tc};"></div>
                        <span style="color:white;font-size:0.72rem;font-weight:600;">{ls["team"]}</span>
                    </div>
                    <span style="color:#4a6888;font-size:0.62rem;">{ls["track"]}</span>
                    <div style="display:flex;align-items:center;gap:4px;">
                        <div style="width:10px;height:10px;border-radius:50%;background:{cmp_c};"></div>
                        <span style="color:#4a6888;font-size:0.62rem;">{ls["compound"]} Tires</span>
                    </div>
                </div>
                <div style="text-align:right;">
                    <div class="lbl">BEST LAP TIME</div>
                    <div class="val-sm">{ls["best_lap"]:.2f}s</div>
                    <div class="lbl" style="margin-top:4px;">LAPS: {ls["laps"]}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


def setup_panel():
    """Render the pre-race configuration panel (right column).

    Lets the player choose:
      - Weather condition (Clear / Wet) — affects lap times and conditions
      - Constructor (team) — applies the team performance delta
      - Starting tyre compound — sets initial degradation rate and speed offset
      - Track — determines base lap time and total race laps

    Pressing START fires start_race() and transitions to the racing phase.
    """
    s = st.session_state
    st.markdown('<div class="panel">', unsafe_allow_html=True)

    weather_icon = "☀️ Clear" if s.weather == "Clear" else "🌧️ Wet"
    st.markdown(f'<div class="panel-hdr"><span>◀</span> START NEW SIMULATION <span style="float:right;color:#4a88cc;">Weather: {weather_icon}</span></div>', unsafe_allow_html=True)

    # Weather toggle — two mutually exclusive buttons
    weather_cols = st.columns(2)
    with weather_cols[0]:
        if st.button("☀️  Clear", key="w_clear", use_container_width=True,
                     type="primary" if s.weather == "Clear" else "secondary"):
            s.weather = "Clear"; st.rerun()
    with weather_cols[1]:
        if st.button("🌧️  Wet", key="w_wet", use_container_width=True,
                     type="primary" if s.weather == "Wet" else "secondary"):
            s.weather = "Wet"; st.rerun()

    team_col, tire_col = st.columns([3, 2], gap="medium")

    with team_col:
        st.markdown('<div class="section-lbl">SELECT TEAM</div>', unsafe_allow_html=True)
        team_list = list(TEAMS.keys())
        # Render teams in a 2-column grid; selected team gets a colored glow border
        for i in range(0, len(team_list), 2):
            row = team_list[i:i+2]
            cols = st.columns(len(row))
            for c, team in zip(cols, row):
                with c:
                    tc = TEAMS[team]
                    sel = s.team == team
                    border = f"2px solid {tc}" if sel else "1px solid #1c2333"
                    glow   = f"box-shadow:0 0 12px {tc}44;" if sel else ""
                    st.markdown(f"""
                    <div style="background:#0d1117;border:{border};border-radius:8px;
                                padding:10px;text-align:center;{glow}margin-bottom:4px;">
                        <div style="width:22px;height:22px;border-radius:50%;
                                    background:{tc};margin:0 auto 5px;"></div>
                        <div style="color:white;font-size:0.62rem;font-weight:600;
                                    letter-spacing:1px;">{team.upper()}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("✓" if sel else team, key=f"team_{team}", use_container_width=True,
                                 type="primary" if sel else "secondary"):
                        s.team = team; st.rerun()

    with tire_col:
        st.markdown('<div class="section-lbl">STARTING TIRE</div>', unsafe_allow_html=True)
        # Each compound rendered as a coloured dot card; selected one gets a glow border
        for cmp in ["SOFT", "MEDIUM", "HARD"]:
            cc  = COMPOUNDS[cmp]["color"]
            sel = s.compound == cmp
            border = f"2px solid {cc}" if sel else "1px solid #1c2333"
            glow   = f"box-shadow:0 0 10px {cc}44;" if sel else ""
            st.markdown(f"""
            <div style="background:#080c14;border:{border};border-radius:8px;
                        padding:9px 12px;margin-bottom:4px;display:flex;
                        align-items:center;gap:8px;{glow}">
                <div style="width:24px;height:24px;border-radius:50%;
                            background:{cc};flex-shrink:0;"></div>
                <div style="color:white;font-size:0.65rem;font-weight:600;">S {cmp}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("✓" if sel else cmp, key=f"cmp_{cmp}", use_container_width=True,
                         type="primary" if sel else "secondary"):
                s.compound = cmp; st.rerun()

    st.markdown('<div class="section-lbl">SELECT TRACK</div>', unsafe_allow_html=True)
    track = st.selectbox("Track", list(TRACKS.keys()),
                         index=list(TRACKS.keys()).index(s.track),
                         label_visibility="collapsed")
    if track != s.track:
        s.track = track

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("▶  START SIMULATION", key="setup_start", use_container_width=True, type="primary"):
        start_race(); st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


def race_panel():
    """Render the live race control panel (left column, below hero).

    During racing phase shows:
      - Current lap counter and team/compound info
      - Tyre wear bars for all three compounds (active compound is live; others show 100 %)
      - Recommended pit window derived from get_pit_window()
      - Compound selector for the upcoming pit stop
      - NEXT LAP and PIT NOW action buttons

    During finished phase shows only a NEW RACE reset button.
    Always shows a weather strip at the bottom.
    """
    s = st.session_state
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-hdr"><span>◀</span> RACE IN PROGRESS</div>', unsafe_allow_html=True)

    if s.phase == "setup":
        st.markdown('<div style="color:#2a3a4a;font-size:0.8rem;text-align:center;padding:20px 0;">Race not started yet</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        return

    total  = TRACKS[s.track]["laps"]
    times  = s.lap_times
    best   = min(times) if times else 0.0
    last   = times[-1]  if times else 0.0
    cur_lap = min(s.lap - 1, total)   # lap - 1 because s.lap is the *next* lap to run
    tc  = TEAMS.get(s.team, "#ff0000")
    cc  = COMPOUNDS[s.compound]["color"]

    # Lap counter (left) and best/last lap times (right)
    r1, r2 = st.columns([1, 2], gap="small")
    with r1:
        st.markdown(f"""
        <div class="info-card" style="text-align:center;">
            <div class="lbl">LAP</div>
            <div style="font-family:'Orbitron',monospace;font-size:2rem;font-weight:900;color:white;line-height:1;">{cur_lap}</div>
            <div style="color:#3a5878;font-size:0.7rem;">/ {total}</div>
        </div>
        """, unsafe_allow_html=True)
    with r2:
        st.markdown(f"""
        <div class="info-card">
            <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">
                <div style="width:14px;height:14px;border-radius:50%;background:{tc};"></div>
                <span style="color:white;font-size:0.72rem;font-weight:600;">{s.team}</span>
                <div style="width:14px;height:14px;border-radius:50%;background:{cc};margin-left:6px;"></div>
                <span style="color:#aaa;font-size:0.62rem;">{s.compound}</span>
            </div>
            <div style="display:flex;gap:16px;">
                <div><div class="lbl">BEST LAP</div><div class="val-sm">{best:.2f}s</div></div>
                <div><div class="lbl">LAST LAP</div><div class="val-sm">{last:.2f}s</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Tyre wear bars — colour shifts green → amber → red as life drops
    st.markdown('<div class="section-lbl">TYRE WEAR</div>', unsafe_allow_html=True)
    for cmp, cfg in COMPOUNDS.items():
        remaining = s.tire_life if cmp == s.compound else 100.0
        bar_color = "#00e676" if remaining > 60 else "#ffab00" if remaining > 30 else "#ff1744"
        st.markdown(f"""
        <div style="margin-bottom:6px;">
            <div style="display:flex;justify-content:space-between;margin-bottom:2px;">
                <div style="display:flex;align-items:center;gap:5px;">
                    <div style="width:9px;height:9px;border-radius:50%;background:{cfg['color']};"></div>
                    <span style="color:#4a6888;font-size:0.6rem;">{cmp.capitalize()}</span>
                </div>
                <span style="color:white;font-size:0.6rem;font-family:'Orbitron',monospace;">{remaining:.0f}%</span>
            </div>
            <div style="background:#0a0e18;border-radius:3px;height:5px;">
                <div style="background:{bar_color};width:{remaining}%;height:100%;border-radius:3px;transition:width 0.3s;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    if s.phase == "racing":
        ws, we = get_pit_window()
        st.markdown(f"""
        <div class="pit-box">
            <div class="lbl">PIT STRATEGY</div>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-top:8px;">
                <div>
                    <div style="color:#666;font-size:0.55rem;">Next Pit Window</div>
                    <div style="font-family:'Orbitron',monospace;font-size:0.95rem;font-weight:700;color:white;">LAP {ws} – {we}</div>
                </div>
                <div style="text-align:right;">
                    <div style="color:#666;font-size:0.55rem;">Current Tyre</div>
                    <div style="display:flex;align-items:center;gap:4px;margin-top:2px;justify-content:flex-end;">
                        <div style="width:11px;height:11px;border-radius:50%;background:{cc};"></div>
                        <span style="color:white;font-size:0.65rem;">{s.compound}</span>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Compound selector for the next pit stop; toggled by clicking a compound button
        st.markdown('<div class="section-lbl">PIT ONTO:</div>', unsafe_allow_html=True)
        pc1, pc2, pc3 = st.columns(3)
        for pcol, cmp in [(pc1, "SOFT"), (pc2, "MEDIUM"), (pc3, "HARD")]:
            with pcol:
                csel = s.pit_compound == cmp
                ccc  = COMPOUNDS[cmp]["color"]
                border = f"2px solid {ccc}" if csel else "1px solid #1c2333"
                st.markdown(f"""
                <div style="border:{border};border-radius:6px;background:#080c14;
                            padding:6px;text-align:center;margin-bottom:4px;">
                    <div style="width:18px;height:18px;border-radius:50%;background:{ccc};margin:0 auto 2px;"></div>
                    <div style="color:#aaa;font-size:0.48rem;font-family:'Orbitron',monospace;">{cmp}</div>
                </div>
                """, unsafe_allow_html=True)
                # Clicking an already-selected compound deselects it (toggle behaviour)
                if st.button("✓" if csel else cmp[0], key=f"pit_cmp_{cmp}", use_container_width=True,
                             type="primary" if csel else "secondary"):
                    s.pit_compound = None if csel else cmp
                    st.rerun()

        a1, a2 = st.columns(2)
        with a1:
            if st.button("NEXT LAP ▶", key="next_lap", use_container_width=True):
                do_lap(pit=False); st.rerun()
        with a2:
            if st.button("🔴  PIT NOW", key="pit_now", use_container_width=True, type="primary"):
                do_lap(pit=True); st.rerun()

        if s.message:
            st.markdown(f'<div style="color:#88ffaa;font-size:0.68rem;margin-top:6px;text-align:center;">{s.message}</div>', unsafe_allow_html=True)

    elif s.phase == "finished":
        # Race over — clear in-race keys so setup_panel shows fresh defaults next time
        if st.button("▶  NEW RACE", key="new_race_btn", use_container_width=True, type="primary"):
            for k in ["phase","lap","lap_times","tire_life","stints","pit_times",
                      "pit_count","pit_compound","message"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

    # Weather strip always visible at the bottom of the race panel
    icon = "☀️" if s.weather == "Clear" else "🌧️"
    st.markdown(f"""
    <div class="weather-strip">
        <span>{icon} {s.weather}</span>
        <span>💨 {s.wind} km/h</span>
        <span>🌡️ {s.temp}°C</span>
        <span>💧 {s.humidity}%</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


def results_panel():
    """Render the race results panel (right column, below setup).

    Displays (once lap_times is populated):
      - Best lap time card with team colour dot
      - Plotly line chart of lap-by-lap times (hidden if only one lap)
      - Summary stats: total race time, average lap, pit stop count, fastest pit
      - Strategy bar: colour-coded stints proportional to their lap share,
        with lap-number markers below

    Also provides an EXPORT CSV download button for the lap time data.
    """
    s = st.session_state
    times = s.lap_times

    st.markdown('<div class="panel">', unsafe_allow_html=True)

    hdr1, hdr2 = st.columns([3, 1])
    with hdr1:
        st.markdown('<div class="panel-hdr"><span>◀</span> RACE RESULTS</div>', unsafe_allow_html=True)
    with hdr2:
        if times:
            df  = pd.DataFrame({"Lap": range(1, len(times)+1), "LapTime_s": times})
            buf = io.StringIO()
            df.to_csv(buf, index=False)
            st.download_button("EXPORT CSV", buf.getvalue(), "race_results.csv", "text/csv",
                               use_container_width=True, key="export_btn")

    if not times:
        st.markdown('<div style="color:#2a3a4a;font-size:0.8rem;text-align:center;padding:20px 0;">No data yet</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        return

    best  = min(times)
    avg   = sum(times) / len(times)
    total = sum(times)
    # Format total race time as H:MM:SS.mmm (drop hours if under 60 min)
    h, rem = divmod(total, 3600)
    m, sec = divmod(rem, 60)
    total_str = f"{int(h)}:{int(m):02d}:{sec:06.3f}" if h else f"{int(m)}:{sec:06.3f}"
    fastest_pit = min(s.pit_times) if s.pit_times else None
    tc  = TEAMS.get(s.team, "#ff0000")

    st.markdown(f"""
    <div class="info-card" style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">
        <div style="width:36px;height:36px;border-radius:50%;background:{tc};flex-shrink:0;"></div>
        <div>
            <div class="lbl">BEST LAP TIME</div>
            <div class="val">{best:.2f}s</div>
            <div style="color:#4a6888;font-size:0.6rem;">{s.team}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Lap time chart — only rendered when there are at least two data points
    if len(times) > 1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=list(range(1, len(times) + 1)),
            y=times,
            mode="lines",
            line=dict(color="#7B2FBE", width=2),
            fill="tozeroy",
            fillcolor="rgba(123,47,190,0.08)",
            hovertemplate="Lap %{x}: %{y:.2f}s<extra></extra>",
        ))
        total_laps = TRACKS[s.track]["laps"]
        fig.update_layout(
            height=150,
            margin=dict(l=0, r=0, t=4, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=True, gridcolor="#0f1a28",
                       tickfont=dict(color="#3a5878", size=8),
                       range=[1, total_laps],
                       title=dict(text="LAP", font=dict(color="#3a5878", size=8))),
            yaxis=dict(showgrid=True, gridcolor="#0f1a28",
                       tickfont=dict(color="#3a5878", size=8)),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # Four headline stats in a single row
    c1, c2, c3, c4 = st.columns(4)
    for col, lbl, val in [
        (c1, "TOTAL RACE TIME", total_str),
        (c2, "AVERAGE LAP",     f"{avg:.2f}s"),
        (c3, "PIT STOPS",       str(s.pit_count)),
        (c4, "FASTEST PIT",     f"{fastest_pit:.2f}s" if fastest_pit else "—"),
    ]:
        with col:
            st.markdown(f"""
            <div class="stat-mini">
                <div class="lbl">{lbl}</div>
                <div class="val-sm">{val}</div>
            </div>
            """, unsafe_allow_html=True)

    # Strategy bar -> each stint becomes a coloured segment whose width is
    # proportional to the fraction of total laps it covers
    if s.stints:
        st.markdown('<div class="section-lbl" style="margin-top:14px;">STRATEGY OVERVIEW</div>', unsafe_allow_html=True)
        total_laps = TRACKS[s.track]["laps"]
        segs = []
        for stint in s.stints:
            start = stint["start_lap"]
            end   = stint["end_lap"] or (s.lap - 1)
            laps  = max(1, end - start + 1)
            pct   = round(laps / total_laps * 100, 1)
            cc    = COMPOUNDS[stint["compound"]]["color"]
            letter = stint["compound"][0]          # S / M / H label inside the bar
            segs.append(
                f'<div class="strategy-seg" style="flex:{pct};background:{cc};">'
                f'{letter}</div>'
            )
        # Lap-number markers are positioned absolutely below each stint start
        lap_markers = []
        for stint in s.stints:
            pct = round((stint["start_lap"] - 1) / total_laps * 100, 1)
            lap_markers.append(
                f'<div style="position:absolute;left:{pct}%;transform:translateX(-50%);'
                f'font-size:0.45rem;color:#3a5878;font-family:Orbitron,monospace;">'
                f'LAP {stint["start_lap"]}</div>'
            )
        st.markdown(
            f'<div class="strategy-bar">{"".join(segs)}</div>'
            f'<div style="position:relative;height:14px;">{"".join(lap_markers)}</div>',
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)

# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    """Entry point — initialise state, inject CSS, and render the two-column layout.

    Left column (2/5 width):  hero_panel  →  race_panel
    Right column (3/5 width): setup_panel →  results_panel
    """
    init_state()
    st.markdown(CSS, unsafe_allow_html=True)

    left, right = st.columns([2, 3], gap="medium")
    with left:
        hero_panel()
        race_panel()
    with right:
        setup_panel()
        results_panel()

main()
