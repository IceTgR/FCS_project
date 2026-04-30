import streamlit as st

def render_team_selector():
    st.write("### 🏎️ Select Your Team")
    
    # F1 Team Hex Colors (Optimized so white text remains readable)
    team_colors = {
        "Ferrari": "#DC0000",       # Ferrari Red
        "Red Bull": "#1E41FF",      # Racing Blue
        "Mercedes": "#00A19C",      # Petronas Teal
        "McLaren": "#FF8000",       # Papaya Orange
        "Aston Martin": "#229971",  # British Racing Green
        "Alpine": "#0090FF",        # French Blue
        "Williams": "#005AFF",      # Deep Blue
        "RB": "#00293F",            # Visa Cash App Dark Blue
        "Sauber": "#000000",        # Black (Neon green is unreadable with white text)
        "Haas": "#333333"           # Dark Grey
    }

    # Initialize the selected team in session state if it doesn't exist
    if 'team_player' not in st.session_state:
        st.session_state.team_player = "Ferrari" 

    teams = list(team_colors.keys())
    
    # Create the first row of 5 teams
    cols1 = st.columns(5)
    for i in range(5):
        team = teams[i]
        color = team_colors[team]
        with cols1[i]:
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
                st.button("✅ Selected", key=f"btn_{team}", disabled=True, use_container_width=True)
            else:
                if st.button("Select", key=f"btn_{team}", use_container_width=True):
                    st.session_state.team_player = team
                    st.rerun() # Refresh immediately to show the checkmark

    # Add a little breathing room between rows
    st.write("") 
    
    # Create the second row of 5 teams
    cols2 = st.columns(5)
    for i in range(5, 10):
        team = teams[i]
        color = team_colors[team]
        with cols2[i-5]:
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
            
            if st.session_state.team_player == team:
                st.button("✅ Selected", key=f"btn_{team}", disabled=True, use_container_width=True)
            else:
                if st.button("Select", key=f"btn_{team}", use_container_width=True):
                    st.session_state.team_player = team
                    st.rerun()

    st.markdown("---")
    
    # Return the chosen team so app.py can use it
    return st.session_state.team_player
