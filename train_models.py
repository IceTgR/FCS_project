# ML-Modell-Training für Rundenzeit-Vorhersagen.
import os
from datetime import datetime
import sqlite3

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


def ensure_ml_assets(progress_callback=None):
    """Erstellt Datenbank und trainiert ML-Modelle falls nicht vorhanden."""
    status = {
        'created_db': False,
        'trained_models': False,
        'results': None,
    }

    # Erstelle Datenbank wenn nicht vorhanden oder wenn Tabelle fehlt
    need_create = False
    if not os.path.exists(DB_PATH):
        need_create = True
    else:
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='laptimes'")
            if not cur.fetchone():
                need_create = True
            conn.close()
        except Exception:
            need_create = True

    if need_create:
        current_year = datetime.now().year
        years = range(2018, current_year + 1)
        ret = fastf1_to_sql(years, TRACK_LIST, TEAM_LIST, progress_callback=progress_callback)
        status['created_db'] = True
        if isinstance(ret, dict):
            status['rate_limited'] = ret.get('rate_limited', False)
            status['rate_limit_wait'] = ret.get('max_wait_seconds', 0)

    # Trainiere Modelle wenn nicht vorhanden
    if status['created_db'] or not models_exist():
        df_dry, _ = get_preprocessed_datasets()
        results = train_dry_models(df_dry)
        status['trained_models'] = True
        status['results'] = results

    return status