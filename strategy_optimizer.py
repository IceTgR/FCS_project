"""Optimierung von 1- und 2-Stopp-Strategien via ML-Simulation aller möglichen Stopp-Runden."""
import streamlit as st
import pandas as pd
import joblib
import numpy as np
import os


def load_track_model(track_name, condition="dry"):
    """Lädt ML-Modell und Feature-Spalten für die angegebene Strecke."""
    # Leerzeichen → Unterstrich für Dateinamen.
    track_id = track_name.replace(' ', '_')

    model_path = f"models/{condition}/rf_{track_id}.pkl"
    cols_path = f"models/{condition}/cols_{track_id}.pkl"

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Kein Modell für '{track_name}' unter {model_path}. Bitte erst trainieren.")

    model = joblib.load(model_path)
    train_columns = joblib.load(cols_path)

    return model, train_columns


def simulate_race_time(model, train_cols, total_laps, team, start_compound, next_compound, pit_lap, air_temp, pit_loss_sec=22.0):
    """Berechnet die simulierte Gesamtzeit für einen 1-Stopp."""
    total_time = 0.0
    tyre_life = 1
    current_compound = start_compound

    laps_data = []

    for lap in range(1, total_laps + 1):
        if lap == pit_lap:
            current_compound = next_compound
            tyre_life = 1
            total_time += pit_loss_sec

        laps_data.append({
            'LapNumber': lap,
            'TyreLife': tyre_life,
            'AirTemp': air_temp,
            'Team': team,
            'Compound': current_compound
        })
        tyre_life += 1

    df_sim = pd.DataFrame(laps_data)

    # One-Hot-Encoding muss mit dem Training übereinstimmen.
    X_sim = pd.get_dummies(df_sim, columns=['Team', 'Compound'])
    X_sim = X_sim.reindex(columns=train_cols, fill_value=0)

    total_time += np.sum(model.predict(X_sim))

    return total_time


def simulate_race_time_multi(model, train_cols, total_laps, team, start_compound, pit_stops, air_temp, pit_loss_sec=22.0):
    """Berechnet die simulierte Gesamtzeit für beliebig viele Boxenstopps."""
    total_time = 0.0
    tyre_life = 1
    current_compound = start_compound
    pit_stops = sorted(pit_stops, key=lambda x: x['lap']) # pit_stops: Liste von {'lap': int, 'compound': str}, nach Runde sortiert.
    next_stop_idx = 0

    laps_data = []

    for lap in range(1, total_laps + 1):
        if next_stop_idx < len(pit_stops) and lap == pit_stops[next_stop_idx]['lap']:
            current_compound = pit_stops[next_stop_idx]['compound']
            tyre_life = 1
            total_time += pit_loss_sec
            next_stop_idx += 1

        laps_data.append({
            'LapNumber': lap,
            'TyreLife': tyre_life,
            'AirTemp': air_temp,
            'Team': team,
            'Compound': current_compound
        })
        tyre_life += 1

    df_sim = pd.DataFrame(laps_data)
    X_sim = pd.get_dummies(df_sim, columns=['Team', 'Compound'])
    X_sim = X_sim.reindex(columns=train_cols, fill_value=0)

    total_time += np.sum(model.predict(X_sim))
    return total_time


@st.cache_data
def optimize_hybrid_strategy(track_name, total_laps, team, start_compound, compound_2, air_temp):
    """Vergleicht 1-Stopp- und 2-Stopp-Strategien und gibt die schnellere mit allen Details zurück.

    Der Nutzer wählt Start- und 2. Reifen; die KI wählt den optimalen 3. Reifen und alle Stopp-Runden.
    """
    model, train_cols = load_track_model(track_name, "dry")
    compounds = ['SOFT', 'MEDIUM', 'HARD']
    min_stint = 8  # Mindest-Stint-Länge gegen unrealistische Kurzstints.

    # ── 1-Stopp ──────────────────────────────────────────────────────────────
    best_1_stop_time = float('inf')
    best_1_stop_lap = -1

    if start_compound != compound_2:
        for pit1 in range(min_stint, total_laps - min_stint):
            t = simulate_race_time(
                model, train_cols, total_laps, team,
                start_compound, compound_2, pit1, air_temp,
            )
            if t < best_1_stop_time:
                best_1_stop_time = t
                best_1_stop_lap = pit1

    # ── 2-Stopp ──────────────────────────────────────────────────────────────
    best_2_stop_time = float('inf')
    best_2_stop_pit1 = -1
    best_2_stop_pit2 = -1
    best_compound_3 = None

    for comp3 in compounds:
        # FIA-Regel: mindestens 2 verschiedene Mischungen müssen gefahren werden.
        if start_compound == compound_2 == comp3:
            continue

        for pit1 in range(min_stint, total_laps - min_stint * 2):
            for pit2 in range(pit1 + min_stint, total_laps - min_stint):
                t = simulate_race_time_multi(
                    model, train_cols, total_laps, team, start_compound,
                    [{'lap': pit1, 'compound': compound_2},
                     {'lap': pit2, 'compound': comp3}],
                    air_temp,
                )
                if t < best_2_stop_time:
                    best_2_stop_time = t
                    best_2_stop_pit1 = pit1
                    best_2_stop_pit2 = pit2
                    best_compound_3 = comp3

    # ── Entscheidung ─────────────────────────────────────────────────────────
    if best_2_stop_time < best_1_stop_time:
        return {
            "recommendation": "2-Stop",
            "time_saved": best_1_stop_time - best_2_stop_time,
            "total_time": best_2_stop_time,
            "pit1_lap": best_2_stop_pit1,
            "pit1_tyre": compound_2,
            "pit2_lap": best_2_stop_pit2,
            "pit2_tyre": best_compound_3,
        }
    return {
        "recommendation": "1-Stop",
        "time_saved": best_2_stop_time - best_1_stop_time,
        "total_time": best_1_stop_time,
        "pit1_lap": best_1_stop_lap,
        "pit1_tyre": compound_2,
    }


@st.cache_data
def find_best_overall_strategy(track_name, total_laps, team, start_compound, air_temp):
    """Testet alle möglichen compound_2-Varianten und gibt die insgesamt schnellste Strategie zurück."""
    compounds = ['SOFT', 'MEDIUM', 'HARD']
    best_result = None
    best_time = float('inf')

    for compound_2 in compounds:
        try:
            result = optimize_hybrid_strategy(
                track_name, total_laps, team, start_compound, compound_2, air_temp
            )
            if result['total_time'] < best_time:
                best_time = result['total_time']
                best_result = dict(result)
                best_result['compound_2'] = compound_2
        except Exception:
            continue

    return best_result
