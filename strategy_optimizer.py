import pandas as pd
import joblib
import numpy as np
import os

def load_track_model(track_name, condition="dry"):
    """Loads the trained ML model and its training columns for a specific track."""
    # Convert "Monaco Grand Prix" to "Monaco_Grand_Prix" to match the saved files
    track_id = track_name.replace(' ', '_') 
    
    # Update the paths to match what ML_lap_times.py is saving
    model_path = f"models/{condition}/rf_{track_id}.pkl"
    cols_path = f"models/{condition}/cols_{track_id}.pkl"
    
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model for {track_name} not found at {model_path}. Train it first!")
        
    model = joblib.load(model_path)
    train_columns = joblib.load(cols_path) 
    
    return model, train_columns

def simulate_race_time(model, train_cols, total_laps, team, start_compound, next_compound, pit_lap, air_temp, pit_loss_sec=22.0):
    """Simulates the total race time for a specific pit strategy."""
    
    total_time = 0.0
    tyre_life = 1
    current_compound = start_compound
    
    # Create a list to store lap data before turning it into a DataFrame (for speed)
    laps_data = []
    
    for lap in range(1, total_laps + 1):
        # Check if this is the pit stop lap
        if lap == pit_lap:
            current_compound = next_compound
            tyre_life = 1 # Reset tyre life on out-lap
            total_time += pit_loss_sec # Add the time penalty for driving through pit lane
            
        laps_data.append({
            'LapNumber': lap,
            'TyreLife': tyre_life,
            'AirTemp': air_temp,
            'Team': team,
            'Compound': current_compound
        })
        
        tyre_life += 1

    # Convert simulation to DataFrame
    df_sim = pd.DataFrame(laps_data)
    
    # One-hot encode Team and Compound exactly as the model expects
    X_sim = pd.get_dummies(df_sim, columns=['Team', 'Compound'])
    
    # Ensure all columns from training are present (fill missing with 0)
    # This is crucial because if we only simulate 'SOFT' and 'HARD', the model might crash looking for 'MEDIUM'
    X_sim = X_sim.reindex(columns=train_cols, fill_value=0)
    
    # Predict lap times for the whole race in one go (much faster)
    predicted_lap_times = model.predict(X_sim)
    
    # Add the predicted lap times to our total
    total_time += np.sum(predicted_lap_times)
    
    return total_time

def find_optimal_pit_lap(track_name, total_laps, team, start_compound, next_compound, air_temp):
    """
    Simulates the entire race for every possible pit lap to find the 
    mathematically fastest strategy using ML predictions.
    """
    best_total_time = float('inf')
    best_lap = 0

    # Test every possible lap as a potential pit stop lap (e.g., between lap 10 and the end)
    for pit_lap in range(10, total_laps - 5):
        total_race_time = 0
        current_compound = start_compound
        
        for lap in range(1, total_laps + 1):
            # 1. Predict lap time based on the tire CURRENTLY on the car
            # This uses the ML model to account for tire wear/degradation
            lap_time = predict_lap_time(track_name, team, current_compound, lap, air_temp)
            total_race_time += lap_time
            
            # 2. THE PIT STOP LOGIC:
            # If we reach our 'test' pit lap, swap to the target tire and add pit loss
            if lap == pit_lap:
                current_compound = next_compound # This is your 'Target Pit Tire'
                total_race_time += 22.0          # Estimated time lost in a pit stop (s)
                
        # 3. Compare this strategy to the best one found so far
        if total_race_time < best_total_time:
            best_total_time = total_race_time
            best_lap = pit_lap
            
    return best_lap

# ==========================================
# Example usage:
# ==========================================
# ==========================================
# Example usage: Master Strategy Report for All Teams
# ==========================================
#if __name__ == "__main__":
#    # List of all the teams in your database
#    all_teams = ['Ferrari', 'Mercedes', 'Red Bull', 'McLaren', 'Williams']
#    track = 'Monaco Grand Prix'
#    laps = 78
#    
#    print(f"🏁 MASTER STRATEGY REPORT: {track.upper()} 🏁\n")
#    
#    # Loop through every single team and calculate their unique optimal pit lap
#    for team_name in all_teams:
#        best_lap = find_optimal_pit_lap(
#            track_name=track, 
#            total_laps=laps, 
#            team=team_name, 
#            start_compound='SOFT', 
#            next_compound='HARD', 
#            air_temp=25.0, 
#            pit_window_start=15, 
#            pit_window_end=35
#        )
#        
#        # Print a clear summary line for the team
#        print(f"🏎️  {team_name.upper()} Optimal Strategy: Pit on Lap {best_lap}\n")
#        print("-" * 50 + "\n")
