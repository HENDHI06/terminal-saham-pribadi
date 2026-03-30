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
# Pastikan st.secrets sudah diisi di dashboard Streamlit
conn_gs = st.connection("gsheets", type=GSheetsConnection)

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

def get_sidebar_log(u):
    try:
        df = conn_gs.read(worksheet="users")
        res = df[df['username'] == u]
        if not res.empty:
            return res.iloc[0]['last_login'], res.iloc[0]['ip_address'], res.iloc[0]['location']
    except: pass
    return "-", "-", "-"

def check_login_db(u, p):
    try:
        df = conn_gs.read(worksheet="users")
        res = df[(df['username'] == u) & (df['password'].astype(str) == str(p))]
        return res.iloc[0]['role'] if not res.empty else None
    except: return None

def add_to_portfolio(u, t, p, l, tp, cl):
    df = conn_gs.read(worksheet="portfolio")
    new_id = int(df['id'].max() + 1) if not df.empty and 'id' in df.columns else 1
    new_row = pd.DataFrame([{
        "id": new_id, "username": u, "ticker": t.upper().strip(), 
        "buy_price": p, "lots": l, "tp_price": tp, "cl_price": cl, 
        "date": datetime.now().strftime("%Y-%m-%d")
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    conn_gs.update(worksheet="portfolio", data=df)

def sell_position(u, row_id, ticker, buy_p, sell_p, lots):
    pnl = (sell_p - buy_p) * lots * 100
    date_now = datetime.now().strftime("%Y-%m-%d")
    df_h = conn_gs.read(worksheet="history")
    new_id_h = int(df_h['id'].max() + 1) if not df_h.empty and 'id' in df_h.columns else 1
    new_h = pd.DataFrame([{
        "id": new_id_h, "username": u, "ticker": ticker, "buy_price": buy_p, 
        "sell_price": sell_p, "lots": lots, "pnl": pnl, "date": date_now
    }])
    df_h = pd.concat([df_h, new_h], ignore_index=True)
    conn_gs.update(worksheet="history", data=df_h)
    df_p = conn_gs.read(worksheet="portfolio")
    df_p = df_p[df_p['id'] != row_id]
    conn_gs.update(worksheet="portfolio", data=df_p)

def get_user_portfolio(u, r):
    df = conn_gs.read(worksheet="portfolio")
    if df.empty: return pd.DataFrame()
    return df if r == 'admin' else df[df['username'] == u]

# --- 1. STYLE ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Orbitron:wght@400;900&display=swap');
    [data-testid="stHeaderActionElements"], .stDeployButton, #MainMenu { display: none !important; }
    header { background-color: transparent !important; }
    .stApp {
        background-color: #05070a;
        background-image: linear-gradient(rgba(204, 255, 0, 0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(204, 255, 0, 0.02) 1px, transparent 1px);
        background-size: 20px 20px;
        font-family: 'JetBrains Mono', monospace;
        color: #e0e0e0;
    }
    div[data-testid="stMetric"], .status-box, .stDataFrame, div[data-testid="stExpander"], .stTabs, .stForm {
        background: rgba(0, 10, 20, 0.5) !important;
        backdrop-filter: blur(12px);
        border: 1px solid rgba(204, 255, 0, 0.15) !important;
        border-radius: 10px !important;
    }
    h1 {
        font-family: 'Orbitron', sans-serif;
        background: linear-gradient(90deg, #ccff00, #00ffff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. AUTHENTICATION ---
if "auth" not in st.session_state:
    st.session_state["auth"] = {"logged_in": False, "user": None, "role": None}

if not st.session_state["auth"]["logged_in"]:
    _, col2, _ = st.columns([1,1.5,1])
    with col2:
        st.markdown("<div style='text-align:center; padding:50px 0;'><h1 style='font-size:3rem; margin-bottom:0;'>IDX</h1><p style='color:#888; letter-spacing:5px;'>CYBER TERMINAL</p></div>", unsafe_allow_html=True)
        with st.form("login_form"):
            u = st.text_input("OPERATOR ID").strip()
            p = st.text_input("ACCESS KEY", type="password")
            if st.form_submit_button("AUTHORIZE ACCESS", width="stretch"):
                role = check_login_db(u, p)
                if role:
                    update_login_info(u)
                    st.session_state["auth"] = {"logged_in": True, "user": u, "role": role}
                    st.rerun()
                else: st.error("ACCESS DENIED")
    st.stop()

# --- 3. LOGIKA SIDEBAR & KONTEN ---
role = st.session_state["auth"]["role"]
user_now = st.session_state["auth"]["user"]
last_l, ip_l, loc_l = get_sidebar_log(user_now)

st.sidebar.markdown(f"**USER:** {user_now.upper()}  \n**ROLE:** {role.upper()}")
if st.sidebar.button("🔴 TERMINATE SESSION"):
    st.session_state["auth"] = {"logged_in": False}
    st.rerun()

menu = st.sidebar.radio("COMMAND CENTER", ["STRATEGY SCANNER", "MONEY MANAGEMENT"])

if menu == "STRATEGY SCANNER":
    st.title("🛰️ MARKET_INTELLIGENCE")
    st.write("Scanner active...")
    # (Bagian scanner yfinance Anda di sini)

elif menu == "MONEY MANAGEMENT":
    st.title("💰 MONEY_MANAGEMENT")
    # (Bagian tabel portfolio Anda di sini)
