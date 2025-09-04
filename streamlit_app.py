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
                'duplicasy': 'count',
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
            util_value = round(numerator / denominator, 4) if denominator else None
            utils.append(util_value)

        grouped['Util'] = utils
        grouped['Util'] = grouped['Util'].apply(lambda x: f"{round(x * 100, 2)}%" if pd.notnull(x) else None)

        def adjusted_trips(row):
            route = row['route']
            trip_count = row['duplicasy']
            if isinstance(route, str) and route:
                segments = route.count('-') if route.count('-') > 0 else 1
                return trip_count / segments
            else:
                return trip_count

        grouped['Total Trips'] = grouped.apply(adjusted_trips, axis=1)

        def cpkg_calc(row):
            try:
                utils_array = filtered[
                    (filtered['Month'] == row['Month']) &
                    (filtered['Lane'] == row['Lane']) &
                    (filtered['route'] == row['route'])
                ]['Section UTIL']
                dists_array = filtered[
                    (filtered['Month'] == row['Month']) &
                    (filtered['Lane'] == row['Lane']) &
                    (filtered['route'] == row['route'])
                ]['Section Distance']

                utils_array = utils_array.tolist() if hasattr(utils_array, 'tolist') else [utils_array]
                dists_array = dists_array.tolist() if hasattr(dists_array, 'tolist') else [dists_array]

                if not utils_array or not dists_array:
                    return None

                utils_array = [u if pd.notnull(u) else 0 for u in utils_array]
                dists_array = [d if pd.notnull(d) else 0 for d in dists_array]

                numerator = sum(float(u) * float(d) for u, d in zip(utils_array, dists_array))
                denominator = sum(float(d) for d in dists_array)
                util_decimal = numerator / denominator if denominator else 0

                if util_decimal == 0:
                    return None

                if row['Capacity Moved'] == 0 or pd.isna(row['Capacity Moved']):
                    return None

                return row['Section Cost'] / (row['Capacity Moved'] * util_decimal)
            except Exception:
                return None

        grouped['cpkg'] = grouped.apply(cpkg_calc, axis=1)

        grouped = grouped.rename(
            columns={
                'Section Cost': 'Total cost',
                'Capacity Moved': 'Total Capacity moved'
            }
        )

        sheets = {}
        months = grouped['Month'].unique()
        for m in months:
            df = grouped[grouped['Month'] == m].copy()
            df = df.dropna(subset=['Lane', 'route'], how='all')
            df = df[(df[['Lane', 'route', 'Total cost', 'Total Capacity moved']].notnull().any(axis=1))]
            df_final = df[[
                'Lane', 'route', 'Total cost', 'Total Capacity moved', 'Util', 'Total Trips', 'cpkg'
            ]]
            df_final = df_final[~(
                (df_final['Total cost'].fillna(0) == 0) &
                (df_final['Total Capacity moved'].fillna(0) == 0) &
                (df_final['Util'].isnull())
            )]
            sheets[str(m)] = df_final.reset_index(drop=True)

        # Create Comparison sheet with common routes across all months
        if len(months) > 1:
            # Pick first month's df
            common_routes = sheets[months[0]][['route']].copy()
            # Intersect routes from other months
            for month in months[1:]:
                common_routes = pd.merge(
                    common_routes,
                    sheets[month][['route']],
                    on='route',
                    how='inner'
                )
            # Now prepare the comparison DataFrame
            comp_dfs = []
            for month in months:
                df = sheets[month][sheets[month]['route'].isin(common_routes['route'])].copy()
                # Prefix columns with month to distinguish
                df = df.rename(
                    columns={
                        'Total cost': f'Total cost ({month})',
                        'Total Capacity moved': f'Total Capacity moved ({month})',
                        'Util': f'Util ({month})',
                        'Total Trips': f'Total Trips ({month})',
                        'cpkg': f'cpkg ({month})'
                    }
                )
                # Keep route for merge
                comp_dfs.append(df.set_index('route'))

            # Merge all on route
            comparison_df = pd.concat(comp_dfs, axis=1, join='inner').reset_index()

            sheets['Comparison'] = comparison_df

        return sheets

    def export_filtered_excel(df_dict):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            for sheet_name, df in df_dict.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
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

else:
    st.warning('Please upload at least one data file to continue.')
