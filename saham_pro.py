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
    # Cek hashed password
    c.execute("SELECT role FROM users WHERE username=? AND password=?", (u, hashed))
    res = c.fetchone()
    # Fallback untuk user lama (plain text) - Migrasi Otomatis
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

# --- 3. DATA ENGINE & LOGIC ---
@st.cache_data(ttl=86400)
def load_tickers():
    try:
        url = "https://raw.githubusercontent.com/datasets-id/idx-stocks/main/data/stock_codes.csv"
        df_idx = pd.read_csv(url)
        tickers = [str(t).strip().upper() + ".JK" for t in df_idx['ticker'].tolist() if len(str(t)) <= 5]
        if len(tickers) > 100: return tickers
    except: pass
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
                <span style="color: {chg_color}; font-weight: bold;">{row['CHG%']}% {row['SIGNAL']}</span>
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
            # Mengambil 60 hari data untuk MA50 & RSI
            data = yf.download(batch, period="60d", interval="1d", group_by='ticker', progress=False, auto_adjust=True)
            for t in batch:
                try:
                    df_t = data[t].dropna() if len(batch) > 1 else data.dropna()
                    if len(df_t) < 51: continue # Butuh minimal 50 hari
                    
                    df_t.columns = [c[0] if isinstance(c, tuple) else c for c in df_t.columns]
                    
                    # 1. Advanced Technicals (MA & RSI)
                    last_close = df_t['Close']
                    ma20 = last_close.rolling(20).mean().iloc[-1]
                    ma50 = last_close.rolling(50).mean().iloc[-1]
                    
                    delta = last_close.diff()
                    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                    rs = gain / loss
                    rsi = (100 - (100 / (1 + rs))).iloc[-1]

                    last, prev = df_t.iloc[-1], df_t.iloc[-2]
                    c_now, h_now, o_now = float(last['Close']), float(last['High']), float(last['Open'])
                    vol, vol_avg5 = float(last['Volume']), df_t['Volume'].iloc[-6:-1].mean()
                    vol_spike = vol > (vol_avg5 * 1.5)
                    chg = ((c_now - float(prev['Close'])) / float(prev['Close'])) * 100
                    val = c_now * vol
                    
                    # 2. BSJP & HOLD Logic
                    # BSJP: Beli Sore Jual Pagi (Strong Close)
                    # HOLD: Uptrend kuat, diatas MA50
                    sig = "-"
                    if c_now >= (h_now * 0.99) and chg > 3: sig = "🚀 BSJP"
                    elif c_now > ma50 and ma20 > ma50 and rsi < 70: sig = "💎 HOLD"

                    # Filters
                    if mode == "Ketat":
                        cond = (val > 1_000_000_000 and 2.5 < chg < 15 and c_now > ma20 and vol_spike)
                    else:
                        cond = (val > 200_000_000 and chg > 1.5 and vol_spike)
                    
                    if cond:
                        results.append({
                            "TICKER": t.replace(".JK",""), "LAST": int(c_now), "CHG%": round(chg, 2), 
                            "SIGNAL": sig, "RSI": round(rsi, 1),
                            "ENTRY": f"{int(c_now)}-{int(c_now*1.01)}", 
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
            tab_desk, tab_mob = st.tabs(["🖥️ DESKTOP VIEW", "📱 MOBILE VIEW"])
            with tab_desk: st.dataframe(df.drop(columns=['FULL']), use_container_width=True, hide_index=True)
            with tab_mob: draw_mobile_cards(df)
            
            sel_t = st.selectbox("FOCUS_TARGET", df['TICKER'].tolist())
            full_t = df[df['TICKER'] == sel_t]['FULL'].values[0]
            chart_data = yf.download(full_t, period="6mo", interval="1d", progress=False, auto_adjust=True)
            chart_data.columns = [c[0] if isinstance(c, tuple) else c for c in chart_data.columns]
            chart_data['MA20'] = chart_data['Close'].rolling(20).mean()
            chart_data['MA50'] = chart_data['Close'].rolling(50).mean()
            delta = chart_data['Close'].diff(); gain = (delta.where(delta > 0, 0)).rolling(14).mean(); loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            chart_data['RSI'] = 100 - (100 / (1 + (gain/loss)))

            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_width=[0.2, 0.15, 0.65])
            fig.add_trace(go.Candlestick(x=chart_data.index, open=chart_data['Open'], high=chart_data['High'], low=chart_data['Low'], close=chart_data['Close'], name="Price"), row=1, col=1)
            fig.add_trace(go.Scatter(x=chart_data.index, y=chart_data['MA20'], line=dict(color='#ffcc00', width=1), name="MA20"), row=1, col=1)
            fig.add_trace(go.Scatter(x=chart_data.index, y=chart_data['MA50'], line=dict(color='#00ffff', width=1.5), name="MA50"), row=1, col=1)
            fig.add_trace(go.Bar(x=chart_data.index, y=chart_data['Volume'], name="Vol", opacity=0.4), row=2, col=1)
            fig.add_trace(go.Scatter(x=chart_data.index, y=chart_data['RSI'], line=dict(color='#ff00ff'), name="RSI"), row=3, col=1)
            fig.add_hline(y=70, line_dash="dot", line_color="red", row=3, col=1)
            fig.add_hline(y=30, line_dash="dot", line_color="green", row=3, col=1)
            fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=600, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)

