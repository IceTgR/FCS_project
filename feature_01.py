# this is the feature that runs the simulation

def write_chosen_options():
    st.write(f'You have selected {st.session_state.player.driver} as your driver, '
        f'starting on {st.session_state.player.tire} tires at the {track} track.')



