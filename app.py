import streamlit as st
from feature_01 import write_chosen_options
from car import Car
from car_monaco import Car_Monaco

if 'race_started' not in st.session_state: # to check if race has started, if not, initialize it to False
    st.session_state.race_started = False

st.title('F1 Race Strategy Simulator')

if not st.session_state.race_started:
    st.write(f'You are now in the seat of the F1 race strategist for Ferrari!\n'
         f' Prepare yourself to make crucial decisions on pit stops, tire choices, and '
         f'guide your driver to victory!')



    # User input for driver, track, and starting tire, which is needed to start the simulation
    col1, col2, col3 = st.columns(3)
    driver_player = col1.selectbox('Select your driver:', ['Lewis Hamilton', 'Charles Leclerc'])

    st.session_state.track = col2.selectbox('Select the track:', ['Monaco', 'Silverstone'])

    tire_start = col3.radio('Choose your starting tire:', ['soft', 'medium', 'hard'])

    if st.button('Start the simulation'):
        st.session_state.race_started = True
        if st.session_state.track == 'Monaco':
            st.session_state.player = Car_Monaco(driver_player, tire_start) # create an instance for Monaco
        elif st.session_state.track == 'Silverstone':
            st.session_state.player = Car(driver_player, tire_start) # create an instance for Silverstone
        st.rerun

if st.session_state.race_started:
    write_chosen_options()

