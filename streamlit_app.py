
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Set page title
st.title('Provision Analysis: Load Trend and Cost Trend')

# Sidebar to upload multiple files
st.sidebar.header('Upload your Data Files')
uploaded_files = st.sidebar.file_uploader('Choose Provision files', accept_multiple_files=True, type=['xlsx'])

# Check if files are uploaded before proceeding
if uploaded_files:
    # Load all files into a single dataframe
    dataframes = [pd.read_excel(file) for file in uploaded_files]
    data = pd.concat(dataframes, ignore_index=True)

    # Sidebar options to choose between Load Trend and Cost Trend
    trend_option = st.sidebar.selectbox('Choose Trend Type', ['Load Trend', 'Cost Trend'])
    
    # Add your other code here (like filters, plots, etc.)
else:
    st.warning('Please upload at least one file to proceed.')



  

