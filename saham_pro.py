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
    try:
        response = requests.get('https://ipapi.co/json/', timeout=3).json()
        return response.get('ip', 'Unknown'), f"{response.get('city')}, {response.get('region')}"
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
    query = "SELECT * FROM portfolio ORDER BY date DESC" if r == 'admin' else "SELECT * FROM portfolio WHERE username=? ORDER BY date DESC"
    df = pd.read_sql_query(query, conn, params=(u,) if r != 'admin' else None)
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
        return [f"{str(t).strip().upper()}.JK" for t in df_idx['ticker'].tolist() if len(str(t)) <= 4]
    except:
        return ["BBCA.JK", "BBRI.JK", "TLKM.JK", "ASII.JK", "GOTO.JK", "BMRI.JK"]

def draw_mobile_cards(df):
    for _, row in df.iterrows():
        chg_color = "#ccff00" if row['CHG%'] > 0 else "#ff4b4b"
        st.markdown(f"""
        <div style="background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(204, 255, 0, 0.2); 
                    border-radius: 12px; padding: 15px; margin-bottom: 12px; border-left: 5px solid {chg_color};">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <b style="font-size: 1.2rem; color: #ccff00;">{row['TICKER']}</b>
                <span style="color: {chg_color}; font-weight: bold;">{row['CHG%']}%</span>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 10px; font-size: 0.85rem; color: #bbb;">
                <div>Last: <b style="color:#fff;">{row['LAST']}</b></div>
                <div>Value: <b style="color:#fff;">{row['VAL(M)']}M</b></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

def run_scan(tickers, mode):
    results = []
    status_ui = st.empty(); p_bar = st.progress(0)
    # Batch processing 20 to avoid Yahoo block
    for i in range(0, len(tickers), 20):
        batch = tickers[i:i+20]
        status_ui.caption(f"SCANNING: {i}/{len(tickers)}")
        p_bar.progress(min(i / len(tickers), 1.0))
        try:
            data = yf.download(batch, period="10d", interval="1d", group_by='ticker', progress=False)
            for t in batch:
                try:
                    df_t = data[t].dropna() if len(batch) > 1 else data.dropna()
                    if len(df_t) < 5: continue
                    last_c, prev_c = df_t['Close'].iloc[-1], df_t['Close'].iloc[-2]
                    vol, vol_avg = df_t['Volume'].iloc[-1], df_t['Volume'].iloc[-6:-1].mean()
                    chg = ((last_c - prev_c) / prev_c) * 100
                    val = last_c * vol
                    
                    cond = (val > 200_000_000 and chg > 1.5 and vol > vol_avg)
                    if mode == "Ketat":
                        cond = (val > 1_000_000_000 and 2.5 < chg < 12 and vol > vol_avg * 1.5)
                    
                    if cond:
                        results.append({
                            "TICKER": t.replace(".JK",""), "LAST": int(last_c), "CHG%": round(chg, 2), 
                            "VAL(M)": round(val/1_000_000, 1), "FULL": t
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
    
    # --- FIXED IHSG FEED ---
    try:
        ihsg_data = yf.download("^JKSE", period="5d", progress=False)
        if not ihsg_data.empty:
            curr_c = ihsg_data['Close'].iloc[-1]
            prev_c = ihsg_data['Close'].iloc[-2]
            diff = curr_c - prev_c
            clr = "#ccff00" if diff >= 0 else "#ff4b4b"
            st.markdown(f"<div class='status-box' style='padding:10px; border-left: 5px solid {clr} !important;'>IHSG: <span style='color:{clr}; font-weight:bold;'>{curr_c:,.2f} ({diff:+.2f})</span></div>", unsafe_allow_html=True)
    except: st.caption("IHSG Feed Offline")

    mode_scan = st.radio("ALGO_SENSITIVITY", ["Ketat", "Agresif"], horizontal=True)

    if st.button("⚡ EXECUTE_DEEP_SCAN", width="stretch"):
        st.session_state.results = run_scan(load_tickers(), mode_scan)
        st.session_state.scan_time = datetime.now().strftime("%H:%M:%S")

    if 'results' in st.session_state and not st.session_state.results.empty:
        df = st.session_state.results
        st.caption(f"Last Sync: {st.session_state.scan_time} WIB")
        tab_desk, tab_mob = st.tabs(["🖥️ DESKTOP VIEW", "📱 MOBILE VIEW"])
        with tab_desk: st.dataframe(df.drop(columns=['FULL']), use_container_width=True, hide_index=True)
        with tab_mob: draw_mobile_cards(df)
        
        sel_t = st.selectbox("FOCUS_TARGET", df['TICKER'].tolist())
        full_t = df[df['TICKER'] == sel_t]['FULL'].values[0]
        chart_data = yf.download(full_t, period="6mo", progress=False)
        fig = go.Figure(data=[go.Candlestick(x=chart_data.index, open=chart_data['Open'], high=chart_data['High'], low=chart_data['Low'], close=chart_data['Close'])])
        fig.update_layout(template="plotly_dark", height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

elif menu == "MONEY MANAGEMENT":
    st.title("💰 MONEY_MANAGEMENT")
    tab1, tab2 = st.tabs(["📈 ACTIVE PORTFOLIO", "📜 TRADING HISTORY"])
    
    with tab1:
        with st.expander("➕ ADD NEW POSITION"):
            with st.form("add_p"):
                c1, c2, c3 = st.columns(3)
                t_in = c1.text_input("Ticker"); p_in = c2.number_input("Buy Price", min_value=0.0); l_in = c3.number_input("Lots", min_value=1)
                if st.form_submit_button("SAVE"):
                    if t_in: add_to_portfolio(user_now, t_in, p_in, l_in, 0, 0); st.rerun()
        
        df_p = get_user_portfolio(user_now, role)
        if not df_p.empty:
            # --- PORTFOLIO VISUALIZER ---
            st.markdown("### 📊 PORTFOLIO ALLOCATION")
            g1, g2 = st.columns(2)
            with g1:
                fig_pie = go.Figure(data=[go.Pie(labels=df_p['ticker'], values=df_p['lots'], hole=.4)])
                fig_pie.update_layout(template="plotly_dark", height=300, paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=30,b=0))
                st.plotly_chart(fig_pie, use_container_width=True)
            with g2:
                st.metric("TOTAL POSITIONS", len(df_p))
                st.metric("UNIQUE ASSETS", df_p['ticker'].nunique())
            
            st.dataframe(df_p.drop(columns=['username','tp_price','cl_price']), use_container_width=True, hide_index=True)
            for i, row in df_p.iterrows():
                with st.expander(f"MANAGE: {row['ticker']} ({row['lots']} Lots)"):
                    cs, cd = st.columns([3, 1])
                    s_price = cs.number_input(f"Sell Price {row['ticker']}", value=float(row['buy_price']), key=f"s_{row['id']}")
                    if cs.button(f"🚀 SELL {row['ticker']}", key=f"btn_s_{row['id']}", use_container_width=True):
                        sell_position(user_now, row['id'], row['ticker'], row['buy_price'], s_price, row['lots'])
                        st.rerun()
                    if cd.button("🗑️", key=f"btn_d_{row['id']}", use_container_width=True):
                        conn = sqlite3.connect('users.db'); conn.cursor().execute("DELETE FROM portfolio WHERE id=?", (row['id'],)); conn.commit(); conn.close(); st.rerun()
        else: st.info("No active positions.")

    with tab2:
        conn = sqlite3.connect('users.db')
        df_h = pd.read_sql_query("SELECT * FROM history WHERE username=? ORDER BY date DESC", conn, params=(user_now,))
        conn.close()
        if not df_h.empty:
            # --- PERFORMANCE DASHBOARD ---
            total_pnl = df_h['pnl'].sum()
            df_h['cum_pnl'] = df_h['pnl'].cumsum()
            st.metric("TOTAL NET P/L", f"Rp {total_pnl:,.0f}")
            
            fig_perf = go.Figure(go.Scatter(y=df_h['cum_pnl'], mode='lines+markers', line=dict(color='#ccff00', width=3), fill='tozeroy'))
            fig_perf.update_layout(title="Equity Growth Curve", template="plotly_dark", height=300, paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_perf, use_container_width=True)
            st.dataframe(df_h.drop(columns=['id', 'username']), use_container_width=True, hide_index=True)

elif menu == "USER MANAGEMENT":
    st.title("👤 ACCESS_CONTROL")
    conn = sqlite3.connect('users.db')
    df_u = pd.read_sql_query("SELECT username, role, last_login FROM users", conn)
    conn.close(); st.dataframe(df_u, use_container_width=True, hide_index=True)
    c1, c2 = st.columns(2)
    with c1:
        with st.form("add_u"):
            nu, np, nr = st.text_input("User"), st.text_input("Key", type="password"), st.selectbox("Role", ["user", "admin"])
            if st.form_submit_button("GRANT ACCESS"):
                if add_user_db(nu, np, nr): st.success("User Authorized"); st.rerun()
    with c2:
        du = st.text_input("Revoke Operator ID")
        if st.button("🔴 DELETE PERMANENTLY"):
            if delete_user_db(du): st.warning("Access Revoked"); st.rerun()

elif menu == "SECURITY SETTINGS":
    st.title("🔒 SECURITY_VAULT")
    with st.form("p"):
        new_p = st.text_input("NEW ACCESS KEY", type="password")
        if st.form_submit_button("UPDATE"):
            if update_password_db(user_now, new_p): st.success("Access Key Updated")
