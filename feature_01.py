# this is the feature that runs the simulation
import streamlit as st
from car import Car
from car_monaco import Car_Monaco
from car_silverstone import Car_Silverstone

def write_chosen_options():
    st.write(f'You have selected {st.session_state.player.driver} as your driver, '
        f'starting on {st.session_state.player.tire} tires at the {st.session_state.track} track.')
    
def race_simulation():
    if 'lap' not in st.session_state:
        st.session_state.lap = 1
    st.session_state.player.calculate_lap_time()
    st.write(f'Current lap time: {st.session_state.player.lap_time}'
             f'Laps completed: {st.session_state.lap - 1}')
    
    if st.button('Next Lap'):
        st.session_state.player.tire_age += 1
        st.session_state.lap += 1
        st.rerun(scope = 'app')




