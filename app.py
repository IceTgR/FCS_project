import streamlit as st
import pandas as pd
from feature_01 import write_chosen_options, race_simulation
from car import Car
from InterfaceDM import main

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



    # User input for driver, track, and starting tire, which is needed to start the simulation
    col1, col2, col3 = st.columns(3)
    team_player = col1.selectbox('Select your team:', ['Ferrari', 'Mercedes', 'Red Bull', 'McLaren', 'Williams'])

    st.session_state.track = col2.selectbox('Select the track:', ['Monaco Grand Prix', 'British Grand Prix'])

    tire_start = col3.radio('Choose your starting tire:', ['SOFT', 'MEDIUM', 'HARD'])

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
    write_chosen_options()
    race_simulation()

