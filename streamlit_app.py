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
    route_type_filter = st.sidebar.selectbox('route_type', ['All', 'REGIONAL', 'NATIONAL'])
    vendor_type_filter = st.sidebar.selectbox('vendor_type', ['All', 'VENDOR_SCHEDULED', 'MARKET', 'FEEDER'])
    cluster_filter = st.sidebar.selectbox('Cluster', ['All'] + sorted(data['Cluster'].dropna().unique().tolist()))
    
    # Lane filter with search capability
    lane_options = ['All'] + sorted(data['Lane'].dropna().unique().tolist())
    lane_filter = st.sidebar.selectbox('Search for Lane', options=lane_options, index=0, key='lane_filter')

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

    # Function to annotate bars with formatted values, adjusting text size for large numbers
    def annotate_bars(ax, fmt="{:,.1f}"):
        for p in ax.patches:
            ax.annotate(fmt.format(p.get_height()),
                        (p.get_x() + p.get_width() / 2., p.get_height()),
                        ha='center', va='center', 
                        xytext=(0, 9),
                        textcoords='offset points',
                        fontsize=8 if p.get_height() > 1000 else 10)  # Adjust font size for readability

    # Function to plot load trend
    def plot_load_trend(data):
        st.subheader('Load Trend Analysis (in Tonnes)')

        # Group data by 'Week No' and 'Month' for weekly comparison of capacity moved
        weekly_capacity = data.groupby(['Week No', 'Month'])['Capacity Moved'].sum().reset_index()

        # Sort months in chronological order
        months_order = data['Month'].dropna().unique().tolist()
        weekly_capacity['Month'] = pd.Categorical(weekly_capacity['Month'], categories=months_order, ordered=True)

        # Weekly comparison of capacity moved
        plt.figure(figsize=(10, 6))
        ax = sns.barplot(data=weekly_capacity, x='Week No', y='Capacity Moved', hue='Month', ci=None)
        annotate_bars(ax, fmt="{:,.1f}")
        plt.title('Capacity Moved - Weekly Comparison')
        plt.xlabel('Week Number')
        plt.ylabel('Capacity Moved (Tonnes)')
        plt.legend(title='Month', loc='upper left')
        st.pyplot(plt)

        # Monthly comparison of capacity moved
        plt.figure(figsize=(8, 6))
        monthly_capacity = data.groupby('Month')['Capacity Moved'].sum().reset_index()
        monthly_capacity['Month'] = pd.Categorical(monthly_capacity['Month'], categories=months_order, ordered=True)
        ax = sns.barplot(data=monthly_capacity, x='Month', y='Capacity Moved', color='green', ci=None)
        annotate_bars(ax, fmt="{:,.1f}")
        plt.title('Capacity Moved - Monthly Comparison')
        plt.xlabel('Month')
        plt.ylabel('Total Capacity Moved (Tonnes)')
        st.pyplot(plt)

    # Function to plot cost trend
    def plot_cost_trend(data):
        st.subheader('Cost Trend Analysis')

        # Group data by 'Week No' and 'Month' for weekly comparison of section cost
        weekly_cost = data.groupby(['Week No', 'Month'])['Section Cost (Lakhs)'].sum().reset_index()

        # Sort months in chronological order
        months_order = data['Month'].dropna().unique().tolist()
        weekly_cost['Month'] = pd.Categorical(weekly_cost['Month'], categories=months_order, ordered=True)

        # Weekly comparison of section cost in lakhs
        plt.figure(figsize=(10, 6))
        ax = sns.barplot(data=weekly_cost, x='Week No', y='Section Cost (Lakhs)', hue='Month', ci=None)
        annotate_bars(ax, fmt="{:,.1f}")
        plt.title('Section Cost - Weekly Comparison (in Lakhs)')
        plt.xlabel('Week Number')
        plt.ylabel('Section Cost (Lakhs)')
        plt.legend(title='Month', loc='upper left')
        st.pyplot(plt)

        # Monthly comparison of section cost with cluster filter adjustment
        plt.figure(figsize=(8, 6))
        monthly_cost = data.groupby('Month')['Section Cost (Lakhs)' if cluster_filter != 'All' else 'Section Cost (Crores)'].sum().reset_index()
        monthly_cost['Month'] = pd.Categorical(monthly_cost['Month'], categories=months_order, ordered=True)
        ax = sns.barplot(data=monthly_cost, x='Month', y=monthly_cost.columns[1], color='red', ci=None)
        annotate_bars(ax, fmt="{:,.1f}")
        plt.title(f'Section Cost - Monthly Comparison (in {"Lakhs" if cluster_filter != "All" else "Crores"})')
        plt.xlabel('Month')
        plt.ylabel(f'Total Section Cost (in {"Lakhs" if cluster_filter != "All" else "Crores"})')
        st.pyplot(plt)

    # Display the relevant trend based on user selection
    if trend_option == 'Load Trend':
        plot_load_trend(filtered_data)
    else:
        plot_cost_trend(filtered_data)

else:
    st.warning('Please upload at least one file to proceed.')





