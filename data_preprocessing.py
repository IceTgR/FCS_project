# Vorverarbeitung von F1-Daten für ML-Modell-Training.
import sqlite3
import pandas as pd

def get_preprocessed_datasets():
    """Lädt und bereitet Daten für ML-Training vor (Nass/Trocken)."""
    # Lade Daten aus SQL-Datenbank
    conn = sqlite3.connect('f1_project.db')
    df = pd.read_sql("SELECT * FROM laptimes", conn)
    conn.close()

    # Reifen-Standardisierung: Verschiedene Jahrzehnte nutzten unterschiedliche Namen
    # Standardisiere auf SOFT, MEDIUM, HARD
    tyre_map = {
        'SOFT': 'SOFT', 'SUPERSOFT': 'SOFT', 'ULTRASOFT': 'SOFT', 'HYPERSOFT': 'SOFT',
        'MEDIUM': 'MEDIUM',
        'HARD': 'HARD',
        'INTERMEDIATE': 'INTERMEDIATE',
        'WET': 'WET',
    }
    df['Compound'] = df['Compound'].map(tyre_map)

    # Runden-Filterung: Entferne nicht "saubere" Runden für bessere Datenqualität
    df_clean = df[
        (df['IsOutlap'] == 0) &      # Entferne Outlaps
        (df['IsPitstop'] == 0)       # Entferne Inlaps
    ].copy()

    # Teile in Nass- und Trocken-Datensätze auf
    dry_tyres = ['SOFT', 'MEDIUM', 'HARD']
    wet_tyres = ['INTERMEDIATE', 'WET']

    # Trocken: Nur Trockenreifen UND kein Regen
    df_dry = df_clean[
        (df_clean['Compound'].isin(dry_tyres)) & 
        (df_clean['IsRaining'] == 0)
    ].copy()

    # Nass: Nur Nassreifen UND Regen
    df_wet = df_clean[
        (df_clean['Compound'].isin(wet_tyres)) & 
        (df_clean['IsRaining'] == 1)
    ].copy()

    # Entferne Ausreißer (Unfälle, Fahrfehler): > 10% über Median-Rundenzeit
    def remove_outliers(df):
        df['MedianTime'] = df.groupby('Track')['LapTimeSec'].transform('median')
        df = df[df['LapTimeSec'] < df['MedianTime'] * 1.10]
        return df.drop(columns=['MedianTime'])

    df_dry = remove_outliers(df_dry)
    df_wet = remove_outliers(df_wet)
    
    print(f"Preprocessing fertig: {len(df_dry)} Trocken-Runden, {len(df_wet)} Regen-Runden.")
    return df_dry, df_wet