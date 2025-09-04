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

    data['Section Cost'] = data['Section Cost']  # cost in ones, no conversion

    st.sidebar.header('Datewise Filter')
    min_day = int(data['Day'].min())
    max_day = int(data['Day'].max())
    datewise_day = st.sidebar.number_input(
        'Enter Day of Month for Comparison', min_value=min_day, max_value=max_day, value=min_day, step=1
    )
    datewise_data = data[data['Day'] == datewise_day]

    trend_option = st.sidebar.selectbox(
        'Choose Trend Type', ['Load Trend', 'Cost Trend', 'Zonal Analysis']
    )
    filtered_data = datewise_data.copy()

    st.sidebar.header('Filters')
    route_type_filter = st.sidebar.selectbox(
        'Route Type', ['All', 'REGIONAL', 'NATIONAL']
    )
    vendor_type_options = ['All', 'MARKET', 'Scheduled & Feeder']
    vendor_type_filter = st.sidebar.selectbox('Vendor Type', vendor_type_options)

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
        if vendor_type_filter == 'Scheduled & Feeder':
            filtered_data = filtered_data[
                filtered_data['vendor_type'].isin(['VENDOR_SCHEDULED', 'FEEDER'])
            ]
        else:
            filtered_data = filtered_data[filtered_data['vendor_type'] == vendor_type_filter]

    if cluster_filter != 'All':
        if cluster_filter == 'DEL_NOI':
            filtered_data = filtered_data[filtered_data['Cluster'].isin(['DEL', 'NOI'])]
        else:
            filtered_data = filtered_data[filtered_data['Cluster'] == cluster_filter]

    if lane_filter != 'All':
        filtered_data = filtered_data[filtered_data['Lane'] == lane_filter]

    def prepare_filtered_summaries(
        data, selected_day, route_type, vendor_type, cluster_filter, lane_filter
    ):
        filtered = data[data['Day'] == selected_day].copy()

        if route_type != 'All':
            filtered = filtered[filtered['route_type'] == route_type]

        if vendor_type != 'All':
            if vendor_type == 'Scheduled & Feeder':
                filtered = filtered[filtered['vendor_type'].isin(['VENDOR_SCHEDULED', 'FEEDER'])]
            else:
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

        grouped = filtered.groupby(['Month', 'Lane', 'route'], dropna=False).agg(
            {
                'Section Cost': 'sum',
                'Capacity Moved': 'sum',
                'Duplicasy': 'sum',
                'Section UTIL': lambda x: list(x),
                'Section Distance': lambda x: list(x)
            }
        ).reset_index()

        utils = []
        for _, row in grouped.iterrows():
            utils_array = row['Section UTIL']
            dists_array = row['Section Distance']

            if not isinstance(utils_array, list):
                utils_array = [utils_array]
            if not isinstance(dists_array, list):
                dists_array = [dists_array]

            utils_array = [u if pd.notnull(u) else 0 for u in utils_array]
            dists_array = [d if pd.notnull(d) else 0 for d in dists_array]

            numerator = sum(float(u) * float(d) for u, d in zip(utils_array, dists_array))
            denominator = sum(float(d) for d in dists_array)
            util_value = round((numerator / denominator) * 100, 2) if denominator else None
            utils.append(util_value)

        grouped['Util'] = utils

        sheets = {}
        months = grouped['Month'].unique()
        for m in months:
            df = grouped[grouped['Month'] == m].copy()
            df = df.dropna(subset=['Lane', 'route'], how='all')

            # No 'Not Operated' substitution here, keep data as is

            df.rename(columns={'Duplicasy': 'Total Trips'}, inplace=True)

            df_final = df[['Lane', 'route', 'Section Cost', 'Capacity Moved', 'Util', 'Total Trips']].rename(
                columns={
                    'Section Cost': 'Total cost',
                    'Capacity Moved': 'Total Capacity moved'
                }
            )

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

    # Your plotting or zonal analysis code here...

else:
    st.warning('Please upload at least one data file to continue.')
