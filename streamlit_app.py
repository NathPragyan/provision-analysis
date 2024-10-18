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

    # Apply filters to the data
    filtered_data = data.copy()
    if route_type_filter != 'All':
        filtered_data = filtered_data[filtered_data['route_type'] == route_type_filter]

    if vendor_type_filter != 'All':
        filtered_data = filtered_data[filtered_data['vendor_type'] == vendor_type_filter]

    if cluster_filter != 'All':
        filtered_data = filtered_data[filtered_data['Cluster'] == cluster_filter]

    # Function to annotate bars with formatted values
    def annotate_bars(ax, fmt="{:,.1f}"):
        for p in ax.patches:
            ax.annotate(fmt.format(p.get_height()),  # Format the number according to the specified format
                        (p.get_x() + p.get_width() / 2., p.get_height()), 
                        ha='center', va='center', 
                        xytext=(0, 9), 
                        textcoords='offset points')

    # Function to get the sorted order of months available in the data
    def get_sorted_months(data):
        month_order = ['January', 'February', 'March', 'April', 'May', 'June', 
                       'July', 'August', 'September', 'October', 'November', 'December']
        # Filter the months present in the data and maintain the order
        available_months = [month for month in month_order if month in data['Month'].unique()]
        return available_months

    # Function to plot load trend
    def plot_load_trend(data):
        st.subheader('Load Trend Analysis (in Tonnes)')

        # Group data by 'Week No' and 'Month' for weekly comparison of capacity moved
        weekly_capacity = data.groupby(['Week No', 'Month'])['Capacity Moved'].sum().reset_index()

        # Weekly comparison of capacity moved
        sorted_months = get_sorted_months(data)
        plt.figure(figsize=(10, 6))
        ax = sns.barplot(data=weekly_capacity, x='Week No', y='Capacity Moved', hue='Month', ci="sd", hue_order=sorted_months)
        annotate_bars(ax, fmt="{:,.0f}")
        plt.title('Capacity Moved - Weekly Comparison')
        plt.xlabel('Week Number')
        plt.ylabel('Capacity Moved (Tonnes)')
        plt.legend(title='Month', loc='upper right')
        st.pyplot(plt)

        # Monthly comparison of capacity moved
        plt.figure(figsize=(8, 6))
        monthly_capacity = data.groupby('Month')['Capacity Moved'].sum().reset_index()
        monthly_capacity = monthly_capacity.sort_values('Month', key=lambda x: pd.Categorical(x, categories=sorted_months, ordered=True))
        ax = sns.barplot(data=monthly_capacity, x='Month', y='Capacity Moved', color='green', ci="sd", order=sorted_months)
        annotate_bars(ax, fmt="{:,.0f}")
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
        sorted_months = get_sorted_months(data)
        plt.figure(figsize=(10, 6))
        ax = sns.barplot(data=weekly_cost, x='Week No', y='Section Cost (Lakhs)', hue='Month', ci="sd", hue_order=sorted_months)
        annotate_bars(ax, fmt="{:,.1f}")
        plt.title('Section Cost - Weekly Comparison (in Lakhs)')
        plt.xlabel('Week Number')
        plt.ylabel('Section Cost (Lakhs)')
        plt.legend(title='Month', loc='upper right')
        st.pyplot(plt)

        # Monthly comparison of section cost
        if cluster_filter != 'All':  # Show cost in lakhs if a specific cluster is selected
            monthly_cost = data.groupby('Month')['Section Cost (Lakhs)'].sum().reset_index()
            y_label = 'Total Section Cost (Lakhs)'
            cost_column = 'Section Cost (Lakhs)'
        else:  # Otherwise, show cost in crores
            monthly_cost = data.groupby('Month')['Section Cost (Crores)'].sum().reset_index()
            y_label = 'Total Section Cost (Crores)'
            cost_column = 'Section Cost (Crores)'

        # Ensure data is sorted by the actual available months
        monthly_cost = monthly_cost.sort_values('Month', key=lambda x: pd.Categorical(x, categories=sorted_months, ordered=True))

        # Monthly comparison of section cost
        plt.figure(figsize=(8, 6))
        ax = sns.barplot(data=monthly_cost, x='Month', y=cost_column, color='red', ci="sd", order=sorted_months)
        annotate_bars(ax, fmt="{:,.1f}")
        plt.title('Section Cost - Monthly Comparison')
        plt.xlabel('Month')
        plt.ylabel(y_label)
        st.pyplot(plt)

    # Display the relevant trend based on user selection
    if trend_option == 'Load Trend':
        plot_load_trend(filtered_data)
    else:
        plot_cost_trend(filtered_data)

else:
    st.warning('Please upload at least one file to proceed.')



