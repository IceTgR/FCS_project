import streamlit as st
from feature_01 import showcase_square #to import function from feature_01.py

st.title('F1 Race Strategy Simulator')

st.write('Hello world!')

st.write(f'This shows that the function from the file feature_01.py' 
         f'also works here: 5 squared equals {showcase_square(5)}') # you can test that on streamlit