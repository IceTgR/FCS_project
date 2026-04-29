# Here we preprocess the retrieved data so that it is ready for training our ML models.
import sqlite3
import pandas as pd

def get_preprocessed_datasets():
    """This function will return the preprocessed datasets, split into wet and dry, ready for training our ML models."""
    # Loading data from SQL
    conn = sqlite3.connect('f1_project.db')
    df = pd.read_sql("SELECT * FROM laptimes", conn)
    conn.close()

    # Tyre Mapping: Due to different tyre compounds being used in different seasons,
    # we need to create a mapping to standardize the tyre types across all seasons.
    tyre_map = {
        'SOFT': 'SOFT', 'SUPERSOFT': 'SOFT', 'ULTRASOFT': 'SOFT', 'HYPERSOFT': 'SOFT',
        'MEDIUM': 'MEDIUM',
        'HARD': 'HARD',
        'INTERMEDIATE': 'INTERMEDIATE',
        'WET': 'WET',
    }
    df['Compound'] = df['Compound'].map(tyre_map)

    # Lap Filtering: We remove everything, which is not a "clean" lap to ensure data quality for better ML results.
    df_clean = df[
        (df['IsOutlap'] == 0) &      # Remove outlaps (will implement this logic manually)
        (df['IsPitstop'] == 0)       # Remove inlaps (will implement this logic manually)
    ].copy()

    # Splitting into wet and dry datasets
    dry_tyres = ['SOFT', 'MEDIUM', 'HARD']
    wet_tyres = ['INTERMEDIATE', 'WET']

    # Dry dataset: Only dry tyres AND no rain flag to ensure data quality
    df_dry = df_clean[
        (df_clean['Compound'].isin(dry_tyres)) & 
        (df_clean['IsRaining'] == 0)
    ].copy()

    # Wet dataset: Only wet tyres AND rain flag to ensure data quality
    df_wet = df_clean[
        (df_clean['Compound'].isin(wet_tyres)) & 
        (df_clean['IsRaining'] == 1)
    ].copy()

    # Removing outliers, which are likely to be caused by safety cars, driving mistakes, or other incidents. 
    # We do this by removing laps which are more than 7% slower than the median lap time of the respective track.
    def remove_outliers(df):
        df['MedianTime'] = df.groupby('Track')['LapTimeSec'].transform('median')
        df = df[df['LapTimeSec'] < df['MedianTime'] * 1.07]
        return df.drop(columns=['MedianTime'])

    df_dry = remove_outliers(df_dry)
    df_wet = remove_outliers(df_wet)
    
    print(f"Preprocessing fertig: {len(df_dry)} Trocken-Runden, {len(df_wet)} Regen-Runden.")
    return df_dry, df_wet