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

    # Sidebar options to choose between Load Trend, Cost Trend, and Zonal Analysis
    trend_option = st.sidebar.selectbox('Choose Trend Type', ['Load Trend', 'Cost Trend', 'Zonal Analysis'])

    # Sidebar filters for general Load and Cost Trends
    st.sidebar.header('Filters')
    vendor_type_filter = st.sidebar.selectbox('Vendor Type', ['All', 'VENDOR_SCHEDULED', 'MARKET', 'FEEDER'])
    
    # Zone filter
    zone_options = ['All'] + sorted(data['Zone'].dropna().unique().tolist())
    zone_filter = st.sidebar.selectbox('Zone', zone_options)

    # Apply filters to the data
    filtered_data = data.copy()

    # Vendor type filter logic
    if vendor_type_filter != 'All':
        filtered_data = filtered_data[filtered_data['vendor_type'] == vendor_type_filter]

    # Zone filter logic
    if zone_filter != 'All':
        filtered_data = filtered_data[filtered_data['Zone'] == zone_filter]

    # Function to annotate bars with formatted values
    def annotate_bars(ax):
        for p in ax.patches:
            value = p.get_height()
            formatted_value = "{:,.2f}".format(value)
            ax.annotate(formatted_value,
                        (p.get_x() + p.get_width() / 2., value),
                        ha='center', va='bottom',
                        xytext=(0, 3),
                        textcoords='offset points',
                        fontsize=7)

    # Function to plot load trend
    def plot_load_trend(data):
        st.subheader('Load Trend Analysis (in Tonnes)')

        # Group data by 'Week No' for weekly comparison of capacity moved
        weekly_capacity = data.groupby(['Week No'])['Capacity Moved'].sum().reset_index()

        # Weekly comparison of capacity moved
        plt.figure(figsize=(10, 6))
        ax = sns.barplot(data=weekly_capacity, x='Week No', y='Capacity Moved', color='blue', ci=None)
        annotate_bars(ax)
        plt.title('Capacity Moved - Weekly Comparison')
        plt.xlabel('Week Number')
        plt.ylabel('Capacity Moved (Tonnes)')
        st.pyplot(plt)

        # Monthly comparison of capacity moved
        plt.figure(figsize=(8, 6))
        monthly_capacity = data.groupby('Month')['Capacity Moved'].sum().reset_index()
        ax = sns.barplot(data=monthly_capacity, x='Month', y='Capacity Moved', color='green', ci=None)
        annotate_bars(ax)
        plt.title('Capacity Moved - Monthly Comparison')
        plt.xlabel('Month')
        plt.ylabel('Total Capacity Moved (Tonnes)')
        st.pyplot(plt)

    # Function to plot cost trend
    def plot_cost_trend(data):
        st.subheader('Cost Trend Analysis')

        # Group data by 'Week No' for weekly comparison of section cost
        weekly_cost = data.groupby(['Week No'])['Section Cost (Lakhs)'].sum().reset_index()

        # Weekly comparison of section cost in lakhs
        plt.figure(figsize=(10, 6))
        ax = sns.barplot(data=weekly_cost, x='Week No', y='Section Cost (Lakhs)', color='orange', ci=None)
        annotate_bars(ax)
        plt.title('Cost - Weekly Comparison (in Lakhs)')
        plt.xlabel('Week Number')
        plt.ylabel('Cost (Lakhs)')
        st.pyplot(plt)

        # Monthly comparison of section cost
        monthly_cost = data.groupby('Month')['Section Cost (Lakhs)'].sum().reset_index()
        plt.figure(figsize=(8, 6))
        ax = sns.barplot(data=monthly_cost, x='Month', y='Section Cost (Lakhs)', color='red', ci=None)
        annotate_bars(ax)
        plt.title('Cost - Monthly Comparison (in Lakhs)')
        plt.xlabel('Month')
        plt.ylabel('Total Cost (Lakhs)')
        st.pyplot(plt)

    # Function to plot zonal analysis
    def plot_zonal_analysis(data):
        st.subheader('Zonal Analysis: Load and Cost')

        # Group data by 'Week No' for weekly analysis
        zonal_weekly_capacity = data.groupby(['Week No'])['Capacity Moved'].sum().reset_index()
        zonal_weekly_cost = data.groupby(['Week No'])['Section Cost (Lakhs)'].sum().reset_index()

        # Group data by 'Month' for monthly analysis
        zonal_monthly_capacity = data.groupby('Month')['Capacity Moved'].sum().reset_index()
        zonal_monthly_cost = data.groupby('Month')['Section Cost (Lakhs)'].sum().reset_index()

        # Plotting capacity moved vs week number
        plt.figure(figsize=(10, 6))
        ax = sns.barplot(data=zonal_weekly_capacity, x='Week No', y='Capacity Moved', color='blue', ci=None)
        annotate_bars(ax)
        plt.title('Total Capacity Moved by Week Number')
        plt.xlabel('Week Number')
        plt.ylabel('Total Capacity Moved (Tonnes)')
        st.pyplot(plt)

        # Plotting cost vs week number
        plt.figure(figsize=(10, 6))
        ax = sns.barplot(data=zonal_weekly_cost, x='Week No', y='Section Cost (Lakhs)', color='orange', ci=None)
        annotate_bars(ax)
        plt.title('Total Cost by Week Number')
        plt.xlabel('Week Number')
        plt.ylabel('Total Cost (Lakhs)')
        st.pyplot(plt)

        # Plotting capacity moved vs month
        plt.figure(figsize=(10, 6))
        ax = sns.barplot(data=zonal_monthly_capacity, x='Month', y='Capacity Moved', color='green', ci=None)
        annotate_bars(ax)
        plt.title('Total Capacity Moved by Month')
        plt.xlabel('Month')
        plt.ylabel('Total Capacity Moved (Tonnes)')
        st.pyplot(plt)

        # Plotting cost vs month
        plt.figure(figsize=(10, 6))
        ax = sns.barplot(data=zonal_monthly_cost, x='Month', y='Section Cost (Lakhs)', color='red', ci=None)
        annotate_bars(ax)
        plt.title('Total Cost by Month')
        plt.xlabel('Month')
        plt.ylabel('Total Cost (Lakhs)')
        st.pyplot(plt)

    # Display the relevant trend based on user selection
    if trend_option == 'Load Trend':
        plot_load_trend(filtered_data)
    elif trend_option == 'Cost Trend':
        plot_cost_trend(filtered_data)
    else:  # Zonal Analysis
        plot_zonal_analysis(filtered_data)

else:
    st.warning('Please upload at least one file to proceed.')
