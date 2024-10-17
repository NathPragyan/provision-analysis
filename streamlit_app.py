import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Set page title
st.title('Provision Analysis: Load Trend and Cost Trend ')

# Sidebar to upload multiple files
st.sidebar.header('Upload your  Data Files')
uploaded_files = st.sidebar.file_uploader("Choose Provision excel files", accept_multiple_files=True, type=['xlsx'])

# Load all files into a single dataframe
dataframes = [pd.read_xlsx(file) for file in uploaded_files]
data = pd.concat(dataframes)

 # Sidebar options to choose between Load Trend and Cost Trend
trend_option = st.sidebar.selectbox('Choose Trend Type', ['Load Trend', 'Cost Trend'])
