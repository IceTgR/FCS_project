import streamlit as st
import pandas as pd
import os
from feature_01 import write_chosen_options, race_simulation
from car import Car
from InterfaceDM import main
from data_preprocessing import get_preprocessed_datasets
from ML_lap_times import train_dry_models
from retrieve_data import fastf1_to_sql

#main()

# Track whether the simulation has been started in the current Streamlit session.
if 'race_started' not in st.session_state: # to check if race has started, if not, initialize it to False
    st.session_state.race_started = False

st.title('F1 Race Strategy Simulator')

# Start screen: show intro and collect race setup options.
if not st.session_state.race_started:
    st.write(f'You are now in the seat of the F1 race strategist for Ferrari!\n'
         f'Prepare yourself to make crucial decisions on pit stops, tire choices, and '
         f'guide your driver to victory!')

    # ML Model Training Section
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
                        track_list = ['Monaco', 'Silverstone']
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

    # User input for driver, track, and starting tire, which is needed to start the simulation
    col1, col2, col3 = st.columns(3)
    team_player = col1.selectbox('Select your team:', ['Ferrari', 'Mercedes', 'Red Bull', 'McLaren', 'Williams'])

    st.session_state.track = col2.selectbox('Select the track:', ['Monaco Grand Prix', 'British Grand Prix'])

    tire_start = col3.radio('Choose your starting tire:', ['SOFT', 'MEDIUM', 'HARD'])

    # Build the correct car object based on track and begin the race loop.
    if st.button('Start the simulation'):
        st.session_state.race_started = True
        if st.session_state.track == 'Monaco Grand Prix':
            st.session_state.player = Car(team_player, 'Monaco Grand Prix', tire_start) # create an instance for Monaco
            st.session_state.total_laps = 78 # set total laps for Monaco
        elif st.session_state.track == 'British Grand Prix':
            st.session_state.player = Car(team_player, 'British Grand Prix', tire_start) # create an instance for Silverstone
            st.session_state.total_laps = 52 # set total laps for Silverstone
        st.rerun(scope='app')

# Race screen: show selected options and advance race state lap by lap.
if st.session_state.race_started:
    write_chosen_options()
    race_simulation()

