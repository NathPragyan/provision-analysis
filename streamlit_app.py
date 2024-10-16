import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# Set page title
st.title('Interactive Dashboard: Load Trend and Cost Trend Analysis')

# Sidebar to upload multiple files
st.sidebar.header('Upload your 4 Data Files')
uploaded_files = st.sidebar.file_uploader("Choose CSV files", accept_multiple_files=True, type=['xlsx'])

 # Sidebar options to choose between Load Trend and Cost Trend
    trend_option = st.sidebar.selectbox('Choose Trend Type', ['Load Trend', 'Cost Trend'])
