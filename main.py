import streamlit as st
import requests
import pandas as pd
import time
import plotly.express as px
from datetime import datetime
import numpy as np
from AltAzRange import AltAzimuthRange
from plotly.subplots import make_subplots

st.set_page_config(page_title="Dashboard", layout="wide")

# location constants
gs_lat = 34.1385158
gs_lon = -118.1272493
gs_elev = 235

AltAzimuthRange.default_observer(gs_lat, gs_lon, gs_elev)
balloon_track = AltAzimuthRange()


if 'wait_time' not in st.session_state:
    st.session_state.wait_time = 120

st.title("Real-Time APRS Dashboard")

# Create placeholders for visualizations
map_placeholder = st.empty()
altitude_chart_placeholder = st.empty()
speed_course_placeholder = st.empty()

import pandas as pd
from datetime import datetime, timedelta

def temp_filter(df, hours=2, timestamp_col='time'):
    # Ensure the timestamp column is in datetime format
    # df[timestamp_col] = pd.to_datetime(df[timestamp_col])
    
    # Calculate the cutoff time for one hour ago
    valid_range = datetime.now() - timedelta(hours=hours)
    
    # Filter the DataFrame
    filtered_df = df[pd.to_datetime(df[timestamp_col]) >= valid_range]
    
    return filtered_df

def total_temp_filter(df, hours=2, timestamp_col='time'):
        # Calculate the cutoff time for one hour ago
    valid_range = np.max(pd.to_datetime(df[timestamp_col])) - timedelta(hours=hours)

    # Filter the DataFrame
    filtered_df = df[pd.to_datetime(df[timestamp_col]) >= valid_range]
    
    return filtered_df

battery_bounds = 6

def get_metric_delta(df, column):
    df_cleaned =  df.dropna(subset=[column])

    filt_df = df_cleaned
    if not filt_df.empty:
        datapoint = filt_df[column].iloc[-1]
        if len(filt_df) > 1:
        
            prev_datapoint = filt_df[column].iloc[-2]
        else:
            prev_datapoint = datapoint
        return datapoint, round(datapoint - prev_datapoint, 2)
    else:
        return None, 0.0

import folium
from streamlit_folium import st_folium
def plot_map(df):
    polygon_points = [
        (34.353851, -118.170281), (34.658468, -117.967722), (34.812067, -117.350069), 
        (34.85, -117.116594), (34.5, -117.116594), (34.43851, -117.398520)
    ]

    traj = list(zip(df['Latitude (deg)'], df['Longitude (deg)']))
   

    center_lat = np.mean(df['Latitude (deg)'])
    center_lon = np.mean(df['Longitude (deg)'])
    print("CENTER LAT AND LON")

    m = folium.Map(location=[center_lat, center_lon], zoom_start=11)

    
    weight = 8
    
    folium.PolyLine(traj, color='lightblue', weight=weight, opacity=1, popup="light aprs").add_to(m)
    

    style1 = {'fillColor': '#FFA500', 'color': '#FFA500'}
    style2 = {'fillColor': '#FF0000', 'color': '#FF0000'}
    style3 = {'fillColor': '#FF00FF', 'color': '#FF00FF'}

    uas_file = "filtered_FAA_UAS_FacilityMap_Data.geojson"
    special_zones_file = "filtered_Special_Use_Airspace.geojson"
    urban_areas = "filtered_Adjusted_Urban_Area.geojson"

    polygon_coordinates = [[lat, lon] for lat, lon in polygon_points]  # Ensure correct lat-lon order
    folium.Polygon(locations=polygon_coordinates, color='green', fill=True, fill_opacity=0.2).add_to(m)

    # folium.GeoJson(uas_file, style_function=lambda x:style1).add_to(m)
    folium.GeoJson(special_zones_file, style_function=lambda x:style2).add_to(m)
    folium.GeoJson(urban_areas, style_function=lambda x:style3).add_to(m)
    folium.LayerControl().add_to(m)
    return m

