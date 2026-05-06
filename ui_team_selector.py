# Team-Auswahl Interface mit farbigen Team-Buttons.
import streamlit as st

def render_team_selector():
    """Rendert interaktive Team-Auswahl mit 5 F1-Teams."""
    st.write("### 🏎️ Wähle dein Team")
    
    # F1 Team Farben als Hex-Codes
    team_colors = {
        "Ferrari": "#DC0000",       # Ferrari Rot
        "Red Bull": "#121F45",      # Dunkles Navy Blau
        "Mercedes": "#00A19C",      # Petronas Türkis
        "McLaren": "#FF8000",       # Papaya Orange
        "Williams": "#005AFF",      # Helles True Blau
    }

    # Initialisiere ausgewähltes Team im Session State
    if 'team_player' not in st.session_state:
        st.session_state.team_player = "Ferrari" 

    teams = list(team_colors.keys())
    
    # Erstelle eine Reihe mit 5 Teams
    cols = st.columns(5)
    for i in range(5):
        team = teams[i]
        color = team_colors[team]
        with cols[i]:
            # 1. Farbiger Box für Team-Name (HTML)
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
            
            # 2. Auswahl-Button (zeigt Checkmark oder Team-Name)
            if st.session_state.team_player == team:
                st.button("✅ Ausgewählt", key=f"btn_{team}", disabled=True, use_container_width=True)
            else:
                if st.button("Wählen", key=f"btn_{team}", use_container_width=True):
                    st.session_state.team_player = team
                    st.rerun() # Refresh immediately to show the checkmark

    st.markdown("---")
    
    # Das gewählte Team zurückgeben, damit app.py es verwenden kann
    return st.session_state.team_player
