import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO

st.title('Provision Analysis: Load Trend and Cost Trend')

st.sidebar.header('Upload your Data Files')
uploaded_files = st.sidebar.file_uploader(
    'Choose Provision files', accept_multiple_files=True, type=['xlsx']
)

if uploaded_files:
    dataframes = [pd.read_excel(file, sheet_name='RAW Data') for file in uploaded_files]
    data = pd.concat(dataframes, ignore_index=True)

    data['Start_location_scheduled_dispatch_time'] = pd.to_datetime(
        data['Start_location_scheduled_dispatch_time']
    )
    data['Month'] = data['Start_location_scheduled_dispatch_time'].dt.month_name()
    data['Month Number'] = data['Start_location_scheduled_dispatch_time'].dt.month
    data['Day'] = data['Start_location_scheduled_dispatch_time'].dt.day

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

    # No kg/tonne conversion
    data['Section Cost'] = data['Section Cost']  # already in ones

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

    filtered_data = datewise_data.copy()

    st.sidebar.header('Filters')

    route_type_filter = st.sidebar.selectbox(
        'Route Type', ['All', 'REGIONAL', 'NATIONAL']
    )
    vendor_type_filter = st.sidebar.selectbox(
        'Vendor Type', ['All', 'VENDOR_SCHEDULED', 'MARKET', 'FEEDER']
    )

    cluster_options = ['All'] + sorted(data['Cluster'].dropna().unique().tolist())
    if 'DEL' in cluster_options and 'NOI' in cluster_options:
        cluster_options = [opt for opt in cluster_options if opt not in ['DEL', 'NOI']]
        cluster_options.append('DEL_NOI')

    cluster_filter = st.sidebar.selectbox('Cluster', cluster_options)

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
    def prepare_filtered_summaries(
        data, selected_day, route_type, vendor_type, cluster_filter, lane_filter
    ):
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

        if 'route' not in filtered.columns:
            filtered['route'] = ''
        # Ensure columns exist to avoid KeyError
        if 'duplicasy' not in filtered.columns:
            filtered['duplicasy'] = 0
        if 'Section UTIL' not in filtered.columns:
            filtered['Section UTIL'] = 0
        if 'Section Distance' not in filtered.columns:
            filtered['Section Distance'] = 0

        grouped = filtered.groupby(['Month', 'Lane', 'route'], dropna=False).agg(
            {
                'Section Cost': 'sum',
                'Capacity Moved': 'sum',
                'duplicasy': 'sum',
                'Section UTIL': lambda x: list(x),
                'Section Distance': lambda x: list(x)
            }
        ).reset_index()

        # Calculate Util (weighted avg)
        utils = []
        for _, row in grouped.iterrows():
            utils_array = row['Section UTIL']
            dists_array = row['Section Distance']
            # Convert to arrays if not already
            if not isinstance(utils_array, list):
                utils_array = [utils_array]
            if not isinstance(dists_array, list):
                dists_array = [dists_array]
            utils_array = [u if pd.notnull(u) else 0 for u in utils_array]
            dists_array = [d if pd.notnull(d) else 0 for d in dists_array]
            numerator = sum(float(u) * float(d) for u, d in zip(utils_array, dists_array))
            denominator = sum(float(d) for d in dists_array)
            util_value = round(numerator / denominator, 4) if denominator else None
            utils.append(util_value)

        grouped['Util'] = utils
        # Convert Util to percentage string format
        grouped['Util'] = grouped['Util'].apply(lambda x: f"{round(x * 100, 2)}%" if pd.notnull(x) else None)

        sheets = {}
        months = grouped['Month'].unique()
        for m in months:
            df = grouped[grouped['Month'] == m].copy()
            df = df.dropna(subset=['Lane', 'route'], how='all')
            df = df[(df[['Lane', 'route', 'Section Cost', 'Capacity Moved']].notnull().any(axis=1))]
            df_final = df[['Lane', 'route', 'Section Cost', 'Capacity Moved', 'Util', 'duplicasy']].rename(
                columns={
                    'Section Cost': 'Total cost',
                    'Capacity Moved': 'Total Capacity moved',
                    'duplicasy': 'Total Trips'
                }
            )
            # Remove rows where both total cost and capacity are 0 or NaN
            df_final = df_final[~(
                (df_final['Total cost'].fillna(0) == 0) &
                (df_final['Total Capacity moved'].fillna(0) == 0) &
                (df_final['Util'].isnull())
            )]
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

    # The plotting and rest of your code would go here as before.

else:
    st.warning('Please upload at least one data file to continue.')
