import streamlit as st
from strategy_optimizer import find_optimal_pit_lap
import pandas as pd
import os
from racelogic import write_chosen_options, race_simulation
from car import Car
from opponents import create_opponents
from train_models import train_models
from ui_team_selector import render_team_selector


#main()

# Track whether the simulation has been started in the current Streamlit session.
if 'race_started' not in st.session_state: # to check if race has started, if not, initialize it to False
    st.session_state.race_started = False

st.title('F1 Race Strategy Simulator')

# Track-specific temperature ranges (realistic F1 conditions)
TRACK_TEMP_RANGES = {
    'Monaco Grand Prix': {'min': 16, 'max': 28, 'default': 22},      # May, mild Mediterranean weather
    'British Grand Prix': {'min': 14, 'max': 26, 'default': 20},     # July, UK climate
}


# Start screen: show intro and collect race setup options.
if not st.session_state.race_started:
    st.write('You are now in the seat of the F1 race strategist!')
    
    train_models() 

    # --- TEAM SELECTION ---
    # Call your new function. It will draw the UI and give you the chosen team!
    team_player = render_team_selector() 

    # --- TRACK AND TIRE SELECTION ---
    st.write("### 🛠️ Race Parameters")
    col_track, col_start_tire, col_target_tire = st.columns(3)
    
    with col_track:
        st.session_state.track = st.selectbox('Select the track:', 
                                             ['Monaco Grand Prix', 'British Grand Prix'])
    
    with col_start_tire:
        # Key 'start_tire' ensures this value is saved in session state
        tire_start = st.radio('Starting Tire:', ['SOFT', 'MEDIUM', 'HARD'], key="start_tire")
    
    with col_target_tire:
        # This is the tire the AI will calculate for the second stint
        target_tire = st.radio('Target Pit Tire:', ['SOFT', 'MEDIUM', 'HARD'], index=2, key="target_tire")
    
    # When the Start Button is clicked, save these to the session state
    if st.button('Start the simulation', use_container_width=True):
        st.session_state.race_started = True
  


    # Temperature slider with track-specific ranges
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

   # --- NEW ML STRATEGIST WINDOW HERE ---
    # Determine the laps for the AI simulation before the race starts
    sim_laps = 78 if st.session_state.track == 'Monaco Grand Prix' else 52
    
    with st.expander("🏎️ ML Strategist Briefing", expanded=True):
        st.write("Let our AI simulate the race to find your mathematically fastest pit stop strategy!")
        
        if st.button("Ask the AI for the Optimal Pit Lap", use_container_width=True):
            with st.spinner("Simulating multi-compound race times..."):
                try:
                    # --- STEP 3 INTEGRATED HERE ---
                    best_lap = find_optimal_pit_lap(
                        track_name=st.session_state.track, 
                        total_laps=sim_laps,             
                        team=team_player, 
                        start_compound=tire_start, 
                        next_compound=target_tire, # Now uses the tire they chose from the menu!
                        air_temp=st.session_state.air_temp 
                    )
                    
                    # Updated success message to show the tire switch
                    st.success(f"**Optimal Strategy Found:** Pit on Lap {best_lap} to switch from {tire_start} to {target_tire}s!")
                    
                    # --- DYNAMIC EXPLANATION SECTION ---
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
    # -------------------------------------

    # Build the correct car object based on track and begin the race loop.
    if st.button('Start the simulation'):
        st.session_state.race_started = True
        if st.session_state.track == 'Monaco Grand Prix':
            st.session_state.player = Car(team_player, 'Monaco Grand Prix', tire_start) # create an instance for Monaco
            st.session_state.total_laps = 78 # set total laps for Monaco
        elif st.session_state.track == 'British Grand Prix':
            st.session_state.player = Car(team_player, 'British Grand Prix', tire_start) # create an instance for Silverstone
            st.session_state.total_laps = 52 # set total laps for Silverstone
        st.session_state.opponents = create_opponents(team_player, st.session_state.track, st.session_state.total_laps)
        st.rerun(scope='app')

# Race screen: show selected options and advance race state lap by lap.
if st.session_state.race_started:
    write_chosen_options()
    race_simulation()

    # Mid-race ML strategist: allow re-running the optimizer during the race
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

