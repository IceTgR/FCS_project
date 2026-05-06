import streamlit as st
from strategy_optimizer import find_optimal_pit_lap
import pandas as pd
import os
from racelogic import write_chosen_options, race_simulation
from car import Car
from opponents import create_opponents
from train_models import ensure_ml_assets
from ui_team_selector import render_team_selector

# --- 1. PAGE SETUP ---
st.set_page_config(layout="wide")

# Initialize session state for page routing
if 'race_started' not in st.session_state: 
    st.session_state.race_started = False

if 'ml_bootstrap_done' not in st.session_state:
    with st.spinner('Vorbereitung von Daten und ML-Modellen beim ersten Start...'):
        st.session_state.ml_bootstrap_status = ensure_ml_assets()

    st.session_state.ml_bootstrap_done = True

    bootstrap_status = st.session_state.ml_bootstrap_status
    status_lines = []
    if bootstrap_status['created_db']:
        status_lines.append('Datenbank erstellt')
    elif os.path.exists('f1_project.db'):
        status_lines.append('Datenbank bereit')

    if bootstrap_status['trained_models']:
        status_lines.append('Modelle trainiert')
    elif os.path.exists('models/dry/rf_Monaco_Grand_Prix.pkl') and os.path.exists('models/dry/rf_British_Grand_Prix.pkl'):
        status_lines.append('Modelle bereit')

    if status_lines:
        st.info('ML-Einrichtung: ' + ' | '.join(status_lines))

    if bootstrap_status['trained_models'] and bootstrap_status['results']:
        st.caption('Validierungs-MAE (Sekunden): ' + ', '.join(f"{track}: {mae:.3f}" for track, mae in bootstrap_status['results'].items()))

st.title('F1 Rennstrategie-Simulator')

# Track-specific temperature ranges
TRACK_TEMP_RANGES = {
    'Monaco Grand Prix': {'min': 16, 'max': 28, 'default': 22},      
    'British Grand Prix': {'min': 14, 'max': 26, 'default': 20},     
}

# ==========================================
# 🚪 PAGE 1: THE MAIN MENU (Setup Screen)
# ==========================================
if not st.session_state.race_started:
    st.write('Du bist jetzt in der Position eines F1-Rennstrategen!')

    # --- TEAM SELECTION ---
    team_player = render_team_selector() 

    # --- TRACK AND TIRE SELECTION ---
    st.write("### 🛠️ Rennparameter")
    col_track, col_start_tire, col_target_tire = st.columns(3)
    
    with col_track:
        st.session_state.track = st.selectbox('Strecke wählen:', 
                                             ['Monaco Grand Prix', 'British Grand Prix'])
    
    with col_start_tire:
        tire_start = st.radio('Startreifen:', ['SOFT', 'MEDIUM', 'HARD'], key="start_tire")
    
    with col_target_tire:
        target_tire = st.radio('Zielreifen:', ['SOFT', 'MEDIUM', 'HARD'], index=2, key="target_tire")

    # --- TEMPERATURE SLIDER ---
    st.markdown("---")
    track_temps = TRACK_TEMP_RANGES.get(st.session_state.track, {'min': 15, 'max': 30, 'default': 22})
    air_temp = st.slider(
        '🌡️ Lufttemperatur (°C)',
        min_value=track_temps['min'],
        max_value=track_temps['max'],
        value=track_temps['default'],
        step=1,
        help=f"Stelle die Umgebungstemperatur für {st.session_state.track} ein. Typische Bedingungen liegen zwischen {track_temps['min']}°C und {track_temps['max']}°C."
    )
    st.session_state.air_temp = air_temp

    # --- ML STRATEGIST PRE-RACE BRIEFING ---
    sim_laps = 78 if st.session_state.track == 'Monaco Grand Prix' else 52
    
    with st.expander("🏎️ KI-Stratege Briefing", expanded=True):
        st.write("Lass die KI das Rennen simulieren, um deine mathematisch schnellste Boxenstrategie zu finden!")
        
        if st.button("KI nach optimalem Boxenstopp fragen", use_container_width=True):
            with st.spinner("Simuliere Multi-Compound-Rundenzeiten..."):
                try:
                    best_lap = find_optimal_pit_lap(
                        track_name=st.session_state.track, 
                        total_laps=sim_laps,             
                        team=team_player, 
                        start_compound=tire_start, 
                        next_compound=target_tire, 
                        air_temp=st.session_state.air_temp 
                    )
                    
                    st.success(f"**Optimale Strategie gefunden:** Boxenstopp in Runde {best_lap} um von {tire_start} zu {target_tire} zu wechseln!")
                    
                    st.markdown("### 💡 Warum diese Runde?")
                    if team_player in ['Red Bull', 'Mercedes']:
                        st.info(f"**Effizienzprofil:** {team_player} zeigt historisch ein besseres Reifenmanagement. Die KI schlägt vor, bis Runde {best_lap} zu drücken, da dein Auto das Tempo hält, auch wenn die Reifen verschleißen, was einen kürzeren und schnelleren Endstoß ermöglicht.")
                    elif team_player in ['Ferrari', 'McLaren']:
                        st.info(f"**Performance-Peak:** {team_player} hat hohe Spitzenkraft, aber schnelleren Abfall. Ein Boxenstopp in Runde {best_lap} vermeidet die 'Klippe', wo deine Rundenzeiten zusammenbrechen würden, und sichert einen Wechsel zu frischen {target_tire}n ab, wenn deine {tire_start}s ihre Wirkung verlieren.")
                    else:
                        st.info(f"**Risikominderung:** Für {team_player} priorisiert die KI Rennposition. Ein Boxenstopp in Runde {best_lap} minimiert die Zeit auf verschlissenen Reifen, wo dein Auto am anfälligsten ist, überholt zu werden.")

                except FileNotFoundError:
                    st.error("Modell nicht gefunden. App neu laden, damit der Start-Bootstrap abgeschlossen wird.")
                except Exception as e:
                    st.error(f"Ein Fehler während der Simulation ist aufgetreten: {e}")

    # --- THE ONE AND ONLY START BUTTON ---
    st.markdown("---")
    if st.button('🏁 Simulation starten', type="primary", use_container_width=True):
        # 1. Flag the race as started
        st.session_state.race_started = True
        
        # 2. Build the player car and set laps
        if st.session_state.track == 'Monaco Grand Prix':
            st.session_state.player = Car(team_player, 'Monaco Grand Prix', tire_start) 
            st.session_state.total_laps = 78 
        elif st.session_state.track == 'British Grand Prix':
            st.session_state.player = Car(team_player, 'British Grand Prix', tire_start) 
            st.session_state.total_laps = 52 
            
        # 3. Create opponents
        st.session_state.opponents = create_opponents(team_player, st.session_state.track, st.session_state.total_laps)
        
        # 4. Rerun to instantly switch to Page 2
        st.rerun()


