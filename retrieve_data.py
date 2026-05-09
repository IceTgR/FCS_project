"""FastF1-Datenabruf mit Rate-Limit-Handling und Speicherung in SQLite."""
import fastf1
import sqlite3
import pandas as pd
import os
import time
from fastf1.req import RateLimitExceededError

_RATE_LIMITED_OCCURRED = False
_MAX_WAIT_SECONDS = 0
_RATE_LIMIT_RECOVERED_SIGNAL = '__FASTF1_RATE_LIMIT_RECOVERED__'


def _format_wait_seconds(wait_seconds):
    """Formatiert Sekunden als lesbare Zeichenkette (z.B. 'ca. 2h 15m')."""
    wait_seconds = max(0, int(round(wait_seconds)))
    if wait_seconds >= 3600:
        hours = wait_seconds // 3600
        minutes = (wait_seconds % 3600) // 60
        if minutes:
            return f"ca. {hours}h {minutes}m"
        return f"ca. {hours}h"
    if wait_seconds >= 60:
        minutes = wait_seconds // 60
        seconds = wait_seconds % 60
        if seconds:
            return f"ca. {minutes}m {seconds}s"
        return f"ca. {minutes}m"
    return f"ca. {wait_seconds}s"





def _sleep_with_progress(wait_seconds, progress_callback=None, prefix=''):
    """Wartet die angegebene Zeit und sendet alle 30s ein Callback-Update an die UI."""
    global _MAX_WAIT_SECONDS
    wait_seconds = max(0, float(wait_seconds))
    if wait_seconds <= 0:
        return

    _MAX_WAIT_SECONDS = max(_MAX_WAIT_SECONDS, wait_seconds)
    remaining = wait_seconds
    last_callback_time = 0
    while remaining > 0:
        if remaining >= 3600:
            chunk = min(300, remaining)
        elif remaining >= 600:
            chunk = min(120, remaining)
        elif remaining >= 120:
            chunk = min(60, remaining)
        elif remaining >= 30:
            chunk = min(15, remaining)
        else:
            chunk = min(5, remaining)

        message = f"Wartezeit bis zum nächsten Retry: {_format_wait_seconds(remaining)} (Im schlimmsten Fall kann dies bis zu 1h dauern)"
        print(message)
        
        # Drossle Callback-Aufrufe — nur alle 30 Sekunden aktualisieren, um Streamlit nicht zu überlasten
        now = time.time()
        if progress_callback and (now - last_callback_time >= 30 or remaining <= 30):
            try:
                progress_callback(message)
                last_callback_time = now
            except Exception:
                pass

        time.sleep(chunk)
        remaining -= chunk


def _call_fastf1_with_retry(description, func, progress_callback=None):
    """Führt func() aus und wiederholt bei RateLimitExceededError mit exponentiellem Backoff."""
    transient_attempts = 0
    rate_limited_once = False
    while True:
        try:
            result = func()
            if rate_limited_once and progress_callback:
                try:
                    progress_callback(_RATE_LIMIT_RECOVERED_SIGNAL)
                except Exception:
                    pass
            return result
        except RateLimitExceededError as exc:
            global _RATE_LIMITED_OCCURRED
            _RATE_LIMITED_OCCURRED = True
            rate_limited_once = True

            # FastF1 liefert die exakte Wartezeit nicht – wir verwenden ein exponentielles Backoff
            wait_seconds = min(3600, max(30, 15 * (transient_attempts + 1)))
            context_msg = f"FastF1 API-Rate-Limit erreicht beim {description}."
            print(f"[FastF1 RateLimitExceededError] {context_msg}")
            if progress_callback:
                try:
                    progress_callback(context_msg)
                except Exception:
                    pass

            detail_msg = f"Wartezeit bis zum nächsten Retry: {_format_wait_seconds(wait_seconds)} (Im schlimmsten Fall kann dies bis zu 1 Stunde dauern)."
            print(f"[FastF1 RateLimitExceededError] {detail_msg}")
            if progress_callback:
                try:
                    progress_callback(detail_msg)
                except Exception:
                    pass

            _sleep_with_progress(wait_seconds, progress_callback, prefix="")
            transient_attempts += 1
        except Exception:
            raise


