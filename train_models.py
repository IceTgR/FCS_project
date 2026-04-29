 # ML Model Training Section
import streamlit as st
import joblib
import os
from data_preprocessing import get_preprocessed_datasets
from ML_lap_times import train_dry_models
from retrieve_data import fastf1_to_sql

def train_models():
    with st.expander("🤖 Train ML Models"):
        st.write("""Train and save ML models for lap time prediction.
                 You need to do this the first time you run the app, or if you want to retrain the models.""")
        
        # Check if models exist
        models_exist = (
            os.path.exists('models/dry/rf_Monaco_Grand_Prix.pkl') and
            os.path.exists('models/dry/rf_British_Grand_Prix.pkl')
        )
        
        if models_exist:
            st.success("✅ ML Models already trained and saved!")
        else:
            st.info("No trained models found. Click the button below to train them.")
        
        if st.button('🚀 Train Models Now', key='train_button'):
            try:
                # Step 1: Check if database exists, create if not
                if not os.path.exists('f1_project.db'):
                    st.info("📥 Database not found. Creating database from F1 API...")
                    with st.spinner('Downloading F1 data from fastf1 (this may take a few minutes)...'):
                        # Define years and tracks for data retrieval
                        years = range(2018, 2026) # 2018-2025
                        track_list = ['Monaco Grand Prix', 'Biritish Grand Prix']
                        team_list = ['Ferrari', 'Mercedes', 'Red Bull', 'McLaren', 'Williams']
                        fastf1_to_sql(years, track_list, team_list)
                    st.success("✅ Database created successfully!")
                
                # Step 2: Load and preprocess data
                with st.spinner('Loading data...'):
                    df_dry, df_wet = get_preprocessed_datasets()
                
                # Step 3: Train models
                with st.spinner('Training models (this may take a minute)...'):
                    results = train_dry_models(df_dry)
                
                st.success("✅ Models trained and saved successfully!")
                st.write("**Results (MAE in seconds):**")
                for track, mae in results.items():
                    st.write(f"  • {track}: {mae:.3f}s")
                
            except FileNotFoundError as e:
                st.error(f"❌ Error: {e}")
            except Exception as e:
                st.error(f"❌ Training failed: {e}")