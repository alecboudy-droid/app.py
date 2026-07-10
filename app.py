import streamlit as st
import google.generativeai as genai
import gspread
import json
from google.oauth2.service_account import Credentials
from streamlit_calendar import calendar
from datetime import datetime

st.set_page_config(page_title="Cabin App", layout="centered")

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-pro')

@st.cache_resource
def get_client():
    creds_dict = json.loads(st.secrets["GCP_CREDENTIALS"])
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

def get_bookings_sheet():
    return get_client().open("CabinBookings").sheet1

def get_inventory_sheet():
    spreadsheet = get_client().open("CabinBookings")
    try:
        return spreadsheet.worksheet("Inventory")
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title="Inventory", rows=100, cols=2)
        ws.append_row(["Item", "Added"])
        return ws

def clear_dates():
    st.session_state.date_range = ()

def is_overlapping(new_start, new_end):
    sheet = get_bookings_sheet()
    data = sheet.get_all_values()
    for row in data[1:]:
        if len(row) >= 3:
            existing_start = datetime.strptime(row[1], '%Y-%m-%d').date()
            existing_end = datetime.strptime(row[2], '%Y-%m-%d').date()
            if new_start <= existing_end and new_end >= existing_start:
                return True
    return False

def save_to_sheet(name, start, end):
    sheet = get_bookings_sheet()
    sheet.append_row([name, str(start), str(end)])

col1, col2, col3 = st.columns([1, 8, 1])

with col2:
    st.title("🌲 Cabin Booking Portal")
    tab1, tab2, tab3 = st.tabs(["🤖 AI Assistant", "📅 Calendar & Booking", "🧺 Inventory"])

    with tab1:
        st.subheader("Need info?")
        user_query = st.text_input("Ask about the cabin:")
        if user_query:
            with st.spinner("Thinking..."):
                st.write(model.generate_content(user_query).text)

    with tab2:
        st.subheader("Availability")

        booking_data = get_bookings_sheet().get_all_values()[1:]
        booked_events = []
        for row in booking_data:
            if len(row) >= 3:
                booked_events.append({
                    "title": f"Booked: {row[0]}",
                    "start": row[1],
                    "end": row[2],
                    "color": "#e74c3c"
                })

        calendar(
            events=booked_events,
            options={
                "headerToolbar": {"left": "prev,next", "center": "title", "right": "dayGridMonth"},
                "initialView": "dayGridMonth",
                "height": 450
            }
        )

        st.divider()
        st.subheader("Reserve Your Dates")
        user_name = st.text_input("Guest Name:")

        date_selection = st.date_input("Select range:", value=st.session_state.get("date_range", ()), key="date_range")
        st.button("Clear Dates", on_click=clear_dates)

        if isinstance(date_selection, (list, tuple)) and len(date_selection) == 2:
            start, end = date_selection
            st.success(f"**Selected:** {start} to {end}")

            if st.button("Confirm Booking"):
                if not user_name:
                    st.error("Please enter your name.")
                elif is_overlapping(start, end):
                    st.error("⚠️ These dates are already booked.")
                else:
                    save_to_sheet(user_name, start, end)
                    st.balloons()
                    st.success("Booking confirmed!")

    with tab3:
        st.subheader("What do we need to bring up?")

        inventory_sheet = get_inventory_sheet()

        new_item = st.text_input("Add an item:", key="new_item_input")
        if st.button("Add Item"):
            if new_item.strip():
                inventory_sheet.append_row([new_item.strip(), str(datetime.today().date())])
                st.rerun()
            else:
                st.warning("Type something first.")

        st.divider()

        rows = inventory_sheet.get_all_values()[1:]

        if not rows:
            st.write("Nothing on the list right now 🎉")
        else:
            for i, row in enumerate(rows):
                item_name = row[0] if len(row) > 0 else ""
                c1, c2 = st.columns([6, 1])
                with c1:
                    st.write(f"🧻 {item_name}")
                with c2:
                    if st.button("✅", key=f"check_{i}"):
                        inventory_sheet.delete_rows(i + 2)
                        st.rerun()