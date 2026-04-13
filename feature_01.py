# this is the feature that runs the simulation
import streamlit as st
import pandas as pd
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
        if st.session_state.player.pitstop_counter == 0:
            st.write('You have been disqualified for not making a pit stop!')
        else:
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

    st.subheader('Race History')
    history = pd.DataFrame(st.session_state.player.race_history, columns=['Lap', 'Lap Time', 'Tire', 'Tire Age', 'Pitstop'])

    st.metric('Lap Time Development', (f"{st.session_state.player.race_history[-1]['Lap Time']:.2f} seconds" if st.session_state.player.lap > 1 else 0),
            delta = ((st.session_state.player.race_history[-1]['Lap Time'] - st.session_state.player.race_history[-2]['Lap Time']) if st.session_state.player.lap > 2 else 'n.a.'),
            chart_data = history['Lap Time'], chart_type = 'line', border = True, delta_color = 'inverse')
    
    st.table(history) if st.session_state.player.lap > 1 else st.write('No history yet, this is your first lap!')


    



