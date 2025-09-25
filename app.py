import streamlit as st
from streamlit_folium import st_folium
import folium
import json
import os
from streamlit_autorefresh import st_autorefresh
import threading
import serial
import time

# -----------------------------
# BRIDGE FUNCTION (from bridge.py)
# -----------------------------
def bridge_reader():
    SERIAL_PORT = "COM5"   # Change if needed (e.g., "/dev/ttyUSB0" on Linux)
    BAUD_RATE = 9600

    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE)
    except Exception as e:
        print("⚠️ Could not open serial port:", e)
        return

    data = {"condition": "", "lat": "", "lon": ""}

    while True:
        try:
            line = ser.readline().decode(errors="ignore").strip()
            print("ARDUINO:", line)

            if line.startswith("Condition:"):
                data["condition"] = line.replace("Condition:", "").strip()
            elif line.startswith("Latitude:"):
                data["lat"] = line.replace("Latitude:", "").strip()
            elif line.startswith("Longitude:"):
                data["lon"] = line.replace("Longitude:", "").strip()
                # Save event if condition exists
                if data["condition"]:
                    with open("coordinates.json", "w") as f:
                        json.dump(data, f)
                else:
                    with open("coordinates.json", "w") as f:
                        json.dump({"condition": "", "lat": "", "lon": ""}, f)
        except Exception as e:
            print("⚠️ Serial read error:", e)
            time.sleep(1)

# -----------------------------
# START BRIDGE IN BACKGROUND
# -----------------------------
if "bridge_started" not in st.session_state:
    thread = threading.Thread(target=bridge_reader, daemon=True)
    thread.start()
    st.session_state.bridge_started = True

# -----------------------------
# STREAMLIT APP (your original app.py)
# -----------------------------
st.set_page_config(page_title="ECE Waste Management Dashboard", layout="wide")

# Auto-refresh every 2 seconds
st_autorefresh(interval=2000, key="refresh")

CREDENTIALS_FILE = "credentials.json"
default_credentials = {"ECE": "1234"}

if not os.path.exists(CREDENTIALS_FILE):
    with open(CREDENTIALS_FILE, "w") as f:
        json.dump(default_credentials, f)
with open(CREDENTIALS_FILE, "r") as f:
    credentials = json.load(f)

security_questions = {"ECE": {"question": "What is your name?", "answer": "s"}}

if "page" not in st.session_state: st.session_state.page = "login"
if "logged_in" not in st.session_state: st.session_state.logged_in = False

# --- LOGIN PAGE ---
if st.session_state.page == "login":
    st.title("🔑 ECE Waste Management Login")
    with st.form("login_form"):
        username = st.selectbox("Select Section", list(credentials.keys()))
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            if username in credentials and password == credentials[username]:
                st.session_state.logged_in = True
                st.session_state.page = "dashboard"
            else:
                st.error("Incorrect username or password")

    with st.expander("Forgot Password"):
        section_fp = st.selectbox("Select Section", list(credentials.keys()))
        question = security_questions[section_fp]["question"]
        user_answer = st.text_input(question)
        if st.button("Verify and Show Password"):
            correct_answer = security_questions[section_fp]["answer"]
            if user_answer.strip().lower() == correct_answer.lower():
                st.success(f"Password for {section_fp}: {credentials[section_fp]}")
            else:
                st.error("Incorrect answer")

# --- DASHBOARD PAGE ---
if "autorefresh_key" not in st.session_state:
    st.session_state.autorefresh_key = 0
st_autorefresh(interval=2000, key=f"refresh_{st.session_state.autorefresh_key}")

if st.session_state.page == "dashboard":
    st.sidebar.title("Welcome, ECE Section")
    if st.sidebar.button("Logout"):
        st.session_state.page = "login"
        st.session_state.logged_in = False

    st.title("📡 ECE Waste Management Dashboard - Live GPS Events")

    coords = {"condition": "", "lat": "", "lon": ""}
    if os.path.exists("coordinates.json"):
        with open("coordinates.json", "r") as f:
            try:
                coords = json.load(f)
            except:
                coords = {"condition": "", "lat": "", "lon": ""}

    lat_str = coords.get("lat", "")
    lon_str = coords.get("lon", "")
    condition = coords.get("condition", "").lower()

    if lat_str and lon_str:
        lat = float(lat_str)
        lon = float(lon_str)
        color = "red" if ("tilt" in condition or "height" in condition or "alert" in condition) else "green"

        st.subheader("📍 Latest Event Coordinates")
        st.write(f"Condition: {coords['condition']}")
        st.write(f"Latitude: {lat}")
        st.write(f"Longitude: {lon}")

        m = folium.Map(location=[lat, lon], zoom_start=20)
        folium.Marker(
            location=[lat, lon],
            popup=f"{coords['condition']}<br>Lat: {lat}<br>Lon: {lon}",
            icon=folium.Icon(color=color)
        ).add_to(m)
        st_folium(m, width=700, height=500)
    else:
        st.info("No active event — all clear ✅")
