import streamlit as st
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_calendar import calendar
from datetime import datetime

# --- GOOGLE SHEETS CONNECTION ---
def get_sheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('key.json', scope)
    client = gspread.authorize(creds)
    # Ensure your sheet is named 'CabinBookings'
    return client.open("CabinBookings").sheet1

sheet = get_sheet()

# --- UI ---
st.set_page_config(page_title="Cabin Scheduler", layout="wide")
st.title("Cabin Scheduler 🏠")

# --- MAIN SCREEN: BOOKING ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Add New Booking")
    user_name = st.text_input("Your Name")
    selected_date = st.date_input("Select Date")
    
    if st.button("Confirm Booking"):
        if user_name:
            # Append to sheet: 'date' and 'name' columns
            sheet.append_row([str(selected_date), user_name])
            st.success(f"Booking saved for {user_name} on {selected_date}!")
            st.rerun()
        else:
            st.warning("Please enter your name.")

# --- CALENDAR SECTION ---
with col2:
    st.subheader("Calendar View")
    data = sheet.get_all_records()
    events = []
    for row in data:
        # Maps 'date' and 'name' from your Google Sheet
        events.append({
            "title": f"Booked: {row['name']}", 
            "start": row['date'], 
            "backgroundColor": "red"
        })
    
    calendar(events=events, options={"initialView": "dayGridMonth"})