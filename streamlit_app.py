import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Set Streamlit page title
st.title('Provision Analysis: Load Trend and Cost Trend')

# Sidebar for uploading files
st.sidebar.header('Upload your Data Files')
uploaded_files = st.sidebar.file_uploader(
    'Choose Provision files', accept_multiple_files=True, type=['xlsx']
)

if uploaded_files:
    # Load all files into a single DataFrame from the "RAW Data" sheet
    dataframes = [pd.read_excel(file, sheet_name='RAW Data') for file in uploaded_files]
    data = pd.concat(dataframes, ignore_index=True)

    # Ensure the date column is in datetime format
    data['Start_location_scheduled_dispatch_time'] = pd.to_datetime(
        data['Start_location_scheduled_dispatch_time']
    )

    # Extract month info
    data['Month'] = data['Start_location_scheduled_dispatch_time'].dt.month_name()
    data['Month Number'] = data['Start_location_scheduled_dispatch_time'].dt.month
    data['Day'] = data['Start_location_scheduled_dispatch_time'].dt.day

    # Map month numbers to month names for ordering
    unique_months = data['Month Number'].unique()
    unique_months_sorted = sorted(unique_months)
    month_order = {
        1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May',
        6: 'June', 7: 'July', 8: 'August', 9: 'September', 10: 'October',
        11: 'November', 12: 'December'
    }
    months_in_data = [month_order[month] for month in unique_months_sorted if month in month_order]
    data['Month'] = pd.Categorical(
        data['Month'], categories=months_in_data, ordered=True
    )

    # Section Cost conversions
    data['Section Cost (Lakhs)'] = data['Section Cost'] / 10**5  # 1 lakh = 1,00,000
    data['Section Cost (Crores)'] = data['Section Cost'] / 10**7  # 1 crore = 1,00,00,000
    # Convert Capacity Moved to tonnes (assuming input is in kg)
    data['Capacity Moved'] = data['Capacity Moved'] / 1000

    # --- DATEWISE FILTER SECTION ---
    st.sidebar.header('Datewise Filter')
    min_day = int(data['Day'].min())
    max_day = int(data['Day'].max())
    datewise_day = st.sidebar.number_input(
        'Enter Day of Month for Comparison', min_value=min_day, max_value=max_day, value=min_day, step=1
    )
    datewise_data = data[data['Day'] == datewise_day]
    # --------------------------------

    # Sidebar: main trend type selection
    trend_option = st.sidebar.selectbox(
        'Choose Trend Type', ['Load Trend', 'Cost Trend', 'Zonal Analysis']
    )
    # Start with datewise filter
    filtered_data = datewise_data.copy()

    # --- General Filters for Load/Cost Trend ---
    if trend_option in ['Load Trend', 'Cost Trend']:
        st.sidebar.header('Filters')
        route_type_filter = st.sidebar.selectbox(
            'Route Type', ['All', 'REGIONAL', 'NATIONAL']
        )
        vendor_type_filter = st.sidebar.selectbox(
            'Vendor Type', ['All', 'VENDOR_SCHEDULED', 'MARKET', 'FEEDER']
        )
        # Cluster filter (with "DEL_NOI" logic)
        cluster_options = ['All'] + sorted(data['Cluster'].dropna().unique().tolist())
        if 'DEL' in cluster_options and 'NOI' in cluster_options:
            cluster_options = [opt for opt in cluster_options if opt not in ['DEL', 'NOI']]
            cluster_options.append('DEL_NOI')
        cluster_filter = st.sidebar.selectbox('Cluster', cluster_options)
        # Lane filter
        if cluster_filter != 'All':
            if cluster_filter == 'DEL_NOI':
                lane_options = ['All'] + sorted(
                    data[data['Cluster'].isin(['DEL', 'NOI'])]['Lane'].dropna().unique().tolist()
                )
            else:
                lane_options = ['All'] + sorted(
                    data[data['Cluster'] == cluster_filter]['Lane'].dropna().unique().tolist()
                )
        else:
            lane_options = ['All'] + sorted(data['Lane'].dropna().unique().tolist())
        lane_filter = st.sidebar.selectbox('Lane', lane_options)

        # Apply filters
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

    # --- Annotate Bars Function ---
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

    # --- Plot Load Trend ---
    def plot_load_trend(data):
        st.subheader('Load Trend Analysis (in Tonnes)')
        # Weekly comparison
        if 'Week No' in data.columns and not data.empty:
            weekly_capacity = data.groupby(['Week No', 'Month'])['Capacity Moved'].sum().reset_index()
            plt.figure(figsize=(10, 6))
            ax = sns.barplot(data=weekly_capacity, x='Week No', y='Capacity Moved', hue='Month', ci=None)
            annotate_bars(ax)
            plt.title('Capacity Moved - Weekly Comparison')
            plt.xlabel('Week Number')
            plt.ylabel('Capacity Moved (Tonnes)')
            plt.legend(title='Month')
            st.pyplot(plt)
        # Monthly comparison
        monthly_capacity = data.groupby('Month')['Capacity Moved'].sum().reset_index()
        plt.figure(figsize=(8, 6))
        ax = sns.barplot(data=monthly_capacity, x='Month', y='Capacity Moved', color='green', ci=None)
        annotate_bars(ax)
        plt.title('Capacity Moved - Monthly Comparison')
        plt.xlabel('Month')
        plt.ylabel('Total Capacity Moved (Tonnes)')
        st.pyplot(plt)

    # --- Plot Cost Trend ---
    def plot_cost_trend(data):
        st.subheader('Cost Trend Analysis')
        # Weekly comparison
        if 'Week No' in data.columns and not data.empty:
            weekly_cost = data.groupby(['Week No', 'Month'])['Section Cost (Lakhs)'].sum().reset_index()
            plt.figure(figsize=(10, 6))
            ax = sns.barplot(data=weekly_cost, x='Week No', y='Section Cost (Lakhs)', hue='Month', ci=None)
            annotate_bars(ax)
            plt.title('Cost - Weekly Comparison (in Lakhs)')
            plt.xlabel('Week Number')
            plt.ylabel('Cost (Lakhs)')
            plt.legend(title='Month')
            st.pyplot(plt)
        # Monthly comparison
        monthly_cost = data.groupby('Month')['Section Cost (Lakhs)'].sum().reset_index()
        plt.figure(figsize=(8, 6))
        ax = sns.barplot(data=monthly_cost, x='Month', y='Section Cost (Lakhs)', color='red', ci=None)
        annotate_bars(ax)
        plt.title('Cost - Monthly Comparison (Lakhs)')
        plt.xlabel('Month')
        plt.ylabel('Total Cost (Lakhs)')
        st.pyplot(plt)

    # --- Zonal Data Filtering ---
    def filter_zonal_data(data, zone):
        if zone == 'N1':
            return data[data['Lane'].isin(data[data['Cluster'].isin(['DEL', 'JAI', 'LKO'])]['Lane'])]
        elif zone == 'N2':
            return data[(data['Cluster'] == 'AMB') & (~data['Lane'].str.contains('IXJ', na=False))]
        elif zone == 'N3':
            return data[data['Lane'].str.contains('IXJ', na=False)]
        elif zone == 'S1':
            return data[(data['Cluster'].isin(['BLR', 'CJB', 'HYD', 'MAA'])) & (~data['Lane'].str.contains('CCJ', na=False))]
        elif zone == 'S2':
            return data[data['Lane'].str.contains('CCJ', na=False)]
        elif zone == 'E':
            return data[((data['Cluster'].isin(['IXW', 'CCU'])) & (~data['Lane'].str.contains('NAG', na=False))) | (data['Lane'].str.contains('RPR', na=False))]
        elif zone == 'W1':
            return data[(data['Cluster'].isin(['BOM', 'NAG', 'PNQ'])) & (~data['Lane'].str.contains('RPR|GOI', na=False))]
        elif zone == 'W2':
            return data[data['Cluster'] == 'AMD']
        elif zone == 'W3':
            return data[data['Lane'].str.contains('GOI', na=False)]
        elif zone == 'C':
            return data[data['Cluster'] == 'IDR']
        elif zone == 'NE1':
            return data[(data['Cluster'] == 'GAU') & (data['route_type'] == 'NATIONAL')]
        elif zone == 'NE2':
            return data[(data['Cluster'] == 'GAU') & (data['route_type'] == 'REGIONAL')]
        else:
            return data

    # --- Zonal Analysis Logic ---
    if trend_option == 'Zonal Analysis':
        st.sidebar.header('Zonal Filters')
        zone_options = ['N1', 'N2', 'N3', 'S1', 'S2', 'E', 'W1', 'W2', 'W3', 'C', 'NE1', 'NE2']
        selected_zone = st.sidebar.selectbox('Select Zone', zone_options)
        zonal_data = filter_zonal_data(datewise_data, selected_zone)
        if zonal_data.empty:
            st.warning(f"No data available for the selected zone: {selected_zone}")
        else:
            plot_load_trend(zonal_data)
            plot_cost_trend(zonal_data)

    # --- Load or Cost Trend Analysis ---
    elif trend_option in ['Load Trend', 'Cost Trend']:
        if filtered_data.empty:
            st.warning("No data available for the selected filters.")
        else:
            if trend_option == 'Load Trend':
                plot_load_trend(filtered_data)
            elif trend_option == 'Cost Trend':
                plot_cost_trend(filtered_data)

else:
    st.warning('Please upload at least one data file to continue.')
