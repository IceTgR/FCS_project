"""This is the car module, which contains the Car class."""

class Car:
    """This is the Car class, which represents a F1 car."""

    def __init__(self, driver, tire):
        """Initialize the Car object."""
        self._driver = driver
        self._team = 'Ferrari'
        self.tire = tire
        self.tire_age = 0
        self.lap = 1
        self.lap_time = 0.0
        self.total_time = 0.0
        self.safety_car = False

    @property
    def driver(self):
        """Return the cars driver."""
        return self._driver
    
    @property
    def team(self):
        """Return the cars team."""
        return self._team
    
    @property
    def tire(self):
        """Return the cars tire."""
        return self._tire
    
    @tire.setter
    def tire(self, value):
        """Set the cars tire."""
        if value not in ["soft", "medium", "hard"]:
            raise ValueError("Tire must be 'soft', 'medium', or 'hard'.")
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

    def advance_lap(self):
        """Simulate the car advancing to the next lap."""
        self.total_time += self.lap_time
        self.lap += 1
        self.tire_age += 1

    def box(self, new_tire):
        """Simulate the car going to the box and changing tires."""
        self.tire = new_tire
        self.tire_age = 0

    def age_tires(self, laps):
        """Simulate the car aging its tires by a certain number of laps."""
        self.tire_age += laps

    def __repr__(self):
        """return a string representation for repr()."""
        return f"Car(driver={self.driver}, team={self.team}, tire={self.tire}, tire_age={self.tire_age})"
    
    def __str__(self):
        """return a string representation for str()."""
        return f"{self.driver} is driving for {self.team} with {self.tire} tires that are {self.tire_age} laps old."
    
    