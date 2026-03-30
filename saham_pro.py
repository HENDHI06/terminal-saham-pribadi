import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import sqlite3
import warnings
import hashlib
import requests 
import pytz 

# --- 0. CONFIG & DATABASE SETUP ---
warnings.filterwarnings("ignore", category=FutureWarning)
st.set_page_config(page_title="IDX CYBER TERMINAL PRO", page_icon="⚡", layout="wide")

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def init_db():
    with sqlite3.connect('users.db') as conn:
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
        # Default Admin: admin | admin123
        admin_pass = hash_password('admin123')
        c.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES ('admin', ?, 'admin')", (admin_pass,))
        conn.commit()

def get_visitor_info():
    try:
        response = requests.get('https://ipapi.co/json/', timeout=3).json()
        return response.get('ip', 'Unknown'), f"{response.get('city', 'Unknown')}, {response.get('region', 'Unknown')}"
    except: return "127.0.0.1", "Local Node"

def update_login_info(u):
    ip, loc = get_visitor_info()
    tz = pytz.timezone('Asia/Jakarta') 
    now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect('users.db') as conn:
        conn.execute("UPDATE users SET last_login=?, ip_address=?, location=? WHERE username=?", (now, ip, loc, u))

def check_login_db(u, p):
    hp = hash_password(p)
    with sqlite3.connect('users.db') as conn:
        c = conn.cursor()
        c.execute("SELECT role FROM users WHERE username=? AND password=?", (u, hp))
        res = c.fetchone()
    return res[0] if res else None

def add_to_portfolio(u, t, p, l):
    with sqlite3.connect('users.db') as conn:
        conn.execute("INSERT INTO portfolio (username, ticker, buy_price, lots, date) VALUES (?, ?, ?, ?, ?)",
                     (u, t.upper().strip(), p, l, datetime.now().strftime("%Y-%m-%d")))

def sell_position(u, row_id, ticker, buy_p, sell_p, lots):
    pnl = (sell_p - buy_p) * lots * 100
    date_now = datetime.now().strftime("%Y-%m-%d")
    with sqlite3.connect('users.db') as conn:
        conn.execute("INSERT INTO history (username, ticker, buy_price, sell_price, lots, pnl, date) VALUES (?, ?, ?, ?, ?, ?, ?)",
                     (u, ticker, buy_p, sell_p, lots, pnl, date_now))
        conn.execute("DELETE FROM portfolio WHERE id=?", (row_id,))

init_db()

