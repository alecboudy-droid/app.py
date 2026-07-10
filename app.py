import streamlit as st
import google.generativeai as genai
import gspread
import json
from google.oauth2.service_account import Credentials
from streamlit_calendar import calendar
from datetime import datetime

st.set_page_config(page_title="Cabin App", page_icon="🌲", layout="centered")

# --- CUSTOM STYLING (mobile-friendly, polished look) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Poppins', sans-serif;
    }

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 700px;
    }

    .cabin-header {
        text-align: center;
        padding: 1.5rem 1rem;
        background: linear-gradient(135deg, #1e3d2f 0%, #2d5a3d 100%);
        border-radius: 16px;
        margin-bottom: 1.5rem;
        color: white;
    }
    .cabin-header h1 {
        font-size: 1.8rem;
        margin: 0;
        color: white;
    }
    .cabin-header p {
        margin: 0.25rem 0 0 0;
        opacity: 0.85;
        font-size: 0.9rem;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px 10px 0 0;
        padding: 10px 16px;
        font-weight: 600;
    }

    .stButton button {
        border-radius: 10px;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
        width: 100%;
        transition: all 0.15s ease;
    }
    .stButton button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
    }

    .stTextInput input, .stDateInput input {
        border-radius: 10px;
        padding: 0.6rem;
        font-size: 1rem;
    }

    hr {
        margin: 1.5rem 0;
        opacity: 0.2;
    }

    .cabin-card {
        background: rgba(150, 150, 150, 0.06);
        border-radius: 14px;
        padding: 1.2rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# --- SETUP ---
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

CABIN_INFO = """
You are a helpful assistant for a family cabin. Only answer questions using the information below.
If someone asks something not covered here, say you don't have that info and suggest they ask the family directly.

CABIN DETAILS:
- Address: [YOUR CABIN ADDRESS HERE]
- WiFi Network: [WIFI NAME] / Password: [WIFI PASSWORD]
- Check-in time: [e.g. 3:00 PM]
- Check-out time: [e.g. 11:00 AM]
- House rules: [e.g. no shoes inside, quiet hours after 10pm, no smoking indoors]
- Thermostat instructions: [e.g. set to 68 in winter, don't go below 60 when away]
- Trash day: [e.g. Tuesdays, bins are behind the shed]
- Nearest grocery store: [name / distance]
- Emergency contact: [name / number]
- Anything else guests commonly ask about
"""

model = genai.GenerativeModel('gemini-flash-lite-latest', system_instruction=CABIN_INFO)

# --- SHARED GOOGLE SHEETS CLIENT (cached so we don't re-auth every rerun) ---
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

# --- UI LAYOUT ---
st.markdown("""
<div class="cabin-header">
    <h1>🌲 Cabin Booking Portal</h1>
    <p>Plan your next trip up</p>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["🤖 Assistant", "📅 Calendar", "🧺 Inventory"])

with tab1:
    st.markdown('<div class="cabin-card">', unsafe_allow_html=True)
    st.subheader("Need info?")
    user_query = st.text_input("Ask about the cabin:", placeholder="e.g. What's the wifi password?")
    if user_query:
        with st.spinner("Thinking..."):
            st.write(model.generate_content(user_query).text)
    st.markdown('</div>', unsafe_allow_html=True)

with tab2:
    st.markdown('<div class="cabin-card">', unsafe_allow_html=True)
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
            "height": 420,
            "aspectRatio": 1.0
        }
    )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="cabin-card">', unsafe_allow_html=True)
    st.subheader("Reserve Your Dates")
    user_name = st.text_input("Guest Name:", placeholder="Your name")

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
    st.markdown('</div>', unsafe_allow_html=True)

with tab3:
    st.markdown('<div class="cabin-card">', unsafe_allow_html=True)
    st.subheader("What do we need to bring up?")

    inventory_sheet = get_inventory_sheet()

    new_item = st.text_input("Add an item:", key="new_item_input", placeholder="e.g. paper towels")
    if st.button("Add Item"):
        if new_item.strip():
            inventory_sheet.append_row([new_item.strip(), str(datetime.today().date())])
            st.rerun()
        else:
            st.warning("Type something first.")
    st.markdown('</div>', unsafe_allow_html=True)

    rows = inventory_sheet.get_all_values()[1:]

    if not rows:
        st.markdown('<div class="cabin-card">Nothing on the list right now 🎉</div>', unsafe_allow_html=True)
    else:
        for i, row in enumerate(rows):
            item_name = row[0] if len(row) > 0 else ""
            c1, c2 = st.columns([6, 1])
            with c1:
                st.markdown(f'<div class="cabin-card">🧻 {item_name}</div>', unsafe_allow_html=True)
            with c2:
                if st.button("✅", key=f"check_{i}"):
                    inventory_sheet.delete_rows(i + 2)
                    st.rerun()