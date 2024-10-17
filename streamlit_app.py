
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

# Sidebar filters
st.sidebar.header('Filters')
route_type_filter = st.sidebar.selectbox('route_type', ['All', 'Regional', 'National'])
vehicle_type_filter = st.sidebar.selectbox('vendor_type', ['All', 'Vendor Scheduled', 'Ad-Hoc'])
cluster_filter = st.sidebar.selectbox('Cluster', ['All'] + list(data['cluster'].unique()))

# Apply filters to the data
        filtered_data = data.copy()
        if route_type_filter != 'All':
            filtered_data = filtered_data[filtered_data['route_type'] == route_type_filter]
        if vehicle_type_filter != 'All':
            filtered_data = filtered_data[filtered_data['vendor_type'] == vehicle_type_filter]
        if cluster_filter != 'All':
            filtered_data = filtered_data[filtered_data['Cluster'] == cluster_filter]




  

