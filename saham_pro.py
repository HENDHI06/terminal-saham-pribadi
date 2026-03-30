import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import warnings
import requests 
import pytz 

# --- 0. CONFIG & DATABASE SETUP ---
warnings.filterwarnings("ignore", category=FutureWarning)
st.set_page_config(page_title="IDX CYBER TERMINAL", page_icon="⚡", layout="wide")

# Inisialisasi Koneksi ke Google Sheets
try:
    conn_gs = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Koneksi GSheets Gagal Konfigurasi: {e}")

def get_visitor_info():
    providers = ['https://ipapi.co/json/', 'https://ipinfo.io/json', 'https://ifconfig.co/json']
    for url in providers:
        try:
            response = requests.get(url, timeout=3).json()
            ip = response.get('ip') or response.get('query', 'Unknown')
            city = response.get('city', 'Unknown')
            region = response.get('region', 'Unknown') or response.get('regionName', 'Unknown')
            if ip != 'Unknown': return ip, f"{city}, {region}"
        except: continue
    return "Cloud Node", "Data Center"

def update_login_info(u):
    try:
        ip, loc = get_visitor_info()
        tz = pytz.timezone('Asia/Jakarta') 
        now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
        df = conn_gs.read(worksheet="users")
        df.loc[df['username'] == u, ['last_login', 'ip_address', 'location']] = [now, ip, loc]
        conn_gs.update(worksheet="users", data=df)
    except: pass

def check_login_db(u, p):
    try:
        # Membaca data terbaru dari Google Sheets
        df = conn_gs.read(worksheet="users")
        
        # Bersihkan data (pastikan string dan tidak ada spasi)
        df['username'] = df['username'].astype(str).str.strip()
        df['password'] = df['password'].astype(str).str.strip()
        
        # Filter mencari user
        res = df[(df['username'] == str(u).strip()) & (df['password'] == str(p).strip())]
        
        if not res.empty:
            return res.iloc[0]['role']
        return None
    except Exception as e:
        st.error(f"Error saat verifikasi login: {e}")
        return None

# --- 1. STYLE ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Orbitron:wght@400;900&display=swap');
    .stApp { background-color: #05070a; font-family: 'JetBrains Mono', monospace; color: #e0e0e0; }
    h1 { font-family: 'Orbitron', sans-serif; background: linear-gradient(90deg, #ccff00, #00ffff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .stForm { background: rgba(0, 10, 20, 0.5) !important; border: 1px solid rgba(204, 255, 0, 0.15) !important; border-radius: 10px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. AUTHENTICATION ---
if "auth" not in st.session_state:
    st.session_state["auth"] = {"logged_in": False, "user": None, "role": None}

if not st.session_state["auth"]["logged_in"]:
    _, col2, _ = st.columns([1,1.5,1])
    with col2:
        st.markdown("<div style='text-align:center; padding:50px 0;'><h1>IDX</h1><p style='color:#888;'>CYBER TERMINAL</p></div>", unsafe_allow_html=True)
        
        # --- KODE DEBUG DIMULAI ---
        st.divider()
        if st.checkbox("🔍 DEBUG: LIHAT DATA DARI GOOGLE SHEETS"):
            try:
                test_df = conn_gs.read(worksheet="users")
                st.write("Data yang terdeteksi di Sheets:")
                st.dataframe(test_df)
            except Exception as e:
                st.error(f"Gagal baca Sheets: {e}")
                st.info("Pastikan link di Secrets sudah benar dan Tab bernama 'users'")
        st.divider()
        # --- KODE DEBUG SELESAI ---

        with st.form("login_form"):
            u = st.text_input("OPERATOR ID").strip()
            p = st.text_input("ACCESS KEY", type="password")
            if st.form_submit_button("AUTHORIZE ACCESS", width="stretch"):
                role = check_login_db(u, p)
                if role:
                    update_login_info(u)
                    st.session_state["auth"] = {"logged_in": True, "user": u, "role": role}
                    st.rerun()
                else: 
                    st.error("ACCESS DENIED: Username atau Password Salah")
    st.stop()

# --- 3. LANJUTKAN KE MENU UTAMA ---
st.success(f"Welcome back, {st.session_state['auth']['user']}!")
# ... (masukkan kode menu scanner/portfolio kamu di sini)
