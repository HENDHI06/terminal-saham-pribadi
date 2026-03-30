import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import sqlite3
import warnings
import os
import requests 
import pytz 
from streamlit_gsheets import GSheetsConnection

# --- 0. CONFIG & DATABASE SETUP ---
warnings.filterwarnings("ignore", category=FutureWarning)
st.set_page_config(page_title="IDX CYBER TERMINAL", page_icon="⚡", layout="wide")

# Fungsi Khusus GSheets untuk Data Permanen
def load_permanent_data(worksheet_name):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        return conn.read(worksheet=worksheet_name, ttl=0)
    except:
        return pd.DataFrame()

def save_permanent_data(df, worksheet_name):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        conn.update(worksheet=worksheet_name, data=df)
        return True
    except:
        return False

# Database lokal tetap dipakai untuk LOGIN saja (agar cepat)
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, role TEXT, 
                  last_login TEXT, ip_address TEXT, location TEXT)''')
    c.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES ('admin', 'admin123', 'admin')")
    conn.commit()
    conn.close()

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
    ip, loc = get_visitor_info()
    tz = pytz.timezone('Asia/Jakarta') 
    now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET last_login=?, ip_address=?, location=? WHERE username=?", (now, ip, loc, u))
    conn.commit()
    conn.close()

def get_sidebar_log(u):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT last_login, ip_address, location FROM users WHERE username=?", (u,))
    res = c.fetchone()
    conn.close()
    return res if res else ("-", "-", "-")

def check_login_db(u, p):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT role FROM users WHERE username=? AND password=?", (u, p))
    res = c.fetchone()
    conn.close()
    return res[0] if res else None

# --- MODIFIKASI: FUNGSI PORTFOLIO KE GSHEETS ---
def add_to_portfolio(u, t, p, l, tp, cl):
    df = load_permanent_data("portfolio")
    new_data = pd.DataFrame([{
        "username": u, "ticker": t.upper().strip(), "buy_price": p, 
        "lots": l, "tp_price": tp, "cl_price": cl, "date": datetime.now().strftime("%Y-%m-%d")
    }])
    df = pd.concat([df, new_data], ignore_index=True)
    save_permanent_data(df, "portfolio")

def sell_position(u, ticker, buy_p, sell_p, lots, original_df_index):
    # 1. Update History
    df_h = load_permanent_data("history")
    pnl = (sell_p - buy_p) * lots * 100
    new_h = pd.DataFrame([{
        "username": u, "ticker": ticker, "buy_price": buy_p, 
        "sell_price": sell_p, "lots": lots, "pnl": pnl, "date": datetime.now().strftime("%Y-%m-%d")
    }])
    df_h = pd.concat([df_h, new_h], ignore_index=True)
    save_permanent_data(df_h, "history")
    
    # 2. Hapus dari Portfolio
    df_p = load_permanent_data("portfolio")
    df_p = df_p.drop(original_df_index)
    save_permanent_data(df_p, "portfolio")

def get_user_portfolio(u, r):
    df = load_permanent_data("portfolio")
    if df.empty: return df
    if r == 'admin': return df
    return df[df['username'] == u]

# Fungsi User tetap di SQLite (Keamanan)
def add_user_db(u, p, r):
    try:
        conn = sqlite3.connect('users.db'); c = conn.cursor()
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (u, p, r))
        conn.commit(); conn.close(); return True
    except: return False

def delete_user_db(u):
    if u == 'admin': return False
    conn = sqlite3.connect('users.db'); c = conn.cursor()
    c.execute("DELETE FROM users WHERE username=?", (u,)); conn.commit(); conn.close(); return True

def update_password_db(u, new_p):
    try:
        conn = sqlite3.connect('users.db'); c = conn.cursor()
        c.execute("UPDATE users SET password=? WHERE username=?", (new_p, u))
        conn.commit(); conn.close(); return True
    except: return False

init_db()

# --- 1. PRO CYBER STYLING (TEMA ANDA) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Orbitron:wght@400;900&display=swap');
    [data-testid="stHeaderActionElements"], .stDeployButton, #MainMenu { display: none !important; }
    header { background-color: transparent !important; }
    .stApp {
        background-color: #05070a;
        background-image: 
            linear-gradient(rgba(204, 255, 0, 0.02) 1px, transparent 1px),
            linear-gradient(90deg, rgba(204, 255, 0, 0.02) 1px, transparent 1px),
            radial-gradient(circle at center, rgba(10, 25, 47, 0.4), #05070a);
        background-size: 20px 20px, 20px 20px, 100% 100%;
        font-family: 'JetBrains Mono', monospace;
        color: #e0e0e0;
    }
    div[data-testid="stMetric"], .status-box, .stDataFrame, div[data-testid="stExpander"], .stTabs, .stForm {
        background: rgba(0, 10, 20, 0.5) !important;
        backdrop-filter: blur(12px);
        border: 1px solid rgba(204, 255, 0, 0.15) !important;
        border-radius: 10px !important;
    }
    h1 { font-family: 'Orbitron', sans-serif; background: linear-gradient(90deg, #ccff00, #00ffff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. AUTHENTICATION ---
if "auth" not in st.session_state:
    st.session_state["auth"] = {"logged_in": False, "user": None, "role": None}

if not st.session_state["auth"]["logged_in"]:
    _, col2, _ = st.columns([1,1.5,1])
    with col2:
        st.markdown("<div style='text-align:center; padding:50px 0;'><h1 style='font-size:3rem;'>IDX</h1><p style='color:#888;'>CYBER TERMINAL</p></div>", unsafe_allow_html=True)
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

# --- 3. DATA ENGINE (TICKER & SCANNER) ---
@st.cache_data(ttl=86400)
def load_tickers():
    try:
        url = "https://raw.githubusercontent.com/datasets-id/idx-stocks/main/data/stock_codes.csv"
        df_idx = pd.read_csv(url)
        return [str(t).strip().upper() + ".JK" for t in df_idx['ticker'].tolist() if len(str(t)) <= 5]
    except: return []

def run_scan(tickers, mode):
    results = []
    status_ui = st.empty(); p_bar = st.progress(0)
    for i in range(0, min(len(tickers), 300), 30): # Scan 300 saham pertama agar cepat
        batch = tickers[i:i+30]
        status_ui.caption(f"SCANNING: {i}/{len(tickers)}")
        p_bar.progress(min(i / 300, 1.0))
        try:
            data = yf.download(batch, period="5d", interval="1d", group_by='ticker', progress=False)
            for t in batch:
                try:
                    df_t = data[t].dropna()
                    if len(df_t) < 3: continue
                    last, prev = df_t.iloc[-1], df_t.iloc[-2]
                    chg = ((last['Close'] - prev['Close']) / prev['Close']) * 100
                    if (mode == "Ketat" and chg > 3) or (mode == "Agresif" and chg > 1.5):
                        results.append({
                            "TICKER": t.replace(".JK",""), "LAST": int(last['Close']), "CHG%": round(chg, 2),
                            "ENTRY": f"{int(last['Close'])}-{int(last['Close']*1.01)}", "TP": int(last['Close']*1.03), 
                            "CL": int(last['Close']*0.97), "VAL(M)": round((last['Close']*last['Volume'])/1_000_000, 1), "FULL": t
                        })
                except: continue
        except: continue
    status_ui.empty(); p_bar.empty()
    return pd.DataFrame(results)

def draw_mobile_cards(df):
    for _, row in df.iterrows():
        chg_color = "#ccff00" if row['CHG%'] > 0 else "#ff4b4b"
        st.markdown(f"""<div style="background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(204, 255, 0, 0.2); border-radius: 12px; padding: 15px; margin-bottom: 12px; border-left: 5px solid {chg_color};">
            <b>{row['TICKER']}</b> | <span style="color:{chg_color}">{row['CHG%']}%</span><br>Last: {row['LAST']} | Val: {row['VAL(M)']}M</div>""", unsafe_allow_html=True)

# --- 4. NAVIGATION ---
role = st.session_state["auth"]["role"]
user_now = st.session_state["auth"]["user"]
last_l, ip_l, loc_l = get_sidebar_log(user_now)

st.sidebar.markdown(f"<div style='padding:10px; border:1px solid #ccff0033; border-radius:10px;'><h3>{user_now.upper()}</h3><p style='font-size:10px;'>{loc_l}</p></div>", unsafe_allow_html=True)
menu_list = ["STRATEGY SCANNER", "MONEY MANAGEMENT", "SECURITY SETTINGS"]
if role == "admin": menu_list.insert(1, "USER MANAGEMENT")
menu = st.sidebar.radio("COMMAND CENTER", menu_list)

if st.sidebar.button("🔴 TERMINATE SESSION", width="stretch"):
    st.session_state["auth"] = {"logged_in": False}; st.rerun()

# --- 5. CONTENT (STRATEGY SCANNER) ---
if menu == "STRATEGY SCANNER":
    st.title("🛰️ MARKET_INTELLIGENCE")
    mode_scan = st.radio("ALGO_SENSITIVITY", ["Ketat", "Agresif"], horizontal=True)
    if st.button("⚡ EXECUTE_DEEP_SCAN", width="stretch"):
        st.session_state.results = run_scan(load_tickers(), mode_scan)

    if 'results' in st.session_state:
        df = st.session_state.results
        tab_desk, tab_mob = st.tabs(["🖥️ DESKTOP VIEW", "📱 MOBILE VIEW"])
        with tab_desk: st.dataframe(df.drop(columns=['FULL']), use_container_width=True, hide_index=True)
        with tab_mob: draw_mobile_cards(df)

# --- 6. CONTENT (MONEY MANAGEMENT - MODIFIED FOR PERMANENT) ---
elif menu == "MONEY MANAGEMENT":
    st.title("💰 MONEY_MANAGEMENT")
    tab1, tab2 = st.tabs(["📈 ACTIVE PORTFOLIO", "📜 TRADING HISTORY"])
    
    with tab1:
        with st.expander("➕ ADD NEW POSITION"):
            with st.form("add_p"):
                c1, c2, c3 = st.columns(3)
                t_in = c1.text_input("Ticker"); p_in = c2.number_input("Buy Price"); l_in = c3.number_input("Lots", min_value=1)
                if st.form_submit_button("SAVE"):
                    add_to_portfolio(user_now, t_in, p_in, l_in, 0, 0); st.success("Stored to Cloud"); st.rerun()
        
        df_p = get_user_portfolio(user_now, role)
        if not df_p.empty:
            st.dataframe(df_p, use_container_width=True)
            for idx, row in df_p.iterrows():
                if st.button(f"SELL {row['ticker']}", key=f"s_{idx}"):
                    sell_position(user_now, row['ticker'], row['buy_price'], row['buy_price'], row['lots'], idx)
                    st.rerun()
        else: st.info("No active positions in GSheets.")

    with tab2:
        df_h = load_permanent_data("history")
        if not df_h.empty:
            if role != "admin": df_h = df_h[df_h['username'] == user_now]
            st.dataframe(df_h, use_container_width=True)
        else: st.info("History Empty.")

# --- 7. USER & SECURITY (TETAP SAMA) ---
elif menu == "USER MANAGEMENT":
    st.title("👤 ACCESS_CONTROL")
    conn = sqlite3.connect('users.db')
    df_u = pd.read_sql_query("SELECT username, role, last_login, location FROM users", conn)
    st.dataframe(df_u, use_container_width=True)

elif menu == "SECURITY SETTINGS":
    st.title("🔒 SECURITY_VAULT")
    new_p = st.text_input("NEW ACCESS KEY", type="password")
    if st.button("UPDATE"):
        if update_password_db(user_now, new_p): st.success("Updated")
