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


