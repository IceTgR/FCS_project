import streamlit as st
import logging
from strategy_optimizer import find_optimal_pit_lap
import pandas as pd
import os
from racelogic import write_chosen_options, race_simulation
from car import Car
from opponents import create_opponents
from train_models import ensure_ml_assets, TRACK_LIST
from ui_team_selector import render_team_selector

_FASTF1_LOGGER_NAMES = (
    'fastf1',
    'fastf1.fastf1',
    'fastf1.fastf1.core',
    'fastf1.fastf1.req',
    'fastf1.fastf1.api',
    'fastf1.fastf1.utils',
    'fastf1.core',
    'fastf1.req',
    'fastf1.api',
    'fastf1.utils',
)

# --- 1. SEITENKONFIGURATION ---
st.set_page_config(layout="wide")

# Session-State für Seitenwechsel initialisieren.
if 'race_started' not in st.session_state: 
    st.session_state.race_started = False

if 'ml_bootstrap_done' not in st.session_state:
    placeholder = st.empty()

    # Drosseln der FastF1-Logger auf WARNING, um die Ausgabe im Terminal zu reduzieren
    for logger_name in _FASTF1_LOGGER_NAMES:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    def _render_bootstrap_warning():
        context_msg = st.session_state.get('ml_bootstrap_rate_limit_context')
        retry_msg = st.session_state.get('ml_bootstrap_rate_limit_retry')
        if context_msg and retry_msg:
            placeholder.warning(f"{context_msg}\n\n{retry_msg}")
        elif context_msg:
            placeholder.warning(context_msg)
        elif retry_msg:
            placeholder.warning(retry_msg)
        else:
            placeholder.empty()

    def _progress_cb(msg: str):
        try:
            if msg == '__FASTF1_RATE_LIMIT_RECOVERED__':
                st.session_state.ml_bootstrap_rate_limit_context = None
                st.session_state.ml_bootstrap_rate_limit_retry = None
                _render_bootstrap_warning()
                return
            if msg.startswith('FastF1 API-Rate-Limit erreicht beim '):
                st.session_state.ml_bootstrap_rate_limit_context = msg
                _render_bootstrap_warning()
            elif msg.startswith('Wartezeit bis zum nächsten Retry: '):
                st.session_state.ml_bootstrap_rate_limit_retry = msg
                _render_bootstrap_warning()
        except Exception:
            pass

    with st.spinner('Vorbereitung von Daten und ML-Modellen beim ersten Start (dies kann einige Minuten dauern)...'):
        try:
            st.session_state.ml_bootstrap_status = ensure_ml_assets(progress_callback=_progress_cb)
        except TypeError as exc:
            if 'progress_callback' not in str(exc):
                raise
            st.session_state.ml_bootstrap_status = ensure_ml_assets()

    st.session_state.ml_bootstrap_done = True

    # Leere die Ladewarnung, damit sie sofort verschwindet
    placeholder.empty()
    st.session_state.ml_bootstrap_rate_limit_context = None
    st.session_state.ml_bootstrap_rate_limit_retry = None

    bootstrap_status = st.session_state.ml_bootstrap_status
    status_lines = []
    if bootstrap_status['created_db']:
        status_lines.append('Datenbank erstellt')
    elif os.path.exists('f1_project.db'):
        status_lines.append('Datenbank bereit')

    if bootstrap_status['trained_models']:
        status_lines.append('Modelle trainiert')
    else:
        # Überprüfe, ob alle neuen Modelle vorhanden sind
        all_models_exist = all(os.path.exists(f"models/dry/rf_{track.replace(' ', '_')}.pkl") for track in TRACK_LIST)
        if all_models_exist:
            status_lines.append('Modelle bereit')

    if status_lines:
        st.info('ML-Einrichtung: ' + ' | '.join(status_lines))

    # Falls Rate-Limit auftrat, den User informieren
    if bootstrap_status.get('rate_limited'):
        wait_s = bootstrap_status.get('rate_limit_wait', 0)
        if wait_s >= 3600:
            wait_text = f"ca. {wait_s // 3600} Stunde(n)"
        elif wait_s >= 60:
            wait_text = f"ca. {wait_s//60} Minuten"
        elif wait_s > 0:
            wait_text = f"ca. {wait_s} Sekunden"
        else:
            wait_text = "die genaue Wartezeit ist unbekannt"
        st.warning(
            "FastF1 API-Rate-Limit erreicht beim Laden externer Daten. "
            f"Das Bootstrapping läuft weiter. Wartezeit bis zum nächsten Retry: {wait_text}. "
            "Im schlimmsten Fall kann FastF1 bis zu etwa 1 Stunde blockieren."
        )

    # Ausgabe der MAE-Ergebnisse explizit in die Konsole/Terminal
    try:
        logging.basicConfig(level=logging.INFO)
        for logger_name in _FASTF1_LOGGER_NAMES:
            logging.getLogger(logger_name).setLevel(logging.WARNING)
        results = bootstrap_status.get('results')
        if results:
            for track, mae in results.items():
                logging.info(f'MAE für {track}: {mae:.3f} Sekunden')
    except Exception:
        pass

