"""This is the car module, which contains the Car class."""

import joblib
import pandas as pd
import os
from ML_lap_times import train_dry_models

class Car:
    """This is the Car class, which represents a F1 car."""

    def __init__(self, team, track, tire):
        """Initialize the Car object."""
        self._team = team
        self._track = track
        self.tire = tire
        self.tire_age = 0
        self.lap = 1
        self.lap_time = 0.0
        self.race_history = []
        self.total_time = 0.0
        self.safety_car = False
        self.pitstop_counter = 0

    @property
    def team(self):
        """Return the cars driver."""
        return self._team
    
    @property
    def track(self):
        """Return the cars track."""
        return self._track
        
    @property
    def tire(self):
        """Return the cars tire."""
        return self._tire
    
    @tire.setter
    def tire(self, value):
        """Set the cars tire."""
        if value not in ["SOFT", "MEDIUM", "HARD"]:
            raise ValueError("Tire must be 'SOFT', 'MEDIUM', or 'HARD'.")
        self._tire = value

    @property
    def tire_age(self):
        """Return the cars tire age."""
        return self._tire_age
    
    @tire_age.setter
    def tire_age(self, value):
        """Set the cars tire age."""
        if value < 0:
            raise ValueError("Tire age cannot be negative.")
        self._tire_age = value

    @property
    def lap(self):
        """Return the cars current lap."""
        return self._lap
    
    @lap.setter
    def lap(self, value):
        """Set the cars current lap."""
        if value < 1:
            raise ValueError("Lap must be at least 1.")
        self._lap = value

    @property
    def lap_time(self):
        """Return the cars lap time."""
        return self._lap_time
    
    @lap_time.setter
    def lap_time(self, value):
        """Set the cars lap time."""
        if value < 0:
            raise ValueError("Lap time cannot be negative.")
        self._lap_time = value

    @property
    def race_history(self):
        """Return the race history of the car (a list of lap times)."""
        return self._race_history
    
    @race_history.setter
    def race_history(self, value):
        """Set the race history of the car (a list of lap times)."""
        if not isinstance(value, list):
            raise ValueError("Race history must be a list of lap times.")
        self._race_history = value

    @property
    def total_time(self):      
        """Return the cars total time."""
        return self._total_time
    
    @total_time.setter
    def total_time(self, value):
        """Set the cars total time."""
        if value < 0:
            raise ValueError("Total time cannot be negative.")
        self._total_time = value

    @property
    def safety_car(self):
        """Return whether the car is under safety car conditions."""
        return self._safety_car
    
    @safety_car.setter
    def safety_car(self, value):
        """Set whether the car is under safety car conditions."""
        if not isinstance(value, bool):
            raise ValueError("Safety car must be a boolean value.")
        self._safety_car = value

    @property
    def pitstop_counter(self):        
        """Return the number of pitstops the car has made."""
        return self._pitstop_counter   

    @pitstop_counter.setter
    def pitstop_counter(self, value):
        """Set the number of pitstops the car has made."""
        if value < 0:
            raise ValueError("Pitstop counter cannot be negative.")
        self._pitstop_counter = value 

    def advance_lap(self):
        """Simulate the car advancing to the next lap."""
        self.total_time += self.lap_time
        self.race_history.append({'Lap': self.lap, 'Lap Time': self.lap_time, 'Tire': self.tire, 'Tire Age': self.tire_age, 'Pitstop': 'No'})
        self.lap += 1
        self.tire_age += 1

    def box(self, new_tire):
        """Simulate the car going to the box and changing tires."""
        self.tire = new_tire
        self.tire_age = 0
        self.total_time += self.lap_time # The additional time for pitstop is added at subclass
        self.race_history.append({'Lap': self.lap, 'Lap Time': self.lap_time, 'Tire': self.tire, 'Tire Age': self.tire_age, 'Pitstop': 'Yes'})
        self.lap += 1
        self.pitstop_counter += 1
        self.lap_time += 20.0 # Simulate the time lost in the pitstop (this can be adjusted based on the track and conditions)

    def age_tires(self, laps):
        """Simulate the car aging its tires by a certain number of laps."""
        self.tire_age += laps

    def predict_lap_time(self, air_temp=25, is_raining=False):
        """Vorhersage der Rundenzeit basierend auf dem entsprechenden ML Modell."""

        if is_raining == False:
            track_id = self.track.replace(' ', '_')
            model_path = f'models/dry/rf_{track_id}.pkl'
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Model file not found for track {self.track}. Please train the model first.")
            model = joblib.load(model_path)
            saved_cols = joblib.load(f'models/dry/cols_{track_id}.pkl')
            base_path = f'models/dry/base_{track_id}.pkl'
            compound_baseline = joblib.load(base_path) if os.path.exists(base_path) else None

            # add live data to the model input
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
            if compound_baseline is not None:
                prediction += float(compound_baseline.get(self.tire, 0.0))

            # if self.safety_car:
            # prediction *= 1.5 # Safety car conditions increase lap time by 50%

            self.lap_time = prediction
            return prediction

    def __repr__(self):
        """return a string representation for repr()."""
        return f"Car(driver={self.driver}, team={self.team}, tire={self.tire}, tire_age={self.tire_age})"
    
    def __str__(self):
        """return a string representation for str()."""
        return f"{self.driver} is driving for {self.team} with {self.tire} tires that are {self.tire_age} laps old."
    
    