def fastf1_to_sql(years, track_list, team_list, progress_callback=None):
    '''Lädt die DB von fastf1 und speichert sie in SQLite-DB, damit schnellere Abfragen möglich sind.'''

    # Verzeichnis für Cache erstellen, damit die Daten lokal gespeichert werden und es somit schneller geht
    os.makedirs('f1_cache', exist_ok=True)
    fastf1.Cache.enable_cache('f1_cache')

    # Schreiben auf die SQLite DB vorbereiten
    conn = sqlite3.connect('f1_project.db')
    cur = conn.cursor()
    # Tabelle sicherstellen (falls neu)
    cur.execute('''
    CREATE TABLE IF NOT EXISTS laptimes (
        Year INTEGER,
        Track TEXT,
        Team TEXT,
        LapNumber INTEGER,
        LapTimeSec REAL,
        Compound TEXT,
        TyreLife INTEGER,
        AirTemp REAL,
        IsRaining INTEGER,
        IsOutlap INTEGER,
        IsPitstop INTEGER
    )
    ''')
    conn.commit()

    for year in years:
        try:
            schedule = _call_fastf1_with_retry(
                f"den Rennkalender für {year} zu laden",
                lambda: fastf1.get_event_schedule(year),
                progress_callback=progress_callback,
            )
        except Exception as e:
            print(f"Fehler beim Laden des Rennkalenders für {year}: {e}")
            continue

        # Nur die Events laden, die später auch für Training und Vorhersage genutzt werden.
        filtered_events = schedule[schedule['EventName'].isin(track_list)]

        for _, event in filtered_events.iterrows():
            track_name = event['EventName']
            # Prüfen, ob dieses Jahr+Track bereits in der DB existiert
            cur.execute("SELECT 1 FROM laptimes WHERE Year=? AND Track=? LIMIT 1", (year, track_name))
            if cur.fetchone():
                print(f"Skip (bereits vorhanden): {year} {track_name}")
                continue

            try:
                print(f"Lade {year} {track_name}...")
                session = _call_fastf1_with_retry(
                    f"die Session {year} {track_name} zu laden",
                    lambda: fastf1.get_session(year, event['RoundNumber'], 'R'),
                    progress_callback=progress_callback,
                )

                # Nur die Daten laden, die nachher im ML-Training wirklich verwendet werden.
                session.load(laps=True, telemetry=False, weather=True, messages=False)

                required_lap_columns = ['LapNumber', 'LapTime', 'Compound', 'TyreLife', 'PitOutTime', 'PitInTime', 'Team', 'Time']
                laps = session.laps.pick_teams(team_list)[required_lap_columns].copy()
                if laps.empty:
                    print(f"Keine Laps für Teams: {year} {track_name}")
                    continue

                weather = session.weather_data[['Time', 'AirTemp', 'Rainfall']].copy()
                weather['Time'] = weather['Time'].dt.total_seconds() # Wir runden die Zeitstempel, um sie mit den Laps zu matchen
                weather_seconds = weather['Time'].to_numpy()
                rain_flags = weather['Rainfall'].fillna(0).to_numpy()

                # Hilfsfunktion: Gab es Regen während dieser Runde?
                def check_rain(lap_row):
                    """Prüft, ob während der Runde Regen auftrat."""
                    if pd.isna(lap_row['Time']) or pd.isna(lap_row['LapTime']):
                        return 0

                    end = lap_row['Time'].total_seconds()
                    start = end - lap_row['LapTime'].total_seconds()
                    start_idx = weather_seconds.searchsorted(start, side='left')
                    end_idx = weather_seconds.searchsorted(end, side='right')
                    return 1 if rain_flags[start_idx:end_idx].any() else 0

                # Zeit in Sekunden umwandeln
                laps['LapTimeSec'] = laps['LapTime'].dt.total_seconds()

                # Nötige Spalten für ML Modell
                laps['IsRaining'] = laps.apply(check_rain, axis=1) # Pro Runde prüfen
                laps['AirTemp'] = weather['AirTemp'].mean() # Durchschnitt für die Session
                laps['Track'] = track_name
                laps['Year'] = year
                laps['IsOutlap'] = laps['PitOutTime'].notnull().astype(int)
                laps['IsPitstop'] = laps['PitInTime'].notnull().astype(int)

                # Bereinigen und Speichern
                db_data = laps.dropna(subset=[
                    'Year', 'Track', 'Team', 'LapNumber', 'LapTimeSec', 
                    'Compound', 'TyreLife', 'AirTemp', 'IsRaining', 'IsOutlap', 'IsPitstop'
                ])[[
                    'Year', 'Track', 'Team', 'LapNumber', 'LapTimeSec', 
                    'Compound', 'TyreLife', 'AirTemp', 'IsRaining', 'IsOutlap', 'IsPitstop'
                ]]

                db_data.to_sql('laptimes', conn, if_exists='append', index=False)
                print(f"Erfolg: {year} {track_name}")

            except Exception as e:
                print(f"Skip {year} {track_name}: {e}")

    conn.close()
    # Rückgabe-Status über Rate-Limit-Ereignisse
    return {
        'rate_limited': bool(_RATE_LIMITED_OCCURRED),
        'max_wait_seconds': int(round(_MAX_WAIT_SECONDS))
    }