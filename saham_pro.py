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
from streamlit_gsheets import GSheetsConnection

# --- 0. CONFIG & INITIALIZATION ---
warnings.filterwarnings("ignore", category=FutureWarning)
st.set_page_config(page_title="IDX CYBER TERMINAL", page_icon="⚡", layout="wide")

# Inisialisasi Session State di paling atas agar tidak NameError
if "auth" not in st.session_state:
    st.session_state["auth"] = {"logged_in": False, "user": None, "role": None}

# --- 1. DATABASE ENGINE (GSHEETS) ---
def get_conn():
    return st.connection("gsheets", type=GSheetsConnection)

def load_gs_data(sheet_name):
    try:
        conn = get_conn()
        df = conn.read(worksheet=sheet_name, ttl=0)
        return df.dropna(how='all')
    except:
        if sheet_name == "users":
            return pd.DataFrame([{"username": "admin", "password": "admin123", "role": "admin"}])
        return pd.DataFrame()

def save_gs_data(df, sheet_name):
    conn = get_conn()
    conn.update(worksheet=sheet_name, data=df)

# --- 2. AUTHENTICATION LOGIC ---
def check_login(u, p):
    df = load_gs_data("users")
    if df.empty: return None
    # Pastikan password dicek sebagai string
    match = df[(df['username'] == u) & (df['password'].astype(str) == str(p))]
    return match.iloc[0]['role'] if not match.empty else None

def update_password_gs(u, new_p):
    df = load_gs_data("users")
    if u in df['username'].values:
        df.loc[df['username'] == u, 'password'] = str(new_p)
        save_gs_data(df, "users")
        return True
    return False