# --- 1. PRO CYBER STYLING ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono&family=Orbitron:wght@400;900&display=swap');
    .stApp { background-color: #05070a; font-family: 'JetBrains Mono', monospace; color: #e0e0e0; }
    div[data-testid="stMetric"] { background: rgba(204, 255, 0, 0.05); border: 1px solid #ccff0033; border-radius: 10px; padding: 15px; }
    h1, h2, h3 { font-family: 'Orbitron', sans-serif; color: #ccff00; }
    .stButton>button { background-color: #ccff00; color: black; font-weight: bold; border: none; }
    .stButton>button:hover { background-color: #e6ff80; }
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
            u = st.text_input("OPERATOR ID")
            p = st.text_input("ACCESS KEY", type="password")
            if st.form_submit_button("AUTHORIZE ACCESS", use_container_width=True):
                role = check_login_db(u, p)
                if role:
                    update_login_info(u)
                    st.session_state["auth"] = {"logged_in": True, "user": u, "role": role}
                    st.rerun()
                else: st.error("ACCESS DENIED")
    st.stop()

# --- 3. DATA ENGINE ---
@st.cache_data(ttl=3600)
def load_tickers():
    try:
        url = "https://raw.githubusercontent.com/datasets-id/idx-stocks/main/data/stock_codes.csv"
        df_idx = pd.read_csv(url)
        return [f"{t}.JK" for t in df_idx['ticker'].tolist() if len(str(t)) <= 4]
    except: return ['BBCA.JK', 'BBRI.JK', 'BMRI.JK', 'TLKM.JK', 'ASII.JK', 'GOTO.JK', 'ADRO.JK', 'ITMG.JK', 'UNTR.JK', 'AMRT.JK']

def run_scan(tickers, mode):
    results = []
    p_bar = st.progress(0)
    for i, t in enumerate(tickers[:100]): # Limit 100 saham untuk kecepatan
        try:
            df = yf.download(t, period="60d", interval="1d", progress=False)
            if len(df) < 30: continue
            
            # Technical Indicators
            df['MA20'] = df['Close'].rolling(20).mean()
            df['MA50'] = df['Close'].rolling(50).mean()
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            df['RSI'] = 100 - (100 / (1 + (gain/loss)))

            last = df.iloc[-1]
            c_now, p_prev, h_now = float(last['Close']), float(df.iloc[-2]['Close']), float(last['High'])
            vol, vol_avg = float(last['Volume']), df['Volume'].iloc[-20:-1].mean()
            ma20, ma50, rsi = float(last['MA20']), float(last['MA50']), float(last['RSI'])
            turnover = (c_now * vol) / 1_000_000_000
            change = ((c_now - p_prev) / p_prev) * 100

            # --- STRATEGY LOGIC ---
            action = "🔎 MONITOR"
            is_closing_strong = c_now >= (h_now * 0.99)
            is_uptrend = c_now > ma20 > ma50
            
            if is_closing_strong and is_uptrend: action = "🔥 SUPER: BSJP + HOLD"
            elif is_closing_strong: action = "🚀 BSJP (Beli Sore)"
            elif is_uptrend: action = "💎 HOLD (Uptrend)"

            # Filter Sensitivity
            min_chg = 2.5 if mode == "Ketat" else 1.0
            min_val = 5.0 if mode == "Ketat" else 1.0

            if c_now > ma20 and 40 < rsi < 75 and turnover >= min_val and change >= min_chg:
                results.append({
                    "TICKER": t.replace(".JK",""), "LAST": int(c_now), "CHG%": round(change, 2), 
                    "ACTION": action, "RSI": round(rsi, 1), "VAL(B)": round(turnover, 1)
                })
        except: continue
        p_bar.progress((i + 1) / 100)
    return pd.DataFrame(results)

# --- 4. NAVIGATION ---
user_now = st.session_state["auth"]["user"]
role = st.session_state["auth"]["role"]
menu = st.sidebar.radio("COMMAND CENTER", ["STRATEGY SCANNER", "MONEY MANAGEMENT", "SECURITY"])

if st.sidebar.button("🔴 TERMINATE"):
    st.session_state["auth"] = {"logged_in": False}; st.rerun()

# --- 5. MAIN CONTENT ---
if menu == "STRATEGY SCANNER":
    st.title("🛰️ MARKET_INTELLIGENCE")
    mode = st.radio("SENSITIVITY", ["Ketat", "Agresif"], horizontal=True)
    
    if st.button("⚡ EXECUTE DEEP SCAN", use_container_width=True):
        st.session_state.results = run_scan(load_tickers(), mode)

    if 'results' in st.session_state and not st.session_state.results.empty:
        df = st.session_state.results
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Detail Chart
        sel = st.selectbox("CHART FOCUS", df['TICKER'].tolist())
        c_df = yf.download(f"{sel}.JK", period="6mo", progress=False)
        fig = go.Figure(data=[go.Candlestick(x=c_df.index, open=c_df['Open'], high=c_df['High'], low=c_df['Low'], close=c_df['Close'])])
        fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=400)
        st.plotly_chart(fig, use_container_width=True)

elif menu == "MONEY MANAGEMENT":
    st.title("💰 MONEY_INTELLIGENCE")
    privacy = st.checkbox("🕶️ PRIVACY MODE", value=False)
    
    def fmt(v, curr=True):
        if privacy: return "Rp *****" if curr else "*****"
        return f"Rp {v:,.0f}" if curr else f"{v:,.0f}"

    tab1, tab2 = st.tabs(["📈 PORTFOLIO", "📜 HISTORY"])
    
    with tab1:
        with st.expander("➕ ADD POSITION"):
            with st.form("add_p"):
                c1, c2, c3 = st.columns(3)
                t_in = c1.text_input("Ticker")
                p_in = c2.number_input("Price", min_value=0)
                l_in = c3.number_input("Lots", min_value=1)
                if st.form_submit_button("SAVE"):
                    add_to_portfolio(user_now, t_in, p_in, l_in); st.rerun()

        with sqlite3.connect('users.db') as conn:
            df_p = pd.read_sql_query("SELECT * FROM portfolio WHERE username=?", conn, params=(user_now,))
        
        if not df_p.empty:
            # Kalkulasi P/L Live
            tk_list = [f"{t}.JK" for t in df_p['ticker']]
            live_px = yf.download(tk_list, period="1d", progress=False)['Close'].iloc[-1]
            
            def process_p(r):
                px = live_px[f"{r['ticker']}.JK"] if len(tk_list) > 1 else live_px
                cost = r['buy_price'] * r['lots'] * 100
                val = px * r['lots'] * 100
                return pd.Series([px, cost, val, val-cost])
            
            df_p[['Live', 'Cost', 'Value', 'P/L']] = df_p.apply(process_p, axis=1)
            
            st.metric("TOTAL EQUITY", fmt(df_p['Value'].sum()), f"{(df_p['P/L'].sum()/df_p['Cost'].sum()*100):.2f}%")
            
            for i, r in df_p.iterrows():
                with st.expander(f"{r['ticker']} | {fmt(r['P/L'])}"):
                    c_sl, c_dl = st.columns([3, 1])
                    sell_p = c_sl.number_input("Sell Price", value=float(r['Live']), key=f"sl_{r['id']}")
                    if c_sl.button(f"SELL {r['ticker']}", key=f"btn_{r['id']}", use_container_width=True):
                        sell_position(user_now, r['id'], r['ticker'], r['buy_price'], sell_p, r['lots']); st.rerun()
                    if c_dl.button("🗑️", key=f"del_{r['id']}", use_container_width=True):
                        with sqlite3.connect('users.db') as conn: conn.execute("DELETE FROM portfolio WHERE id=?", (r['id'],))
                        st.rerun()

    with tab2:
        with sqlite3.connect('users.db') as conn:
            df_h = pd.read_sql_query("SELECT * FROM history WHERE username=? ORDER BY date DESC", conn, params=(user_now,))
        if not df_h.empty:
            st.dataframe(df_h.drop(columns=['id', 'username']), use_container_width=True)
            if st.button("CLEAR ALL HISTORY"):
                with sqlite3.connect('users.db') as conn: conn.execute("DELETE FROM history WHERE username=?", (user_now,))
                st.rerun()

elif menu == "SECURITY":
    st.title("🔒 SECURITY_VAULT")
    with st.form("sec"):
        new_k = st.text_input("NEW ACCESS KEY", type="password")
        if st.form_submit_button("UPDATE KEY"):
            if new_k:
                with sqlite3.connect('users.db') as conn:
                    conn.execute("UPDATE users SET password=? WHERE username=?", (hash_password(new_k), user_now))
                st.success("Access Key Updated!")
