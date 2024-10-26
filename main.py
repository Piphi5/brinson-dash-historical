import streamlit as st
import requests
import pandas as pd
import time
import plotly.express as px
from datetime import datetime
from AltAzRange import AltAzimuthRange

st.set_page_config(page_title="Dashboard", layout="wide")

# location constants
gs_lat = 34.6891816
gs_lon = -117.6730863
gs_elev = 235.70712838

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

def display_dash(df):
    col1, col2, col3 = st.columns([1, 3.5, 2.5])
    balloon_track.target(df['latitude'].iloc[-1], df['longitude'].iloc[-1], df['altitude'].iloc[-1])

    pointing_data = balloon_track.calculate()
    with col1:
        # Top: Two side-by-side text displays
        st.metric("Voltage", f"{df['voltage'].iloc[-1]:.2f} V")
        st.metric("Altitude", f"{df['altitude'].iloc[-1]:.2f} m")
        st.metric("Temperature", f"{df['temperature'].iloc[-1]:.2f} C")
        st.metric("Speed", f"{df['speed'].iloc[-1]:.2f} km/h")
        st.metric("Azimuth", f"{pointing_data['azimuth']:.2f} °")
        st.metric("Elevation Angle", f"{pointing_data['elevation']:.2f} °")
        st.metric("Distance", f"{pointing_data['distance']:.2f} m")

    # -------------------- Middle Column --------------------
    with col2:
        with st.expander("Voltage Plot"):
            voltage_chart = px.line(df, x='time', y='voltage', title="Voltage (V) over Time", color='type')
            st.plotly_chart(voltage_chart)
        with st.expander("Temperature Plot"):
            temp_chart = px.line(df, x='time', y='temperature', title="Temperature (C) over Time", color='type')
            st.plotly_chart(temp_chart)
        with st.expander("Altitude Plot"):
            alt_chart = px.line(df, x='time', y='altitude', title="Altitude (m) over Time", color='type')
            st.plotly_chart(alt_chart)
        with st.expander("Pressure Plot"):
            press_chart = px.line(df, x='time', y='pressure', title="Pressure (hPa) over Time", color='type')
            st.plotly_chart(press_chart)
        with st.expander("Pressure Temperature Plot"):
            press_temp_chart = px.line(df, x='temperature', y='pressure', title="Pressure over Temperature", color='type')
            st.plotly_chart(press_temp_chart)
        

    # -------------------- Right Column --------------------
    with col3:
        st.subheader("Map")
        # Use Streamlit's built-in map function to show the last known location
        st.map(df[['latitude', 'longitude']], size=20)
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
    # TODO ADD temporal filter
    if os.path.isfile(filename):
        old_df = pd.read_csv(filename)
        new_df = pd.concat([old_df, df]).drop_duplicates().reset_index(drop=True)
    else:
        new_df = df
    
    
    new_df.to_csv("Historical.csv")

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
