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


# Set API parameters
api_url = 'https://api.aprs.fi/api/get'
api_key = '203831.U2jPXLFW6m14qJ'
# name = 'KQ4AOR-11'
light_aprs_params = {
    'name': 'KQ4AOR-11',
    'what': 'loc',
    'apikey': api_key,
    'format': 'json'
}

eagle_aprs_params = {
    'name': 'KO6DNK-11',
    'what': 'loc',
    'apikey': api_key,
    'format': 'json'
}

if 'data' not in st.session_state:
    st.session_state.data = []

if 'wait_time' not in st.session_state:
    st.session_state.wait_time = 120



st.title("Real-Time APRS Dashboard")

# Create placeholders for visualizations
map_placeholder = st.empty()
altitude_chart_placeholder = st.empty()
speed_course_placeholder = st.empty()

def fetch_data(aprs_params):
    """Fetch APRS data from the API."""
    response = requests.get(api_url, params=aprs_params)
    if response.status_code == 200:
        return response.json()
    else:
        st.error("Failed to fetch data from APRS API")
        return None


def process_light_aprs(result):
    entry = result['entries'][0]
    lat = float(entry["lat"])
    lng = float(entry["lng"])
    altitude = float(entry["altitude"])
    speed = float(entry["speed"])
    course = float(entry["course"])
    timestamp = pd.to_datetime(int(entry["time"]), unit='s')

    other_telem = entry["comment"].split()
    temp = float(other_telem[1].rstrip("C"))
    press = float(other_telem[2].rstrip("hPa"))
    voltage = float(other_telem[3].rstrip("V"))

    # Append data to the list
    st.session_state.data.append({
        'time': timestamp,
        'latitude': lat,
        'longitude': lng,
        'altitude': altitude,
        'speed': speed,
        'course': course,
        'temperature': temp,
        'pressure':press,
        'voltage':voltage,
        'type': "Light APRS"

    })

def process_eagle_aprs(result):
    entry = result['entries'][0]
    lat = float(entry["lat"])
    lng = float(entry["lng"])
    if 'altitude' in entry:
        altitude = float(entry["altitude"])
    else:
        altitude = None
    speed = float(entry["speed"])
    course = float(entry["course"])
    timestamp = pd.to_datetime(int(entry["time"]), unit='s')

    other_telem = entry["comment"].split(",")
    temp = float(other_telem[1].rstrip("C"))
    press = float(other_telem[2].rstrip("mb"))

    # Append data to the list
    st.session_state.data.append({
        'time': timestamp,
        'latitude': lat,
        'longitude': lng,
        'altitude': altitude,
        'speed': speed,
        'course': course,
        'temperature': temp,
        'pressure':press,
        'voltage':None,
        'type': "Eagle Flight"
    })


def fetch_data_refresh(aprs_params):
    result = fetch_data(aprs_params)
    print(result)

    if result and result["result"] == "ok":
        st.session_state.wait_time = 120
        return result
        
    else:
        st.session_state.wait_time *= 2
        return None

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

battery_bounds = 6

