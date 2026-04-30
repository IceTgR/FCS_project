import streamlit as st

def render_team_selector():
    """Renders the 5 team buttons and returns the selected team."""
    
    st.write("### 🏎️ Choose Your Constructor")
    teams = ['Ferrari', 'Mercedes', 'Red Bull', 'McLaren', 'Williams']
    team_cols = st.columns(5)
    
    # Initialize default team
    if 'selected_team' not in st.session_state:
        st.session_state.selected_team = 'Ferrari'

    # Generate the buttons
    for i, team in enumerate(teams):
        with team_cols[i]:
            if st.button(team, key=f"btn_{team}", use_container_width=True):
                st.session_state.selected_team = team
                st.rerun()

    # Display selection
    team_player = st.session_state.selected_team
    st.info(f"Currently selected: **{team_player}**")
    st.divider()
    
    # Return the selected team back to app.py
    return team_player
