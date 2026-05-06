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
    with st.spinner('Preparing data and ML models for the first launch...'):
        st.session_state.ml_bootstrap_status = ensure_ml_assets()

    st.session_state.ml_bootstrap_done = True

    bootstrap_status = st.session_state.ml_bootstrap_status
    status_lines = []
    if bootstrap_status['created_db']:
        status_lines.append('Database created')
    elif os.path.exists('f1_project.db'):
        status_lines.append('Database ready')

    if bootstrap_status['trained_models']:
        status_lines.append('Models trained')
    elif os.path.exists('models/dry/rf_Monaco_Grand_Prix.pkl') and os.path.exists('models/dry/rf_British_Grand_Prix.pkl'):
        status_lines.append('Models ready')

    if status_lines:
        st.info('ML setup: ' + ' | '.join(status_lines))

    if bootstrap_status['trained_models'] and bootstrap_status['results']:
        st.caption('Validation MAE (seconds): ' + ', '.join(f"{track}: {mae:.3f}" for track, mae in bootstrap_status['results'].items()))

st.title('F1 Race Strategy Simulator')

# Track-specific temperature ranges
TRACK_TEMP_RANGES = {
    'Monaco Grand Prix': {'min': 16, 'max': 28, 'default': 22},      
    'British Grand Prix': {'min': 14, 'max': 26, 'default': 20},     
}

# ==========================================
# 🚪 PAGE 1: THE MAIN MENU (Setup Screen)
# ==========================================
if not st.session_state.race_started:
    st.write('You are now in the seat of the F1 race strategist!')

    # --- TEAM SELECTION ---
    team_player = render_team_selector() 

    # --- TRACK AND TIRE SELECTION ---
    st.write("### 🛠️ Race Parameters")
    col_track, col_start_tire, col_target_tire = st.columns(3)
    
    with col_track:
        st.session_state.track = st.selectbox('Select the track:', 
                                             ['Monaco Grand Prix', 'British Grand Prix'])
    
    with col_start_tire:
        tire_start = st.radio('Starting Tire:', ['SOFT', 'MEDIUM', 'HARD'], key="start_tire")
    
    with col_target_tire:
        target_tire = st.radio('Target Pit Tire:', ['SOFT', 'MEDIUM', 'HARD'], index=2, key="target_tire")

    # --- TEMPERATURE SLIDER ---
    st.markdown("---")
    track_temps = TRACK_TEMP_RANGES.get(st.session_state.track, {'min': 15, 'max': 30, 'default': 22})
    air_temp = st.slider(
        '🌡️ Air Temperature (°C)',
        min_value=track_temps['min'],
        max_value=track_temps['max'],
        value=track_temps['default'],
        step=1,
        help=f"Set the ambient air temperature for {st.session_state.track}. Typical race conditions range from {track_temps['min']}°C to {track_temps['max']}°C."
    )
    st.session_state.air_temp = air_temp

    # --- ML STRATEGIST PRE-RACE BRIEFING ---
    sim_laps = 78 if st.session_state.track == 'Monaco Grand Prix' else 52
    
    with st.expander("🏎️ ML Strategist Briefing", expanded=True):
        st.write("Let our AI simulate the race to find your mathematically fastest pit stop strategy!")
        
        if st.button("Ask the AI for the Optimal Pit Lap", use_container_width=True):
            with st.spinner("Simulating multi-compound race times..."):
                try:
                    best_lap = find_optimal_pit_lap(
                        track_name=st.session_state.track, 
                        total_laps=sim_laps,             
                        team=team_player, 
                        start_compound=tire_start, 
                        next_compound=target_tire, 
                        air_temp=st.session_state.air_temp 
                    )
                    
                    st.success(f"**Optimal Strategy Found:** Pit on Lap {best_lap} to switch from {tire_start} to {target_tire}s!")
                    
                    st.markdown("### 💡 Why this lap?")
                    if team_player in ['Red Bull', 'Mercedes']:
                        st.info(f"**Efficiency Profile:** {team_player} historically shows better tire management. The AI suggests pushing until Lap {best_lap} because your car maintains pace even as the rubber thins, allowing for a shorter, faster final stint.")
                    elif team_player in ['Ferrari', 'McLaren']:
                        st.info(f"**Performance Peak:** {team_player} has high peak grip but faster drop-off. Pitting on Lap {best_lap} avoids the 'cliff' where your lap times would collapse, ensuring you switch to fresh {target_tire}s right as your {tire_start}s lose their edge.")
                    else:
                        st.info(f"**Risk Mitigation:** For {team_player}, the AI prioritizes track position. Pitting on Lap {best_lap} minimizes the time spent on degraded tires where your car is most vulnerable to being overtaken.")

                except FileNotFoundError:
                    st.error("Model not found. Reload the app so the startup bootstrap can finish.")
                except Exception as e:
                    st.error(f"An error occurred during simulation: {e}")

    # --- THE ONE AND ONLY START BUTTON ---
    st.markdown("---")
    if st.button('🏁 Start the Simulation', type="primary", use_container_width=True):
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
        if st.button("⬅️ Back"):
            st.session_state.race_started = False
            if 'player' in st.session_state:
                del st.session_state['player']
            st.rerun()
            
    with col_title:
        st.markdown("<h3 style='text-align: center; margin-top: 0px;'>🏁 The Race is On!</h3>", unsafe_allow_html=True)
    
    st.divider()

    if 'player' in st.session_state:
        
        # --- NEW: LIVE AI STRATEGY DASHBOARD ---
        st.markdown("#### 🧠 Live AI Strategy Advisor")
        
        # Create columns to put the dropdown next to the AI's recommendation
        col_advisor_input, col_advisor_output = st.columns([1, 2])
        
        with col_advisor_input:
            # The dropdown for the user to change their mind mid-race
            live_target_tire = st.selectbox(
                "Evaluate Pit Strategy for:", 
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
                st.success(f"**Target Window:** Box on **Lap {best_lap}** for fresh **{live_target_tire}** tires.")
            except Exception as e:
                st.warning("AI requires models to be trained to provide live data.")

        st.divider()

        # --- EXISTING RACE LOGIC ---
        write_chosen_options()
        race_simulation()

    else:
        st.error("Car data failed to load. Please go back to the main menu and try again.")
