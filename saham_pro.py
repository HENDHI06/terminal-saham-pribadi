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

# --- 1. PRO CYBER STYLING (FIXED SIDEBAR BUTTON) ---
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

    /* Tabs Styling */
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

# --- 3. DATA ENGINE & MOBILE OPTIMIZATION ---
@st.cache_data(ttl=86400)
def load_tickers():
    # Coba Internet
    try:
        url = "https://raw.githubusercontent.com/datasets-id/idx-stocks/main/data/stock_codes.csv"
        df_idx = pd.read_csv(url)
        tickers = [str(t).strip().upper() + ".JK" for t in df_idx['ticker'].tolist() if len(str(t)) <= 5]
        if len(tickers) > 100: return tickers
    except: pass
    # Coba Excel Backup
    try:
        df = pd.read_excel("daftar_saham.xlsx")
        col = 'Kode' if 'Kode' in df.columns else df.columns[0]
        return [f"{str(t).strip().upper()}.JK" for t in df[col].tolist() if len(str(t)) <= 5]
    except: return []

def draw_mobile_cards(df):
    for _, row in df.iterrows():
        chg_color = "#ccff00" if row['CHG%'] > 0 else "#ff4b4b"
        st.markdown(f"""
        <div style="background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(204, 255, 0, 0.2); 
                    border-radius: 12px; padding: 15px; margin-bottom: 12px; border-left: 5px solid {chg_color};">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <b style="font-size: 1.2rem; color: #ccff00;">{row['TICKER']}</b>
                <span style="color: {chg_color}; font-weight: bold;">{row['CHG%']}% {row['VOL_S']}</span>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 10px; font-size: 0.85rem; color: #bbb;">
                <div>Last: <b style="color:#fff;">{row['LAST']}</b></div>
                <div>Value: <b style="color:#fff;">{row['VAL(M)']}M</b></div>
                <div style="color: #00ffff;">Entry: {row['ENTRY']}</div>
                <div style="color: #00ff00;">TP: {row['TP']}</div>
                <div style="color: #ff4b4b;">CL: {row['CL']}</div>
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
            data = yf.download(batch, period="10d", interval="1d", group_by='ticker', progress=False, auto_adjust=True)
            for t in batch:
                try:
                    df_t = data[t].dropna() if len(batch) > 1 else data.dropna()
                    if len(df_t) < 6: continue
                    df_t.columns = [c[0] if isinstance(c, tuple) else c for c in df_t.columns]
                    last, prev = df_t.iloc[-1], df_t.iloc[-2]
                    c_now, h_now = float(last['Close']), float(last['High'])
                    vol, vol_avg5 = float(last['Volume']), df_t['Volume'].iloc[-6:-1].mean()
                    vol_spike = vol > (vol_avg5 * 1.5)
                    chg = ((c_now - float(prev['Close'])) / float(prev['Close'])) * 100
                    val = c_now * vol
                    if mode == "Ketat":
                        cond = (val > 1_000_000_000 and 2.5 < chg < 12 and c_now >= (h_now * 0.985) and vol_spike)
                    else:
                        cond = (val > 200_000_000 and chg > 1.5 and vol_spike)
                    if cond:
                        results.append({
                            "TICKER": t.replace(".JK",""), "LAST": int(c_now), "CHG%": round(chg, 2), 
                            "VOL_S": "⚡ SPIKE" if vol_spike else "-", "ENTRY": f"{int(c_now)}-{int(c_now*1.01)}", 
                            "TP": int(c_now*1.03), "CL": int(c_now*0.97), "VAL(M)": round(val/1_000_000, 1), "FULL": t
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
    try:
        ihsg_hist = yf.Ticker("^JKSE").history(period="2d")
        if len(ihsg_hist) >= 2:
            prev_c, curr_c = ihsg_hist['Close'].iloc[-2], ihsg_hist['Close'].iloc[-1]
            diff = curr_c - prev_c
            clr = "#ccff00" if diff >= 0 else "#ff4b4b"
            st.markdown(f"<div class='status-box' style='border-left-color:{clr} !important;'>IHSG: <span style='color:{clr}; font-weight:bold;'>{curr_c:,.2f} ({diff:+.2f})</span></div>", unsafe_allow_html=True)
    except: pass

    c_algo, c_sync = st.columns([4, 1])
    with c_algo: mode_scan = st.radio("ALGO_SENSITIVITY", ["Ketat", "Agresif"], horizontal=True)
    with c_sync:
        if st.button("🔄 REFRESH PRICE", use_container_width=True):
            if 'results' in st.session_state and not st.session_state.results.empty:
                current_tickers = [f"{t}.JK" for t in st.session_state.results['TICKER']]
                try:
                    new_data = yf.download(current_tickers, period="1d", progress=False)['Close']
                    for idx, row in st.session_state.results.iterrows():
                        tk = f"{row['TICKER']}.JK"
                        st.session_state.results.at[idx, 'LAST'] = int(new_data[tk].iloc[-1]) if len(current_tickers) > 1 else int(new_data.iloc[-1])
                    st.session_state.scan_time = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%H:%M:%S")
                except: pass
            st.rerun()

    if st.button("⚡ EXECUTE_DEEP_SCAN", width="stretch"):
        st.session_state.results = run_scan(load_tickers(), mode_scan)
        st.session_state.scan_time = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%H:%M:%S")

    if 'results' in st.session_state:
        df = st.session_state.results
        if not df.empty:
            st.caption(f"Last Sync: {st.session_state.scan_time} WIB")
            
            # TAB VIEW FOR MOBILE OPTIMIZATION
            tab_desk, tab_mob = st.tabs(["🖥️ DESKTOP VIEW", "📱 MOBILE VIEW"])
            with tab_desk: st.dataframe(df.drop(columns=['FULL']), use_container_width=True, hide_index=True)
            with tab_mob: draw_mobile_cards(df)
            
            sel_t = st.selectbox("FOCUS_TARGET", df['TICKER'].tolist())
            full_t = df[df['TICKER'] == sel_t]['FULL'].values[0]
            chart_data = yf.download(full_t, period="6mo", interval="1d", progress=False, auto_adjust=True)
            chart_data.columns = [c[0] if isinstance(c, tuple) else c for c in chart_data.columns]
            chart_data['MA20'] = chart_data['Close'].rolling(20).mean()
            delta = chart_data['Close'].diff(); gain = (delta.where(delta > 0, 0)).rolling(14).mean(); loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            chart_data['RSI'] = 100 - (100 / (1 + (gain/loss)))

            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_width=[0.2, 0.15, 0.65])
            fig.add_trace(go.Candlestick(x=chart_data.index, open=chart_data['Open'], high=chart_data['High'], low=chart_data['Low'], close=chart_data['Close'], name="Price"), row=1, col=1)
            fig.add_trace(go.Scatter(x=chart_data.index, y=chart_data['MA20'], line=dict(color='#ffcc00'), name="MA20"), row=1, col=1)
            fig.add_trace(go.Bar(x=chart_data.index, y=chart_data['Volume'], name="Vol", opacity=0.4), row=2, col=1)
            fig.add_trace(go.Scatter(x=chart_data.index, y=chart_data['RSI'], line=dict(color='#ff00ff'), name="RSI"), row=3, col=1)
            fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=500, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)

# --- 5. CONTENT: MONEY MANAGEMENT (UPDATED) ---
elif menu == "MONEY MANAGEMENT":
    st.title("💰 MONEY_INTELLIGENCE")
    
    tab1, tab2 = st.tabs(["📈 ACTIVE PORTFOLIO", "📜 TRADING HISTORY"])
    
    with tab1:
        with st.expander("➕ ADD NEW POSITION"):
            with st.form("add_p"):
                c1, c2, c3 = st.columns(3)
                t_in = c1.text_input("Ticker (Tanpa .JK)")
                p_in = c2.number_input("Buy Price", min_value=0.0)
                l_in = c3.number_input("Lots", min_value=1)
                if st.form_submit_button("AUTHORIZE PURCHASE"):
                    if t_in: 
                        add_to_portfolio(user_now, t_in, p_in, l_in, 0, 0)
                        st.rerun()

        df_p = get_user_portfolio(user_now, role)
        if not df_p.empty:
            # Fetch Live Prices
            tickers_jk = [f"{t}.JK" for t in df_p['ticker'].unique()]
            try:
                live_data = yf.download(tickers_jk, period="1d", progress=False)['Close']
                if isinstance(live_data, pd.Series):
                    live_prices = {tickers_jk[0]: live_data.iloc[-1]}
                else:
                    live_prices = live_data.iloc[-1].to_dict()
            except: live_prices = {}

            def calc_active(row):
                tk = f"{row['ticker']}.JK"
                curr = live_prices.get(tk, row['buy_price'])
                if isinstance(curr, (pd.Series, pd.DataFrame)): curr = curr.iloc[0]
                cost = float(row['buy_price'] * row['lots'] * 100)
                val = float(curr * row['lots'] * 100)
                return pd.Series([float(curr), cost, val, (val-cost)])

            df_p[['Live', 'Cost', 'Value', 'P/L']] = df_p.apply(calc_active, axis=1)
            
            # --- DASHBOARD METRICS ---
            m1, m2, m3 = st.columns(3)
            t_inv = df_p['Cost'].sum()
            t_pl = df_p['P/L'].sum()
            m1.metric("TOTAL INVESTMENT", f"Rp {t_inv:,.0f}")
            m2.metric("FLOATING P/L", f"Rp {t_pl:,.0f}", f"{(t_pl/t_inv*100 if t_inv!=0 else 0):.2f}%")
            m3.metric("CURRENT VALUE", f"Rp {t_inv+t_pl:,.0f}")

            # --- PORTFOLIO VISUALIZATION ---
            col_chart, col_list = st.columns([1, 1])
            with col_chart:
                fig_pie = go.Figure(data=[go.Pie(labels=df_p['ticker'], values=df_p['Value'], hole=.4, marker=dict(colors=['#ccff00', '#00ffff', '#ff00ff', '#ffffff']))])
                fig_pie.update_layout(title="Asset Allocation", template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', showlegend=False, height=300)
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col_list:
                for i, row in df_p.iterrows():
                    clr = "#ccff00" if row['P/L'] >= 0 else "#ff4b4b"
                    st.markdown(f"""
                        <div style='border:1px solid {clr}33; padding:10px; border-radius:5px; margin-bottom:5px; background:rgba(0,0,0,0.2)'>
                            <small>{row['ticker']}</small><br>
                            <b style='color:{clr}'>P/L: Rp {row['P/L']:,.0f}</b>
                        </div>
                    """, unsafe_allow_html=True)

            # --- MANAGEMENT TABLE ---
            st.dataframe(df_p.drop(columns=['username','tp_price','cl_price']), use_container_width=True, hide_index=True)
            
            for i, row in df_p.iterrows():
                with st.expander(f"EXECUTE SELL: {row['ticker']}"):
                    cs, cd = st.columns([3, 1])
                    s_price = cs.number_input(f"Sell Price", value=float(row['Live']), key=f"s_{row['id']}")
                    if cs.button(f"CONFIRM SELL {row['ticker']}", key=f"btn_s_{row['id']}", use_container_width=True):
                        sell_position(user_now, row['id'], row['ticker'], row['buy_price'], s_price, row['lots'])
                        st.rerun()
                    if cd.button("DEL", key=f"btn_d_{row['id']}", use_container_width=True):
                        with sqlite3.connect('users.db') as conn:
                            conn.execute("DELETE FROM portfolio WHERE id=?", (row['id'],))
                        st.rerun()
        else: st.info("No active positions detected.")

    with tab2:
        conn = sqlite3.connect('users.db')
        df_h = pd.read_sql_query("SELECT * FROM history WHERE username=? ORDER BY date ASC", conn, params=(user_now,))
        conn.close()
        
        if not df_h.empty:
            df_h['date'] = pd.to_datetime(df_h['date'])
            df_h['P/L %'] = ((df_h['sell_price'] - df_h['buy_price']) / df_h['buy_price']) * 100
            
            # --- HISTORY FILTERS ---
            period = st.radio("TIME_RANGE", ["1 Month", "1 Year", "All Time"], horizontal=True)
            now = datetime.now()
            if period == "1 Month": df_h = df_h[df_h['date'] > (now - pd.DateOffset(months=1))]
            elif period == "1 Year": df_h = df_h[df_h['date'] > (now - pd.DateOffset(years=1))]

            # --- CALCULATE AGGREGATES ---
            total_profit = df_h[df_h['pnl'] > 0]['pnl'].sum()
            total_loss = df_h[df_h['pnl'] <= 0]['pnl'].sum()
            win_rate = (len(df_h[df_h['pnl'] > 0]) / len(df_h)) * 100 if len(df_h) > 0 else 0
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("TOTAL PROFIT", f"Rp {total_profit:,.0f}")
            c2.metric("TOTAL CUT LOSS", f"Rp {total_loss:,.0f}", delta_color="inverse")
            c3.metric("NET PNL", f"Rp {(total_profit + total_loss):,.0f}")
            c4.metric("WIN RATE", f"{win_rate:.1f}%")

            # --- EQUITY CURVE CHART ---
            df_h['Cumulative PnL'] = df_h['pnl'].cumsum()
            fig_curve = go.Figure()
            fig_curve.add_trace(go.Scatter(x=df_h['date'], y=df_h['Cumulative PnL'], mode='lines+markers', line=dict(color='#ccff00', width=2), fill='tozeroy', fillcolor='rgba(204,255,0,0.1)', name="Equity Curve"))
            fig_curve.update_layout(title="Growth Analysis (Equity Curve)", template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=350, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_curve, use_container_width=True)

            # --- DETAILED LOG ---
            st.dataframe(df_h[['date', 'ticker', 'buy_price', 'sell_price', 'lots', 'pnl', 'P/L %']].sort_values('date', ascending=False), use_container_width=True, hide_index=True)
        else:
            st.info("No trading history recorded.")

elif menu == "USER MANAGEMENT":
    st.title("👤 ACCESS_CONTROL")
    conn = sqlite3.connect('users.db')
    df_u = pd.read_sql_query("SELECT username, role, last_login, location FROM users", conn)
    conn.close(); st.dataframe(df_u, use_container_width=True, hide_index=True)
    c1, c2 = st.columns(2)
    with c1:
        with st.form("add_u"):
            nu, np, nr = st.text_input("User"), st.text_input("Key", type="password"), st.selectbox("Role", ["user", "admin"])
            if st.form_submit_button("GRANT"):
                if add_user_db(nu, np, nr): st.success("Added"); st.rerun()
    with c2:
        du = st.text_input("Revoke ID")
        if st.button("🔴 DELETE PERMANENTLY"):
            if delete_user_db(du): st.warning("Removed"); st.rerun()

elif menu == "SECURITY SETTINGS":
    st.title("🔒 SECURITY_VAULT")
    with st.form("p"):
        new_p = st.text_input("NEW ACCESS KEY", type="password")
        if st.form_submit_button("UPDATE"):
            if update_password_db(user_now, new_p): st.success("Updated")
