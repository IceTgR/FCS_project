# Teamauswahl Interface mit farbigen Buttons.
import streamlit as st

def render_team_selector():
    """Rendert interaktive Team-Auswahl mit 5 F1-Teams."""
    st.write("### 🏎️ Wähle dein Team")
    
    # F1-Teamfarben als Hex-Codes.
    team_colors = {
        "Ferrari": "#DC0000",       # Ferrari Rot
        "Red Bull": "#121F45",      # Dunkles Navy Blau
        "Mercedes": "#00A19C",      # Petronas Türkis
        "McLaren": "#FF8000",       # Papaya Orange
        "Williams": "#005AFF",      # Helles True Blau
    }

    # Gewähltes Team im Session-State initialisieren.
    if 'team_player' not in st.session_state:
        st.session_state.team_player = "Ferrari" 

    teams = list(team_colors.keys())
    
    # Eine Reihe mit 5 Teams erstellen.
    cols = st.columns(5)
    for i in range(5):
        team = teams[i]
        color = team_colors[team]
        with cols[i]:
            # 1. Farbige Box für den Teamnamen (HTML).
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
            
            # 2. Auswahl-Button (Haken oder Teamname).
            if st.session_state.team_player == team:
                st.button("✅ Ausgewählt", key=f"btn_{team}", disabled=True, use_container_width=True)
            else:
                if st.button("Wählen", key=f"btn_{team}", use_container_width=True):
                    st.session_state.team_player = team
                    st.rerun() # Sofort neu laden, damit der Haken erscheint.

    st.markdown("---")
    
    # Gewähltes Team für app.py zurückgeben.
    return st.session_state.team_player
