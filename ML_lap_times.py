"""Training von Random-Forest-Modellen pro Strecke für trockene Streckenbedingungen."""
import pandas as pd
import joblib
import os
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error

def train_dry_models(df_dry):
    """Trainiert je einen Random Forest pro Strecke und speichert Modell und Feature-Spalten."""
    os.makedirs('models/dry', exist_ok=True)

    tracks = df_dry['Track'].unique()
    results = {}

    for track in tracks:
        track_df = df_dry[df_dry['Track'] == track].copy()

        # Team und Compound sind kategorial, weshalb One-Hot-Encoding angewendet wird.
        features = ['LapNumber', 'TyreLife', 'AirTemp', 'Team', 'Compound']
        X = pd.get_dummies(track_df[features], columns=['Team', 'Compound'])
        y = track_df['LapTimeSec']

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        model = RandomForestRegressor(
            n_estimators=200,
            max_depth=12,
            min_samples_leaf=4,
            min_samples_split=8,
            random_state=42,
        )
        model.fit(X_train, y_train)

        mae = mean_absolute_error(y_test, model.predict(X_test))
        print(f'MAE {track}: {mae:.3f}s')

        # Leerzeichen zu Unterstrich für Dateinamen.
        track_id = track.replace(' ', '_')
        joblib.dump(model, f'models/dry/rf_{track_id}.pkl')
        joblib.dump(X.columns.tolist(), f'models/dry/cols_{track_id}.pkl')

        results[track] = mae
        print(f'Modell gespeichert: {track}')

    return results

