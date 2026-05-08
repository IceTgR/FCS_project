# Optimierung von Rennstrategien mittels ML-Modelle.
import streamlit as st
import pandas as pd
import joblib
import numpy as np
import os
from ML_lap_times import predict_lap_time

def load_track_model(track_name, condition="dry"):
    """Lädt trainiertes ML-Modell und Spalten für spezifische Strecke."""
    # Konvertiere "Monaco Grand Prix" zu "Monaco_Grand_Prix" für Dateinamen
    track_id = track_name.replace(' ', '_') 
    
    # Pfade zu Modell und Spalten-Info
    model_path = f"models/{condition}/rf_{track_id}.pkl"
    cols_path = f"models/{condition}/cols_{track_id}.pkl"
    
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model for {track_name} not found at {model_path}. Train it first!")
        
    model = joblib.load(model_path)
    train_columns = joblib.load(cols_path) 
    
    return model, train_columns

def simulate_race_time(model, train_cols, total_laps, team, start_compound, next_compound, pit_lap, air_temp, pit_loss_sec=22.0):
    """Simuliert Gesamtrennzeit für spezifische Boxenstrategie."""
    
    total_time = 0.0
    tyre_life = 1
    current_compound = start_compound
    
    # Erstelle Liste mit Runden-Daten vor DataFrame-Konvertierung
    laps_data = []
    
    for lap in range(1, total_laps + 1):
        # Überprüfe Boxenstopp-Runde
        if lap == pit_lap:
            current_compound = next_compound
            tyre_life = 1  # Setze Reifenalter zurück
            total_time += pit_loss_sec  # Füge Boxenstopp-Zeitverlust hinzu
            
        laps_data.append({
            'LapNumber': lap,
            'TyreLife': tyre_life,
            'AirTemp': air_temp,
            'Team': team,
            'Compound': current_compound
        })
        
        tyre_life += 1

    # Konvertiere Daten zu DataFrame
    df_sim = pd.DataFrame(laps_data)
    
    # One-Hot-Encode Team und Compound wie das Modell es erwartet
    X_sim = pd.get_dummies(df_sim, columns=['Team', 'Compound'])
    
    # Stelle sicher, dass alle Trainings-Spalten vorhanden sind
    X_sim = X_sim.reindex(columns=train_cols, fill_value=0)
    
    # Vorhersage aller Rundenzeiten auf einmal
    predicted_lap_times = model.predict(X_sim)
    
    # Addiere vorhergesagte Rundenzeiten zur Gesamtzeit
    total_time += np.sum(predicted_lap_times)
    
    return total_time
def simulate_race_time_multi(model, train_cols, total_laps, team, start_compound, pit_stops, air_temp, pit_loss_sec=22.0):
    """Simuliert Gesamtrennzeit für beliebig viele Boxenstopps (z.B. 1-Stop, 2-Stop)."""
    total_time = 0.0
    tyre_life = 1
    current_compound = start_compound
    
    # Sortiere Boxenstopps nach Runden, um sie in der richtigen Reihenfolge abzuarbeiten
    pit_stops = sorted(pit_stops, key=lambda x: x['lap'])
    next_stop_idx = 0
    
    laps_data = []
    
    for lap in range(1, total_laps + 1):
        # Überprüfe, ob in dieser Runde ein Boxenstopp ansteht
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
    
    predicted_lap_times = model.predict(X_sim)
    total_time += np.sum(predicted_lap_times)
    
    return total_time
    
@st.cache_data
def find_optimal_pit_lap(track_name, total_laps, team, start_compound, next_compound, air_temp):
    """Findet optimale Boxenstopp-Runde durch Vergleich aller möglichen Strategien."""
    
    # Modell und Spalten einmal laden
    try:
        model, train_cols = load_track_model(track_name, "dry")
    except FileNotFoundError:
        return total_laps // 2  # Fallback, falls kein Modell existiert
        
    best_total_time = float('inf')
    best_lap = 0

    # Vergleiche alle möglichen Boxenstopp-Runden
    for pit_lap in range(10, total_laps - 5):
        
        # Nutze deine korrekte Simulations-Funktion, die das Reifenalter auf 1 zurücksetzt
        total_race_time = simulate_race_time(
            model=model, 
            train_cols=train_cols, 
            total_laps=total_laps, 
            team=team, 
            start_compound=start_compound, 
            next_compound=next_compound, 
            pit_lap=pit_lap, 
            air_temp=air_temp
        )
        
        if total_race_time < best_total_time:
            best_total_time = total_race_time
            best_lap = pit_lap
            
    return best_lap


@st.cache_data
def optimize_hybrid_strategy(track_name, total_laps, team, start_compound, compound_2, air_temp):
    """
    User provides Start Tyre and 2nd Tyre.
    AI predicts if a 2nd stop is needed, what the 3rd tyre should be, and all pit laps.
    """
    model, train_cols = load_track_model(track_name)
    
    compounds = ['SOFT', 'MEDIUM', 'HARD']
    min_stint = 8 # Prevent unrealistic 2-lap stints
    
    # --- 1-STOP OPTIMIZATION ---
    best_1_stop_time = float('inf')
    best_1_stop_lap = -1
    
    # Test all laps for the 1st pit stop
    for pit1 in range(min_stint, total_laps - min_stint):
        pit_stops = [{'lap': pit1, 'compound': compound_2}]
        # VERWENDET JETZT DIE NEUE FUNKTION:
        time = simulate_race_time_multi(model, train_cols, total_laps, team, start_compound, pit_stops, air_temp)
        
        if time < best_1_stop_time:
            best_1_stop_time = time
            best_1_stop_lap = pit1

    # --- 2-STOP OPTIMIZATION ---
    best_2_stop_time = float('inf')
    best_2_stop_pit1 = -1
    best_2_stop_pit2 = -1
    best_compound_3 = None
    
    # Test all possible 3rd tyres
    for comp3 in compounds:
        # F1 Rule: Must use at least 2 different compounds in a race
        if start_compound == compound_2 and compound_2 == comp3:
            continue
            
        # Test all lap combinations for Pit 1 and Pit 2
        for pit1 in range(min_stint, total_laps - (min_stint * 2)):
            for pit2 in range(pit1 + min_stint, total_laps - min_stint):
                
                pit_stops = [
                    {'lap': pit1, 'compound': compound_2},
                    {'lap': pit2, 'compound': comp3}
                ]
                
                # VERWENDET JETZT DIE NEUE FUNKTION:
                time = simulate_race_time_multi(model, train_cols, total_laps, team, start_compound, pit_stops, air_temp)
                
                if time < best_2_stop_time:
                    best_2_stop_time = time
                    best_2_stop_pit1 = pit1
                    best_2_stop_pit2 = pit2
                    best_compound_3 = comp3

    # --- FINAL DECISION ---
    # Compare the best 1-stop against the best 2-stop
    if best_2_stop_time < best_1_stop_time:
        return {
            "recommendation": "2-Stop",
            "time_saved": best_1_stop_time - best_2_stop_time, 
            "total_time": best_2_stop_time,
            "pit1_lap": best_2_stop_pit1,
            "pit1_tyre": compound_2,
            "pit2_lap": best_2_stop_pit2,
            "pit2_tyre": best_compound_3
        }
    else:
        return {
            "recommendation": "1-Stop",
            "time_saved": best_2_stop_time - best_1_stop_time,
            "total_time": best_1_stop_time,
            "pit1_lap": best_1_stop_lap,
            "pit1_tyre": compound_2
        }


