import streamlit as st
from feature_01 import showcase_square #to import function from feature_01.py
from car import Car
from car_monaco import Car_Monaco

st.title('F1 Race Strategy Simulator')

st.write(f'You are now in the seat of the F1 race strategist for Ferrari!\n'
         f' Prepare yourself to make crucial decisions on pit stops, tire choices, and '
         f'guide your driver to victory!')

# User input for driver, track, and starting tire, which is needed to start the simulation
col1, col2, col3 = st.columns(3)
driver_player = col1.selectbox('Select your driver:', ['Lewis Hamilton', 'Charles Leclerc'])

Track = col2.selectbox('Select the track:', ['Monaco', 'Silverstone', 'Spa-Francorchamps', 'Monza'])

tire_start = col3.radio('Choose your starting tire:', ['soft', 'medium', 'hard'])

st.write(f'This shows that the function from the file feature_01.py ' 
         f'also works here once we imported it: 5 squared equals {showcase_square(5)}') # you can test that on streamlit

# whats goodie