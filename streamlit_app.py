import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Set page title
st.title('Provision Analysis: Load Trend, Cost Trend, and Zonal Analysis')

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

    # Sidebar filters
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
    filtered_data = data.copy()

    # Route type filter logic
    if route_type_filter != 'All':
        filtered_data = filtered_data[filtered_data['route_type'] == route_type_filter]

    # Vendor type filter logic
    if vendor_type_filter != 'All':
        filtered_data = filtered_data[filtered_data['vendor_type'] == vendor_type_filter]

    # Cluster filter logic with DEL_NOI handling
    if cluster_filter != 'All':
        if cluster_filter == 'DEL_NOI':
            filtered_data = filtered_data[filtered_data['Cluster'].isin(['DEL', 'NOI'])]
        else:
            filtered_data = filtered_data[filtered_data['Cluster'] == cluster_filter]

    # Lane filter logic
    if lane_filter != 'All':
        filtered_data = filtered_data[filtered_data['Lane'] == lane_filter]

    # Zonal definitions
    zone_mapping = {
        'N1': ['DEL', 'JAI', 'LKO'],
        'N2': ['AMB'],
        'N3': ['IXJ'],
        'S1': ['BLR', 'CJB', 'HYD', 'MAA'],
        'S2': ['CCJ'],
        'E': ['IXW', 'CCU'],
        'W1': ['BOM', 'NAG', 'PNQ'],
        'W2': ['AMD'],
        'W3': ['GOI'],
        'C': ['IDR'],
        'NE1': ['GAU'],
        'NE2': ['GAU']
    }

    # Function to filter data by zone
    def filter_by_zone(data, zone):
        if zone == 'N2':
            return data[(data['Cluster'] == 'AMB') & (~data['Lane'].str.contains('IXJ'))]
        elif zone == 'S1':
            return data[(data['Cluster'].isin(['BLR', 'CJB', 'HYD', 'MAA'])) & (~data['Lane'].str.contains('CCJ'))]
        elif zone == 'E':
            return data[(data['Cluster'].isin(['IXW', 'CCU'])) & (data['Lane'].str.contains('RPR') | ~data['Lane'].str.contains('NAG'))]
        elif zone == 'W1':
            return data[(data['Cluster'].isin(['BOM', 'NAG', 'PNQ'])) & (~data['Lane'].str.contains('RPR|GOI'))]
        elif zone == 'NE1':
            return data[(data['Cluster'] == 'GAU') & (data['route_type'] == 'NATIONAL')]
        elif zone == 'NE2':
            return data[(data['Cluster'] == 'GAU') & (data['route_type'] == 'REGIONAL')]
        else:
            return data[data['Cluster'].isin(zone_mapping[zone])]

    # Zonal analysis functionality
    if trend_option == 'Zonal Analysis':
        # Zone filter
        zone_filter = st.sidebar.selectbox('Zone', list(zone_mapping.keys()))

        # Filter data by the selected zone
        zonal_data = filter_by_zone(filtered_data, zone_filter)

        # Function to annotate bars with formatted values
        def annotate_bars(ax):
            for p in ax.patches:
                value = p.get_height()
                formatted_value = "{:,.2f}".format(value)
                ax.annotate(formatted_value,
                            (p.get_x() + p.get_width() / 2., value),
                            ha='center', va='bottom',  # Change vertical alignment to bottom
                            xytext=(0, 3),  # Adjusted to be just above the bar
                            textcoords='offset points',
                            fontsize=7)  # Set font size to 7

        # Weekly Cost Analysis
        plt.figure(figsize=(10, 6))
        weekly_cost = zonal_data.groupby('Week No')['Section Cost (Lakhs)'].sum().reset_index()
        ax = sns.barplot(data=weekly_cost, x='Week No', y='Section Cost (Lakhs)', ci=None)
        annotate_bars(ax)
        plt.title('Weekly Cost Analysis (Lakhs)')
        plt.xlabel('Week Number')
        plt.ylabel('Cost (Lakhs)')
        st.pyplot(plt)

        # Monthly Cost Analysis
        plt.figure(figsize=(10, 6))
        monthly_cost = zonal_data.groupby('Month')['Section Cost (Lakhs)'].sum().reset_index()
        ax = sns.barplot(data=monthly_cost, x='Month', y='Section Cost (Lakhs)', ci=None)
        annotate_bars(ax)
        plt.title('Monthly Cost Analysis (Lakhs)')
        plt.xlabel('Month')
        plt.ylabel('Cost (Lakhs)')
        st.pyplot(plt)

        # Weekly Capacity Moved Analysis
        plt.figure(figsize=(10, 6))
        weekly_capacity = zonal_data.groupby('Week No')['Capacity Moved'].sum().reset_index()
        ax = sns.barplot(data=weekly_capacity, x='Week No', y='Capacity Moved', ci=None)
        annotate_bars(ax)
        plt.title('Weekly Capacity Moved (Tonnes)')
        plt.xlabel('Week Number')
        plt.ylabel('Capacity Moved (Tonnes)')
        st.pyplot(plt)

        # Monthly Capacity Moved Analysis
        plt.figure(figsize=(10, 6))
        monthly_capacity = zonal_data.groupby('Month')['Capacity Moved'].sum().reset_index()
        ax = sns.barplot(data=monthly_capacity, x='Month', y='Capacity Moved', ci=None)
        annotate_bars(ax)
        plt.title('Monthly Capacity Moved (Tonnes)')
        plt.xlabel('Month')
        plt.ylabel('Capacity Moved (Tonnes)')
        st.pyplot(plt)

    # Function to plot load trend
    def plot_load_trend(data):
        st.subheader('Load Trend Analysis (in Tonnes)')

        # Group data by 'Week No' and 'Month' for weekly/monthly analysis
        weekly_data = data.groupby('Week No')['Capacity Moved'].sum().reset_index()
        monthly_data = data.groupby('Month')['Capacity Moved'].sum().reset_index()

        # Weekly Load Analysis
        plt.figure(figsize=(10, 6))
        ax = sns.barplot(data=weekly_data, x='Week No', y='Capacity Moved', ci=None)
        annotate_bars(ax)
        plt.title('Weekly Load Analysis')
        plt.xlabel('Week Number')
        plt.ylabel('Capacity Moved (Tonnes)')
        st.pyplot(plt)

        # Monthly Load Analysis
        plt.figure(figsize=(10, 6))
        ax = sns.barplot(data=monthly_data, x='Month', y='Capacity Moved', ci=None)
        annotate_bars(ax)
        plt.title('Monthly Load Analysis')
        plt.xlabel('Month')
        plt.ylabel('Capacity Moved (Tonnes)')
        st.pyplot(plt)

    # Function to plot cost trend
    def plot_cost_trend(data):
        st.subheader('Cost Trend Analysis')

        # Group data by 'Week No' and 'Month' for weekly/monthly analysis
        weekly_data = data.groupby('Week No')['Section Cost (Lakhs)'].sum().reset_index()
        monthly_data = data.groupby('Month')['Section Cost (Lakhs)'].sum().reset_index()

        # Weekly Cost Analysis
        plt.figure(figsize=(10, 6))
        ax = sns.barplot(data=weekly_data, x='Week No', y='Section Cost (Lakhs)', ci=None)
        annotate_bars(ax)
        plt.title('Weekly Cost Analysis')
        plt.xlabel('Week Number')
        plt.ylabel('Cost (Lakhs)')
        st.pyplot(plt)

        # Monthly Cost Analysis
        plt.figure(figsize=(10, 6))
        ax = sns.barplot(data=monthly_data, x='Month', y='Section Cost (Lakhs)', ci=None)
        annotate_bars(ax)
        plt.title('Monthly Cost Analysis')
        plt.xlabel('Month')
        plt.ylabel('Cost (Lakhs)')
        st.pyplot(plt)

    # Trend analysis functionality
    if trend_option == 'Load Trend':
        plot_load_trend(filtered_data)

    elif trend_option == 'Cost Trend':
        plot_cost_trend(filtered_data)

else:
    st.info('Please upload Excel files to proceed.')
