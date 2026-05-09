"""Kernsimulationslogik: Safety-Car-Events, Rundenzeit-Multiplikatoren und Feldkompression."""
import random

import streamlit as st


def roll_safety_event():
    """Würfelt zu Rundenbeginn, ob ein SC oder VSC ausgelöst wird.

    Läuft nur, wenn kein Event aktiv ist. Wahrscheinlichkeiten: SC 1.5%, VSC 2.5%.
    Zufällige Dauer wird in session_state gespeichert.
    """
    if not hasattr(st.session_state, 'safety_event_duration'):
        st.session_state.safety_event_duration = 0
    if not hasattr(st.session_state, 'safety_event_status'):
        st.session_state.safety_event_status = None

    # Kein neues Event starten, solange eines aktiv ist.
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
    """Zählt die verbleibende Event-Dauer um eine Runde herunter und beendet das Event bei 0."""
    if st.session_state.safety_event_status is None:
        return

    if st.session_state.safety_event_duration > 0:
        st.session_state.safety_event_duration -= 1

    if st.session_state.safety_event_duration == 0:
        st.session_state.safety_event_status = None


def get_safety_event_lap_multiplier():
    """Gibt den Rundenzeit-Multiplikator für das aktive Event zurück (SC: ×1.65, VSC: ×1.30)."""
    current_event = st.session_state.safety_event_status if hasattr(st.session_state, 'safety_event_status') else None

    if current_event == 'SAFETYCAR':
        return 1.65
    if current_event == 'VSC':
        return 1.30
    return 1.0


def get_safety_event_pitstop_multiplier():
    """Gibt den Boxenstopp-Zeitfaktor für das aktive Event zurück (SC: ×0.58, VSC: ×0.78)."""
    current_event = st.session_state.safety_event_status if hasattr(st.session_state, 'safety_event_status') else None

    if current_event == 'SAFETYCAR':
        return 0.58
    if current_event == 'VSC':
        return 0.78
    return 1.0


def apply_safety_event_effect(car):
    """Skaliert die bereits berechnete Rundenzeit des Autos mit dem aktiven Event-Multiplikator."""
    car.lap_time *= get_safety_event_lap_multiplier()


def compress_sc_field(player, opponents):
    """Simuliert das Zusammenrücken des Feldes unter Safety Car.

    Pro SC-Runde wird der Abstand zum direkten Vordermann um 75% reduziert,
    sodass das Feld nach 1-2 Runden in einer Kolonne fährt.
    Mindestabstand zwischen zwei aufeinanderfolgenden Autos: 0.8s.
    total_time, lap_time und race_history werden synchron angepasst.
    """
    MIN_GAP = 0.8

    # Alle Autos nach Gesamtzeit sortieren (Führender zuerst).
    cars = [player] + [opp.car for opp in opponents]
    cars.sort(key=lambda c: c.total_time)

    for i in range(1, len(cars)):
        car = cars[i]
        gap = car.total_time - cars[i - 1].total_time
        if gap <= MIN_GAP:
            continue
        # 75% Reduktion, aber mind. MIN_GAP Abstand erhalten.
        new_gap = max(MIN_GAP, gap * 0.25)
        reduction = gap - new_gap
        car.total_time -= reduction
        car.lap_time = max(0.1, car.lap_time - reduction)
        if car.race_history:
            car.race_history[-1]["Rundenzeit"] = max(0.1, car.race_history[-1]["Rundenzeit"] - reduction)
