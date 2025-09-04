import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO

# -- Title --
st.title('Provision Analysis: Load Trend and Cost Trend')

# -- Sidebar for file upload --
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

    # Extract month info and day
    data['Month'] = data['Start_location_scheduled_dispatch_time'].dt.month_name()
    data['Month Number'] = data['Start_location_scheduled_dispatch_time'].dt.month
    data['Day'] = data['Start_location_scheduled_dispatch_time'].dt.day

    # Month ordering
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

    # Section Cost in ones (no conversion)
    # Capacity Moved in Tonnes (assuming input is in kg)
    data['Section Cost'] = data['Section Cost']  # already in 'ones'
    data['Capacity Moved'] = data['Capacity Moved'] / 1000

    # ------------ Datewise Filter Section ------------
    st.sidebar.header('Datewise Filter')
    min_day = int(data['Day'].min())
    max_day = int(data['Day'].max())
    datewise_day = st.sidebar.number_input(
        'Enter Day of Month for Comparison', min_value=min_day, max_value=max_day, value=min_day, step=1
    )
    datewise_data = data[data['Day'] == datewise_day]
    # -------------------------------------------------

    # ------------ Trend Type Selection and Filters ------------
    trend_option = st.sidebar.selectbox(
        'Choose Trend Type', ['Load Trend', 'Cost Trend', 'Zonal Analysis']
    )
    # Start with datewise filter
    filtered_data = datewise_data.copy()

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

    # ------------ Excel Export Functionality ------------
    def prepare_filtered_summaries(data, selected_day, route_type, vendor_type,
                                   cluster_filter, lane_filter):
        filtered = data[data['Day'] == selected_day].copy()
        if route_type != 'All':
            filtered = filtered[filtered['route_type'] == route_type]
        if vendor_type != 'All':
            filtered = filtered[filtered['vendor_type'] == vendor_type]
        if cluster_filter != 'All':
            if cluster_filter == 'DEL_NOI':
                filtered = filtered[filtered['Cluster'].isin(['DEL', 'NOI'])]
            else:
                filtered = filtered[filtered['Cluster'] == cluster_filter]
        if lane_filter != 'All':
            filtered = filtered[filtered['Lane'] == lane_filter]
        # "route" column fallback in case it does not exist
        if 'route' not in filtered.columns:
            filtered['route'] = ''
        grp = filtered.groupby(['Month', 'Lane', 'route'], dropna=False).agg({
            'Section Cost': 'sum',
            'Capacity Moved': 'sum'
        }).reset_index()

        # Remove lanes with all values null across exported sheets
        # Keep only the required columns, naming as per your requirements
        sheets = {}
        months = grp['Month'].unique()
        for m in months:
            df = grp[grp['Month'] == m].copy()
            df = df.dropna(subset=['Lane', 'route'], how='all')
            df = df[(df[['Lane', 'route', 'Section Cost', 'Capacity Moved']].notnull().any(axis=1))]
            df_final = df[['Lane', 'route', 'Section Cost', 'Capacity Moved']].rename(
                columns={
                    'Section Cost': 'Total cost',
                    'Capacity Moved': 'Total Capacity moved'
                }
            )
            # Remove rows where both total cost and capacity are 0 or NaN
            df_final = df_final[~((df_final['Total cost'].fillna(0) == 0) &
                                  (df_final['Total Capacity moved'].fillna(0) == 0))]
            sheets[str(m)] = df_final.reset_index(drop=True)
        return sheets

    def export_filtered_excel(df_dict):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            for sheet, df in df_dict.items():
                df.to_excel(writer, sheet_name=str(sheet), index=False)
        output.seek(0)
        return output

    if st.button('Download Comparison Excel'):
        sheets = prepare_filtered_summaries(
            data, datewise_day, route_type_filter, vendor_type_filter, cluster_filter, lane_filter
        )
        # Remove empty sheets
        sheets = {k: v for k, v in sheets.items() if not v.empty}
        if sheets:
            excel_file = export_filtered_excel(sheets)
            st.download_button(
                label='Download Comparison Excel File',
                data=excel_file,
                file_name='comparison_report.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        else:
            st.warning("No data to export for the selected filters.")

    # ------------ Annotate Bars Function ------------
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

    # ------------ Plots and Zonal Analysis ------------
    def plot_load_trend(data):
        st.subheader('Load Trend Analysis (in Tonnes)')
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
        monthly_capacity = data.groupby('Month')['Capacity Moved'].sum().reset_index()
        plt.figure(figsize=(8, 6))
        ax = sns.barplot(data=monthly_capacity, x='Month', y='Capacity Moved', color='green', ci=None)
        annotate_bars(ax)
        plt.title('Capacity Moved - Monthly Comparison')
        plt.xlabel('Month')
        plt.ylabel('Total Capacity Moved (Tonnes)')
        st.pyplot(plt)

    def plot_cost_trend(data):
        st.subheader('Cost Trend Analysis')
        if 'Week No' in data.columns and not data.empty:
            weekly_cost = data.groupby(['Week No', 'Month'])['Section Cost'].sum().reset_index()
            plt.figure(figsize=(10, 6))
            ax = sns.barplot(data=weekly_cost, x='Week No', y='Section Cost', hue='Month', ci=None)
            annotate_bars(ax)
            plt.title('Cost - Weekly Comparison (in Ones)')
            plt.xlabel('Week Number')
            plt.ylabel('Cost (Ones)')
            plt.legend(title='Month')
            st.pyplot(plt)
        monthly_cost = data.groupby('Month')['Section Cost'].sum().reset_index()
        plt.figure(figsize=(8, 6))
        ax = sns.barplot(data=monthly_cost, x='Month', y='Section Cost', color='red', ci=None)
        annotate_bars(ax)
        plt.title('Cost - Monthly Comparison (Ones)')
        plt.xlabel('Month')
        plt.ylabel('Total Cost (Ones)')
        st.pyplot(plt)

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

    if trend_option == 'Zonal Analysis':
        st.sidebar.header('Zonal Filters')
        zone_options = ['N1', 'N2', 'N3', 'S1', 'S2', 'E', 'W1', 'W2', 'W3', 'C', 'NE1', 'NE2']
        selected_zone = st.sidebar.selectbox('Select Zone', zone_options)
        zonal_data = filter_zonal_data(filtered_data, selected_zone)
        if zonal_data.empty:
            st.warning(f"No data available for the selected zone: {selected_zone}")
        else:
            plot_load_trend(zonal_data)
            plot_cost_trend(zonal_data)
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
