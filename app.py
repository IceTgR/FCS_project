import streamlit as st
from strategy_optimizer import find_optimal_pit_lap
from streamlit_option_menu import option_menu
import pandas as pd
import os
from feature_01 import write_chosen_options, race_simulation
from car import Car
# from InterfaceDM import main
from train_models import train_models

#main()

# Track whether the simulation has been started in the current Streamlit session.
if 'race_started' not in st.session_state: # to check if race has started, if not, initialize it to False
    st.session_state.race_started = False

st.title('F1 Race Strategy Simulator')

# Start screen: show intro and collect race setup options.
if not st.session_state.race_started:
    st.write(f'You are now in the seat of the F1 race strategist for Ferrari!\n'
         f'Prepare yourself to make crucial decisions on pit stops, tire choices, and '
         f'guide your driver to victory!')
    
   #daten laden und modell trainieren, falls noch nicht vorhanden
    train_models() 

    # User input for driver, track, and starting tire, which is needed to start the simulation
    col1, col2, col3 = st.columns(3)
    team_player = col1.selectbox('Select your team:', ['Ferrari', 'Mercedes', 'Red Bull', 'McLaren', 'Williams'])


    
    st.session_state.track = col2.selectbox('Select the track:', ['Monaco Grand Prix', 'British Grand Prix'])
    tire_start = col3.radio('Choose your starting tire:', ['SOFT', 'MEDIUM', 'HARD'])

    # --- NEW ML STRATEGIST WINDOW HERE ---
    # Determine the laps for the AI simulation before the race starts
    sim_laps = 78 if st.session_state.track == 'Monaco Grand Prix' else 52
    
    with st.expander("🏎️ ML Strategist Briefing", expanded=True):
        st.write("Let our AI simulate the race to find your mathematically fastest pit stop strategy!")
        
 
        
    if st.button("Ask the AI for the Optimal Pit Lap"):
        with st.spinner("Simulating race times..."):
            try:
                best_lap = find_optimal_pit_lap(
                    track_name=st.session_state.track, 
                    total_laps=sim_laps,             
                    team=team_player, 
                    start_compound=tire_start, 
                    next_compound='HARD',
                    air_temp=25.0, 
                    pit_window_start=10, 
                    pit_window_end=sim_laps - 15
                )
                
                st.success(f"**Optimal Strategy Found:** The AI recommends pitting on Lap {best_lap}!")
                
                # --- DYNAMIC EXPLANATION SECTION ---
                st.markdown("### 💡 Why this lap?")
                
                if team_player in ['Red Bull', 'Mercedes']:
                    st.info(f"**Efficiency Profile:** {team_player} historically shows better tire management. The AI suggests pushing until Lap {best_lap} because your car maintains pace even as the rubber thins, allowing for a shorter, faster final stint.")
                elif team_player in ['Ferrari', 'McLaren']:
                    st.info(f"**Performance Peak:** {team_player} has high peak grip but faster drop-off. Pitting on Lap {best_lap} avoids the 'cliff' where your lap times would collapse, ensuring you switch to fresh Hards right as your Softs lose their edge.")
                else:
                    st.info(f"**Risk Mitigation:** For {team_player}, the AI prioritizes track position. Pitting on Lap {best_lap} minimizes the time spent on degraded tires where your car is most vulnerable to being overtaken.")

            except FileNotFoundError:
                st.error("Model not found! Make sure to click 'Train Models Now' first.")
            except Exception as e:
                st.error(f"An error occurred: {e}")
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
        st.rerun(scope='app')


# Race screen: show selected options and advance race state lap by lap.
if st.session_state.race_started:
    # --- ADD THIS CHECK HERE ---
    if 'player' in st.session_state:
        with st.sidebar:
            st.header("🎧 Pit Wall Radio")
            
            # Use current lap from the player object safely
            # Note: Verify if your Car class uses 'lap_count' or 'current_lap'
            current_lap = st.session_state.player.lap_count 
            
            if 'ideal_lap' not in st.session_state:
                with st.spinner("AI is calculating the optimal path..."):
                    st.session_state.ideal_lap = find_optimal_pit_lap(
                        track_name=st.session_state.track,
                        total_laps=st.session_state.total_laps,
                        team=st.session_state.player.team,
                        start_compound=st.session_state.player.tire,
                        next_compound='HARD',
                        air_temp=25.0,
                        pit_window_start=10,
                        pit_window_end=st.session_state.total_laps - 10
                    )
            
            st.subheader("🤖 ML Strategist Advice")
            st.info(f"**Ideal Pit Lap: {st.session_state.ideal_lap}**")
            st.write(f"Current Lap: {current_lap}")

    # Standard simulation calls
    write_chosen_options()
    race_simulation()


