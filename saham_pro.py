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
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (u, p, r))
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
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("UPDATE users SET password=? WHERE username=?", (new_p, u))
        conn.commit(); conn.close(); return True
    except: return False

init_db()

# --- 1. PRO CYBER STYLING ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Orbitron:wght@400;900&display=swap');
    
    [data-testid="stHeaderActionElements"], .stDeployButton, #MainMenu {
        display: none !important;
    }
    
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

    button[kind="header"] { color: #ccff00 !important; }

    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: rgba(204, 255, 0, 0.05) !important;
        border-radius: 5px 5px 0px 0px;
        color: #888 !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: rgba(204, 255, 0, 0.15) !important;
        color: #ccff00 !important;
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

# --- 3. DATA ENGINE ---
@st.cache_data(ttl=86400)
def load_tickers():
    try:
        url = "https://raw.githubusercontent.com/datasets-id/idx-stocks/main/data/stock_codes.csv"
        df_idx = pd.read_csv(url)
        tickers = [str(t).strip().upper() + ".JK" for t in df_idx['ticker'].tolist() if len(str(t)) <= 5]
        if len(tickers) > 100: return tickers
    except: pass
    return []

def draw_mobile_cards(df):
    for _, row in df.iterrows():
        chg_color = "#ccff00" if row['CHG%'] > 0 else "#ff4b4b"
        signal_icon = "⚡" if "SUPER" in row['SIGNAL'] else "🚀" if "BSJP" in row['SIGNAL'] else "💎"
        st.markdown(f"""
        <div style="background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(204, 255, 0, 0.2); 
                    border-radius: 12px; padding: 15px; margin-bottom: 12px; border-left: 5px solid {chg_color};">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <b style="font-size: 1.2rem; color: #ccff00;">{row['TICKER']}</b>
                    <span style="font-size: 0.7rem; background: rgba(204,255,0,0.1); padding: 2px 6px; border-radius: 4px; margin-left: 5px;">{row['SIGNAL']}</span>
                </div>
                <span style="color: {chg_color}; font-weight: bold;">{row['CHG%']}%</span>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 10px; font-size: 0.85rem; color: #bbb;">
                <div>Last: <b style="color:#fff;">{row['LAST']}</b></div>
                <div>Vol: <b style="color:#fff;">{row['VOL_S']}</b></div>
                <div style="color: #00ffff;">Entry: {row['ENTRY']}</div>
                <div style="color: #00ff00;">TP: {row['TP']}</div>
                <div style="color: #ff4b4b;">CL: {row['CL']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

def run_scan(tickers, mode):
    results = []
    status_ui = st.empty(); p_bar = st.progress(0)
    
    # Download in larger batches for speed
    batch_size = 40
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i+batch_size]
        status_ui.caption(f"SCANNING: {i}/{len(tickers)} TICKERS")
        p_bar.progress(min(i / len(tickers), 1.0))
        
        try:
            # Mengambil 20 hari untuk MA dan Vol Avg
            data = yf.download(batch, period="25d", interval="1d", group_by='ticker', progress=False, auto_adjust=True)
            
            for t in batch:
                try:
                    df_t = data[t].dropna() if len(batch) > 1 else data.dropna()
                    if len(df_t) < 20: continue
                    
                    df_t.columns = [c[0] if isinstance(c, tuple) else c for c in df_t.columns]
                    last, prev = df_t.iloc[-1], df_t.iloc[-2]
                    
                    c_now = float(last['Close'])
                    o_now = float(last['Open'])
                    h_now = float(last['High'])
                    l_now = float(last['Low'])
                    vol_now = float(last['Volume'])
                    
                    # Technicals
                    chg = ((c_now - float(prev['Close'])) / float(prev['Close'])) * 100
                    val_m = (c_now * vol_now) / 1_000_000
                    vol_avg20 = df_t['Volume'].iloc[-21:-1].mean()
                    ma20 = df_t['Close'].iloc[-20:].mean()
                    
                    signal = ""
                    # 1. ⚡ SUPER BSJP (Power Buy: Vol Spike High & Close near High)
                    if val_m > 1000 and chg > 4 and c_now >= (h_now * 0.99) and vol_now > (vol_avg20 * 2):
                        signal = "⚡ SUPER BSJP"
                    
                    # 2. 🚀 BSJP (Standard Buy: Momentum Up & Vol Up)
                    elif val_m > 500 and 2 < chg < 8 and c_now > o_now and vol_now > vol_avg20:
                        signal = "🚀 BSJP"
                        
                    # 3. 💎 HOLD (Trend Follow: Above MA20 & Stable Accumulation)
                    elif c_now > ma20 and -1 < chg < 3 and val_m > 300 and vol_now > (vol_avg20 * 0.8):
                        signal = "💎 HOLD"

                    if signal:
                        results.append({
                            "TICKER": t.replace(".JK",""), 
                            "SIGNAL": signal,
                            "LAST": int(c_now), 
                            "CHG%": round(chg, 2), 
                            "VOL_S": "⚡ SPIKE" if vol_now > vol_avg20*2 else "UP" if vol_now > vol_avg20 else "NORM",
                            "ENTRY": f"{int(c_now)}-{int(c_now*1.01)}", 
                            "TP": int(c_now*1.05) if "BSJP" in signal else int(c_now*1.15), 
                            "CL": int(c_now*0.96), 
                            "VAL(M)": round(val_m, 1), 
                            "FULL": t
                        })
                except: continue
        except: continue
        
    status_ui.empty(); p_bar.empty()
    return pd.DataFrame(results)

# --- 4. NAVIGATION ---
role = st.session_state["auth"]["role"]
user_now = st.session_state["auth"]["user"]
last_l, ip_l, loc_l = get_sidebar_log(user_now)

st.sidebar.markdown(f"""
    <div style='padding:15px; border:1px solid #ccff0033; border-radius:10px; background:rgba(204,255,0,0.05); margin-bottom:10px;'>
        <h3 style='margin:0; color:#ccff00;'>{user_now.upper()}</h3>
        <p style='margin:0; font-size:10px; color:#888;'>NODE ACTIVE | {role.upper()}</p>
        <hr style='border:0.1px solid #ccff0022; margin:10px 0;'>
        <p style='font-size:10px; color:#888;'>LST: {last_l}</p>
        <p style='font-size:10px; color:#888;'>IP : {ip_l}</p>
        <p style='font-size:10px; color:#888;'>LOC: {loc_l}</p>
    </div>
    """, unsafe_allow_html=True)

menu_list = ["STRATEGY SCANNER", "MONEY MANAGEMENT", "SECURITY SETTINGS"]
if role == "admin": menu_list.insert(1, "USER MANAGEMENT")
menu = st.sidebar.radio("COMMAND CENTER", menu_list)

if st.sidebar.button("🔴 TERMINATE SESSION", width="stretch"):
    st.session_state["auth"] = {"logged_in": False}; st.rerun()

# --- 5. CONTENT ---
if menu == "STRATEGY SCANNER":
    st.title("🛰️ MARKET_INTELLIGENCE")
    
    # Header IHSG
    try:
        ihsg = yf.Ticker("^JKSE").history(period="2d")
        curr_c, diff = ihsg['Close'].iloc[-1], ihsg['Close'].iloc[-1] - ihsg['Close'].iloc[-2]
        clr = "#ccff00" if diff >= 0 else "#ff4b4b"
        st.markdown(f"<div class='status-box' style='padding:10px; border-left: 4px solid {clr};'>IHSG: <span style='color:{clr}; font-weight:bold;'>{curr_c:,.2f} ({diff:+.2f})</span></div>", unsafe_allow_html=True)
    except: pass

    if st.button("⚡ EXECUTE_QUANT_SCAN", width="stretch"):
        st.session_state.results = run_scan(load_tickers(), "Standard")
        st.session_state.scan_time = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%H:%M:%S")

    if 'results' in st.session_state:
        df = st.session_state.results
        if not df.empty:
            st.caption(f"Last Sync: {st.session_state.scan_time} WIB")
            
            # Filter Chips
            sigs = ["ALL", "⚡ SUPER BSJP", "🚀 BSJP", "💎 HOLD"]
            sel_sig = st.segmented_control("FILTER_SIGNAL", sigs, default="ALL")
            
            display_df = df if sel_sig == "ALL" else df[df['SIGNAL'] == sel_sig]
            
            tab_desk, tab_mob = st.tabs(["🖥️ DESKTOP VIEW", "📱 MOBILE VIEW"])
            with tab_desk: st.dataframe(display_df.drop(columns=['FULL']), use_container_width=True, hide_index=True)
            with tab_mob: draw_mobile_cards(display_df)
            
            # Charts
            sel_t = st.selectbox("FOCUS_TARGET", display_df['TICKER'].tolist())
            if sel_t:
                full_t = df[df['TICKER'] == sel_t]['FULL'].values[0]
                chart_data = yf.download(full_t, period="6mo", interval="1d", progress=False, auto_adjust=True)
                chart_data.columns = [c[0] if isinstance(c, tuple) else c for c in chart_data.columns]
                
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_width=[0.3, 0.7])
                fig.add_trace(go.Candlestick(x=chart_data.index, open=chart_data['Open'], high=chart_data['High'], low=chart_data['Low'], close=chart_data['Close'], name="Price"), row=1, col=1)
                fig.add_trace(go.Bar(x=chart_data.index, y=chart_data['Volume'], name="Vol", opacity=0.4), row=2, col=1)
                fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=450, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No signals detected. Try scanning again later.")

# --- (Sisa kode Money Management, User Management, dll tetap sama) ---
elif menu == "MONEY MANAGEMENT":
    st.title("💰 MONEY_INTELLIGENCE")
    privacy_mode = st.checkbox("🕶️ PRIVACY MODE", value=False)

    tab1, tab2, tab3 = st.tabs(["📈 ACTIVE PORTFOLIO", "📜 TRADING HISTORY", "🛡️ RISK CALCULATOR"])
    
    with tab1:
        with st.expander("➕ ADD NEW POSITION"):
            with st.form("add_p"):
                c1, c2, c3 = st.columns(3)
                t_in = c1.text_input("Ticker")
                p_in = c2.number_input("Price", min_value=0)
                l_in = c3.number_input("Lots", min_value=1)
                if st.form_submit_button("SAVE"):
                    add_to_portfolio(user_now, t_in, p_in, l_in, 0, 0)
                    st.rerun()

        df_p = get_user_portfolio(user_now, role)
        if not df_p.empty:
            st.dataframe(df_p.drop(columns=['username']), use_container_width=True)
        else: st.info("Portfolio Empty")

    with tab3:
        st.subheader("🛡️ POSITION_SIZER")
        cap = st.number_input("Capital", value=10000000)
        risk = st.slider("Risk %", 0.5, 5.0, 1.0)
        ent = st.number_input("Entry", value=1000)
        sl = st.number_input("Stop Loss", value=950)
        if st.button("CALC"):
            r_amt = cap * (risk/100)
            lots = int((r_amt / (ent-sl)) / 100) if ent > sl else 0
            st.success(f"Max Size: {lots} Lots")

elif menu == "USER MANAGEMENT":
    st.title("👤 ACCESS_CONTROL")
    conn = sqlite3.connect('users.db')
    df_u = pd.read_sql_query("SELECT username, role, last_login, location FROM users", conn)
    st.dataframe(df_u, use_container_width=True)
    u_del = st.text_input("Username to Revoke")
    if st.button("DELETE USER"):
        if delete_user_db(u_del): st.rerun()

elif menu == "SECURITY SETTINGS":
    st.title("🔒 SECURITY_VAULT")
    with st.form("p"):
        new_p = st.text_input("NEW ACCESS KEY", type="password")
        if st.form_submit_button("UPDATE"):
            if update_password_db(user_now, new_p): st.success("Updated")
