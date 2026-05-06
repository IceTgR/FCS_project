import streamlit as st

def render_team_selector():
    st.write("### 🏎️ Wähle dein Team")
    
    # F1 Team Hex Colors 
    team_colors = {
        "Ferrari": "#DC0000",       # Ferrari Red
        "Red Bull": "#121F45",      # Dark Navy Blue
        "Mercedes": "#00A19C",      # Petronas Teal
        "McLaren": "#FF8000",       # Papaya Orange
        "Williams": "#005AFF",      # Bright True Blue
    }

    # Initialize the selected team in session state if it doesn't exist
    if 'team_player' not in st.session_state:
        st.session_state.team_player = "Ferrari" 

    teams = list(team_colors.keys())
    
    # Create a single row of 5 teams
    cols = st.columns(5)
    for i in range(5):
        team = teams[i]
        color = team_colors[team]
        with cols[i]:
            # 1. The custom colored box (HTML)
            st.markdown(f"""
            <div style="
                background-color: {color};
                padding: 15px 5px;
                border-radius: 8px;
                text-align: center;
                color: white;
                font-weight: bold;
                margin-bottom: 10px;
                height: 55px;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            ">
                {team}
            </div>
            """, unsafe_allow_html=True)
            
            # 2. The selection button
            if st.session_state.team_player == team:
                st.button("✅ Ausgewählt", key=f"btn_{team}", disabled=True, use_container_width=True)
            else:
                if st.button("Wählen", key=f"btn_{team}", use_container_width=True):
                    st.session_state.team_player = team
                    st.rerun() # Refresh immediately to show the checkmark

    st.markdown("---")
    
    # Das gewählte Team zurückgeben, damit app.py es verwenden kann
    return st.session_state.team_player
