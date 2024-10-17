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
    # Load all files into a single dataframe from the "RAW Data" sheet
    dataframes = [pd.read_excel(file, sheet_name='RAW Data') for file in uploaded_files]
    data = pd.concat(dataframes, ignore_index=True)

    # Ensure the date column is in datetime format
    data['Start_location_scheduled_dispatch_time'] = pd.to_datetime(data['Start_location_scheduled_dispatch_time'])

    # Extract month from the date column
    data['Month'] = data['Start_location_scheduled_dispatch_time'].dt.month_name()

    # Sidebar options to choose between Load Trend and Cost Trend
    trend_option = st.sidebar.selectbox('Choose Trend Type', ['Load Trend', 'Cost Trend'])
    
    # Sidebar filters
    st.sidebar.header('Filters')
    route_type_filter = st.sidebar.selectbox('route_type', ['All', 'REGIONAL', 'NATIONAL'])
    vendor_type_filter = st.sidebar.selectbox('vendor_type', ['All', 'VENDOR_SCHEDULED', 'MARKET', 'FEEDER'])

    # Apply filters to the data
    filtered_data = data.copy()
    if route_type_filter != 'All':
        filtered_data = filtered_data[filtered_data['route_type'] == route_type_filter]

    if vendor_type_filter != 'All':
        filtered_data = filtered_data[filtered_data['vendor_type'] == vendor_type_filter]

    # Function to plot load trend
    def plot_load_trend(data):
        st.subheader('Load Trend Analysis')
        
        # Weekly comparison of capacity moved
        plt.figure(figsize=(10, 6))
        sns.barplot(data=data, x='Week No', y='Capacity Moved', hue='Month', ci="sd")
        plt.title('Capacity Moved - Weekly Comparison ')
        plt.xlabel('Week Number')
        plt.ylabel('Capacity Moved')
        plt.legend(title='Month')
        st.pyplot(plt)

        # Monthly comparison of capacity moved
        plt.figure(figsize=(8, 6))
        monthly_capacity = data.groupby('Month')['Capacity Moved'].sum().reset_index()
        sns.barplot(data=monthly_capacity, x='Month', y='Capacity Moved', color='green', ci="sd")
        plt.title('Capacity Moved - Monthly Comparison')
        plt.xlabel('Month')
        plt.ylabel('Total Capacity Moved')
        st.pyplot(plt)

    # Function to plot cost trend
    def plot_cost_trend(data):
        st.subheader('Cost Trend Analysis')

        # Weekly comparison of section cost
        plt.figure(figsize=(10, 6))
        sns.barplot(data=data, x='Week No', y='Section Cost', hue='Month', ci="sd")
        plt.title('Section Cost - Weekly Comparison')
        plt.xlabel('Week Number')
        plt.ylabel('Section Cost')
        plt.legend(title='Month')
        st.pyplot(plt)

        # Monthly comparison of section cost
        plt.figure(figsize=(8, 6))
        monthly_cost = data.groupby('Month')['Section Cost'].sum().reset_index()
        sns.barplot(data=monthly_cost, x='Month', y='Section Cost', color='red', ci="sd")
        plt.title('Section Cost - Monthly Comparison')
        plt.xlabel('Month')
        plt.ylabel('Total Section Cost')
        st.pyplot(plt)

    # Display the relevant trend based on user selection
    if trend_option == 'Load Trend':
        plot_load_trend(filtered_data)
    else:
        plot_cost_trend(filtered_data)

else:
    st.warning('Please upload at least one file to proceed.')
