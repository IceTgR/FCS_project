import fastf1
import sqlite3
import pandas as pd
import os



def fastf1_to_sqlite(years, track_list, team_list):
    '''Lädt die DB von fastf1 und speichert sie in SQLite-DB, damit schnellere Abfragen möglich sind.'''

    # Verzeichnis für Cache erstellen, damit die Daten lokal gespeichert werden und es somit schneller geht
    if not os.path.exists('f1_cache'):
        os.makedirs('f1_cache')
    fastf1.Cache.enable_cache('f1_cache')

    # existierende db löschen, falls sie existiert
    if os.path.exists('f1_project.db'):
        os.remove('f1_project.db')
        print(f"Existierende Datenbank wurde erfolgreich gelöscht. Neue wird erstellt. Dies kann einige Minuten dauern...")

    conn = sqlite3.connect('f1_project.db')
    
    for year in years:
        schedule = fastf1.get_event_schedule(year)
        # Filtern der Rennstrecken, Benutzung von str.contains für flexible Suche
        filtered_events = schedule[schedule['EventName'].str.contains('|'.join(track_list), case=False)]
        
        for _, event in filtered_events.iterrows():
            try:
                print(f"Lade {year} {event['EventName']}...")
                session = fastf1.get_session(year, event['RoundNumber'], 'R')
                
                # Laden der Runden- und Wetterdaten und Messages, keine Telemetrie für schnellere Verarbeitung
                session.load(laps=True, telemetry=False, weather=True, messages=True)
                
                laps = session.laps.pick_teams(team_list).copy()
                if laps.empty: continue

                weather = session.weather_data
                weather['Time'] = weather['Time'].dt.total_seconds() # Wir runden die Zeitstempel, um sie mit den Laps zu matchen
                
                # Hilfsfunktion: Gab es Regen während dieser Runde?
                def check_rain(lap_row):
                    # Wir schauen, ob im Zeitfenster der Runde Rainfall registriert wurde
                    start = lap_row['Time'].total_seconds() - lap_row['LapTime'].total_seconds()
                    end = lap_row['Time'].total_seconds()
                    rain_in_lap = weather[(weather['Time'] >= start) & (weather['Time'] <= end)]['Rainfall']
                    return 1 if rain_in_lap.any() else 0

                # Zeit in Sekunden umwandeln
                laps['LapTimeSec'] = laps['LapTime'].dt.total_seconds()
                
                # Nötige Spalten für ML Modell
                laps['IsRaining'] = laps.apply(check_rain, axis=1) # Pro Runde prüfen
                laps['AirTemp'] = weather['AirTemp'].mean() # Durchschnitt für die Session
                laps['Track'] = event['EventName']
                laps['Year'] = year
                laps['IsOutlap'] = laps['PitOutTime'].notnull().astype(int)
                laps['IsPitstop'] = laps['PitInTime'].notnull().astype(int)

                # Bereinigen und Speichern
                db_data = laps.dropna(subset=['LapTimeSec'])[[
                    'Year', 'Track', 'Team', 'LapNumber', 'LapTimeSec', 
                    'Compound', 'TyreLife', 'AirTemp', 'IsRaining', 'IsOutlap', 'IsPitstop'
                ]]

                db_data.to_sql('laptimes', conn, if_exists='append', index=False)
                print(f"Erfolg: {year} {event['EventName']}")

            except Exception:
                print(f"Skip {year} {event['EventName']}")
    
    conn.close()