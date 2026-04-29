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

def find_optimal_pit_lap(track_name, total_laps, team, start_compound, next_compound, air_temp, pit_window_start, pit_window_end):
    """Loops through all realistic pit laps to find the minimum total race time."""
    
    print(f"--- Strategy Analysis: {team} at {track_name} ---")
    print(f"Strategy: {start_compound} -> {next_compound}")
    
    # Load the ML model
    model, train_cols = load_track_model(track_name)
    
    best_lap = None
    best_time = float('inf')
    
    # Test every single lap in the pit window
    for pit_lap in range(pit_window_start, pit_window_end + 1):
        race_time = simulate_race_time(
            model=model,
            train_cols=train_cols,
            total_laps=total_laps,
            team=team,
            start_compound=start_compound,
            next_compound=next_compound,
            pit_lap=pit_lap,
            air_temp=air_temp,
            pit_loss_sec=22.0 # Average pit lane loss
        )
        
        # Convert total seconds to Hours:Minutes:Seconds for readability
        hours, remainder = divmod(race_time, 3600)
        minutes, seconds = divmod(remainder, 60)
        time_str = f"{int(hours)}h {int(minutes)}m {seconds:.2f}s"
        
        print(f"Pit Lap {pit_lap}: Est. Race Time = {time_str}")
        
        if race_time < best_time:
            best_time = race_time
            best_lap = pit_lap
            
    # Print the final verdict
    print("\n✅ OPTIMAL STRATEGY FOUND ✅")
    print(f"The AI recommends pitting on Lap {best_lap}.")
    
    return best_lap

# ==========================================
# Example usage:
# ==========================================
if __name__ == "__main__":
    # You can change these variables to test different tracks and teams
    optimal_lap = find_optimal_pit_lap(
        track_name='Monaco', 
        total_laps=78, 
        team='Ferrari', 
        start_compound='SOFT', 
        next_compound='HARD', 
        air_temp=25.0, 
        pit_window_start=15, 
        pit_window_end=35
    )
