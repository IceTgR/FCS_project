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

@st.cache_data
def find_optimal_pit_lap(track_name, total_laps, team, start_compound, next_compound, air_temp):
    """Findet optimale Boxenstopp-Runde durch Vergleich aller möglichen Strategien."""
    # 1. Berechne ALLE möglichen Rundenzeiten für beide Reifen im Voraus
    time_on_start_tire = []
    time_on_target_tire = []
    
    for lap in range(1, total_laps + 1):
        time_on_start_tire.append(predict_lap_time(track_name, team, start_compound, lap, air_temp))
        time_on_target_tire.append(predict_lap_time(track_name, team, next_compound, lap, air_temp))
        
    best_total_time = float('inf')
    best_lap = 0

    # 2. Vergleiche alle möglichen Boxenstopp-Runden
    for pit_lap in range(10, total_laps - 5):
        # Stint 1: Runde 1 bis Boxenstopp mit Startreifen
        stint_1_time = sum(time_on_start_tire[:pit_lap - 1])
        # Stint 2: Nach Boxenstopp bis Ende mit Zielreifen
        stint_2_time = sum(time_on_target_tire[pit_lap - 1:])
        
        # Gesamtzeit = Stint 1 + Stint 2 + Boxenstopp-Zeit
        total_race_time = stint_1_time + stint_2_time + 22.0
        
        if total_race_time < best_total_time:
            best_total_time = total_race_time
            best_lap = pit_lap
            
    return best_lap