st.title('F1 Rennstrategie-Simulator')

# Streckenspezifische Temperaturbereiche und Runden.
TRACK_TEMP_RANGES = {
    'Abu Dhabi Grand Prix': {'min': 20, 'max': 32, 'default': 26},      
    'Austrian Grand Prix': {'min': 12, 'max': 28, 'default': 20},
    'Belgian Grand Prix': {'min': 10, 'max': 22, 'default': 16},      
    'British Grand Prix': {'min': 14, 'max': 26, 'default': 20},     
    'Hungarian Grand Prix': {'min': 14, 'max': 30, 'default': 22},
    'Italian Grand Prix': {'min': 14, 'max': 28, 'default': 21},
}

TRACK_LAP_COUNTS = {
    'Abu Dhabi Grand Prix': 58,
    'Austrian Grand Prix': 71,
    'Belgian Grand Prix': 44,
    'British Grand Prix': 52,
    'Hungarian Grand Prix': 70,
    'Italian Grand Prix': 53,
}

# ==========================================
# 🚪 SEITE 1: HAUPTMENÜ (Konfiguration)
# ==========================================
if not st.session_state.race_started:
    st.write('Du bist jetzt in der Position eines F1-Rennstrategen!')

    # --- TEAMAUSWAHL ---
    team_player = render_team_selector() 

    # --- STRECKEN- UND REIFENAUSWAHL ---
    st.write("### 🛠️ Rennparameter")
    col_track, col_start_tire, col_target_tire = st.columns(3)
    
    with col_track:
        st.session_state.track = st.selectbox('Strecke wählen:', 
                                             ['Abu Dhabi Grand Prix', 'Austrian Grand Prix', 'Belgian Grand Prix', 'British Grand Prix', 'Hungarian Grand Prix', 'Italian Grand Prix'])
    
    with col_start_tire:
        tire_start = st.radio('Startreifen:', ['SOFT', 'MEDIUM', 'HARD'], key="start_tire")
    
    with col_target_tire:
        target_tire = st.radio('Zielreifen:', ['SOFT', 'MEDIUM', 'HARD'], index=2, key="target_tire")

    # --- TEMPERATUR-SLIDER ---
    st.markdown("---")
    track_temps = TRACK_TEMP_RANGES.get(st.session_state.track, {'min': 15, 'max': 30, 'default': 22})
    air_temp = st.slider(
        '🌡️ Lufttemperatur (°C)',
        min_value=track_temps['min'],
        max_value=track_temps['max'],
        value=track_temps['default'],
        step=1,
        help=f"Stelle die Umgebungstemperatur für {st.session_state.track} ein. Typische Bedingungen liegen zwischen {track_temps['min']}°C und {track_temps['max']}°C."
    )
    st.session_state.air_temp = air_temp

    # --- KI-STRATEGE: VORBESPRECHUNG ---
    sim_laps = TRACK_LAP_COUNTS.get(st.session_state.track, 52)
    
    with st.expander("🏎️ KI-Stratege Briefing", expanded=True):
        st.write("Lass die KI das Rennen simulieren, um deine mathematisch schnellste Boxenstrategie zu finden!")
        
        if st.button("KI nach optimalem Boxenstopp fragen", use_container_width=True):
            with st.spinner("Simuliere Multi-Compound-Rundenzeiten..."):
                try:
                    best_lap = find_optimal_pit_lap(
                        track_name=st.session_state.track, 
                        total_laps=sim_laps,             
                        team=team_player, 
                        start_compound=tire_start, 
                        next_compound=target_tire, 
                        air_temp=st.session_state.air_temp 
                    )
                    
                    st.success(f"**Optimale Strategie gefunden:** Boxenstopp in Runde {best_lap} um von {tire_start} zu {target_tire} zu wechseln!")
                    
                    st.markdown("### 💡 Warum diese Runde?")
                    if team_player in ['Red Bull', 'Mercedes']:
                        st.info(f"**Effizienzprofil:** {team_player} zeigt historisch ein besseres Reifenmanagement. Die KI schlägt vor, bis Runde {best_lap} zu drücken, da dein Auto das Tempo hält, auch wenn die Reifen verschleißen, was einen kürzeren und schnelleren Endstoß ermöglicht.")
                    elif team_player in ['Ferrari', 'McLaren']:
                        st.info(f"**Performance-Peak:** {team_player} hat hohe Spitzenkraft, aber schnelleren Abfall. Ein Boxenstopp in Runde {best_lap} vermeidet die 'Klippe', wo deine Rundenzeiten zusammenbrechen würden, und sichert einen Wechsel zu frischen {target_tire}n ab, wenn deine {tire_start}s ihre Wirkung verlieren.")
                    else:
                        st.info(f"**Risikominderung:** Für {team_player} priorisiert die KI Rennposition. Ein Boxenstopp in Runde {best_lap} minimiert die Zeit auf verschlissenen Reifen, wo dein Auto am anfälligsten ist, überholt zu werden.")

                except FileNotFoundError:
                    st.error("Modell nicht gefunden. App neu laden, damit der Start-Bootstrap abgeschlossen wird.")
                except Exception as e:
                    st.error(f"Ein Fehler während der Simulation ist aufgetreten: {e}")

    # --- STARTBUTTON ---
    st.markdown("---")
    if st.button('🏁 Simulation starten', type="primary", use_container_width=True):
        # 1. Rennen als gestartet markieren.
        st.session_state.race_started = True
        
        # 2. Spielerauto erstellen und Rundenzahl setzen.
        st.session_state.player = Car(team_player, st.session_state.track, tire_start) 
        st.session_state.total_laps = TRACK_LAP_COUNTS.get(st.session_state.track, 52) 
            
        # 3. Gegner erstellen.
        st.session_state.opponents = create_opponents(team_player, st.session_state.track, st.session_state.total_laps)
        
        # 4. Neu laden und direkt zu Seite 2 wechseln.
        st.rerun()