# ==========================================
# 🚪 PAGE 2: THE SIMULATION (Race Screen)
# ==========================================
else: 
    # Navigation header
    col_back, col_title, col_empty = st.columns([1, 4, 1])
    
    with col_back:
        if st.button("⬅️ Zurück"):
            st.session_state.race_started = False
            if 'player' in st.session_state:
                del st.session_state['player']
            st.rerun()
            
    with col_title:
        st.markdown("<h3 style='text-align: center; margin-top: 0px;'>🏁 Das Rennen läuft!</h3>", unsafe_allow_html=True)
    
    st.divider()

    if 'player' in st.session_state:
        
        # --- NEW: LIVE AI STRATEGY DASHBOARD ---
        st.markdown("#### 🧠 Live KI-Strategie-Ratgeber")
        
        # Create columns to put the dropdown next to the AI's recommendation
        col_advisor_input, col_advisor_output = st.columns([1, 2])
        
        with col_advisor_input:
            # The dropdown for the user to change their mind mid-race
            live_target_tire = st.selectbox(
                "Boxenstrategie bewerten für:", 
                ['SOFT', 'MEDIUM', 'HARD'], 
                key="live_target_tire"
            )
            
        with col_advisor_output:
            # The AI instantly calculates the best lap for whatever is in the dropdown!
            try:
                # We add a slight visual padding to align it with the dropdown box
                st.write("") 
                best_lap = find_optimal_pit_lap(
                    track_name=st.session_state.track,
                    total_laps=st.session_state.total_laps,
                    team=st.session_state.player.team,
                    start_compound=st.session_state.player.tire,
                    next_compound=live_target_tire,
                    air_temp=st.session_state.air_temp
                )
                # Display the live recommendation
                st.success(f"**Zielbereich:** Boxenstopp in **Runde {best_lap}** für frische **{live_target_tire}**-Reifen.")
            except Exception as e:
                st.warning("KI benötigt trainierte Modelle für Live-Daten.")

        st.divider()

        # --- EXISTING RACE LOGIC ---
        write_chosen_options()
        race_simulation()

    else:
        st.error("Autodaten konnten nicht geladen werden. Bitte zum Hauptmenü zurückgehen und erneut versuchen.")
