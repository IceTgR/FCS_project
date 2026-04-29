"""This is the car module, which contains the Car class."""

import joblib
import pandas as pd
import os
import random
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
        self.pitstop_counter = 0
        self._outlap_pending = False

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
    def pitstop_counter(self):        
        """Return the number of pitstops the car has made."""
        return self._pitstop_counter   

    @pitstop_counter.setter
    def pitstop_counter(self, value):
        """Set the number of pitstops the car has made."""
        if value < 0:
            raise ValueError("Pitstop counter cannot be negative.")
        self._pitstop_counter = value 

    def _race_comment(self, lap_type, safety_event_status=None):
        """Build a human-readable comment for the race log."""
        comment_parts = []

        if lap_type != 'Normal':
            comment_parts.append(lap_type)

        if safety_event_status == 'SAFETYCAR':
            comment_parts.append('Safety Car')
        elif safety_event_status == 'VSC':
            comment_parts.append('VSC')

        return ', '.join(comment_parts)

    def advance_lap(self, safety_event_status=None):
        """Simulate the car advancing to the next lap."""
        self.total_time += self.lap_time
        # Determine lap type: Outlap if coming out of pit stop, Normal otherwise
        lap_type = 'Outlap' if self._outlap_pending else 'Normal'
        self.race_history.append({'Lap': self.lap, 'Lap Time': self.lap_time, 'Tire': self.tire, 'Tire Age': self.tire_age, 'Kommentar': self._race_comment(lap_type, safety_event_status)})
        if self._outlap_pending:
            self._outlap_pending = False
        self.lap += 1
        self.tire_age += 1

    def inlap_penalty(self):
        """Return the total extra time lost on the inlap.

        In Formula 1 the stop time is counted into the lap that enters the pit
        lane, not as a separate racing lap. We therefore calculate the complete lost time
        from the pitstop here.
        """
        pit_loss = random.uniform(19.5, 25.0)
        return pit_loss

    def outlap_penalty(self):
        """Return the extra time for the first lap after the pit stop.

        The outlap is slower because the tires and brakes are cold and the car
        needs one lap to get back into a normal operating window. We randomize
        this slightly because tire warm-up is not identical every time.
        """
        return random.uniform(0.6, 1.4)

    def box(self, new_tire, safety_event_status=None, pitstop_multiplier=1.0):
        """Simulate the car going to the box and changing tires."""
        # The pit stop is counted into the inlap time, so we add the full
        # combined penalty before storing the lap in the race history.
        self.lap_time += self.inlap_penalty() * pitstop_multiplier
        
        # Store the old tire info before changing it, for the race history entry
        old_tire = self.tire
        old_tire_age = self.tire_age
        
        # Now change the tire
        self.tire = new_tire
        self.tire_age = 0
        self.total_time += self.lap_time
        
        # Record the inlap with the OLD tire and OLD tire age
        self.race_history.append({'Lap': self.lap, 'Lap Time': self.lap_time, 'Tire': old_tire, 'Tire Age': old_tire_age, 'Kommentar': self._race_comment('Inlap', safety_event_status)})
        self.lap += 1
        self.pitstop_counter += 1
        # The next lap after the stop is the outlap, so the following ML
        # prediction should include an extra penalty once.
        self._outlap_pending = True

    def age_tires(self, laps):
        """Simulate the car aging its tires by a certain number of laps."""
        self.tire_age += laps

    def tire_wear_penalty(self):
        """Return a manual tire wear penalty in seconds.

        We keep this outside the ML model because the training data mostly
        contains stints that end before tires become truly extreme. That means
        the model cannot reliably learn a strong wear curve from data alone.

        The penalty is different for each compound because soft tires degrade
        faster, medium tires sit in the middle, and hard tires are more stable.
        We use a quadratic increase after a compound-specific threshold because
        tire degradation usually accelerates as the stint gets longer.
        A small random factor keeps the simulation from feeling perfectly static.
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
        # Use the current tire compound directly..
        profile = wear_profiles[self.tire]

        # Before the threshold, the tire is assumed to be in a usable window.
        # After that, we add a quadratic term so the degradation accelerates
        # with stint length instead of growing only linearly.
        if self.tire_age <= profile['threshold']:
            return 0.0

        wear_laps = self.tire_age - profile['threshold']
        penalty = (wear_laps ** 2) * profile['quadratic'] + wear_laps * profile['linear']

        # Add a small random variation so the effect does not look perfectly linear.
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

            # Apply the outlap penalty once directly after a pit stop.
            # We keep this outside the ML model because outlaps are driven by
            # cold tires and brakes, which are not represented cleanly in the
            # race-lap training data.
            if self._outlap_pending:
                prediction += self.outlap_penalty()
                self._outlap_pending = False

            # Add a manual tire wear penalty on top of the ML prediction.
            # This is intentional: the available race data does not contain enough
            # very long stints for the model to learn the degradation curve well.
            # The ML model still provides the baseline pace, while this term
            # enforces the visible drop-off from tire aging.
            prediction += self.tire_wear_penalty()

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
    
    