# ==========================================
# 🚪 SEITE 2: DIE SIMULATION (Rennansicht)
# ==========================================
else: 
    # Navigationskopf.
    col_back, col_title, col_empty = st.columns([1, 4, 1])
    
    with col_back:
        if st.button("⬅️ Zurück"):
            st.session_state.race_started = False
            if 'player' in st.session_state:
                del st.session_state['player']
            st.rerun()
            
    with col_title:
        st.markdown("<h3 style='text-align: center; margin-top: 0px;'>🏁 Das Rennen läuft!</h3>", unsafe_allow_html=True)
    
    st.divider()

    if 'player' in st.session_state:
        
        # --- NEU: ECHTZEIT-KI-STRATEGIEÜBERSICHT ---
        st.markdown("#### 🧠 Live KI-Strategie-Ratgeber")
        
        # Spalten: Auswahl links, Empfehlung rechts.
        col_advisor_input, col_advisor_output = st.columns([1, 2])
        
        with col_advisor_input:
            # Dropdown für Strategieänderung im Rennen.
            live_target_tire = st.selectbox(
                "Boxenstrategie bewerten für:", 
                ['SOFT', 'MEDIUM', 'HARD'], 
                key="live_target_tire"
            )
            
        with col_advisor_output:
            # KI berechnet direkt die beste Runde zur aktuellen Auswahl.
            try:
                # Kleine visuelle Ausrichtung zur Dropdown-Höhe.
                st.write("") 
                best_lap = find_optimal_pit_lap(
                    track_name=st.session_state.track,
                    total_laps=st.session_state.total_laps,
                    team=st.session_state.player.team,
                    start_compound=st.session_state.player.tire,
                    next_compound=live_target_tire,
                    air_temp=st.session_state.air_temp
                )
                # Live-Empfehlung anzeigen.
                st.success(f"**Zielbereich:** Boxenstopp in **Runde {best_lap}** für frische **{live_target_tire}**-Reifen.")
            except Exception as e:
                st.warning("KI benötigt trainierte Modelle für Live-Daten.")

        st.divider()

            # --- BESTEHENDE RENNLOGIK ---
        write_chosen_options()
        race_simulation()

    else:
        st.error("Autodaten konnten nicht geladen werden. Bitte zum Hauptmenü zurückgehen und erneut versuchen.")
