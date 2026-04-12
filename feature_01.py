# this is the feature that runs the simulation
import streamlit as st
from car import Car
from car_monaco import Car_Monaco
from car_silverstone import Car_Silverstone

def write_chosen_options():
    st.write(f'You have selected {st.session_state.player.driver} as your driver, '
        f'starting on {st.session_state.player.tire} tires at the {st.session_state.track} track.')
    
def race_simulation():
    st.write(f'Last lap time: {st.session_state.player.lap_time if st.session_state.player.lap > 1 else 'this your first lap'}\n'
            f'Current lap: {st.session_state.player.lap if st.session_state.player.lap <= st.session_state.total_laps else 'finished'}')
    
    if st.session_state.player.lap == st.session_state.total_laps + 1:
        st.write('Congratulations, you have finished the race!')

    else:
        st.session_state.player.calculate_lap_time()
    
        if st.button('Stay Out'):
            st.session_state.player.advance_lap()
            st.rerun(scope = 'app')

        new_tire = st.radio('Choose your tire incase you want to pit', ['soft', 'medium', 'hard'])
        if st.button('Pit Stop'):
            st.session_state.player.box(new_tire)
            st.rerun(scope = 'app')