# --- 3. CYBER STYLING ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Orbitron:wght@400;900&display=swap');
    [data-testid="stHeaderActionElements"], .stDeployButton, #MainMenu { display: none !important; }
    .stApp {
        background-color: #05070a;
        background-image: radial-gradient(circle at center, rgba(10, 25, 47, 0.4), #05070a);
        font-family: 'JetBrains Mono', monospace; color: #e0e0e0;
    }
    div[data-testid="stMetric"], .status-box, .stDataFrame, div[data-testid="stExpander"], .stTabs, .stForm {
        background: rgba(0, 10, 20, 0.5) !important;
        backdrop-filter: blur(12px); border: 1px solid rgba(204, 255, 0, 0.15) !important; border-radius: 10px !important;
    }
    h1 { font-family: 'Orbitron', sans-serif; background: linear-gradient(90deg, #ccff00, #00ffff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. LOGIN SCREEN ---
if not st.session_state["auth"]["logged_in"]:
    _, col2, _ = st.columns([1,1.5,1])
    with col2:
        st.markdown("<div style='text-align:center; padding:50px 0;'><h1>IDX</h1><p>CYBER TERMINAL</p></div>", unsafe_allow_html=True)
        with st.form("login_form"):
            u = st.text_input("OPERATOR ID").strip()
            p = st.text_input("ACCESS KEY", type="password")
            if st.form_submit_button("AUTHORIZE ACCESS", width="stretch"):
                role = check_login(u, p)
                if role:
                    st.session_state["auth"] = {"logged_in": True, "user": u, "role": role}
                    st.rerun()
                else: st.error("ACCESS DENIED")
    st.stop()

# --- 5. DATA ENGINE ---
@st.cache_data(ttl=86400)
def load_tickers():
    try:
        df = pd.read_csv("https://raw.githubusercontent.com/datasets-id/idx-stocks/main/data/stock_codes.csv")
        return [str(t).strip().upper() + ".JK" for t in df['ticker'].tolist() if len(str(t)) <= 5]
    except: return ["BBCA.JK", "BBRI.JK", "TLKM.JK", "ASII.JK", "GOTO.JK"]

def run_scan(tickers, mode):
    results = []
    status_ui = st.empty(); p_bar = st.progress(0)
    for i in range(0, len(tickers), 30):
        batch = tickers[i:i+30]
        status_ui.caption(f"SCANNING: {i}/{len(tickers)}")
        p_bar.progress(min(i / len(tickers), 1.0))
        try:
            data = yf.download(batch, period="5d", interval="1d", group_by='ticker', progress=False)
            for t in batch:
                try:
                    df_t = data[t].dropna()
                    if len(df_t) < 3: continue
                    last, prev = df_t.iloc[-1], df_t.iloc[-2]
                    chg = ((last['Close'] - prev['Close']) / prev['Close']) * 100
                    val = last['Close'] * last['Volume']
                    if (mode == "Ketat" and chg > 2.5 and val > 1e9) or (mode == "Agresif" and chg > 1.2):
                        results.append({
                            "TICKER": t.replace(".JK",""), "LAST": int(last['Close']), "CHG%": round(chg, 2), 
                            "VAL(M)": round(val/1e6, 1), "FULL": t
                        })
                except: continue
        except: continue
    status_ui.empty(); p_bar.empty()
    return pd.DataFrame(results)

# --- 6. MAIN NAVIGATION ---
role = st.session_state["auth"]["role"]
user_now = st.session_state["auth"]["user"]

st.sidebar.markdown(f"### {user_now.upper()} [{role}]")
menu_list = ["STRATEGY SCANNER", "MONEY MANAGEMENT", "SECURITY SETTINGS"]
if role == "admin": menu_list.insert(1, "USER MANAGEMENT")
menu = st.sidebar.radio("COMMAND CENTER", menu_list)

if st.sidebar.button("🔴 LOGOUT"):
    st.session_state["auth"] = {"logged_in": False}; st.rerun()

# --- 7. UI: STRATEGY SCANNER ---
if menu == "STRATEGY SCANNER":
    st.title("🛰️ MARKET_INTELLIGENCE")
    
    # IHSG STATUS BOX
    try:
        ihsg = yf.Ticker("^JKSE").history(period="2d")
        curr_c = ihsg['Close'].iloc[-1]; diff = curr_c - ihsg['Close'].iloc[-2]
        clr = "#ccff00" if diff >= 0 else "#ff4b4b"
        st.markdown(f"<div class='status-box' style='border-left: 5px solid {clr}; padding:10px;'>IHSG: <span style='color:{clr}; font-weight:bold;'>{curr_c:,.2f} ({diff:+.2f})</span></div>", unsafe_allow_html=True)
    except: pass

    c_algo, c_sync = st.columns([4, 1])
    with c_algo: mode_scan = st.radio("ALGO_SENSITIVITY", ["Ketat", "Agresif"], horizontal=True)
    with c_sync:
        if st.button("🔄 LAST SYNC", use_container_width=True): st.rerun()

    if st.button("⚡ EXECUTE DEEP SCAN", width="stretch"):
        st.session_state.results = run_scan(load_tickers(), mode_scan)
        st.session_state.scan_time = datetime.now().strftime("%H:%M:%S")

    if 'results' in st.session_state and not st.session_state.results.empty:
        df = st.session_state.results
        st.caption(f"Last Scan: {st.session_state.scan_time}")
        st.dataframe(df.drop(columns=['FULL']), use_container_width=True, hide_index=True)
        
        sel_t = st.selectbox("CHART VIEW", df['TICKER'].tolist())
        full_t = df[df['TICKER'] == sel_t]['FULL'].values[0]
        c_data = yf.download(full_t, period="6mo", progress=False)
        fig = go.Figure(data=[go.Candlestick(x=c_data.index, open=c_data['Open'], high=c_data['High'], low=c_data['Low'], close=c_data['Close'])])
        fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)

# --- 8. UI: MONEY MANAGEMENT (GSHEETS) ---
elif menu == "MONEY MANAGEMENT":
    st.title("💰 MONEY_MANAGEMENT")
    t1, t2 = st.tabs(["📈 PORTFOLIO", "📜 HISTORY"])
    
    with t1:
        with st.form("add_pos"):
            c1, c2, c3 = st.columns(3)
            tk = c1.text_input("Ticker"); pr = c2.number_input("Price"); lt = c3.number_input("Lots", 1)
            if st.form_submit_button("SAVE POSITION"):
                df_p = load_gs_data("portfolio")
                new_row = pd.DataFrame([{"username": user_now, "ticker": tk.upper(), "price": pr, "lots": lt, "date": datetime.now().strftime("%Y-%m-%d")}])
                save_gs_data(pd.concat([df_p, new_row], ignore_index=True), "portfolio")
                st.rerun()
        
        df_p = load_gs_data("portfolio")
        if not df_p.empty:
            my_p = df_p if role == 'admin' else df_p[df_p['username'] == user_now]
            st.dataframe(my_p, use_container_width=True)
            for i, r in my_p.iterrows():
                if st.button(f"🚀 SELL {r['ticker']} (Row {i})"):
                    df_h = load_gs_data("history")
                    save_gs_data(pd.concat([df_h, pd.DataFrame([r])], ignore_index=True), "history")
                    save_gs_data(df_p.drop(i), "portfolio")
                    st.rerun()

    with t2:
        st.dataframe(load_gs_data("history"), use_container_width=True)

# --- 9. UI: USER MANAGEMENT (GSHEETS) ---
elif menu == "USER MANAGEMENT":
    st.title("👤 ACCESS_CONTROL")
    df_u = load_gs_data("users")
    st.dataframe(df_u, use_container_width=True)
    
    col_a, col_b = st.columns(2)
    with col_a:
        with st.form("u_add"):
            st.subheader("Add User")
            un = st.text_input("ID"); pw = st.text_input("Key"); rl = st.selectbox("Role", ["user", "admin"])
            if st.form_submit_button("GRANT"):
                new_u = pd.concat([df_u, pd.DataFrame([{"username": un, "password": pw, "role": rl}])], ignore_index=True)
                save_gs_data(new_u, "users"); st.rerun()
    with col_b:
        target = st.text_input("ID to Revoke")
        if st.button("🔴 DELETE USER"):
            if target != 'admin':
                df_u = df_u[df_u['username'] != target]
                save_gs_data(df_u, "users"); st.rerun()

# --- 10. UI: SECURITY SETTINGS (GSHEETS) ---
elif menu == "SECURITY SETTINGS":
    st.title("🔒 SECURITY_VAULT")
    with st.form("p_update"):
        st.write(f"Update Key for: **{user_now}**")
        new_key = st.text_input("NEW ACCESS KEY", type="password")
        if st.form_submit_button("CONFIRM UPDATE"):
            if update_password_gs(user_now, new_key):
                st.success("Password Updated in GSheets!")
            else: st.error("Error updating password.")
