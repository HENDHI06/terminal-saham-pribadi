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
import hashlib

# --- 0. CONFIG & DATABASE SETUP ---
warnings.filterwarnings("ignore", category=FutureWarning)
st.set_page_config(page_title="IDX CYBER TERMINAL", page_icon="⚡", layout="wide")

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

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
    
    # Admin default (hashed)
    admin_pw = hash_password('admin123')
    c.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES ('admin', ?, 'admin')", (admin_pw,))
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
    hashed = hash_password(p)
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT role FROM users WHERE username=? AND password=?", (u, hashed))
    res = c.fetchone()
    if not res:
        c.execute("SELECT role FROM users WHERE username=? AND password=?", (u, p))
        res = c.fetchone()
        if res:
            c.execute("UPDATE users SET password=? WHERE username=?", (hashed, u))
            conn.commit()
    conn.close()
    return res[0] if res else None

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
    if r == 'admin':
        df = pd.read_sql_query("SELECT * FROM portfolio ORDER BY date DESC", conn)
    else:
        df = pd.read_sql_query("SELECT * FROM portfolio WHERE username=? ORDER BY date DESC", conn, params=(u,))
    conn.close(); return df

def add_user_db(u, p, r):
    try:
        hashed = hash_password(p)
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (u, hashed, r))
        conn.commit(); conn.close(); return True
    except: return False

def delete_user_db(u):
    if u == 'admin': return False
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE username=?", (u,))
    conn.commit(); conn.close(); return True

def update_password_db(u, new_p):
    try:
        hashed = hash_password(new_p)
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("UPDATE users SET password=? WHERE username=?", (hashed, u))
        conn.commit(); conn.close(); return True
    except: return False

init_db()

