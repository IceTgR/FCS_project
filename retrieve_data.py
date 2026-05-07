import fastf1
import sqlite3
import pandas as pd
import os
import time
from collections import deque
from fastf1.req import RateLimitExceededError


# einfache in-memory Rate-Limiter (burst + hourly)
_REQ_SEC = deque()
_REQ_HOUR = deque()
_RATE_LIMITED_OCCURRED = False
_MAX_WAIT_SECONDS = 0


def _wait_for_rate_limit():
    now = time.time()
    global _RATE_LIMITED_OCCURRED, _MAX_WAIT_SECONDS
    # clean old timestamps
    while _REQ_SEC and _REQ_SEC[0] <= now - 1:
        _REQ_SEC.popleft()
    while _REQ_HOUR and _REQ_HOUR[0] <= now - 3600:
        _REQ_HOUR.popleft()
    # Burst: max 4 req per second
    if len(_REQ_SEC) >= 4:
        sleep = 1 - (now - _REQ_SEC[0])
        wait = max(0.25, sleep)
        # mark rate-limited (burst)
        _RATE_LIMITED_OCCURRED = True
        _MAX_WAIT_SECONDS = max(_MAX_WAIT_SECONDS, wait)
        print(f"Rate limit (burst) erreicht — warte ca. {wait:.1f}s")
        time.sleep(wait)
        return _wait_for_rate_limit()
    # Sustained: max 500 per hour
    if len(_REQ_HOUR) >= 500:
        sleep = _REQ_HOUR[0] + 3600 - now
        wait = max(1, sleep)
        # mark rate-limited (sustained)
        _RATE_LIMITED_OCCURRED = True
        _MAX_WAIT_SECONDS = max(_MAX_WAIT_SECONDS, wait)
        print(f"Rate limit (sustained) erreicht — warte ca. {wait:.0f}s")
        time.sleep(wait)
        return _wait_for_rate_limit()
    _REQ_SEC.append(now)
    _REQ_HOUR.append(now)


def _safe_get_event_schedule(year, retries=5):
    for attempt in range(retries):
        try:
            _wait_for_rate_limit()
            return fastf1.get_event_schedule(year)
        except RateLimitExceededError:
            time.sleep(2 ** attempt)
        except Exception:
            time.sleep(1)
    raise


def _safe_get_session(year, roundnum, typ, retries=5):
    for attempt in range(retries):
        try:
            _wait_for_rate_limit()
            return fastf1.get_session(year, roundnum, typ)
        except RateLimitExceededError:
            time.sleep(2 ** attempt)
        except Exception:
            time.sleep(1)
    raise


def fastf1_to_sql(years, track_list, team_list):
    '''Lädt die DB von fastf1 und speichert sie in SQLite-DB, damit schnellere Abfragen möglich sind.'''

    # Verzeichnis für Cache erstellen, damit die Daten lokal gespeichert werden und es somit schneller geht
    if not os.path.exists('f1_cache'):
        os.makedirs('f1_cache')
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
            schedule = _safe_get_event_schedule(year)
        except Exception as e:
            print(f"Fehler beim Laden des Rennkalenders für {year}: {e}")
            continue

        # Filtern der Rennstrecken, Benutzung von str.contains für flexible Suche
        filtered_events = schedule[schedule['EventName'].str.contains('|'.join(track_list), case=False)]

        for _, event in filtered_events.iterrows():
            track_name = event['EventName']
            # Prüfen, ob dieses Jahr+Track bereits in der DB existiert
            cur.execute("SELECT 1 FROM laptimes WHERE Year=? AND Track=? LIMIT 1", (year, track_name))
            if cur.fetchone():
                print(f"Skip (bereits vorhanden): {year} {track_name}")
                continue

            try:
                print(f"Lade {year} {track_name}...")
                session = _safe_get_session(year, event['RoundNumber'], 'R')

                # Laden der Runden- und Wetterdaten und Messages, keine Telemetrie für schnellere Verarbeitung
                session.load(laps=True, telemetry=False, weather=True, messages=True)

                laps = session.laps.pick_teams(team_list).copy()
                if laps.empty:
                    print(f"Keine Laps für Teams: {year} {track_name}")
                    continue

                weather = session.weather_data
                weather['Time'] = weather['Time'].dt.total_seconds() # Wir runden die Zeitstempel, um sie mit den Laps zu matchen

                # Hilfsfunktion: Gab es Regen während dieser Runde?
                def check_rain(lap_row):
                    """Prüft, ob während der Runde Regen auftrat."""
                    start = lap_row['Time'].total_seconds() - lap_row['LapTime'].total_seconds()
                    end = lap_row['Time'].total_seconds()
                    rain_in_lap = weather[(weather['Time'] >= start) & (weather['Time'] <= end)]['Rainfall']
                    return 1 if rain_in_lap.any() else 0

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
        'max_wait_seconds': int(_MAX_WAIT_SECONDS)
    }