# this is the feature that runs the simulation
import random

import streamlit as st
import pandas as pd
from car import Car


def roll_safety_event(car):
    """Randomly assign a race control event without changing lap time yet."""
    event_roll = random.random()

    if event_roll < 0.015:
        car.safety_event_status = 'SAFETYCAR'
    elif event_roll < 0.04:
        car.safety_event_status = 'VSC'
    else:
        car.safety_event_status = None
    return car.safety_event_status

# Show the fixed choices made before the race starts.
def write_chosen_options():
    st.write(f'You have selected {st.session_state.player.team} as your team, '
        f'starting on {st.session_state.player.tire} tires at the {st.session_state.track} track.')
    
def race_simulation():
    # Display the current race status at the top of the screen.
    st.write(f'Last lap time: {st.session_state.player.lap_time if st.session_state.player.lap > 1 else 'this your first lap'}\n'
            f'Current lap: {st.session_state.player.lap if st.session_state.player.lap <= st.session_state.total_laps else 'finished'}')

    current_event = st.session_state.player.safety_event_status
    if current_event == 'SAFETYCAR':
        st.warning('Safety Car deployed.')
    elif current_event == 'VSC':
        st.info('Virtual Safety Car active.')

    # End-of-race checks.
    if st.session_state.player.lap == st.session_state.total_laps + 1:
        if st.session_state.player.pitstop_counter == 0:
            st.write('You have been disqualified for not making a pit stop!')
        else:
            st.write('Congratulations, you have finished the race!')

    else:
        # Compute the lap time before the user chooses an action.
        st.session_state.player.predict_lap_time()
    
        # Continue without pitting.
        if st.button('Stay Out'):
            roll_safety_event(st.session_state.player)
            st.session_state.player.advance_lap()
            st.rerun(scope = 'app')

        # Let user pick next tire compound for an optional pit stop.
        new_tire = st.radio('Choose your tire incase you want to pit', ['SOFT', 'MEDIUM', 'HARD'])
        # Enter pit lane and switch to the selected tire.
        if st.button('Pit Stop'):
            roll_safety_event(st.session_state.player)
            st.session_state.player.box(new_tire)
            st.rerun(scope = 'app')

    # Show race data in table and chart form.
    st.subheader('Race History')
    history = pd.DataFrame(st.session_state.player.race_history, columns=['Lap', 'Lap Time', 'Tire', 'Tire Age', 'Rundenart', 'Kommentar'])

    st.metric('Lap Time Development', (f"{st.session_state.player.race_history[-1]['Lap Time']:.2f} seconds" if st.session_state.player.lap > 1 else 0),
            delta = ((st.session_state.player.race_history[-1]['Lap Time'] - st.session_state.player.race_history[-2]['Lap Time']) if st.session_state.player.lap > 2 else 'n.a.'),
            chart_data = history['Lap Time'], chart_type = 'line', border = True, delta_color = 'inverse')
    
    st.table(history) if st.session_state.player.lap > 1 else st.write('No history yet, this is your first lap!')


    