def display_dash(df):
    print(df)
    col1, col2, col3 = st.columns([1.5, 4, 2.5])
    balloon_track.target(df['Latitude (deg)'].iloc[-1], df['Longitude (deg)'].iloc[-1], df['Altitude (m)'].iloc[-1])

    pointing_data = balloon_track.calculate()
    with col1:
        # Top: Two side-by-side text displays
        voltage, v_delta = get_metric_delta(df, 'BatV')
        st.metric("Voltage", f"{voltage:.2f} V", delta=v_delta)
        # st.progress(voltage / battery_bounds * 100, text="Batt Percentage")
        altitude, a_delta = get_metric_delta(df, 'Altitude (m)')
        st.metric("Altitude", f"{altitude:.2f} m", delta=a_delta)
        # st.progress(altitude / 20000 * 100, text="Percent of max altitude")
        temperature, t_delta = get_metric_delta(df, 'IntT')
        st.metric("Temperature", f"{temperature:.2f} °C", delta=t_delta)
        speed, s_delta = get_metric_delta(df, 'GroundSpeed (m/s)')
        st.metric("Speed", f"{speed:.2f} km/h", delta=s_delta)
        st.metric("Azimuth", f"{pointing_data['azimuth']:.2f} °")
        st.metric("Elevation Angle", f"{pointing_data['elevation']:.2f} °")
        st.metric("Distance", f"{pointing_data['distance']:.2f} m")

    # -------------------- Middle Column --------------------
    with col2:
        fig = make_subplots(
                rows=2, cols=2,
                shared_xaxes=False,
                # vertical_spacing=0.03,
                subplot_titles=("Voltage (V) over Time", "Altitude (m) over time", "Temperature (°C) over time",  "Temperature vs Altitude")
            )
        voltage_chart = px.line(df, x='ts', y='BatV', title="Voltage (V) over Time",  markers=True)
        temp_chart = px.line(df, x='ts', y='IntT', title="Temperature (C) over Time", markers=True)
        alt_chart = px.line(df, x='ts', y='Altitude (m)', title="Altitude (m) over Time",  markers=True)
        press_temp_chart = px.line(df, x='IntT', y='Altitude (m)', title="Temperature vs Altitude",  markers=True)

        for trace in voltage_chart['data']:
            fig.add_trace(trace.update(showlegend=False), row=1, col=1)
        for trace in temp_chart['data']:
            fig.add_trace(trace.update(showlegend=False), row=2, col=1)
        for trace in alt_chart['data']:
            fig.add_trace(trace.update(showlegend=False), row=1, col=2)
        for trace in press_temp_chart['data']:
            fig.add_trace(trace, row=2, col=2)
        # fig.add_trace(temp_chart, row=2, col=1)
        # fig.add_trace(alt_chart, row=1, col=2)
        # fig.add_trace(press_temp_chart, row=2, col=2)

        fig.update_layout(
            height=750,  # Adjust the height as needed
            width=800,   # Optionally adjust width
            title_text="Balloon Status Plots"
        )
        st.plotly_chart(fig)

        

        # with st.expander("Voltage Plot"):
        #     voltage_chart = px.line(df, x='time', y='voltage', title="Voltage (V) over Time", color="type", markers=True)
        #     # voltage_chart.update_traces(fill='tozeroy', fillcolor="rgba(173, 216, 230, 0.3)")  # Light blue gradient with some transparency

        #     st.plotly_chart(voltage_chart)
        # with st.expander("Temperature Plot"):
        #     temp_chart = px.line(df, x='time', y='temperature', title="Temperature (C) over Time", color='type', markers=True)
        #     st.plotly_chart(temp_chart)
        # with st.expander("Altitude Plot"):
        #     alt_chart = px.line(df, x='time', y='altitude', title="Altitude (m) over Time", color='type', markers=True)
        #     st.plotly_chart(alt_chart)
        # with st.expander("Pressure Plot"):
        #     press_chart = px.line(df, x='time', y='pressure', title="Pressure (hPa) over Time", color='type', markers=True)
        #     st.plotly_chart(press_chart)
        # with st.expander("Pressure Temperature Plot"):
        #     press_temp_chart = px.line(df, x='temperature', y='pressure', title="Pressure over Temperature", color='type', markers=True)
        #     st.plotly_chart(press_temp_chart)
    # -------------------- Right Column --------------------
    with col3:
        st.subheader("Map")
        # Use Streamlit's built-in map function to show the last known location
        # st.map(df, latitude='latitude', longitude='longitude', color='map_color', size=20)
        m = plot_map(df)
        st_folium(m, returned_objects=[])


import os.path
filename = "Historical.csv"

df = pd.read_csv("Flight.CSV")
df['ts'] = pd.to_datetime(df['DateTime'])
now = datetime.now().replace(day=17)+ timedelta(hours=1)
filtered_df = df[df['ts'] < now]

if filtered_df.empty:
    filtered_df = df.iloc[:20000]
display_dash(filtered_df)


print(st.session_state.wait_time)
time.sleep(st.session_state.wait_time)
st.rerun()

# while True:


    #     # Update map
    #     map_placeholder.map(pd.DataFrame({'lat': [lat], 'lon': [lng]}))

    #     # Update altitude over time chart
    #     altitude_chart = px.line(df, x='time', y='altitude', title="Altitude Over Time")
    #     altitude_chart_placeholder.plotly_chart(altitude_chart)

    #     # Update speed and course info
    #     speed_course_placeholder.write(f"Speed: {speed} km/h | Course: {course}°")

    # # Sleep for 2 seconds before next API call
    # time.sleep(2)
