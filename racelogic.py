# this is the feature that runs the simulation
import random

import streamlit as st
import pandas as pd
from car import Car
from opponents import advance_opponents, build_opponent_table


def roll_safety_event():
    """Start a new safety event if no event is currently active.
    
    Duration handling happens after the lap is stored so the current lap can
    still see the event that was active while it was driven.
    """
    if not hasattr(st.session_state, 'safety_event_duration'):
        st.session_state.safety_event_duration = 0
    if not hasattr(st.session_state, 'safety_event_status'):
        st.session_state.safety_event_status = None

    if st.session_state.safety_event_status is not None:
        return

    event_roll = random.random()

    if event_roll < 0.015:
        st.session_state.safety_event_status = 'SAFETYCAR'
        st.session_state.safety_event_duration = random.randint(3, 6)
    elif event_roll < 0.04:
        st.session_state.safety_event_status = 'VSC'
        st.session_state.safety_event_duration = random.randint(2, 4)
    else:
        st.session_state.safety_event_status = None
        st.session_state.safety_event_duration = 0


def resolve_safety_event():
    """Count down the active safety event after a lap has been recorded."""
    if st.session_state.safety_event_status is None:
        return

    if st.session_state.safety_event_duration > 0:
        st.session_state.safety_event_duration -= 1

    if st.session_state.safety_event_duration == 0:
        st.session_state.safety_event_status = None


def get_safety_event_lap_multiplier():
    """Return a lap-time multiplier for the active safety event."""
    current_event = st.session_state.safety_event_status if hasattr(st.session_state, 'safety_event_status') else None

    if current_event == 'SAFETYCAR':
        return 1.65
    if current_event == 'VSC':
        return 1.30
    return 1.0


def get_safety_event_pitstop_multiplier():
    """Return a pit-stop multiplier for the active safety event."""
    current_event = st.session_state.safety_event_status if hasattr(st.session_state, 'safety_event_status') else None

    if current_event == 'SAFETYCAR':
        return 0.58
    if current_event == 'VSC':
        return 0.78
    return 1.0


def apply_safety_event_effect(car):
    """Apply the current race-control effect to the predicted lap time."""
    car.lap_time *= get_safety_event_lap_multiplier()

# Show the fixed choices made before the race starts.
def write_chosen_options():
    st.write(f'You have selected {st.session_state.player.team} as your team, '
        f'starting on {st.session_state.player.tire} tires at the {st.session_state.track} track.')
    if hasattr(st.session_state, 'opponents'):
        st.write(f'The field now contains {len(st.session_state.opponents)} AI opponents.')
    
def race_simulation():
    # Display the current race status at the top of the screen.
    st.write(f'Last lap time: {st.session_state.player.lap_time if st.session_state.player.lap > 1 else 'this your first lap'}\n'
            f'Current lap: {st.session_state.player.lap if st.session_state.player.lap <= st.session_state.total_laps else 'finished'}')

    current_event = st.session_state.safety_event_status if hasattr(st.session_state, 'safety_event_status') else None
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
            roll_safety_event()
            apply_safety_event_effect(st.session_state.player)
            st.session_state.player.advance_lap(st.session_state.safety_event_status)
            if hasattr(st.session_state, 'opponents'):
                advance_opponents(
                    st.session_state.opponents,
                    st.session_state.total_laps,
                    st.session_state.safety_event_status,
                    get_safety_event_lap_multiplier(),
                    get_safety_event_pitstop_multiplier(),
                )
            resolve_safety_event()
            st.rerun(scope = 'app')

        # Let user pick next tire compound for an optional pit stop.
        new_tire = st.radio('Choose your tire incase you want to pit', ['SOFT', 'MEDIUM', 'HARD'])
        # Enter pit lane and switch to the selected tire.
        if st.button('Pit Stop'):
            roll_safety_event()
            apply_safety_event_effect(st.session_state.player)
            st.session_state.player.box(
                new_tire,
                st.session_state.safety_event_status,
                pitstop_multiplier=get_safety_event_pitstop_multiplier(),
            )
            if hasattr(st.session_state, 'opponents'):
                advance_opponents(
                    st.session_state.opponents,
                    st.session_state.total_laps,
                    st.session_state.safety_event_status,
                    get_safety_event_lap_multiplier(),
                    get_safety_event_pitstop_multiplier(),
                )
            resolve_safety_event()
            st.rerun(scope = 'app')

    # Show race data in table and chart form.
    st.subheader('Race History')
    history = pd.DataFrame(st.session_state.player.race_history, columns=['Lap', 'Lap Time', 'Tire', 'Tire Age', 'Kommentar'])

    st.metric('Lap Time Development', (f"{st.session_state.player.race_history[-1]['Lap Time']:.2f} seconds" if st.session_state.player.lap > 1 else 0),
            delta = ((st.session_state.player.race_history[-1]['Lap Time'] - st.session_state.player.race_history[-2]['Lap Time']) if st.session_state.player.lap > 2 else 'n.a.'),
            chart_data = history['Lap Time'], chart_type = 'line', border = True, delta_color = 'inverse')
    
    st.table(history) if st.session_state.player.lap > 1 else st.write('No history yet, this is your first lap!')

    if hasattr(st.session_state, 'opponents'):
        st.subheader('Opponents')
        opponent_history = pd.DataFrame(build_opponent_table(st.session_state.opponents, st.session_state.total_laps))
        st.table(opponent_history)


    



