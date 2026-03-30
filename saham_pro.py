import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import warnings
import requests 
import pytz 

# --- 0. CONFIG ---
warnings.filterwarnings("ignore", category=FutureWarning)
st.set_page_config(page_title="IDX CYBER TERMINAL", page_icon="⚡", layout="wide")

# Fungsi Ambil Data Manual (Tanpa Library Relevan yang Error 400)
def fetch_gsheets_data():
    try:
        # Mengambil URL direct CSV dari secrets
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        df = pd.read_csv(url)
        # Bersihkan nama kolom (lowercase & hapus spasi)
        df.columns = [str(c).strip().lower() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Koneksi Database Putus: {e}")
        return pd.DataFrame()

def get_visitor_info():
    try:
        response = requests.get('https://ipapi.co/json/', timeout=3).json()
        return response.get('ip', 'Unknown'), f"{response.get('city')}, {response.get('region')}"
    except:
        return "Unknown", "Data Center"

def check_login_db(u, p):
    df = fetch_gsheets_data()
    if df.empty:
        return None
    
    # Bersihkan input dan data tabel
    u_input = str(u).strip()
    p_input = str(p).strip()
    
    df['username'] = df['username'].astype(str).str.strip()
    df['password'] = df['password'].astype(str).str.strip()
    
    res = df[(df['username'] == u_input) & (df['password'] == p_input)]
    
    if not res.empty:
        return res.iloc[0]['role']
    return None

# --- 1. STYLE ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Orbitron:wght@400;900&display=swap');
    .stApp { background-color: #05070a; font-family: 'JetBrains Mono', monospace; color: #e0e0e0; }
    h1 { font-family: 'Orbitron', sans-serif; background: linear-gradient(90deg, #ccff00, #00ffff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .stForm { background: rgba(0, 10, 20, 0.6) !important; border: 1px solid rgba(204, 255, 0, 0.2) !important; border-radius: 15px !important; padding: 30px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. AUTHENTICATION ---
if "auth" not in st.session_state:
    st.session_state["auth"] = {"logged_in": False, "user": None, "role": None}

if not st.session_state["auth"]["logged_in"]:
    _, col2, _ = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<div style='text-align:center; padding-top:100px;'><h1>IDX</h1><p style='color:#888; letter-spacing:3px;'>CYBER TERMINAL</p></div>", unsafe_allow_html=True)
        
        # DEBUG MODE (Sangat stabil dengan pd.read_csv)
        with st.expander("🛠️ SYSTEM CHECK"):
            if st.button("Test Database Connection"):
                data = fetch_gsheets_data()
                if not data.empty:
                    st.success("Database Connected!")
                    st.dataframe(data)
                else:
                    st.error("Connection Failed. Check Secrets URL.")

        with st.form("login_form"):
            u = st.text_input("OPERATOR ID").strip()
            p = st.text_input("ACCESS KEY", type="password")
            if st.form_submit_button("AUTHORIZE ACCESS", width="stretch"):
                role = check_login_db(u, p)
                if role:
                    st.session_state["auth"] = {"logged_in": True, "user": u, "role": role}
                    st.rerun()
                else: 
                    st.error("INVALID CREDENTIALS")
    st.stop()

# --- 3. MAIN INTERFACE ---
st.sidebar.title("⚡ TERMINAL")
st.sidebar.write(f"USER: {st.session_state['auth']['user'].upper()}")
if st.sidebar.button("LOGOUT"):
    st.session_state["auth"] = {"logged_in": False}
    st.rerun()

st.title("🛰️ MARKET_INTELLIGENCE")
st.success(f"Access Granted. Role: {st.session_state['auth']['role']}")

# Lanjutkan kode scanner/chart Anda di sini...
