# ML-Modell-Training und Rundenzeit-Vorhersagen mit Random Forest.
import streamlit as st
import pandas as pd
import sqlite3
import joblib
import os
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error


# Trockene Bedingungen: Random Forest für nicht-lineare Rundenzeit-Beziehungen.
# Wir wählen RandomForest wegen Robustheit und geringerem Überfitting.

def train_dry_models(df_dry):
    """Trainiert separate Random Forest Modelle für jede Rennstrecke."""
    # Erstelle Verzeichnis für Modelle falls nicht vorhanden
    if not os.path.exists('models/dry'):
        os.makedirs('models/dry')

    # Hole eindeutige Strecken - trainiere ein Modell pro Strecke
    tracks = df_dry['Track'].unique()

    # Initialisiere Ergebnis-Dict für MAE pro Strecke
    results = {}

    # Trainiere ein Modell pro Strecke
    for track in tracks:
        # Hole Daten für spezifische Strecke
        track_df = df_dry[df_dry['Track'] == track].copy()

        # Bereite Features und Ziel vor
        # Team und Compound sind kategorial - werde One-Hot-Encoded
        features = ['LapNumber', 'TyreLife', 'AirTemp', 'Team', 'Compound']
        X = pd.get_dummies(track_df[features], columns=['Team', 'Compound'])
        y = track_df['LapTimeSec']

        # Teile Daten in Trainings- und Test-Set
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Initialisiere und trainiere Random Forest Regressor
        model = RandomForestRegressor(
            n_estimators=200,
            max_depth=12,
            min_samples_leaf=4,
            min_samples_split=8,
            random_state=42,
        )
        model.fit(X_train, y_train)

        # Evaluiere Modell auf Test-Set
        predictions = model.predict(X_test)
        mae = mean_absolute_error(y_test, predictions)
        print(f'Durchschnittlicher Fehler (MAE) für {track}: {mae:.3f} Sekunden')
        
        # Speichere trainiertes Modell für spätere Verwendung
        # Ersetze Leerzeichen mit Unterstrich für Dateinamen
        track_id = track.replace(' ', '_')
        joblib.dump(model, f'models/dry/rf_{track_id}.pkl')
        # Speichere Feature-Namen für spätere Verwendung
        joblib.dump(X.columns.tolist(), f'models/dry/cols_{track_id}.pkl')

        results[track] = mae
        print(f'Modell für {track} gespeichert.')

    return results





@st.cache_data
def predict_lap_time(track_name, team, compound, lap_number, air_temp):
    """Vorhersage der Rundenzeit mit trainiertem ML-Modell."""
    # Formatiere Strecken-Namen wie beim Speichern
    track_id = track_name.replace(' ', '_')
    model_path = f'models/dry/rf_{track_id}.pkl'
    cols_path = f'models/dry/cols_{track_id}.pkl'

    # Fallback-Vorhersage falls Modell nicht trainiert ist
    if not os.path.exists(model_path):
        return 80.0 + (lap_number * 0.1)

    # Lade Modell und Feature-Namen
    model = joblib.load(model_path)
    model_columns = joblib.load(cols_path)

    # Erstelle DataFrame für eine einzelne Runde
    input_data = pd.DataFrame({
        'LapNumber': [lap_number],
        'TyreLife': [lap_number],  # Reifenalter = Rundennummer
        'AirTemp': [air_temp]
    })

    # Fülle fehlende Spalten mit 0
    for col in model_columns:
        if col not in input_data.columns:
            input_data[col] = 0

    # Setze spezifisches Team und Compound zu 1
    if f'Team_{team}' in input_data.columns:
        input_data[f'Team_{team}'] = 1
    if f'Compound_{compound}' in input_data.columns:
        input_data[f'Compound_{compound}'] = 1

    # Ordne Spalten nach Modell-Spalten
    input_data = input_data[model_columns]

    # Vorhersage und Rückgabe
    return model.predict(input_data)[0]
    
