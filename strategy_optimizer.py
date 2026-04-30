import pandas as pd
import joblib
import numpy as np
import os
from ML_lap_times import predict_lap_time

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
    # 1. Pre-calculate ALL possible lap times for BOTH tires up front (Only 156 predictions instead of 4,600!)
    time_on_start_tire = []
    time_on_target_tire = []
    
    for lap in range(1, total_laps + 1):
        time_on_start_tire.append(predict_lap_time(track_name, team, start_compound, lap, air_temp))
        time_on_target_tire.append(predict_lap_time(track_name, team, next_compound, lap, air_temp))
        
    best_total_time = float('inf')
    best_lap = 0

    # 2. Now just do basic math to find the best combination
    for pit_lap in range(10, total_laps - 5):
        # Slice the lists: Start tire from Lap 1 until the pit lap, then Target tire to the end
        # (We use pit_lap - 1 because Python lists start at 0)
        stint_1_time = sum(time_on_start_tire[:pit_lap - 1])
        stint_2_time = sum(time_on_target_tire[pit_lap - 1:])
        
        # Total time is Stint 1 + Stint 2 + Pit Stop Time
        total_race_time = stint_1_time + stint_2_time + 22.0
        
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
