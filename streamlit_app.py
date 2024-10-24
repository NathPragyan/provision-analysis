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

        # Update lane options based on route type selection
        lane_options = ['All'] + sorted(filtered_data['Lane'].unique().tolist())

    # Vendor type filter logic
    if vendor_type_filter != 'All':
        filtered_data = filtered_data[filtered_data['vendor_type'] == vendor_type_filter]

    # Cluster filter logic with DEL_NOI handling
    if cluster_filter != 'All':
        if cluster_filter == 'DEL_NOI':
            # Filter rows where Cluster is either DEL or NOI
            filtered_data = filtered_data[filtered_data['Cluster'].isin(['DEL', 'NOI'])]
        else:
            filtered_data = filtered_data[filtered_data['Cluster'] == cluster_filter]

        lane_options = ['All'] + sorted(filtered_data['Lane'].unique().tolist())

    # Lane filter logic
    if lane_filter != 'All':
        filtered_data = filtered_data[filtered_data['Lane'] == lane_filter]
        # Automatically set cluster filter based on lane selection
        if any(filtered_data['Lane'].str.startswith(lane_filter.split('-')[0])):
            cluster_filter = lane_filter.split('-')[0]

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

    # Function to plot load trend
    def plot_load_trend(data):
        st.subheader('Load Trend Analysis (in Tonnes)')

        # Group data by 'Week No' and 'Month' for weekly comparison of capacity moved
        weekly_capacity = data.groupby(['Week No', 'Month'])['Capacity Moved'].sum().reset_index()

        # Weekly comparison of capacity moved
        plt.figure(figsize=(10, 6))
        ax = sns.barplot(data=weekly_capacity, x='Week No', y='Capacity Moved', hue='Month', ci=None)
        annotate_bars(ax)
        plt.title('Capacity Moved - Weekly Comparison')
        plt.xlabel('Week Number')
        plt.ylabel('Capacity Moved (Tonnes)')
        plt.legend(title='Month')
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

        # Group data by 'Week No' and 'Month' for weekly comparison of section cost
        weekly_cost = data.groupby(['Week No', 'Month'])['Section Cost (Lakhs)'].sum().reset_index()

        # Weekly comparison of section cost in lakhs
        plt.figure(figsize=(10, 6))
        ax = sns.barplot(data=weekly_cost, x='Week No', y='Section Cost (Lakhs)', hue='Month', ci=None)
        annotate_bars(ax)
        plt.title('Cost - Weekly Comparison (in Lakhs)')
        plt.xlabel('Week Number')
        plt.ylabel('Cost (Lakhs)')
        plt.legend(title='Month')
        st.pyplot(plt)

        # Monthly comparison of section cost
        cost_column = 'Section Cost (Crores)' if cluster_filter == 'All' and lane_filter == 'All' else 'Section Cost (Lakhs)'
        monthly_cost = data.groupby('Month')[cost_column].sum().reset_index()

        plt.figure(figsize=(8, 6))
        ax = sns.barplot(data=monthly_cost, x='Month', y=cost_column, color='red', ci=None)
        annotate_bars(ax)
        plt.title(f' Cost - Monthly Comparison ({cost_column.split()[2]})')
        plt.xlabel('Month')
        plt.ylabel(f'Total Cost ({cost_column.split()[2]})')
        st.pyplot(plt)

    # Display the relevant trend based on user selection
    if trend_option == 'Load Trend':
        plot_load_trend(filtered_data)
    else:
        plot_cost_trend(filtered_data)

else:
    st.warning('Please upload at least one file to proceed.')
