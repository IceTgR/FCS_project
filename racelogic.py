# Kernsimulationslogik für das Rennen.
import random
import time

import streamlit as st
import pandas as pd
from car import Car
from opponents import advance_opponents, build_opponent_table


def roll_safety_event():
    """Startet ein neues Sicherheitsereignis (SC/VSC) mit Zufallsdauer."""
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
    """Reduziert die verbleibende Sicherheitsereignis-Dauer um 1 Runde."""
    if st.session_state.safety_event_status is None:
        return

    if st.session_state.safety_event_duration > 0:
        st.session_state.safety_event_duration -= 1

    if st.session_state.safety_event_duration == 0:
        st.session_state.safety_event_status = None


def get_safety_event_lap_multiplier():
    """Gibt Rundenzeit-Multiplikator für aktuelles Sicherheitsereignis zurück."""
    current_event = st.session_state.safety_event_status if hasattr(st.session_state, 'safety_event_status') else None

    if current_event == 'SAFETYCAR':
        return 1.65
    if current_event == 'VSC':
        return 1.30
    return 1.0


def get_safety_event_pitstop_multiplier():
    """Gibt Boxenstopp-Multiplikator für aktuelles Sicherheitsereignis zurück."""
    current_event = st.session_state.safety_event_status if hasattr(st.session_state, 'safety_event_status') else None

    if current_event == 'SAFETYCAR':
        return 0.58
    if current_event == 'VSC':
        return 0.78
    return 1.0


def apply_safety_event_effect(car):
    """Wendet Rundenzeit-Effekt des aktiven Sicherheitsereignisses an."""
    car.lap_time *= get_safety_event_lap_multiplier()

# Zeige die vor dem Rennen gewählten Optionen an.
def write_chosen_options():
    """Zeigt Team, Reifen und Strecke des Spielers an."""
    st.write(f'Du hast {st.session_state.player.team} als dein Team gewählt, '
        f'startest mit {st.session_state.player.tire} Reifen auf der {st.session_state.track}.')
    if hasattr(st.session_state, 'opponents'):
        st.write(f'Das Feld hat nun {len(st.session_state.opponents)} computergesteuerte Gegner.')
    
@st.fragment(run_every=1)
def race_simulation():
    """Verwaltet Rennablauf, Spieler-Aktionen und zeigt Live-Rennstatus an."""
    # Zeige aktuellen Rennstatus oben auf dem Bildschirm an.
    st.write(f'Letzte Rundenzeit: {st.session_state.player.lap_time if st.session_state.player.lap > 1 else "dies ist deine erste Runde"}\n'
            f'Aktuelle Runde: {st.session_state.player.lap if st.session_state.player.lap <= st.session_state.total_laps else "beendet"}')

    current_event = st.session_state.safety_event_status if hasattr(st.session_state, 'safety_event_status') else None
    if current_event == 'SAFETYCAR':
        st.warning('Safety Car ausgelöst.')
    elif current_event == 'VSC':
        st.info('Virtueller Safety Car ist aktiv.')

    # Überprüfe Rennende.
    if st.session_state.player.lap == st.session_state.total_laps + 1:
        if st.session_state.player.pitstop_counter == 0:
            st.write('Du wurdest disqualifiziert, da du keinen Boxenstopp gemacht hast!')
        else:
            st.write('Glückwunsch, du hast das Rennen beendet!')

    else:
        # Berechne Rundenzeit vor Spieler-Aktion.
        air_temp = st.session_state.get('air_temp', 25)
        st.session_state.player.predict_lap_time(air_temp=air_temp)

        # Initialisiere oder aktualisiere den Startzeitpunkt für die aktuelle Runde.
        current_lap = st.session_state.player.lap
        if st.session_state.get('lap_started_for') != current_lap:
            st.session_state.lap_start_time = time.time()
            st.session_state.lap_started_for = current_lap

        # Berechne verstrichene Zeit seit Rundenstart in Sekunden.
        elapsed_time = time.time() - st.session_state.lap_start_time
        timeout_seconds = 5.0
        remaining_time = max(0.0, timeout_seconds - elapsed_time)

        # Auto-Weitermachen nach 5 Sekunden ohne Spieler-Input.
        if remaining_time <= 0:
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
            st.session_state.lap_start_time = time.time()
            st.session_state.lap_started_for = st.session_state.player.lap
            st.rerun()

        # Zeige den Countdown direkt im Fragment an, damit er bei jedem Fragment-Refresh neu berechnet wird.
        st.info(f'⏱️ Automatisch nächste Runde in {remaining_time:.1f} Sekunden... (oder wähle unten manuell)')
        
        # Weiter ohne Boxenstopp.
        col1, col2 = st.columns(2)
        with col1:
            if st.button('Nächste Runde', key='continue_btn'):
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
                st.session_state.lap_start_time = time.time()  # Reset für nächste Runde.
                st.session_state.lap_started_for = st.session_state.player.lap
                st.rerun(scope = 'app')
        
        with col2:
            if st.button('Boxenstopp', key='pit_btn'):
                # Lasse Spieler nächste Reifenmischung für Boxenstopp wählen.
                new_tire = st.radio('Wähle Reifenmischung für Boxenstopp', ['SOFT', 'MEDIUM', 'HARD'])
                # Fahre in die Boxengasse und wechsle Reifen.
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
                st.session_state.lap_start_time = time.time()  # Reset für nächste Runde.
                st.session_state.lap_started_for = st.session_state.player.lap
                st.rerun(scope = 'app')

    # Zeige Rennhistorie als Tabelle und Diagramm.
    st.subheader('Renngeschichte')
    history = pd.DataFrame(st.session_state.player.race_history, columns=['Runde', 'Rundenzeit', 'Reifen', 'Reifenalter', 'Kommentar'])

    st.metric('Rundenzeit-Entwicklung', (f"{st.session_state.player.race_history[-1]['Rundenzeit']:.2f} Sekunden" if st.session_state.player.lap > 1 else 0),
            delta = ((st.session_state.player.race_history[-1]['Rundenzeit'] - st.session_state.player.race_history[-2]['Rundenzeit']) if st.session_state.player.lap > 2 else 'k.A.'),
            chart_data = history['Rundenzeit'], chart_type = 'line', border = True, delta_color = 'inverse')
    
    st.table(history) if st.session_state.player.lap > 1 else st.write('Keine Historie vorhanden, das ist deine erste Runde!')

    st.subheader('Gegner')
    opponents = st.session_state.get('opponents')
    if opponents:
        opponent_history = pd.DataFrame(build_opponent_table(opponents, st.session_state.total_laps))
        st.table(opponent_history)
    else:
        st.write('Es wurden noch keine Gegner erstellt.')


    