def get_metric_delta(df, column):
    df_cleaned =  df.dropna(subset=[column])
    prev_type = df_cleaned['type'].iloc[-1]
    filt_df = df_cleaned[df_cleaned['type'] == prev_type]
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

    light_aprs_traj_mask = df['type'] == "Light APRS"
    eagle_mask = ~light_aprs_traj_mask

    light_aprs_df = df[light_aprs_traj_mask]
    eagle_df = df[eagle_mask]

    light_aprs_traj_points = list(zip(light_aprs_df['latitude'], light_aprs_df['longitude']))
    eagle_traj_points = list(zip(eagle_df['latitude'], eagle_df['longitude']))

    if light_aprs_df.empty:
        center_lat = np.mean(eagle_df['latitude'])
        center_lon = (np.mean(eagle_df['longitude'])) 
    elif eagle_df.empty:
        center_lat = (np.mean(light_aprs_df['latitude']))
        center_lon = (np.mean(light_aprs_df['longitude']))
    else:

        center_lat = (np.mean(light_aprs_df['latitude']) + np.mean(eagle_df['latitude'])) / 2
        center_lon = (np.mean(light_aprs_df['longitude']) + np.mean(eagle_df['longitude'])) / 2
    print("CENTER LAT AND LON")
    print(center_lat, center_lon)
    print(light_aprs_traj_points)
    print(eagle_traj_points)
    m = folium.Map(location=[center_lat, center_lon], zoom_start=11)

    
    weight = 8
    if light_aprs_traj_points:
        folium.PolyLine(light_aprs_traj_points, color='lightblue', weight=weight, opacity=1, popup="light aprs").add_to(m)
    if eagle_traj_points:
        folium.PolyLine(eagle_traj_points, color='blue', weight=weight, opacity=1, popup="eagle").add_to(m)


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
    balloon_track.target(df['latitude'].iloc[-1], df['longitude'].iloc[-1], df['altitude'].iloc[-1])

    pointing_data = balloon_track.calculate()
    with col1:
        # Top: Two side-by-side text displays
        voltage, v_delta = get_metric_delta(df, 'voltage')
        st.metric("Voltage", f"{voltage:.2f} V", delta=v_delta)
        # st.progress(voltage / battery_bounds * 100, text="Batt Percentage")
        altitude, a_delta = get_metric_delta(df, 'altitude')
        st.metric("Altitude", f"{altitude:.2f} m", delta=a_delta)
        # st.progress(altitude / 20000 * 100, text="Percent of max altitude")
        temperature, t_delta = get_metric_delta(df, 'temperature')
        st.metric("Temperature", f"{temperature:.2f} °C", delta=t_delta)
        speed, s_delta = get_metric_delta(df, 'temperature')
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
                subplot_titles=("Voltage (V) over Time", "Altitude (m) over time", "Temperature (°C) over time",  "Pressure (hPa) over Temperature (°C)")
            )
        voltage_chart = px.line(df, x='time', y='voltage', title="Voltage (V) over Time", color="type", markers=True)
        temp_chart = px.line(df, x='time', y='temperature', title="Temperature (C) over Time", color='type', markers=True)
        alt_chart = px.line(df, x='time', y='altitude', title="Altitude (m) over Time", color='type', markers=True)
        press_temp_chart = px.line(df, x='temperature', y='pressure', title="Pressure over Temperature", color='type', markers=True)

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
        
    color_mapper = np.vectorize(lambda x: "#ADD8E6" if x == "Light APRS" else "#00008B")
    df["map_color"] = color_mapper(df["type"].to_numpy())
    # -------------------- Right Column --------------------
    with col3:
        st.subheader("Map")
        # Use Streamlit's built-in map function to show the last known location
        # st.map(df, latitude='latitude', longitude='longitude', color='map_color', size=20)
        m = plot_map(df)
        st_folium(m, returned_objects=[])


import os.path
filename = "Historical.csv"
try:
    # Create DataFrame for plotting
    light_aprs_data = fetch_data_refresh(light_aprs_params)
    if light_aprs_data:
        process_light_aprs(light_aprs_data)
    eagle_aprs_data = fetch_data_refresh(eagle_aprs_params)
    if process_eagle_aprs:
        process_eagle_aprs(eagle_aprs_data)
    df = pd.DataFrame(st.session_state.data).drop_duplicates()
    if os.path.isfile(filename):
        old_df = pd.read_csv(filename)
        new_df = pd.concat([old_df, df]).drop_duplicates().reset_index(drop=True)
    else:
        new_df = df
    
    
    new_df.to_csv("Historical.csv", index=False)

    historical = st.checkbox("Use Historical")
    if historical:
        display_dash(new_df)
    else:
        filtered_df = temp_filter(new_df)
        if not filtered_df.empty:
            display_dash(filtered_df)
        else:
            st.text("No current data found. Try using historical.")
except Exception as e:
    print(e)

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
