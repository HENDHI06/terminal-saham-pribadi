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

# --- GSHEETS PERMANENT STORAGE ---
def get_gs_conn():
    return st.connection("gsheets", type=GSheetsConnection)

def load_gs_data(worksheet):
    try:
        return get_gs_conn().read(worksheet=worksheet, ttl=0).dropna(how='all')
    except:
        return pd.DataFrame()

def save_gs_data(df, worksheet):
    get_gs_conn().update(worksheet=worksheet, data=df)

# SQLite untuk User Management (Tetap di Lokal untuk Keamanan)
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, role TEXT, 
                  last_login TEXT, ip_address TEXT, location TEXT)''')
    c.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES ('admin', 'admin123', 'admin')")
    conn.commit(); conn.close()

def get_visitor_info():
    providers = ['https://ipapi.co/json/', 'https://ipinfo.io/json']
    for url in providers:
        try:
            response = requests.get(url, timeout=3).json()
            return response.get('ip', 'Unknown'), f"{response.get('city', 'Unknown')}, {response.get('region', 'Unknown')}"
        except: continue
    return "Cloud Node", "Data Center"

def update_login_info(u):
    ip, loc = get_visitor_info()
    tz = pytz.timezone('Asia/Jakarta') 
    now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect('users.db'); c = conn.cursor()
    c.execute("UPDATE users SET last_login=?, ip_address=?, location=? WHERE username=?", (now, ip, loc, u))
    conn.commit(); conn.close()

def get_sidebar_log(u):
    conn = sqlite3.connect('users.db'); c = conn.cursor()
    c.execute("SELECT last_login, ip_address, location FROM users WHERE username=?", (u,))
    res = c.fetchone(); conn.close()
    return res if res else ("-", "-", "-")

def check_login_db(u, p):
    conn = sqlite3.connect('users.db'); c = conn.cursor()
    c.execute("SELECT role FROM users WHERE username=? AND password=?", (u, p))
    res = c.fetchone(); conn.close()
    return res[0] if res else None

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

# --- GSHEETS FUNCTIONS FOR PORTFOLIO ---
def add_to_portfolio(u, t, p, l, tp, cl):
    df = load_gs_data("portfolio")
    new_row = pd.DataFrame([{"username": u, "ticker": t.upper().strip(), "buy_price": p, "lots": l, "tp_price": tp, "cl_price": cl, "date": datetime.now().strftime("%Y-%m-%d")}])
    save_gs_data(pd.concat([df, new_row], ignore_index=True), "portfolio")

def sell_position(u, row_idx, ticker, buy_p, sell_p, lots):
    df_h = load_gs_data("history")
    pnl = (sell_p - buy_p) * lots * 100
    new_h = pd.DataFrame([{"username": u, "ticker": ticker, "buy_price": buy_p, "sell_price": sell_p, "lots": lots, "pnl": pnl, "date": datetime.now().strftime("%Y-%m-%d")}])
    save_gs_data(pd.concat([df_h, new_h], ignore_index=True), "history")
    df_p = load_gs_data("portfolio")
    save_gs_data(df_p.drop(row_idx), "portfolio")

init_db()

# --- 1. PRO CYBER STYLING (FIXED) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Orbitron:wght@400;900&display=swap');
    [data-testid="stHeaderActionElements"], .stDeployButton, #MainMenu { display: none !important; }
    .stApp {
        background-color: #05070a;
        background-image: linear-gradient(rgba(204, 255, 0, 0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(204, 255, 0, 0.02) 1px, transparent 1px), radial-gradient(circle at center, rgba(10, 25, 47, 0.4), #05070a);
        background-size: 20px 20px, 20px 20px, 100% 100%;
        font-family: 'JetBrains Mono', monospace; color: #e0e0e0;
    }
    div[data-testid="stMetric"], .status-box, .stDataFrame, div[data-testid="stExpander"], .stTabs, .stForm {
        background: rgba(0, 10, 20, 0.5) !important; backdrop-filter: blur(12px); border: 1px solid rgba(204, 255, 0, 0.15) !important; border-radius: 10px !important;
    }
    h1 { font-family: 'Orbitron', sans-serif; background: linear-gradient(90deg, #ccff00, #00ffff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. AUTHENTICATION ---
if "auth" not in st.session_state: st.session_state["auth"] = {"logged_in": False, "user": None, "role": None}
if not st.session_state["auth"]["logged_in"]:
    _, col2, _ = st.columns([1,1.5,1])
    with col2:
        st.markdown("<div style='text-align:center; padding:50px 0;'><h1>IDX</h1><p>CYBER TERMINAL</p></div>", unsafe_allow_html=True)
        with st.form("login"):
            u = st.text_input("OPERATOR ID").strip()
            p = st.text_input("ACCESS KEY", type="password")
            if st.form_submit_button("AUTHORIZE ACCESS"):
                role = check_login_db(u, p)
                if role:
                    update_login_info(u)
                    st.session_state["auth"] = {"logged_in": True, "user": u, "role": role}
                    st.rerun()
                else: st.error("ACCESS DENIED")
    st.stop()

# --- 3. DATA ENGINE ---
@st.cache_data(ttl=86400)
def load_tickers():
    try:
        df = pd.read_csv("https://raw.githubusercontent.com/datasets-id/idx-stocks/main/data/stock_codes.csv")
        return [f"{str(t).strip().upper()}.JK" for t in df['ticker'].tolist() if len(str(t)) <= 5]
    except: return []

def run_scan(tickers, mode):
    results = []
    status_ui = st.empty(); p_bar = st.progress(0)
    for i in range(0, len(tickers), 30):
        batch = tickers[i:i+30]
        status_ui.caption(f"SCANNING: {i}/{len(tickers)}")
        p_bar.progress(min(i / len(tickers), 1.0))
        try:
            data = yf.download(batch, period="10d", progress=False, auto_adjust=True)
            for t in batch:
                try:
                    df_t = data[t].dropna() if len(batch) > 1 else data.dropna()
                    if len(df_t) < 6: continue
                    last, prev = df_t.iloc[-1], df_t.iloc[-2]
                    c_now, vol = float(last['Close']), float(last['Volume'])
                    chg = ((c_now - float(prev['Close'])) / float(prev['Close'])) * 100
                    val = c_now * vol
                    if (mode == "Ketat" and chg > 3 and val > 1e9) or (mode == "Agresif" and chg > 1):
                        results.append({"TICKER": t.replace(".JK",""), "LAST": int(c_now), "CHG%": round(chg, 2), "VAL(M)": round(val/1e6, 1), "FULL": t})
                except: continue
        except: continue
    status_ui.empty(); p_bar.empty()
    return pd.DataFrame(results)

# --- 4. NAVIGATION ---
role = st.session_state["auth"]["role"]
user_now = st.session_state["auth"]["user"]
last_l, ip_l, loc_l = get_sidebar_log(user_now)

st.sidebar.markdown(f"<div class='status-box' style='padding:10px;'><h3>{user_now.upper()}</h3><p style='font-size:10px; color:#888;'>IP: {ip_l}<br>LOC: {loc_l}</p></div>", unsafe_allow_html=True)
menu_list = ["STRATEGY SCANNER", "MONEY MANAGEMENT", "SECURITY SETTINGS"]
if role == "admin": menu_list.insert(1, "USER MANAGEMENT")
menu = st.sidebar.radio("COMMAND CENTER", menu_list)

if st.sidebar.button("🔴 TERMINATE SESSION", width="stretch"):
    st.session_state["auth"] = {"logged_in": False}; st.rerun()

# --- 5. CONTENT: SCANNER ---
if menu == "STRATEGY SCANNER":
    st.title("🛰️ MARKET_INTELLIGENCE")
    
    # Tombol Refresh Price (Sync)
    c_algo, c_sync = st.columns([4, 1])
    with c_algo: mode_scan = st.radio("ALGO_SENSITIVITY", ["Ketat", "Agresif"], horizontal=True)
    with c_sync:
        if st.button("🔄 REFRESH PRICE", use_container_width=True):
            if 'results' in st.session_state:
                st.session_state.scan_time = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%H:%M:%S")
                st.rerun()

    if st.button("⚡ EXECUTE_DEEP_SCAN", width="stretch"):
        st.session_state.results = run_scan(load_tickers(), mode_scan)
        st.session_state.scan_time = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%H:%M:%S")

    if 'results' in st.session_state and not st.session_state.results.empty:
        st.caption(f"Last Sync: {st.session_state.scan_time} WIB")
        df = st.session_state.results
        st.dataframe(df.drop(columns=['FULL']), use_container_width=True, hide_index=True)
        
        sel_t = st.selectbox("FOCUS_TARGET", df['TICKER'].tolist())
        full_t = df[df['TICKER'] == sel_t]['FULL'].values[0]
        chart_data = yf.download(full_t, period="6mo", progress=False)
        fig = go.Figure(data=[go.Candlestick(x=chart_data.index, open=chart_data['Open'], high=chart_data['High'], low=chart_data['Low'], close=chart_data['Close'])])
        fig.update_layout(template="plotly_dark", height=450, margin=dict(l=0,r=0,b=0,t=0))
        st.plotly_chart(fig, use_container_width=True)

# --- 6. CONTENT: MONEY MANAGEMENT ---
elif menu == "MONEY MANAGEMENT":
    st.title("💰 MONEY_MANAGEMENT")
    t1, t2 = st.tabs(["📈 ACTIVE PORTFOLIO", "📜 TRADING HISTORY"])
    
    with t1:
        with st.expander("➕ ADD NEW POSITION"):
            with st.form("add_p"):
                c1, c2, c3 = st.columns(3)
                tk_in = c1.text_input("Ticker"); pr_in = c2.number_input("Price"); lt_in = c3.number_input("Lots", min_value=1)
                if st.form_submit_button("SAVE"):
                    add_to_portfolio(user_now, tk_in, pr_in, lt_in, 0, 0); st.rerun()
        
        df_p = load_gs_data("portfolio")
        if not df_p.empty:
            view_p = df_p if role == 'admin' else df_p[df_p['username'] == user_now]
            st.dataframe(view_p, use_container_width=True)
            for idx, row in view_p.iterrows():
                if st.button(f"🚀 SELL {row['ticker']}", key=f"sell_{idx}"):
                    sell_position(user_now, idx, row['ticker'], row['buy_price'], row['buy_price'], row['lots'])
                    st.rerun()

    with t2:
        df_h = load_gs_data("history")
        if not df_h.empty:
            view_h = df_h if role == 'admin' else df_h[df_h['username'] == user_now]
            st.dataframe(view_h, use_container_width=True)

# --- 7. CONTENT: USER MANAGEMENT (FIXED) ---
elif menu == "USER MANAGEMENT":
    st.title("👤 ACCESS_CONTROL")
    conn = sqlite3.connect('users.db')
    df_u = pd.read_sql_query("SELECT username, role, last_login, location FROM users", conn)
    st.dataframe(df_u, use_container_width=True, hide_index=True)
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Add User")
        with st.form("add_user"):
            nu, np, nr = st.text_input("Username"), st.text_input("Password"), st.selectbox("Role", ["user", "admin"])
            if st.form_submit_button("GRANT ACCESS"):
                if add_user_db(nu, np, nr): st.success(f"User {nu} Added"); st.rerun()
    with c2:
        st.subheader("Revoke User")
        du = st.text_input("Username to Delete")
        if st.button("🔴 DELETE PERMANENTLY"):
            if delete_user_db(du): st.warning(f"User {du} Deleted"); st.rerun()

elif menu == "SECURITY SETTINGS":
    st.title("🔒 SECURITY_VAULT")
    with st.form("change_p"):
        new_key = st.text_input("NEW ACCESS KEY", type="password")
        if st.form_submit_button("UPDATE"):
            conn = sqlite3.connect('users.db'); c = conn.cursor()
            c.execute("UPDATE users SET password=? WHERE username=?", (new_key, user_now))
            conn.commit(); conn.close(); st.success("Key Updated")
