"""Auto-Modul mit Car-Klasse für F1-Rennverhalten."""

import joblib
import pandas as pd
import os
import random
from ML_lap_times import train_dry_models

class Car:
    """Repräsentiert einen F1-Rennwagen mit Leistung und Rennhistorie."""

    def __init__(self, team, track, tire):
        """Initialisiert Auto mit Team, Strecke und Startreifen."""
        self._team = team
        self._track = track
        self.tire = tire
        self.tire_age = 0
        self.lap = 1
        self.lap_time = 0.0
        self.race_history = []
        self.total_time = 0.0
        self.pitstop_counter = 0
        self.outlap_pending = False
        self.outlap_comment_pending = False

    @property
    def team(self):
        """Gibt das Team des Autos zurück."""
        return self._team
    
    @property
    def track(self):
        """Gibt die Rennstrecke zurück."""
        return self._track
        
    @property
    def tire(self):
        """Gibt die aktuelle Reifenmischung zurück."""
        return self._tire
    
    @tire.setter
    def tire(self, value):
        """Setzt die Reifenmischung (SOFT, MEDIUM, HARD)."""
        if value not in ["SOFT", "MEDIUM", "HARD"]:
            raise ValueError("Tire must be 'SOFT', 'MEDIUM', or 'HARD'.")
        self._tire = value

    @property
    def tire_age(self):
        """Gibt das Alter des Reifens in Runden zurück."""
        return self._tire_age
    
    @tire_age.setter
    def tire_age(self, value):
        """Setzt das Reifenalter."""
        if value < 0:
            raise ValueError("Tire age cannot be negative.")
        self._tire_age = value

    @property
    def lap(self):
        """Gibt die aktuelle Rundennummer zurück."""
        return self._lap
    
    @lap.setter
    def lap(self, value):
        """Setzt die aktuelle Rundennummer."""
        if value < 1:
            raise ValueError("Lap must be at least 1.")
        self._lap = value

    @property
    def lap_time(self):
        """Gibt die Rundenzeit in Sekunden zurück."""
        return self._lap_time
    
    @lap_time.setter
    def lap_time(self, value):
        """Setzt die Rundenzeit in Sekunden."""
        if value < 0:
            raise ValueError("Lap time cannot be negative.")
        self._lap_time = value

    @property
    def race_history(self):
        """Gibt die Rennhistorie als Liste zurück."""
        return self._race_history
    
    @race_history.setter
    def race_history(self, value):
        """Setzt die Rennhistorie."""
        if not isinstance(value, list):
            raise ValueError("Race history must be a list of lap times.")
        self._race_history = value

    @property
    def total_time(self):
        """Gibt die Gesamtzeit des Rennens zurück."""
        return self._total_time
    
    @total_time.setter
    def total_time(self, value):
        """Setzt die Gesamtzeit des Rennens."""
        if value < 0:
            raise ValueError("Total time cannot be negative.")
        self._total_time = value

    @property
    def pitstop_counter(self):
        """Gibt die Anzahl der Boxenstopps zurück."""
        return self._pitstop_counter   

    @pitstop_counter.setter
    def pitstop_counter(self, value):
        """Setzt die Anzahl der Boxenstopps."""
        if value < 0:
            raise ValueError("Pitstop counter cannot be negative.")
        self._pitstop_counter = value 

    @property
    def outlap_pending(self):
        """Gibt zurück, ob eine Outlap nach dem Boxenstopp aussteht."""
        return self._outlap_pending
    
    @outlap_pending.setter
    def outlap_pending(self, value):
        """Setzt die ausstehende Outlap."""
        if not isinstance(value, bool):
            raise ValueError("outlap_pending must be a boolean value.")
        self._outlap_pending = value

    @property
    def outlap_comment_pending(self):
        """Gibt zurück, ob ein Outlap-Kommentar aussteht."""
        return self._outlap_comment_pending
    
    @outlap_comment_pending.setter
    def outlap_comment_pending(self, value):
        """Setzt den ausstehenden Outlap-Kommentar."""
        self._outlap_comment_pending = value

    def _race_comment(self, lap_type, safety_event_status=None):
        """Erstellt Kommentar für Rennprotokoll mit Rundentyp und Event-Status."""
        comment_parts = []

        if lap_type != 'Normal':
            comment_parts.append(lap_type)

        if safety_event_status == 'SAFETYCAR':
            comment_parts.append('Safety Car')
        elif safety_event_status == 'VSC':
            comment_parts.append('VSC')

        return ', '.join(comment_parts)

    def advance_lap(self, safety_event_status=None):
        """Verarbeitet Auto zur nächsten Runde und aktualisiert Historie."""
        self.total_time += self.lap_time
        # Bestimme Rundentyp: Outlap nach Boxenstopp oder Normal.
        lap_type = 'Outlap' if self._outlap_comment_pending else 'Normal'
        self.race_history.append({'Runde': self.lap, 'Rundenzeit': self.lap_time, 'Reifen': self.tire, 'Reifenalter': self.tire_age, 'Kommentar': self._race_comment(lap_type, safety_event_status)})
        if self._outlap_comment_pending:
            self._outlap_comment_pending = False
        self.lap += 1
        self.tire_age += 1

    def inlap_penalty(self):
        """Gibt Zeitverlust der Inlap des Boxenstopps in Sekunden zurück."""
        pit_loss = random.uniform(19.5, 25.0)
        return pit_loss

    def outlap_penalty(self):
        """Gibt Zeitverlust der Outlap nach Boxenstopp zurück."""
        return random.uniform(0.6, 1.4)

    def box(self, new_tire, safety_event_status=None, pitstop_multiplier=1.0):
        """Führt Boxenstopp durch und wechselt Reifenmischung."""
        # Boxenstopp-Zeit wird in der Inlap-Rundenzeit addiert.
        self.lap_time += self.inlap_penalty() * pitstop_multiplier
        
        # Speichere alte Reifen-Daten vor dem Wechsel
        old_tire = self.tire
        old_tire_age = self.tire_age
        
        # Wechsle zur neuen Reifenmischung
        self.tire = new_tire
        self.tire_age = 0
        self.total_time += self.lap_time
        
        # Speichere Inlap mit alten Reifen-Daten.
        self.race_history.append({'Runde': self.lap, 'Rundenzeit': self.lap_time, 'Reifen': old_tire, 'Reifenalter': old_tire_age, 'Kommentar': self._race_comment('Inlap', safety_event_status)})
        self.lap += 1
        self.pitstop_counter += 1
        # Die nächste Runde ist die Outlap; dafür einmal Zusatzverlust einplanen.
        self._outlap_pending = True
        self._outlap_comment_pending = True

    def age_tires(self, laps):
        """Erhöht das Reifenalter um eine Anzahl Runden."""
        self.tire_age += laps

    def tire_wear_penalty(self):
        """Gibt einen manuellen Reifenverschleiß-Aufschlag in Sekunden zurück.

        Außerhalb des ML-Modells, weil sehr lange Stints in den Trainingsdaten
        unterrepräsentiert sind. Nach einem Mischungs-Schwellwert steigt der
        Aufschlag quadratisch an; ein kleiner Zufallsfaktor variiert das Ergebnis.
        """
        wear_profiles = {
            'SOFT': {
                'threshold': 8,
                'quadratic': 0.015,
                'linear': 0.08,
                'random_low': 0.96,
                'random_high': 1.04,
            },
            'MEDIUM': {
                'threshold': 12,
                'quadratic': 0.012,
                'linear': 0.06,
                'random_low': 0.97,
                'random_high': 1.03,
            },
            'HARD': {
                'threshold': 18,
                'quadratic': 0.008,
                'linear': 0.04,
                'random_low': 0.98,
                'random_high': 1.02,
            },
        }
        # Nutze direkt die aktuelle Reifenmischung.
        profile = wear_profiles[self.tire]

        # Bis zum Schwellwert gilt der Reifen als stabil.
        # Danach steigt der Verschleiß beschleunigt statt nur linear.
        if self.tire_age <= profile['threshold']:
            return 0.0

        wear_laps = self.tire_age - profile['threshold']
        penalty = (wear_laps ** 2) * profile['quadratic'] + wear_laps * profile['linear']

        # Kleine Zufallsvarianz für realistischere Entwicklung.
        penalty *= random.uniform(profile['random_low'], profile['random_high'])
        return penalty

    def predict_lap_time(self, air_temp=25, is_raining=False):
        """Vorhersage der Rundenzeit basierend auf dem entsprechenden ML Modell."""

        if is_raining == False:
            track_id = self.track.replace(' ', '_')
            model_path = f'models/dry/rf_{track_id}.pkl'
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Model file not found for track {self.track}. Please train the model first.")
            model = joblib.load(model_path)
            saved_cols = joblib.load(f'models/dry/cols_{track_id}.pkl')

            # Live-Daten zum Modellinput ergänzen.
            row = {
                'Team': self.team,
                'Compound': self.tire,
                'TyreLife': self.tire_age,
                'AirTemp': air_temp,
                'LapNumber': self.lap,
            }

            df = pd.DataFrame([row])
            df = pd.get_dummies(df, columns=['Team', 'Compound'])
            df = df.reindex(columns=saved_cols, fill_value=0)

            prediction = float(model.predict(df)[0])

            # Outlap-Aufschlag einmal direkt nach dem Boxenstopp anwenden.
            # Das bleibt außerhalb des ML-Modells.
            if self._outlap_pending:
                prediction += self.outlap_penalty()
                self._outlap_pending = False

            # Manuellen Reifenverschleiß-Aufschlag auf die ML-Basis addieren.
            prediction += self.tire_wear_penalty()

            # if self.safety_car:
            # prediction *= 1.5 # Safety car conditions increase lap time by 50%

            self.lap_time = prediction
            return prediction

    def __repr__(self):
        """Gibt die technische String-Darstellung zurück."""
        return f"Car(driver={self.driver}, team={self.team}, tire={self.tire}, tire_age={self.tire_age})"
    
    def __str__(self):
        """Gibt die lesbare String-Darstellung zurück."""
        return f"{self.driver} is driving for {self.team} with {self.tire} tires that are {self.tire_age} laps old."
    
    