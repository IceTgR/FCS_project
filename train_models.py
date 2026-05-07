# ML-Modell-Training für Rundenzeit-Vorhersagen.
import os
from datetime import datetime

from data_preprocessing import get_preprocessed_datasets
from ML_lap_times import train_dry_models
from retrieve_data import fastf1_to_sql

DB_PATH = 'f1_project.db'
TRACK_LIST = ['Abu Dhabi Grand Prix', 'Austrian Grand Prix', 'Belgian Grand Prix', 'British Grand Prix', 'Hungarian Grand Prix', 'Italian Grand Prix']
TEAM_LIST = ['Ferrari', 'Mercedes', 'Red Bull', 'McLaren', 'Williams']
MODEL_PATHS = [f"models/dry/rf_{track.replace(' ', '_')}.pkl" for track in TRACK_LIST]


def models_exist():
    """Überprüft, ob alle ML-Modelle vorhanden sind."""
    return all(os.path.exists(path) for path in MODEL_PATHS)


def ensure_ml_assets():
    """Erstellt Datenbank und trainiert ML-Modelle falls nicht vorhanden."""
    status = {
        'created_db': False,
        'trained_models': False,
        'results': None,
    }

    # Erstelle Datenbank wenn nicht vorhanden
    if not os.path.exists(DB_PATH):
        current_year = datetime.now().year
        years = range(2018, current_year + 1)
        fastf1_to_sql(years, TRACK_LIST, TEAM_LIST)
        status['created_db'] = True

    # Trainiere Modelle wenn nicht vorhanden
    if status['created_db'] or not models_exist():
        df_dry, _ = get_preprocessed_datasets()
        results = train_dry_models(df_dry)
        status['trained_models'] = True
        status['results'] = results

    return status