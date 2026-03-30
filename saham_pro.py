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

# --- 1. CORE DATABASE ENGINE (GSheet Permanent Storage) ---
def get_gsheet_url(sheet_name):
    # Mengambil base URL dari secrets dan mengarahkan ke tab spesifik
    base_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    return f"{base_url}&sheet={sheet_name}"

def load_gsheet_data(sheet_name):
    try:
        url = get_gsheet_url(sheet_name)
        df = pd.read_csv(url)
        df.columns = [str(c).strip().lower() for c in df.columns]
        return df
    except:
        return pd.DataFrame()

def check_login_db(u, p):
    df = load_gsheet_data("users")
    if df.empty: return None
    u_in, p_in = str(u).strip(), str(p).strip()
    res = df[(df['username'].astype(str) == u_in) & (df['password'].astype(str) == p_in)]
    return res.iloc[0]['role'] if not res.empty else None

# Fungsi untuk simpan data (Portfolio/History) ke GSheets
# Karena library gsheets-connection sering error 400, kita gunakan 
# instruksi manual atau bantuan gspread jika ingin write, 
# namun untuk saat ini kita gunakan sistem baca yang stabil dulu.
# NOTE: Untuk fitur WRITE PERMANEN ke GSheets tanpa error 400, 
# disarankan menggunakan service_account (JSON).

# --- 2. PRO CYBER STYLING ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Orbitron:wght@400;900&display=swap');
    .stApp { background-color: #05070a; font-family: 'JetBrains Mono', monospace; color: #e0e0e0; }
    h1 { font-family: 'Orbitron', sans-serif; background: linear-gradient(90deg, #ccff00, #00ffff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .stForm, .stTabs, .stDataFrame { background: rgba(0, 10, 20, 0.6) !important; border: 1px solid rgba(204, 255, 0, 0.2) !important; border-radius: 15px !important; }
    div[data-testid="stMetric"] { background: rgba(204, 255, 0, 0.1); border: 1px solid #ccff0044; border-radius: 10px; padding: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. AUTHENTICATION ---
if "auth" not in st.session_state:
    st.session_state["auth"] = {"logged_in": False, "user": None, "role": None}

if not st.session_state["auth"]["logged_in"]:
    _, col2, _ = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<div style='text-align:center; padding-top:80px;'><h1>IDX</h1><p style='color:#888;'>CYBER TERMINAL</p></div>", unsafe_allow_html=True)
        with st.form("login_form"):
            u = st.text_input("OPERATOR ID").strip()
            p = st.text_input("ACCESS KEY", type="password")
            if st.form_submit_button("AUTHORIZE ACCESS", width="stretch"):
                role = check_login_db(u, p)
                if role:
                    st.session_state["auth"] = {"logged_in": True, "user": u, "role": role}
                    st.rerun()
                else: st.error("INVALID CREDENTIALS")
    st.stop()

# --- 4. SCANNER ENGINE ---
@st.cache_data(ttl=3600)
def load_idx_tickers():
    url = "https://raw.githubusercontent.com/datasets-id/idx-stocks/main/data/stock_codes.csv"
    return [f"{t}.JK" for t in pd.read_csv(url)['ticker'].tolist() if len(str(t)) <= 4]

def run_deep_scan(tickers):
    found = []
    p_bar = st.progress(0)
    # Scan batch 50 saham teratas untuk demo kecepatan
    for i, t in enumerate(tickers[:60]):
        p_bar.progress((i+1)/60)
        try:
            df = yf.download(t, period="5d", interval="1d", progress=False)
            if len(df) < 2: continue
            close = df['Close'].iloc[-1]
            prev = df['Close'].iloc[-2]
            chg = ((close - prev) / prev) * 100
            if chg > 2.0:
                found.append({"TICKER": t.replace(".JK",""), "PRICE": int(close), "CHG%": round(chg, 2)})
        except: continue
    p_bar.empty()
    return pd.DataFrame(found)

# --- 5. INTERFACE ---
user_now = st.session_state["auth"]["user"]
role_now = st.session_state["auth"]["role"]

st.sidebar.markdown(f"### ⚡ SYSTEM ACTIVE\n**USER:** {user_now.upper()}\n**ROLE:** {role_now}")
menu = st.sidebar.radio("COMMAND CENTER", ["STRATEGY SCANNER", "PORTFOLIO", "HISTORY", "LOGOUT"])

if menu == "LOGOUT":
    st.session_state["auth"] = {"logged_in": False}
    st.rerun()

elif menu == "STRATEGY SCANNER":
    st.title("🛰️ MARKET_INTELLIGENCE")
    if st.button("🚀 START DEEP SCAN", use_container_width=True):
        st.session_state.scan_results = run_deep_scan(load_idx_tickers())
    
    if 'scan_results' in st.session_state:
        st.dataframe(st.session_state.scan_results, use_container_width=True, hide_index=True)

elif menu == "PORTFOLIO":
    st.title("💰 PERMANENT_PORTFOLIO")
    # Membaca data Portfolio langsung dari Tab 'portfolio' di GSheets
    df_p = load_gsheet_data("portfolio")
    
    if not df_p.empty:
        # Filter hanya milik user ini (kecuali admin)
        if role_now != "admin":
            df_p = df_p[df_p['username'] == user_now]
        
        st.dataframe(df_p, use_container_width=True, hide_index=True)
        
        # Ringkasan Sederhana
        total_lot = df_p['lots'].sum() if 'lots' in df_p.columns else 0
        st.metric("TOTAL ASSETS", f"{len(df_p)} Stocks", f"{total_lot} Lots")
    else:
        st.info("No active positions found in Google Sheets.")

elif menu == "HISTORY":
    st.title("📜 TRADE_HISTORY")
    # Membaca data History langsung dari Tab 'history' di GSheets
    df_h = load_gsheet_data("history")
    
    if not df_h.empty:
        if role_now != "admin":
            df_h = df_h[df_h['username'] == user_now]
        st.dataframe(df_h, use_container_width=True, hide_index=True)
    else:
        st.info("No trade history record found.")
