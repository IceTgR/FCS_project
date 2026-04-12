"""This is the car_silverstone module which defines a Class for cars on silverstone, while the Class inherits from Car"""
from car import Car

class Car_Silverstone(Car):
    """This is the Car_Silverstone class which defines a Class for cars on Silverstone, while the Class inherits from Car"""
    
    def __init__(self, driver, tire):
        """This is the constructor for the Car_Silverstone class which defines a Class for cars on Silverstone, while the Class inherits from Car"""
        super().__init__(driver, tire)

    def calculate_lap_time(self):
        """This is the method which calculates the lap time for the car on silverstone"""
        if self.safety_car:
            self.lap_time = 150  # Must be adapted based on ML
            return self.lap_time
        
        base_time = 100.0  # Base lap time in seconds, must be adapted based on ML
        if self.tire == 'soft':
            tire_factor = 0.7 + (self.tire_age * 0.06) # Tire factor, must be adapted based on ML
        elif self.tire == 'medium':
            tire_factor = 1.0 + (self.tire_age * 0.025) # Tire factor, must be adapted based on ML
        elif self.tire == 'hard':
            tire_factor = 1.25 + (self.tire_age * 0.015) # Tire factor, must be adapted based on ML
        
        self.lap_time = base_time * tire_factor
        return self.lap_time

    def box(self, new_tire):
        """This is the method which simulates a pit stop for the car on silverstone"""
        self.lap_time += 25.0  # Add time for pit stop, must be adapted based on ML
        super().box(new_tire)


    