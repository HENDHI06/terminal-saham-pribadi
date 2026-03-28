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

# --- 0. CONFIG & DATABASE SETUP ---
warnings.filterwarnings("ignore", category=FutureWarning)
st.set_page_config(page_title="IDX CYBER TERMINAL", page_icon="⚡", layout="wide")

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
    return "Localhost", "Internal Network"

def update_login_info(u):
    ip, loc = get_visitor_info()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET last_login=?, ip_address=?, location=? WHERE username=?", (now, ip, loc, u))
    conn.commit()
    conn.close()

def check_login_db(u, p):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT role FROM users WHERE username=? AND password=?", (u, p))
    res = c.fetchone()
    conn.close()
    return res[0] if res else None

def add_user_db(u, p, r):
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (u, p, r))
        conn.commit()
        conn.close()
        return True
    except: return False

def delete_user_db(u):
    if u == 'admin': return False
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE username=?", (u,))
    conn.commit()
    conn.close()
    return True

def update_password_db(u, new_p):
    try:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("UPDATE users SET password=? WHERE username=?", (new_p, u))
        conn.commit()
        conn.close()
        return True
    except: return False

init_db()

# --- 1. CYBER-GLOW STYLING (FULL CSS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
    .stApp { background: radial-gradient(circle at top right, #0a192f, #05070a); font-family: 'JetBrains Mono', monospace; color: #e0e0e0; }
    div[data-testid="stMetric"], .status-box, .stDataFrame, div[data-testid="stExpander"] {
        background: rgba(255, 255, 255, 0.03) !important;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(204, 255, 0, 0.2) !important;
        border-radius: 15px !important;
    }
    section[data-testid="stSidebar"] { background-color: rgba(10, 12, 16, 0.95); border-right: 1px solid #ccff0033; }
    h1, h2, h3, .stSubheader { color: #ccff00 !important; text-shadow: 0 0 10px rgba(204, 255, 0, 0.3); }
    
    /* Green Neon Buttons */
    .stButton>button {
        background: linear-gradient(45deg, #ccff00, #9fcc00) !important;
        color: black !important; font-weight: bold !important; border-radius: 8px !important; border: none !important;
        transition: 0.3s all ease;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 0 15px rgba(204, 255, 0, 0.5); }
    
    /* Red Neon Button (Special for Delete) */
    div.stButton > button[kind="secondary"] {
        background: linear-gradient(45deg, #ff4b4b, #8b0000) !important;
        color: white !important; border: none !important;
    }

    .status-box { padding: 20px; border-left: 5px solid #ccff00 !important; margin-bottom: 20px; }
    .last-time-tag { font-size: 12px; color: #ccff00; opacity: 0.8; margin-bottom: 10px; font-style: italic; }
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
@st.cache_data
def load_tickers():
    file_path = "daftar_saham.xlsx"
    if os.path.exists(file_path):
        df = pd.read_excel(file_path)
        col = 'Kode' if 'Kode' in df.columns else df.columns[1]
        return [f"{str(t).strip().upper()}.JK" for t in df[col].tolist() if len(str(t)) <= 5]
    return []

def run_scan(tickers, mode):
    results = []
    status_ui = st.empty(); p_bar = st.progress(0)
    for i in range(0, len(tickers), 30):
        batch = tickers[i:i+30]
        status_ui.caption(f"DECRYPTING MARKET DATA: {i}/{len(tickers)}")
        p_bar.progress(min(i / len(tickers), 1.0))
        try:
            data = yf.download(batch, period="6d", interval="1d", group_by='ticker', progress=False, auto_adjust=True)
            for t in batch:
                try:
                    df_t = data[t].dropna() if len(batch) > 1 else data.dropna()
                    if len(df_t) < 2: continue
                    df_t.columns = [c[0] if isinstance(c, tuple) else c for c in df_t.columns]
                    last, prev = df_t.iloc[-1], df_t.iloc[-2]
                    c_now, c_prev, h_now, vol = float(last['Close']), float(prev['Close']), float(last['High']), float(last['Volume'])
                    chg = ((c_now - c_prev) / c_prev) * 100
                    val = c_now * vol
                    cond = (val > 1_000_000_000 and 2.5 < chg < 15 and c_now >= (h_now * 0.988)) if mode == "Ketat" else (val > 250_000_000 and chg > 1.2)
                    if cond:
                        results.append({
                            "TICKER": t.replace(".JK",""), "LAST": int(c_now), "CHG%": round(chg, 2), 
                            "ENTRY": f"{int(c_now)}-{int(c_now*1.01)}", "TP": int(c_now*1.03), "CL": int(c_now*0.98),
                            "TREND": df_t['Close'].tolist(), "VAL(M)": round(val/1_000_000, 1), "FULL": t
                        })
                except: continue
        except: continue
    status_ui.empty(); p_bar.empty()
    return pd.DataFrame(results)

# --- 4. NAVIGATION ---
role = st.session_state["auth"]["role"]
user_now = st.session_state["auth"]["user"]
st.sidebar.markdown(f"<div style='padding:15px; border:1px solid #ccff0033; border-radius:10px; background:rgba(204,255,0,0.05); margin-bottom:10px;'><h3 style='margin:0; color:#ccff00;'>{user_now.upper()}</h3><p style='margin:0; font-size:10px; color:#888;'>NODE ACTIVE</p></div>", unsafe_allow_html=True)
menu = st.sidebar.radio("COMMAND CENTER", ["STRATEGY SCANNER", "USER MANAGEMENT", "SECURITY SETTINGS"] if role == "admin" else ["STRATEGY SCANNER", "SECURITY SETTINGS"])

st.sidebar.markdown("---")
if st.sidebar.button("🔴 TERMINATE SESSION", width="stretch"):
    st.session_state["auth"] = {"logged_in": False}; st.rerun()

# --- 5. MAIN CONTENT ---
if menu == "STRATEGY SCANNER":
    st.title("🛰️ MARKET_INTELLIGENCE")
    
    # IHSG Real-time Info
    try:
        ihsg_ticker = yf.Ticker("^JKSE")
        ihsg_hist = ihsg_ticker.history(period="2d")
        if len(ihsg_hist) >= 2:
            prev_c, curr_c = ihsg_hist['Close'].iloc[-2], ihsg_hist['Close'].iloc[-1]
            diff = curr_c - prev_c
            pct = (diff / prev_c) * 100
            clr = "#ccff00" if diff >= 0 else "#ff4b4b"
            st.markdown(f"<div class='status-box' style='border-left-color:{clr} !important;'><p style='margin:0; color:#888; font-size:12px;'>IHSG COMPOSITE</p><h2 style='margin:0; color:{clr};'>{curr_c:,.2f}</h2><p style='margin:0; color:{clr}; font-weight:bold;'>{diff:+.2f} ({pct:.2f}%)</p></div>", unsafe_allow_html=True)
    except: pass

    # Sync Button
    if st.button("🔄 SYNC_LATEST_DATA", width="stretch"):
        st.rerun()

    st.divider()
    
    # Scanner Configuration
    with st.container():
        st.markdown("### ⚙️ SCAN_PROTOCOL")
        mode_scan = st.radio("ALGO_SENSITIVITY", ["Ketat", "Agresif"], horizontal=True)
        if st.button("⚡ EXECUTE_DEEP_SCAN", width="stretch"):
            st.session_state.results = run_scan(load_tickers(), mode_scan)
            st.session_state.scan_time = datetime.now().strftime("%H:%M:%S")

    # Display Results
    if 'results' in st.session_state:
        df = st.session_state.results
        if not df.empty:
            st.markdown(f"<p class='last-time-tag'>[LOG]: Scan completed at {st.session_state.scan_time}</p>", unsafe_allow_html=True)
            sel_t = st.selectbox("FOCUS_TARGET_ASSET", df['TICKER'].tolist())
            
            st.dataframe(df.drop(columns=['FULL']), width="stretch", hide_index=True, column_config={
                "CHG%": st.column_config.NumberColumn(format="%.2f%%"),
                "TREND": st.column_config.LineChartColumn("5D_VELOCITY"),
                "VAL(M)": st.column_config.ProgressColumn("Value(M)", min_value=0, max_value=df["VAL(M)"].max())
            })
            
            # Advanced Charting
            st.divider()
            st.subheader(f"👁️ MONITORING: {sel_t}")
            full_t = df[df['TICKER'] == sel_t]['FULL'].values[0]
            chart_data = yf.download(full_t, period="6mo", interval="1d", progress=False, auto_adjust=True)
            chart_data.columns = [c[0] if isinstance(c, tuple) else c for c in chart_data.columns]
            
            # Technical Indicators
            chart_data['MA20'] = chart_data['Close'].rolling(window=20).mean()
            chart_data['MA50'] = chart_data['Close'].rolling(window=50).mean()
            delta = chart_data['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            chart_data['RSI'] = 100 - (100 / (1 + (gain/loss)))

            # Subplots
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_width=[0.2, 0.15, 0.65])
            
            # Price + MA
            fig.add_trace(go.Candlestick(x=chart_data.index, open=chart_data['Open'], high=chart_data['High'], low=chart_data['Low'], close=chart_data['Close'], increasing_line_color='#ccff00', decreasing_line_color='#ff4b4b', name="Price"), row=1, col=1)
            fig.add_trace(go.Scatter(x=chart_data.index, y=chart_data['MA20'], line=dict(color='#ffcc00', width=1), name="MA20"), row=1, col=1)
            fig.add_trace(go.Scatter(x=chart_data.index, y=chart_data['MA50'], line=dict(color='#00d4ff', width=1), name="MA50"), row=1, col=1)
            
            # Volume
            vol_clr = ['#ccff00' if chart_data['Close'][i] >= chart_data['Open'][i] else '#ff4b4b' for i in range(len(chart_data))]
            fig.add_trace(go.Bar(x=chart_data.index, y=chart_data['Volume'], marker_color=vol_clr, opacity=0.4, name="Vol"), row=2, col=1)
            
            # RSI
            fig.add_trace(go.Scatter(x=chart_data.index, y=chart_data['RSI'], line=dict(color='#ff00ff', width=1.5), name="RSI"), row=3, col=1)
            fig.add_hline(y=70, line_dash="dot", line_color="red", row=3, col=1)
            fig.add_hline(y=30, line_dash="dot", line_color="cyan", row=3, col=1)

            fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=850, margin=dict(l=10, r=10, t=20, b=10), showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, width="stretch")

elif menu == "USER MANAGEMENT":
    st.title("👤 ACCESS_CONTROL_PROTOCOL")
    conn = sqlite3.connect('users.db')
    df_u = pd.read_sql_query("SELECT username, role, last_login, location FROM users", conn)
    conn.close()
    st.dataframe(df_u, width="stretch", hide_index=True)
    
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Add New Operator")
        with st.form("add_user_form"):
            nu, np, nr = st.text_input("Username"), st.text_input("Access Key", type="password"), st.selectbox("Role", ["user", "admin"])
            if st.form_submit_button("GRANT ACCESS"):
                if nu and np:
                    if add_user_db(nu, np, nr): st.success(f"User {nu} Authorized."); st.rerun()
                else: st.error("Fill all fields.")
    
    with col2:
        st.subheader("Revoke Access")
        du = st.text_input("Target Username to Revoke")
        if st.button("🔴 DELETE PERMANENTLY", width="stretch", type="secondary"):
            if du == "admin": st.error("Root admin cannot be deleted.")
            elif delete_user_db(du): st.warning(f"Access Revoked for {du}."); st.rerun()
            else: st.error("User not found.")

elif menu == "SECURITY SETTINGS":
    st.title("🔒 SECURITY_VAULT")
    ip, loc = get_visitor_info()
    st.info(f"CURRENT_NODE_IP: {ip} | LOCATION: {loc}")
    with st.form("change_p"):
        new_pass = st.text_input("NEW_ENCRYPTION_KEY", type="password")
        conf_pass = st.text_input("CONFIRM_KEY", type="password")
        if st.form_submit_button("UPDATE_ACCESS_KEY", width="stretch"):
            if new_pass == conf_pass and new_pass != "":
                if update_password_db(user_now, new_pass): st.success("Access Key Rotated Successfully.")
            else: st.error("Key Mismatch or Empty.")