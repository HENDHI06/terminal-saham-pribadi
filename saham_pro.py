import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import sqlite3
import warnings
import requests 
import pytz 

# --- 0. CONFIG & DATABASE SETUP ---
warnings.filterwarnings("ignore", category=FutureWarning)
st.set_page_config(page_title="IDX CYBER TERMINAL", page_icon="⚡", layout="wide")

def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, role TEXT, 
                  last_login TEXT, ip_address TEXT, location TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS portfolio 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT, ticker TEXT, buy_price REAL, 
                  lots INTEGER, tp_price REAL, cl_price REAL, date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS history 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT, ticker TEXT, buy_price REAL, 
                  sell_price REAL, lots INTEGER, pnl REAL, date TEXT)''')
    c.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES ('admin', 'admin123', 'admin')")
    conn.commit()
    conn.close()

def get_visitor_info():
    try:
        response = requests.get('https://ipapi.co/json/', timeout=3).json()
        return response.get('ip', 'Unknown'), f"{response.get('city', 'Unknown')}, {response.get('region', 'Unknown')}"
    except:
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

# --- PORTFOLIO ENGINE ---
def add_to_portfolio(u, t, p, l, tp, cl):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("INSERT INTO portfolio (username, ticker, buy_price, lots, tp_price, cl_price, date) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (u, t.upper().strip(), p, l, tp, cl, datetime.now().strftime("%Y-%m-%d")))
    conn.commit(); conn.close()

def sell_position(u, row_id, ticker, buy_p, sell_p, lots):
    pnl = (sell_p - buy_p) * lots * 100
    date_now = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("INSERT INTO history (username, ticker, buy_price, sell_price, lots, pnl, date) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (u, ticker, buy_p, sell_p, lots, pnl, date_now))
    c.execute("DELETE FROM portfolio WHERE id=?", (row_id,))
    conn.commit(); conn.close()

def get_user_portfolio(u, r):
    conn = sqlite3.connect('users.db')
    query = "SELECT * FROM portfolio ORDER BY date DESC" if r == 'admin' else f"SELECT * FROM portfolio WHERE username='{u}' ORDER BY date DESC"
    df = pd.read_sql_query(query, conn)
    conn.close(); return df

init_db()

# --- 1. PRO CYBER STYLING ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Orbitron:wght@400;900&display=swap');
    .stApp { background-color: #05070a; font-family: 'JetBrains Mono', monospace; color: #e0e0e0; }
    h1 { font-family: 'Orbitron', sans-serif; background: linear-gradient(90deg, #ccff00, #00ffff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    div[data-testid="stMetric"], .stDataFrame, .stForm { background: rgba(0, 10, 20, 0.5) !important; border: 1px solid rgba(204, 255, 0, 0.15) !important; border-radius: 10px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. AUTHENTICATION ---
if "auth" not in st.session_state:
    st.session_state["auth"] = {"logged_in": False, "user": None, "role": None}

if not st.session_state["auth"]["logged_in"]:
    _, col2, _ = st.columns([1,1.5,1])
    with col2:
        st.markdown("<h1 style='text-align:center;'>IDX TERMINAL</h1>", unsafe_allow_html=True)
        with st.form("login_form"):
            u = st.text_input("OPERATOR ID").strip()
            p = st.text_input("ACCESS KEY", type="password")
            if st.form_submit_button("AUTHORIZE", width="stretch"):
                role = check_login_db(u, p)
                if role:
                    update_login_info(u)
                    st.session_state["auth"] = {"logged_in": True, "user": u, "role": role}
                    st.rerun()
                else: st.error("ACCESS DENIED")
    st.stop()

# --- 3. DATA & SCANNER ---
@st.cache_data(ttl=3600)
def load_tickers():
    try:
        url = "https://raw.githubusercontent.com/datasets-id/idx-stocks/main/data/stock_codes.csv"
        df = pd.read_csv(url)
        return [f"{str(t).strip().upper()}.JK" for t in df['ticker'].tolist() if len(str(t)) <= 5]
    except: return []

def run_scan(tickers, mode):
    results = []
    p_bar = st.progress(0); status = st.empty()
    batch_size = 40
    for i in range(0, min(len(tickers), 200), batch_size): # Limit 200 for speed
        batch = tickers[i:i+batch_size]
        status.caption(f"Scanning {i}/{len(tickers)}...")
        p_bar.progress(i/200 if i < 200 else 1.0)
        try:
            data = yf.download(batch, period="5d", interval="1d", progress=False, group_by='ticker')
            for t in batch:
                try:
                    df_t = data[t].dropna() if len(batch) > 1 else data.dropna()
                    if len(df_t) < 3: continue
                    last = df_t['Close'].iloc[-1]
                    prev = df_t['Close'].iloc[-2]
                    chg = ((last - prev) / prev) * 100
                    if chg > 1.5:
                        results.append({"TICKER": t.replace(".JK",""), "LAST": int(last), "CHG%": round(chg, 2)})
                except: continue
        except: continue
    p_bar.empty(); status.empty()
    return pd.DataFrame(results)

# --- 4. NAVIGATION ---
user_now = st.session_state["auth"]["user"]
role_now = st.session_state["auth"]["role"]
last_l, ip_l, loc_l = get_sidebar_log(user_now)

st.sidebar.markdown(f"### ⚡ NODE: {user_now.upper()}\n`{role_now}`\nIP: {ip_l}")
menu = st.sidebar.radio("COMMAND CENTER", ["SCANNER", "PORTFOLIO", "SETTINGS"])

if st.sidebar.button("🔴 TERMINATE"):
    st.session_state["auth"] = {"logged_in": False}; st.rerun()

# --- 5. CONTENT ---
if menu == "SCANNER":
    st.title("🛰️ MARKET_SCANNER")
    if st.button("⚡ EXECUTE SCAN", use_container_width=True):
        st.session_state.results = run_scan(load_tickers(), "Agresif")
    
    if 'results' in st.session_state:
        st.dataframe(st.session_state.results, use_container_width=True, hide_index=True)

elif menu == "PORTFOLIO":
    st.title("💰 MONEY_MANAGEMENT")
    with st.expander("➕ ADD POSITION"):
        with st.form("new_pos"):
            c1, c2, c3 = st.columns(3)
            t_in = c1.text_input("Ticker")
            p_in = c2.number_input("Price", min_value=0.0)
            l_in = c3.number_input("Lots", min_value=1)
            if st.form_submit_button("SAVE"):
                add_to_portfolio(user_now, t_in, p_in, l_in, 0, 0); st.rerun()
    
    df_p = get_user_portfolio(user_now, role_now)
    st.dataframe(df_p, use_container_width=True, hide_index=True)

elif menu == "SETTINGS":
    st.title("🔒 SECURITY")
    st.write("Operator:", user_now)
    st.write("Location:", loc_l)
