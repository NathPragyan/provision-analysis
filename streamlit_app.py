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

    # Convert Section Cost for different views (weekly in lakhs, monthly in crores)
    data['Section Cost (Lakhs)'] = data['Section Cost'] / 10**5  # 1 lakh = 10^5
    data['Section Cost (Crores)'] = data['Section Cost'] / 10**7  # 1 crore = 10^7

    # Convert Capacity Moved to tonnes (assuming Capacity Moved is in kg)
    data['Capacity Moved'] = data['Capacity Moved'] / 1000  # 1 tonne = 1000 kg

    # Sidebar options to choose between Load Trend and Cost Trend
    trend_option = st.sidebar.selectbox('Choose Trend Type', ['Load Trend', 'Cost Trend'])

    # Sidebar filters
    st.sidebar.header('Filters')
    route_type_filter = st.sidebar.selectbox('Route Type', ['All', 'REGIONAL', 'NATIONAL'])
    vendor_type_filter = st.sidebar.selectbox('Vendor Type', ['All', 'VENDOR_SCHEDULED', 'MARKET', 'FEEDER'])

    # Get available clusters based on data
    available_clusters = ['All'] + sorted(data['Cluster'].dropna().unique().tolist())
    cluster_filter = st.sidebar.selectbox('Cluster', available_clusters)

    # Lane filter that allows typing for search
    lane_options = sorted(data['Lane'].dropna().unique().tolist())
    lane_filter = st.sidebar.selectbox('Lane (search by typing)', ['All'] + lane_options)

    # Apply filters to the data
    filtered_data = data.copy()
    if route_type_filter != 'All':
        filtered_data = filtered_data[filtered_data['route_type'] == route_type_filter]

    if vendor_type_filter != 'All':
        filtered_data = filtered_data[filtered_data['vendor_type'] == vendor_type_filter]

    if cluster_filter != 'All':
        filtered_data = filtered_data[filtered_data['Cluster'] == cluster_filter]

    if lane_filter != 'All':
        filtered_data = filtered_data[filtered_data['Lane'] == lane_filter]

    # Automatically update cluster filter based on selected lane
    if lane_filter != 'All':
        selected_cluster = lane_filter.split('-')[0]
        cluster_filter = selected_cluster

    # Function to annotate bars with formatted values
    def annotate_bars(ax, fmt="{:,.1f}"):
        for p in ax.patches:
            ax.annotate(fmt.format(p.get_height()),
                        (p.get_x() + p.get_width() / 2., p.get_height()),
                        ha='center', va='bottom',
                        xytext=(0, 5),  # Adjusted for better spacing
                        textcoords='offset points',
                        fontsize=8)  # Adjusted for smaller font size

    # Function to plot load trend
    def plot_load_trend(data):
        st.subheader('Load Trend Analysis (in Tonnes)')

        # Group data by 'Week No' and 'Month' for weekly comparison of capacity moved
        weekly_capacity = data.groupby(['Week No', 'Month'])['Capacity Moved'].sum().reset_index()

        # Weekly comparison of capacity moved
        plt.figure(figsize=(10, 6))
        ax = sns.barplot(data=weekly_capacity, x='Week No', y='Capacity Moved', hue='Month', ci="sd")
        annotate_bars(ax, fmt="{:,.1f}")
        plt.title('Capacity Moved - Weekly Comparison')
        plt.xlabel('Week Number')
        plt.ylabel('Capacity Moved (Tonnes)')
        plt.xticks(rotation=45)
        plt.legend(title='Month')
        st.pyplot(plt)

        # Monthly comparison of capacity moved
        plt.figure(figsize=(10, 6))
        monthly_capacity = data.groupby('Month')['Capacity Moved'].sum().reset_index()
        # Sort months
        monthly_capacity['Month'] = pd.Categorical(monthly_capacity['Month'], categories=[
            'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'
        ], ordered=True)
        monthly_capacity = monthly_capacity.sort_values('Month')

        ax = sns.barplot(data=monthly_capacity, x='Month', y='Capacity Moved', color='green', ci="sd")
        annotate_bars(ax, fmt="{:,.1f}")
        plt.title('Capacity Moved - Monthly Comparison')
        plt.xlabel('Month')
        plt.ylabel('Total Capacity Moved (Tonnes)')
        plt.xticks(rotation=45)
        st.pyplot(plt)

    # Function to plot cost trend
    def plot_cost_trend(data):
        st.subheader('Cost Trend Analysis')

        # Group data by 'Week No' and 'Month' for weekly comparison of section cost
        weekly_cost = data.groupby(['Week No', 'Month'])['Section Cost (Lakhs)'].sum().reset_index()

        # Weekly comparison of section cost in lakhs
        plt.figure(figsize=(10, 6))
        ax = sns.barplot(data=weekly_cost, x='Week No', y='Section Cost (Lakhs)', hue='Month', ci="sd")
        annotate_bars(ax, fmt="{:,.1f}")
        plt.title('Section Cost - Weekly Comparison (in Lakhs)')
        plt.xlabel('Week Number')
        plt.ylabel('Section Cost (Lakhs)')
        plt.xticks(rotation=45)
        plt.legend(title='Month')
        st.pyplot(plt)

        # Monthly comparison of section cost
        plt.figure(figsize=(10, 6))
        monthly_cost = data.groupby('Month')['Section Cost (Lakhs)'].sum().reset_index()
        # Sort months
        monthly_cost['Month'] = pd.Categorical(monthly_cost['Month'], categories=[
            'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'
        ], ordered=True)
        monthly_cost = monthly_cost.sort_values('Month')

        ax = sns.barplot(data=monthly_cost, x='Month', y='Section Cost (Lakhs)', color='red', ci="sd")
        annotate_bars(ax, fmt="{:,.1f}")
        plt.title('Section Cost - Monthly Comparison (in Lakhs)')
        plt.xlabel('Month')
        plt.ylabel('Total Section Cost (Lakhs)')
        plt.xticks(rotation=45)
        st.pyplot(plt)

    # Display the relevant trend based on user selection
    if trend_option == 'Load Trend':
        plot_load_trend(filtered_data)
    else:
        plot_cost_trend(filtered_data)

else:
    st.warning('Please upload at least one file to proceed.')