# --- 1. PRO CYBER STYLING ---
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
            linear-gradient(rgba(204, 255, 0, 0.05) 1px, transparent 1px),
            linear-gradient(90deg, rgba(204, 255, 0, 0.05) 1px, transparent 1px),
            radial-gradient(circle at center, rgba(10, 25, 47, 0.4), #05070a);
        background-size: 20px 20px, 20px 20px, 100px 100px, 100px 100px, 100% 100%;
        font-family: 'JetBrains Mono', monospace; color: #e0e0e0;
    }
    div[data-testid="stMetric"], .status-box, .stDataFrame, div[data-testid="stExpander"], .stTabs, .stForm {
        background: rgba(0, 10, 20, 0.5) !important; backdrop-filter: blur(12px);
        border: 1px solid rgba(204, 255, 0, 0.15) !important; border-radius: 10px !important;
    }
    h1 { font-family: 'Orbitron', sans-serif; background: linear-gradient(90deg, #ccff00, #00ffff);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
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

# --- 3. DATA ENGINE & LOGIC ---
@st.cache_data(ttl=86400)
def load_tickers():
    try:
        url = "https://raw.githubusercontent.com/datasets-id/idx-stocks/main/data/stock_codes.csv"
        df_idx = pd.read_csv(url)
        return [str(t).strip().upper() + ".JK" for t in df_idx['ticker'].tolist() if len(str(t)) <= 5]
    except: return []

def draw_mobile_cards(df):
    for _, row in df.iterrows():
        chg_color = "#ccff00" if row['CHG%'] > 0 else "#ff4b4b"
        st.markdown(f"""
        <div style="background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(204, 255, 0, 0.2); 
                    border-radius: 12px; padding: 15px; margin-bottom: 12px; border-left: 5px solid {chg_color};">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <b style="font-size: 1.1rem; color: #ccff00;">{row['TICKER']}</b>
                <span style="color: {chg_color}; font-weight: bold;">{row['CHG%']}% | {row['SIGNAL']}</span>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 10px; font-size: 0.85rem; color: #bbb;">
                <div>Last: <b style="color:#fff;">{row['LAST']}</b></div>
                <div>Val: <b style="color:#fff;">{row['VAL(M)']}M</b></div>
                <div style="color: #00ffff;">In: {row['ENTRY']}</div>
                <div style="color: #00ff00;">TP: {row['TP']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

def run_scan(tickers, mode):
    results = []
    status_ui = st.empty(); p_bar = st.progress(0)
    for i in range(0, len(tickers), 30):
        batch = tickers[i:i+30]
        status_ui.caption(f"SCANNING: {i}/{len(tickers)}")
        p_bar.progress(min(i / len(tickers), 1.0))
        try:
            data = yf.download(batch, period="60d", interval="1d", group_by='ticker', progress=False, auto_adjust=True)
            for t in batch:
                try:
                    df_t = data[t].dropna() if len(batch) > 1 else data.dropna()
                    if len(df_t) < 51: continue
                    df_t.columns = [c[0] if isinstance(c, tuple) else c for c in df_t.columns]
                    
                    # Technicals
                    c_now, h_now, o_now = float(df_t['Close'].iloc[-1]), float(df_t['High'].iloc[-1]), float(df_t['Open'].iloc[-1])
                    prev_c = float(df_t['Close'].iloc[-2])
                    vol, vol_avg5 = float(df_t['Volume'].iloc[-1]), df_t['Volume'].iloc[-6:-1].mean()
                    ma20, ma50 = df_t['Close'].rolling(20).mean().iloc[-1], df_t['Close'].rolling(50).mean().iloc[-1]
                    
                    # RSI Calculation
                    delta = df_t['Close'].diff(); g = delta.where(delta > 0, 0).rolling(14).mean(); l = -delta.where(delta < 0, 0).rolling(14).mean()
                    rsi = (100 - (100 / (1 + (g/l)))).iloc[-1]
                    chg, val = ((c_now - prev_c) / prev_c) * 100, c_now * vol

                    # --- CORE LOGIC (SUPER BSJP, BSJP, HOLD) ---
                    sig = "-"
                    is_strong_close = c_now >= (h_now * 0.99)
                    
                    if is_strong_close and chg > 5 and vol > (vol_avg5 * 2):
                        sig = "⚡ SUPER BSJP"
                    elif is_strong_close and chg > 3:
                        sig = "🚀 BSJP"
                    elif c_now > ma50 and ma20 > ma50 and rsi < 70:
                        sig = "💎 HOLD"

                    # Final Filter
                    min_val = 1_000_000_000 if mode == "Ketat" else 200_000_000
                    min_chg = 2.5 if mode == "Ketat" else 1.5
                    
                    if val > min_val and chg > min_chg and vol > vol_avg5:
                        results.append({
                            "TICKER": t.replace(".JK",""), "LAST": int(c_now), "CHG%": round(chg, 2), 
                            "SIGNAL": sig, "RSI": round(rsi, 1),
                            "ENTRY": f"{int(c_now)}-{int(c_now*1.01)}", "TP": int(c_now*1.03), 
                            "CL": int(c_now*0.97), "VAL(M)": round(val/1_000_000, 1), "FULL": t
                        })
                except: continue
        except: continue
    status_ui.empty(); p_bar.empty()
    return pd.DataFrame(results)

# --- 4. NAVIGATION & SIDEBAR ---
user_now, role = st.session_state["auth"]["user"], st.session_state["auth"]["role"]
last_l, ip_l, loc_l = get_sidebar_log(user_now)

st.sidebar.markdown(f"<div style='padding:15px; border:1px solid #ccff0033; border-radius:10px; background:rgba(204,255,0,0.05);'><b>{user_now.upper()}</b><br><small>{role.upper()} | {ip_l}</small></div>", unsafe_allow_html=True)
menu = st.sidebar.radio("COMMAND", ["STRATEGY SCANNER", "MONEY MANAGEMENT", "USER MANAGEMENT", "SECURITY SETTINGS"] if role == "admin" else ["STRATEGY SCANNER", "MONEY MANAGEMENT", "SECURITY SETTINGS"])

if st.sidebar.button("🔴 LOGOUT"): st.session_state["auth"] = {"logged_in": False}; st.rerun()

# --- 5. APP PAGES ---
if menu == "STRATEGY SCANNER":
    st.title("🛰️ MARKET_INTELLIGENCE")
    mode_scan = st.radio("ALGO_SENSITIVITY", ["Ketat", "Agresif"], horizontal=True)
    
    if st.button("⚡ EXECUTE_SCAN", width="stretch"):
        st.session_state.results = run_scan(load_tickers(), mode_scan)
        st.session_state.scan_time = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%H:%M:%S")

    if 'results' in st.session_state and not st.session_state.results.empty:
        st.caption(f"Last Sync: {st.session_state.scan_time}")
        t1, t2 = st.tabs(["🖥️ DESKTOP", "📱 MOBILE"])
        with t1: st.dataframe(st.session_state.results.drop(columns=['FULL']), use_container_width=True, hide_index=True)
        with t2: draw_mobile_cards(st.session_state.results)

elif menu == "MONEY MANAGEMENT":
    st.title("💰 MONEY_INTELLIGENCE")
    privacy = st.checkbox("🕶️ PRIVACY MODE", value=False)
    
    def fmt(v, curr=True):
        if privacy: return "Rp ***" if curr else "***"
        return f"Rp {v:,.0f}" if curr else f"{v:,.0f}"

    # Portfolio Logic (Simplified)
    df_p = get_user_portfolio(user_now, role)
    if not df_p.empty:
        # Tampilan metrik dan tabel portfolio dengan filter privacy
        m1, m2 = st.columns(2)
        m1.metric("PORTFOLIO VALUE", fmt(10000000)) # Contoh statis
        st.dataframe(df_p if not privacy else "Data Hidden", use_container_width=True)

elif menu == "SECURITY SETTINGS":
    st.title("🔒 SECURITY_VAULT")
    with st.form("p_update"):
        new_p = st.text_input("NEW ACCESS KEY", type="password")
        if st.form_submit_button("UPDATE KEY"):
            if update_password_db(user_now, new_p): st.success("Encrypted & Updated")

elif menu == "USER MANAGEMENT" and role == "admin":
    st.title("👤 ACCESS_CONTROL")
    # Admin tools here...
