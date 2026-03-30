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

# --- 1. PRO CYBER STYLING (ENHANCED CYBER ART) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Orbitron:wght@400;900&display=swap');
    
    [data-testid="stHeaderActionElements"], .stDeployButton, #MainMenu {
        display: none !important;
    }
    
    header { background-color: transparent !important; }

    /* BACKGROUND ART: CYBER GRID & ANIMATED LINES */
    .stApp {
        background-color: #05070a;
        background-image: 
            /* Grid Utama */
            linear-gradient(rgba(204, 255, 0, 0.05) 1px, transparent 1px),
            linear-gradient(90deg, rgba(204, 255, 0, 0.05) 1px, transparent 1px),
            /* Garis Aksen Diagonal */
            linear-gradient(45deg, rgba(0, 255, 255, 0.02) 25%, transparent 25%, transparent 50%, rgba(0, 255, 255, 0.02) 50%, rgba(0, 255, 255, 0.02) 75%, transparent 75%, transparent),
            /* Radial Glow di Tengah */
            radial-gradient(circle at 50% 50%, rgba(10, 25, 47, 0.8), #05070a);
        background-size: 40px 40px, 40px 40px, 100px 100px, 100% 100%;
        font-family: 'JetBrains Mono', monospace;
        color: #e0e0e0;
    }

    /* EFEK SCANLINE BERGERAK */
    .stApp::before {
        content: " ";
        display: block;
        position: absolute;
        top: 0; left: 0; bottom: 0; right: 0;
        background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.1) 50%), 
                    linear-gradient(90deg, rgba(255, 0, 0, 0.02), rgba(0, 255, 0, 0.01), rgba(0, 0, 255, 0.02));
        z-index: 2;
        background-size: 100% 4px, 3px 100%;
        pointer-events: none;
    }

    /* BOX STYLING DENGAN NEON BORDER */
    div[data-testid="stMetric"], .status-box, .stDataFrame, div[data-testid="stExpander"], .stTabs, .stForm {
        background: rgba(0, 10, 20, 0.7) !important;
        backdrop-filter: blur(15px);
        border: 1px solid rgba(204, 255, 0, 0.3) !important;
        box-shadow: 0 0 15px rgba(204, 255, 0, 0.05);
        border-radius: 12px !important;
    }

    /* JUDUL DENGAN EFEK GLOW */
    h1 {
        font-family: 'Orbitron', sans-serif;
        text-transform: uppercase;
        letter-spacing: 3px;
        background: linear-gradient(90deg, #ccff00, #00ffff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        filter: drop-shadow(0 0 10px rgba(204, 255, 0, 0.5));
    }

    /* SIDEBAR CUSTOMIZATION */
    section[data-testid="stSidebar"] {
        background-color: #030508 !important;
        border-right: 1px solid rgba(204, 255, 0, 0.2);
    }

    /* TABS STYLING */
    .stTabs [data-baseweb="tab-list"] { gap: 15px; }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent !important;
        border: 1px solid transparent !important;
        color: #888 !important;
        transition: 0.3s;
    }
    .stTabs [aria-selected="true"] {
        border-bottom: 2px solid #ccff00 !important;
        color: #ccff00 !important;
        text-shadow: 0 0 10px rgba(204, 255, 0, 0.5);
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

elif menu == "MONEY MANAGEMENT":
    st.title("💰 MONEY_MANAGEMENT")
    tab1, tab2 = st.tabs(["📈 ACTIVE PORTFOLIO", "📜 TRADING HISTORY"])
    
    with tab1:
        with st.expander("➕ ADD NEW POSITION"):
            with st.form("add_p"):
                c1, c2, c3 = st.columns(3)
                t_in = c1.text_input("Ticker")
                p_in = c2.number_input("Buy Price", min_value=0.0)
                l_in = c3.number_input("Lots", min_value=1)
                if st.form_submit_button("SAVE"):
                    if t_in: 
                        add_to_portfolio(user_now, t_in, p_in, l_in, 0, 0)
                        st.rerun()
        
        df_p = get_user_portfolio(user_now, role)
        if not df_p.empty:
            tickers = [f"{t}.JK" for t in df_p['ticker'].unique()]
            try:
                live_data = yf.download(tickers, period="1d", progress=False)['Close']
                live_prices = live_data.iloc[-1].to_dict() if len(tickers) > 1 else {tickers[0]: live_data.iloc[-1]}
            except: 
                live_prices = {}
            
            def calc_active(row):
                tk = f"{row['ticker']}.JK"
                curr = live_prices.get(tk, row['buy_price'])
                if isinstance(curr, (pd.Series, pd.DataFrame)): curr = curr.iloc[0]
                cost = float(row['buy_price'] * row['lots'] * 100)
                val = float(curr * row['lots'] * 100)
                return pd.Series([float(curr), cost, val, (val-cost)])
            
            df_p[['Live', 'Cost', 'Value', 'P/L']] = df_p.apply(calc_active, axis=1)
            m1, m2, m3 = st.columns(3)
            t_inv, t_pl = df_p['Cost'].sum(), df_p['P/L'].sum()
            m1.metric("INVESTMENT", f"Rp {t_inv:,.0f}")
            m2.metric("FLOATING P/L", f"Rp {t_pl:,.0f}", f"{(t_pl/t_inv*100 if t_inv!=0 else 0):.2f}%")
            m3.metric("BALANCE", f"Rp {t_inv+t_pl:,.0f}")
            
            for i, row in df_p.iterrows():
                with st.expander(f"MANAGE: {row['ticker']} ({row['lots']} Lots)"):
                    cs, cd = st.columns([3, 1])
                    s_price = cs.number_input(f"Jual {row['ticker']}", value=float(row['Live']), key=f"s_{row['id']}")
                    if cs.button(f"🚀 SELL {row['ticker']}", key=f"btn_s_{row['id']}", use_container_width=True):
                        sell_position(user_now, row['id'], row['ticker'], row['buy_price'], s_price, row['lots'])
                        st.rerun()
                    if cd.button("🗑️", key=f"btn_d_{row['id']}", use_container_width=True):
                        conn = sqlite3.connect('users.db')
                        conn.cursor().execute("DELETE FROM portfolio WHERE id=?", (row['id'],))
                        conn.commit(); conn.close()
                        st.rerun()
            st.dataframe(df_p.drop(columns=['username','tp_price','cl_price']), use_container_width=True, hide_index=True)
        else:
            st.info("Belum ada posisi.")

    with tab2:
        st.subheader("📊 PERFORMANCE DASHBOARD")
        conn = sqlite3.connect('users.db')
        df_h = pd.read_sql_query("SELECT * FROM history WHERE username=? ORDER BY date ASC", conn, params=(user_now,))
        conn.close()
        
        if not df_h.empty:
            df_h['date'] = pd.to_datetime(df_h['date'])
            total_pnl = df_h['pnl'].sum()
            total_win = df_h[df_h['pnl'] > 0]['pnl'].count()
            total_loss = df_h[df_h['pnl'] <= 0]['pnl'].count()
            win_rate = (total_win / len(df_h)) * 100
            df_h['cumulative_pnl'] = df_h['pnl'].cumsum()
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("TOTAL NET P/L", f"Rp {total_pnl:,.0f}")
            m2.metric("TRADES", len(df_h))
            m3.metric("WIN RATE", f"{win_rate:.1f}%")
            m4.metric("W/L RATIO", f"{total_win}W - {total_loss}L")

            st.markdown("### 📈 EQUITY GROWTH (1 YEAR)")
            fig_perf = go.Figure()
            fig_perf.add_trace(go.Scatter(
                x=df_h['date'], y=df_h['cumulative_pnl'],
                mode='lines+markers', line=dict(color='#ccff00', width=3),
                fill='tozeroy', fillcolor='rgba(204, 255, 0, 0.1)'
            ))
            fig_perf.update_layout(template="plotly_dark", height=300, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_perf, use_container_width=True)

            st.markdown("### 📜 TRANSACTION LOG")
            df_display = df_h.sort_values(by='date', ascending=False).copy()
            df_display['P/L %'] = ((df_display['sell_price'] - df_display['buy_price']) / df_display['buy_price']) * 100
            
            for idx, h_row in df_display.iterrows():
                sc = "#ccff00" if h_row['pnl'] > 0 else "#ff4b4b"
                with st.expander(f"{h_row['date'].strftime('%Y-%m-%d')} | {h_row['ticker']} | {h_row['P/L %']:+.2f}%"):
                    st.write(f"Beli: {h_row['buy_price']:,.0f} | Jual: {h_row['sell_price']:,.0f} | Net: Rp {h_row['pnl']:,.0f}")
                    if st.button(f"🗑️ Hapus Record {h_row['id']}", key=f"del_h_{h_row['id']}"):
                        conn = sqlite3.connect('users.db')
                        conn.cursor().execute("DELETE FROM history WHERE id=?", (h_row['id'],))
                        conn.commit(); conn.close()
                        st.rerun()
        else:
            st.info("Belum ada data history.")
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
