import streamlit as st
from strategy_optimizer import find_optimal_pit_lap
import pandas as pd
import os
from racelogic import write_chosen_options, race_simulation
from car import Car
from opponents import create_opponents
from train_models import train_models
from ui_team_selector import render_team_selector

# --- 1. PAGE SETUP ---
st.set_page_config(layout="wide")

# Initialize session state for page routing
if 'race_started' not in st.session_state: 
    st.session_state.race_started = False

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
    
    train_models() 

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
                    st.error("Model not found! Make sure to click 'Train Models Now' first.")
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
    # Because of the 'else', NOTHING from Page 1 will render while this runs!
    
    # Navigation header
    col_back, col_title = st.columns([1, 5]) 
    
    with col_back:
        if st.button("⬅️ Back"):
            st.session_state.race_started = False
            # Clean up the car state when going back so it resets properly next time
            if 'player' in st.session_state:
                del st.session_state['player']
            st.rerun()
            
    with col_title:
        st.write("### 🏁 The Race is On!")
    
    st.divider()

    # Make sure player exists before running logic (safety net)
    if 'player' in st.session_state:
        write_chosen_options()
        race_simulation()

        # Mid-race ML strategist
        with st.expander("🏁 Mid-Race ML Strategist", expanded=False):
            st.write("Run the AI during the race to re-evaluate an optimal pit lap based on current state.")
            next_compound = st.selectbox("Choose next compound (if pitting):", ['SOFT','MEDIUM','HARD'], key='mid_next_compound')
            
            if st.button("Ask AI (mid-race)"):
                with st.spinner("Simulating race times for strategy..."):
                    try:
                        best_lap = find_optimal_pit_lap(
                            track_name=st.session_state.track,
                            total_laps=st.session_state.total_laps,
                            team=st.session_state.player.team,
                            start_compound=st.session_state.player.tire,
                            next_compound=next_compound,
                            air_temp=st.session_state.air_temp,
                            pit_window_start=st.session_state.player.lap + 1,
                            pit_window_end=st.session_state.total_laps - 1,
                        )
                        st.success(f"**Optimal Strategy Found:** The AI recommends pitting on Lap {best_lap}!")
                    except FileNotFoundError:
                        st.error("Model not found! Make sure models are trained before running the strategist.")
                    except Exception as e:
                        st.error(f"An error occurred running the strategist: {e}")
    else:
        # Fallback if something went wrong
        st.error("Car data failed to load. Please go back to the main menu and try again.")
