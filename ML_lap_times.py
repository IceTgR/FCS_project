# Here we create the Machine Learning part and train our models.
import pandas as pd
import sqlite3
import joblib
import os
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error


# Dry model: We will use a Random Forest Regressor to predict lap times in dry conditions.
# We chose this because it can capture complex, non-linear relationships and is robust.
# The chance of overfitting is also reduced.

def train_dry_models(df_dry):
    # Create directory for dry models if it doesn't exist
    if not os.path.exists('models/dry'):
        os.makedirs('models/dry')

    # Get unique tracks because we will train a separate model for each track
    tracks = df_dry['Track'].unique()

    # Initialize results dictionary to store MAE for each track
    results = {}

    # Train a model per track
    for track in tracks:
        track_df = df_dry[df_dry['Track'] == track].copy() # get data for the track

        # Prepare features and target variable
        # Features include polynomial tire degradation to capture realistic tire wear patterns
        features = ['LapNumber', 'TyreLife', 'TyreLifeSquared', 'TyreLifeCubed', 'TyreLifeLog', 'AirTemp', 'Team', 'Compound']
        X = pd.get_dummies(track_df[features], columns=['Team', 'Compound'])
        y = track_df['LapTimeSec']

        # Split data into training and testing sets, to evaluate our model's performance
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Initialize and train the Random Forest Regressor with optimized hyperparameters
        # max_depth=15: Reduces overfitting while capturing non-linear relationships
        # min_samples_leaf=5: Ensures leaves have enough samples for robust predictions
        # min_samples_split=10: Prevents tree from learning noise in data
        model = RandomForestRegressor(
            n_estimators=150,           # More trees = better generalization
            max_depth=15,               # Shallower trees reduce overfitting
            min_samples_leaf=5,         # Minimum samples per leaf
            min_samples_split=10,       # Minimum samples to split a node
            random_state=42
        )
        model.fit(X_train, y_train)

        # Evaluate the model on the test set
        predictions = model.predict(X_test)
        mae = mean_absolute_error(y_test, predictions)
        print(f'Durchschnittlicher Fehler (MAE) für {track}: {mae:.3f} Sekunden')
        
        # Show feature importance to understand tire wear impact
        feature_importance = pd.DataFrame({
            'Feature': X.columns,
            'Importance': model.feature_importances_
        }).sort_values('Importance', ascending=False)
        print(f'\n📊 Top Features für {track}:')
        print(feature_importance.head(10).to_string(index=False))
        print()
    
        # Save the trained model for later use
        track_id = track.replace(' ', '_') # replace spaces with underscores for file naming
        joblib.dump(model, f'models/dry/rf_{track_id}.pkl')
        joblib.dump(X.columns.tolist(), f'models/dry/cols_{track_id}.pkl') # save the feature names for later use

        results[track] = mae
        print(f'Modell für {track} gespeichert.')

    return results