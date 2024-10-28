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

    # Convert 'Month' column to categorical type for correct order
    month_order = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ]

    # Create a categorical variable for 'Month' based on the month_order
    data['Month'] = pd.Categorical(data['Month'], categories=month_order, ordered=True)

    # Convert Section Cost for different views (weekly in lakhs, monthly in crores)
    data['Section Cost (Lakhs)'] = data['Section Cost'] / 10**5  # 1 lakh = 10^5
    data['Section Cost (Crores)'] = data['Section Cost'] / 10**7  # 1 crore = 10^7

    # Convert Capacity Moved to tonnes (assuming Capacity Moved is in kg)
    data['Capacity Moved'] = data['Capacity Moved'] / 1000  # 1 tonne = 1000 kg

    # Sidebar options to choose between Load Trend, Cost Trend, and Zonal Analysis
    trend_option = st.sidebar.selectbox('Choose Trend Type', ['Load Trend', 'Cost Trend', 'Zonal Analysis'])

    # Initialize the filtered data variable
    filtered_data = data.copy()

    # Logic for general filters (Load Trend and Cost Trend)
    if trend_option in ['Load Trend', 'Cost Trend']:
        st.sidebar.header('Filters')
        route_type_filter = st.sidebar.selectbox('Route Type', ['All', 'REGIONAL', 'NATIONAL'])
        vendor_type_filter = st.sidebar.selectbox('Vendor Type', ['All', 'VENDOR_SCHEDULED', 'MARKET', 'FEEDER'])

        # Cluster filter with only DEL_NOI option
        cluster_options = ['All'] + sorted(data['Cluster'].dropna().unique().tolist())
        if 'DEL' in cluster_options and 'NOI' in cluster_options:
            cluster_options = [opt for opt in cluster_options if opt not in ['DEL', 'NOI']]  # Remove DEL and NOI
            cluster_options.append('DEL_NOI')
        cluster_filter = st.sidebar.selectbox('Cluster', cluster_options)

        # Lane filter options based on the selected cluster
        if cluster_filter != 'All':
            if cluster_filter == 'DEL_NOI':
                lane_options = ['All'] + sorted(data[data['Cluster'].isin(['DEL', 'NOI'])]['Lane'].unique().tolist())
            else:
                lane_options = ['All'] + sorted(data[data['Cluster'] == cluster_filter]['Lane'].unique().tolist())
        else:
            lane_options = ['All'] + sorted(data['Lane'].dropna().unique().tolist())

        # Lane filter with search functionality
        lane_filter = st.sidebar.selectbox('Lane', lane_options)

        # Apply filters to the data
        if route_type_filter != 'All':
            filtered_data = filtered_data[filtered_data['route_type'] == route_type_filter]
        
        if vendor_type_filter != 'All':
            filtered_data = filtered_data[filtered_data['vendor_type'] == vendor_type_filter]

        if cluster_filter != 'All':
            if cluster_filter == 'DEL_NOI':
                filtered_data = filtered_data[filtered_data['Cluster'].isin(['DEL', 'NOI'])]
            else:
                filtered_data = filtered_data[filtered_data['Cluster'] == cluster_filter]

        if lane_filter != 'All':
            filtered_data = filtered_data[filtered_data['Lane'] == lane_filter]

    # Function to annotate bars with formatted values
    def annotate_bars(ax):
        for p in ax.patches:
            value = p.get_height()
            formatted_value = "{:,.2f}".format(value)
            ax.annotate(formatted_value,
                        (p.get_x() + p.get_width() / 2., value),
                        ha='center', va='bottom',
                        xytext=(0, 3),  # Adjusted to be just above the bar
                        textcoords='offset points',
                        fontsize=8)  # Set font size to 8

    # Function to plot load trend
    def plot_load_trend(data):
        st.subheader('Load Trend Analysis (in Tonnes)')

        # Monthly comparison of capacity moved
        monthly_capacity = data.groupby('Month')['Capacity Moved'].sum().reset_index()

        plt.figure(figsize=(8, 6))
        ax = sns.barplot(data=monthly_capacity, x='Month', y='Capacity Moved', color='green', ci=None)

        # Get unique months in data for x-axis
        months_in_data = monthly_capacity['Month'].unique()
        ax.set_xticks(range(len(months_in_data)))  # Set ticks to the number of unique months
        ax.set_xticklabels(months_in_data, rotation=45)  # Set month labels and rotate for better visibility
        
        annotate_bars(ax)
        plt.title('Capacity Moved - Monthly Comparison')
        plt.xlabel('Month')
        plt.ylabel('Total Capacity Moved (Tonnes)')
        st.pyplot(plt)

    # Function to plot cost trend
    def plot_cost_trend(data):
        st.subheader('Cost Trend Analysis')

        # Monthly comparison of section cost
        monthly_cost = data.groupby('Month')['Section Cost (Crores)'].sum().reset_index()

        plt.figure(figsize=(8, 6))
        
        ax = sns.barplot(data=monthly_cost, x='Month', y='Section Cost (Crores)', color='red', ci=None)

        # Get unique months in data for x-axis
        months_in_data = monthly_cost['Month'].unique()
        ax.set_xticks(range(len(months_in_data)))  # Set ticks to the number of unique months
        ax.set_xticklabels(months_in_data, rotation=45)  # Set month labels and rotate for better visibility
        
        annotate_bars(ax)
        plt.title('Cost - Monthly Comparison (in Crores)')
        plt.xlabel('Month')
        plt.ylabel('Total Cost (Crores)')
        st.pyplot(plt)

    # Logic for Load Trend or Cost Trend analysis
    if trend_option in ['Load Trend', 'Cost Trend']:
        if filtered_data.empty:
            st.warning("No data available for the selected filters.")
        else:
            if trend_option == 'Load Trend':
                plot_load_trend(filtered_data)
            elif trend_option == 'Cost Trend':
                plot_cost_trend(filtered_data)
else:
    st.warning('Please upload at least one data file to continue.')
