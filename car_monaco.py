"""This is the car_monaco module which defines a Class for cars on monaco, while the Class inherits from Car"""
from car import Car

class Car_Monaco(Car):
    """This is the Car_Monaco class which defines a Class for cars on monaco, while the Class inherits from Car"""
    
    def __init__(self, driver, tire, tire_age):
        """This is the constructor for the Car_Monaco class which defines a Class for cars on monaco, while the Class inherits from Car"""
        super().__init__(driver, tire, tire_age)

    def calculate_lap_time(self):
        """This is the method which calculates the lap time for the car on monaco"""
        if self.safety_car:
            self.lap_time = 150  # Must be adapted based on ML
            return self.lap_time
        
        else:
            base_time = 90.0  # Base lap time in seconds, must be adapted based on ML
            if self.tire == 'soft':
                tire_factor = 0.8 + (self.tire_age * 0.05) # Tire factor, must be adapted based on ML
            elif self.tire == 'medium':
                tire_factor = 1.0 + (self.tire_age * 0.03) # Tire factor, must be adapted based on ML
            elif self.tire == 'hard':
                tire_factor = 1.2 + (self.tire_age * 0.01) # Tire factor, must be adapted based on ML
        
            self.lap_time = base_time * tire_factor
            return self.lap_time

    def box(self, new_tire):
        """This is the method which simulates a pit stop for the car on monaco"""
        super().box(new_tire)
        self.lap_time += 20.0  # Add time for pit stop, must be adapted based on ML

    