elif menu == "MONEY MANAGEMENT":
    st.title("💰 MONEY_INTELLIGENCE")
    privacy_mode = st.checkbox("🕶️ PRIVACY MODE (Hide Balances)", value=False)

    def format_privacy(value, is_currency=True):
        if privacy_mode: return "Rp *****" if is_currency else "*****"
        return f"Rp {value:,.0f}" if is_currency else f"{value:,.0f}"

    tab1, tab2, tab3 = st.tabs(["📈 ACTIVE PORTFOLIO", "📜 TRADING HISTORY", "🛡️ RISK CALCULATOR"])
    
    with tab1:
        with st.expander("➕ ADD NEW POSITION", expanded=False):
            with st.form("form_add_portfolio", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                t_in = c1.text_input("Ticker (Contoh: BBCA)")
                p_in = c2.number_input("Buy Price", min_value=0, step=1)
                l_in = c3.number_input("Lots", min_value=1, step=1)
                submit_add = st.form_submit_button("SAVE TO PORTFOLIO")
                if submit_add:
                    if t_in and p_in > 0:
                        add_to_portfolio(user_now, t_in, p_in, l_in, 0, 0)
                        st.success(f"Berhasil menambahkan {t_in.upper()}"); st.rerun()
                    else: st.error("Isi Ticker dan Harga Beli dengan benar!")

        df_p = get_user_portfolio(user_now, role)
        if not df_p.empty:
            tickers_jk = [f"{t}.JK" for t in df_p['ticker'].unique()]
            try:
                live_data = yf.download(tickers_jk, period="1d", progress=False)['Close']
                if len(tickers_jk) > 1: live_prices = live_data.iloc[-1].to_dict()
                else: live_prices = {tickers_jk[0]: live_data.iloc[-1]}
            except: live_prices = {}

            def calc_active(row):
                tk = f"{row['ticker']}.JK"
                curr = live_prices.get(tk, row['buy_price'])
                if isinstance(curr, (pd.Series, pd.DataFrame)): curr = curr.iloc[0]
                cost = float(row['buy_price'] * row['lots'] * 100)
                val = float(curr * row['lots'] * 100)
                return pd.Series([float(curr), cost, val, (val-cost)])

            df_p[['Live', 'Cost', 'Value', 'P/L']] = df_p.apply(calc_active, axis=1)
            m1, m2, m3 = st.columns(3)
            t_inv = df_p['Cost'].sum(); t_pl = df_p['P/L'].sum()
            
            # Privacy Mode Fix pada Metrik
            m1.metric("INVESTMENT", format_privacy(t_inv))
            m2.metric("FLOATING P/L", format_privacy(t_pl), f"{'***' if privacy_mode else (t_pl/t_inv*100 if t_inv!=0 else 0):.2f}%")
            m3.metric("TOTAL VALUE", format_privacy(t_inv + t_pl))

            fig_pie = go.Figure(data=[go.Pie(labels=df_p['ticker'], values=df_p['Value'], hole=.3)])
            fig_pie.update_layout(template="plotly_dark", height=300, paper_bgcolor='rgba(0,0,0,0)', showlegend=not privacy_mode)
            st.plotly_chart(fig_pie, use_container_width=True)

            df_display = df_p.copy()
            if privacy_mode:
                for col in ['buy_price', 'Live', 'Cost', 'Value', 'P/L']: df_display[col] = "*****"
            
            st.dataframe(df_display.drop(columns=['username','tp_price','cl_price']), use_container_width=True, hide_index=True)
            
            for i, row in df_p.iterrows():
                with st.expander(f"MANAGE {row['ticker']} {'(***)' if privacy_mode else ''}"):
                    cs, cd = st.columns([3, 1])
                    s_price = cs.number_input(f"Harga Jual", value=float(row['Live']), key=f"sell_val_{row['id']}")
                    if cs.button(f"🚀 SELL {row['ticker']}", key=f"btn_sell_{row['id']}", use_container_width=True):
                        sell_position(user_now, row['id'], row['ticker'], row['buy_price'], s_price, row['lots'])
                        st.rerun()
                    if cd.button("🗑️", key=f"btn_del_port_{row['id']}", use_container_width=True):
                        with sqlite3.connect('users.db') as conn:
                            conn.execute("DELETE FROM portfolio WHERE id=?", (row['id'],))
                        st.rerun()
        else: st.info("Portfolio kosong.")

    with tab2:
        st.subheader("📜 TRANSACTION_LOG")
        with sqlite3.connect('users.db') as conn:
            df_h = pd.read_sql_query("SELECT * FROM history WHERE username=? ORDER BY date DESC", conn, params=(user_now,))
        if not df_h.empty:
            df_h['date'] = pd.to_datetime(df_h['date'])
            total_profit = df_h[df_h['pnl'] > 0]['pnl'].sum()
            total_loss = df_h[df_h['pnl'] <= 0]['pnl'].sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("PROFIT", format_privacy(total_profit))
            c2.metric("LOSS", format_privacy(total_loss), delta_color="inverse")
            c3.metric("NET", format_privacy(total_profit + total_loss))

            df_curve = df_h.sort_values('date'); df_curve['cum_pnl'] = df_curve['pnl'].cumsum()
            fig_curve = go.Figure(go.Scatter(x=df_curve['date'], y=df_curve['cum_pnl'], mode='lines+markers', line=dict(color='#ccff00')))
            fig_curve.update_layout(template="plotly_dark", height=250, paper_bgcolor='rgba(0,0,0,0)', yaxis=dict(showticklabels=not privacy_mode))
            st.plotly_chart(fig_curve, use_container_width=True)

            for idx, h_row in df_h.iterrows():
                with st.expander(f"{h_row['date'].strftime('%Y-%m-%d')} | {h_row['ticker']} | {format_privacy(h_row['pnl'])}"):
                    col_txt, col_btn = st.columns([4,1])
                    if privacy_mode:
                        col_txt.write("Data hidden in Privacy Mode")
                    else:
                        col_txt.write(f"Beli: {h_row['buy_price']:,} | Jual: {h_row['sell_price']:,} | Vol: {h_row['lots']} Lot")
                    if col_btn.button("🗑️ Hapus", key=f"del_h_{h_row['id']}"):
                        with sqlite3.connect('users.db') as conn:
                            conn.execute("DELETE FROM history WHERE id=?", (h_row['id'],))
                        st.rerun()
        else: st.info("Belum ada riwayat transaksi.")

    with tab3:
        st.subheader("🛡️ POSITION_SIZER")
        with st.form("risk_calc"):
            c1, c2 = st.columns(2)
            capital = c1.number_input("Total Modal (IDR)", min_value=0, value=10000000, step=1000000)
            risk_pct = c2.slider("Resiko per Trade (%)", 0.5, 10.0, 1.0, 0.5)
            c3, c4 = st.columns(2)
            entry_p = c3.number_input("Rencana Entry", min_value=0, value=1000)
            stop_l = c4.number_input("Stop Loss (Price)", min_value=0, value=950)
            if st.form_submit_button("CALCULATE RISK"):
                risk_amt = capital * (risk_pct / 100)
                risk_per_share = entry_p - stop_l
                if risk_per_share > 0:
                    max_shares = risk_amt / risk_per_share
                    max_lots = int(max_shares / 100)
                    total_val = max_lots * 100 * entry_p
                    st.markdown(f"""
                    <div style="background:rgba(204,255,0,0.1); padding:20px; border-radius:10px; border:1px solid #ccff00;">
                        <h4 style='color:#ccff00; margin-top:0;'>HASIL ANALISA RESIKO</h4>
                        <p>Uang Beresiko (Risk): <b>{format_privacy(risk_amt)}</b></p>
                        <p>Jumlah Maksimal: <b style='font-size:1.5rem;'>{max_lots} LOT</b></p>
                        <p>Total Nilai Beli: <b>{format_privacy(total_val)}</b></p>
                        <p>Persentase Modal: <b>{(total_val/capital*100):.1f}%</b></p>
                    </div>
                    """, unsafe_allow_html=True)
                else: st.error("Stop Loss harus lebih rendah dari harga Entry!")

elif menu == "USER MANAGEMENT":
    st.title("👤 ACCESS_CONTROL")
    conn = sqlite3.connect('users.db')
    # Sembunyikan password di tampilan admin
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
            if update_password_db(user_now, new_p): st.success("Security Key Updated with SHA-256")
