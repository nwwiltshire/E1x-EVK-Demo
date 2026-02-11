import streamlit as st
import serial
import serial.tools.list_ports
import time
import pandas as pd
import numpy as np
import datetime

# --- Configuration & Constants ---
REFRESH_RATE = 0.1 # Seconds

def get_serial_ports():
    return [p.device for p in serial.tools.list_ports.comports()]

def generate_mock_data():
    return {
        "Timestamp": datetime.datetime.now(),
        "VAR (Current)": np.random.normal(120, 5),
        "VAR (Voltage)": np.random.normal(25, 2),
        "VAR (Power)": np.random.normal(15, 1),
    }

def read_serial_data(ser):
    try:
        if ser.in_waiting:
            line = ser.readline().decode('utf-8').strip()
            parts = line.split(',')
            # Expecting CSV format: timestamp(optional), curr, volt, pwr
            # Adjust indices based on your actual device output
            if len(parts) >= 3:
                try:
                    return {
                        "Timestamp": datetime.datetime.now(),
                        "VAR (Current)": float(parts[1]),
                        "VAR (Voltage)": float(parts[2]),
                        "VAR (Power)": float(parts[3])
                    }
                except ValueError:
                    return None
    except Exception:
        return None
    return None

# --- Main App ---

st.set_page_config(page_title="E1x Power Monitor", layout="wide")
st.title("E1x Processor Power Dashboard")

# Initialize Session State
# storage changed to list to keep ALL history for CSV export
if 'data' not in st.session_state:
    st.session_state.data = [] 
if 'monitoring' not in st.session_state:
    st.session_state.monitoring = False

# --- Sidebar ---
with st.sidebar:
    st.header("Settings")
    use_simulation = st.checkbox("Use Simulation Mode", value=True)
    show_full_history = st.toggle("Show Full History Graphs", value=False)
    
    if not use_simulation:
        ports = get_serial_ports()
        selected_port = st.selectbox("Select Serial Port", ports if ports else ["No Ports Found"])
        baud_rate = st.number_input("Baud Rate", value=115200)
    
    st.divider()
    
    # Control Buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶ Start", type="primary"):
            st.session_state.monitoring = True
    with col2:
        if st.button("⏹ Stop"):
            st.session_state.monitoring = False
    
    if st.button("🗑 Clear Data"):
        st.session_state.data = []

    st.divider()

    # Download Button
    if len(st.session_state.data) > 0:
        df_download = pd.DataFrame(st.session_state.data)
        csv = df_download.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Full CSV",
            data=csv,
            file_name=f'e1x_power_log_{int(time.time())}.csv',
            mime='text/csv',
        )

# --- Dashboard Layout ---

# Metrics Row (Optional but helpful)
m1, m2, m3 = st.columns(3)
with m1:
    metric_p = st.empty()
with m2:
    metric_c = st.empty()
with m3:
    metric_v = st.empty()

chart_placeholder = st.empty()

# --- Main Loop ---

if st.session_state.monitoring:
    ser = None
    if not use_simulation:
        try:
            ser = serial.Serial(selected_port, baud_rate, timeout=1)
            ser.reset_input_buffer()
        except Exception as e:
            st.error(f"Failed to open port: {e}")
            st.session_state.monitoring = False
            st.stop()

    while st.session_state.monitoring:
        # 1. Fetch Data
        new_reading = None
        if use_simulation:
            new_reading = generate_mock_data()
            time.sleep(REFRESH_RATE)
        elif ser:
            new_reading = read_serial_data(ser)
            # Add small sleep if serial read didn't block, to prevent CPU spin
            if not new_reading:
                time.sleep(0.05)
        
        # 2. Process & Update Chart
        if new_reading:
            st.session_state.data.append(new_reading)
            
            # Create DataFrame
            df = pd.DataFrame(st.session_state.data)
            
            # Set timestamp as index for proper x-axis formatting
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])
            df_chart = df.set_index('Timestamp')

            # Filter for last 10 seconds if 'Show Full History' is OFF
            if not show_full_history:
                cutoff_time = datetime.datetime.now() - datetime.timedelta(seconds=10)
                df_chart = df_chart[df_chart.index >= cutoff_time]

            # Update Live Metrics
            latest = st.session_state.data[-1]
            metric_p.metric("Power", f"{latest['VAR (Power)']:.2f} mW")
            metric_c.metric("Current", f"{latest['VAR (Current)']:.2f} mA")
            metric_v.metric("Voltage", f"{latest['VAR (Voltage)']:.2f} mV")

            # Update Charts
            with chart_placeholder.container():
                tab1, tab2, tab3 = st.tabs(["Power (mW)", "Current (mA)", "Voltage (mV)"])
                with tab1:
                    st.line_chart(df_chart[['VAR (Power)']], color=["#FAAA19"])
                with tab2:
                    st.line_chart(df_chart[['VAR (Current)']], color=["#454E88"])
                with tab3:
                    st.line_chart(df_chart[['VAR (Voltage)']], color=["#D4D4D4"])

        # Loop control
        time.sleep(0.01)

    if ser:
        ser.close()

else:
    # --- Static View (When stopped) ---
    if len(st.session_state.data) > 0:
        df = pd.DataFrame(st.session_state.data)
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        df_chart = df.set_index('Timestamp')

        # Logic: If stopped, user likely wants to see everything, 
        # unless the toggle is explicitly forcing a window (unlikely use case, but consistent)
        if not show_full_history:
             # Show last 10 seconds of THE DATA (not current time)
            last_timestamp = df_chart.index.max()
            cutoff_time = last_timestamp - datetime.timedelta(seconds=10)
            df_chart = df_chart[df_chart.index >= cutoff_time]

        with chart_placeholder.container():
            tab1, tab2, tab3 = st.tabs(["Power (mW)", "Current (mA)", "Voltage (mV)"])
            with tab1:
                st.line_chart(df_chart[['VAR (Power)']], color=["#FAAA19"])
            with tab2:
                st.line_chart(df_chart[['VAR (Current)']], color=["#454E88"])
            with tab3:
                st.line_chart(df_chart[['VAR (Voltage)']], color=["#D4D4D4"])
    else:
        st.info("Ready to monitor. Click Start in the sidebar.")