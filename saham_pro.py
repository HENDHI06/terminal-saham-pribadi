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

with sqlite3.connect('users.db') as conn:
    try:
        conn.execute("ALTER TABLE history ADD COLUMN lots INTEGER")
        conn.execute("ALTER TABLE history ADD COLUMN profit REAL")
    except:
        pass # Jika kolom sudah ada, abaikan saja

def sell_position(user_id, portfolio_id, ticker, buy_price, sell_price, sell_qty, current_lots):
    import sqlite3
    from datetime import datetime
    
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        
        # 1. Pastikan tabel history ada (Mencegah OperationalError)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                ticker TEXT,
                buy_price REAL,
                sell_price REAL,
                lots INTEGER,
                profit REAL,
                date TEXT
            )
        """)
        
        # 2. Hitung Profit (Selisih x Lot x 100)
        profit = (sell_price - buy_price) * sell_qty * 100
        date_sell = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # 3. Insert ke History
        cursor.execute("""
            INSERT INTO history (user_id, ticker, buy_price, sell_price, lots, profit, date) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, ticker, buy_price, sell_price, sell_qty, profit, date_sell))
        
        # 4. Update atau Hapus di tabel Portfolio
        if sell_qty < current_lots:
            # JUAL SEBAGIAN: Kurangi jumlah lot
            cursor.execute("UPDATE portfolio SET lots = lots - ? WHERE id = ?", (sell_qty, portfolio_id))
        else:
            # JUAL SEMUA: Hapus baris
            cursor.execute("DELETE FROM portfolio WHERE id = ?", (portfolio_id,))
        
        conn.commit()

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

import streamlit as st

# --- GLOBAL CYBER 4K STYLING (TEXTURED VERSION) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Orbitron:wght@400;900&display=swap');

    /* 1. BACKGROUND DENGAN TEKSTUR GRID & SCANLINES */
    .stApp {
        background-color: #020617;
        background-image: 
            linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), 
            linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06)),
            radial-gradient(circle at 50% 50%, #0d1117 0%, #020617 100%);
        background-size: 100% 4px, 3px 100%, 100% 100%; /* Efek Scanline */
        color: #e2e8f0;
        font-family: 'Inter', sans-serif;
    }

    /* 2. EFEK GRID HALUS */
    .stApp::before {
        content: "";
        position: absolute;
        top: 0; left: 0; width: 100%; height: 100%;
        background-image: 
            linear-gradient(rgba(204, 255, 0, 0.05) 1px, transparent 1px),
            linear-gradient(90deg, rgba(204, 255, 0, 0.05) 1px, transparent 1px);
        background-size: 30px 30px;
        pointer-events: none;
        z-index: 0;
    }

    /* 3. JUDUL NEON GLOW */
    h1, h2, h3 {
        font-family: 'Orbitron', sans-serif !important;
        background: linear-gradient(90deg, #ccff00, #00ffff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        filter: drop-shadow(0 0 12px rgba(204, 255, 0, 0.4));
    }

    /* 4. GLASSMORPHISM BOX (TRANSPARAN TEBAL) */
    div[data-testid="stForm"], div[data-testid="stMetric"], .stDataFrame, .stTabs {
        background: rgba(15, 23, 42, 0.8) !important;
        backdrop-filter: blur(20px);
        border: 1px solid rgba(204, 255, 0, 0.2) !important;
        border-radius: 15px !important;
        box-shadow: 0 0 20px rgba(0,0,0,0.5) !important;
    }

    /* 5. INPUT FIELD DENGAN TEKS MENYALA */
    .stTextInput input {
        background-color: rgba(0, 0, 0, 0.7) !important;
        border: 1px solid rgba(204, 255, 0, 0.4) !important;
        color: #ccff00 !important;
        font-family: 'JetBrains Mono', monospace;
        text-shadow: 0 0 5px rgba(204, 255, 0, 0.5);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. AUTHENTICATION (CLEAN & PRO VERSION) ---
if "auth" not in st.session_state:
    st.session_state["auth"] = {"logged_in": False, "user": None, "role": None}

if not st.session_state["auth"]["logged_in"]:
    # Tampilan Header 4K
    st.markdown("""
        <div style="text-align: center; margin-top: 50px; margin-bottom: 30px;">
            <h1 style="font-size: 4.5rem; margin-bottom: 0; font-family: 'Orbitron', sans-serif;">IDX</h1>
            <p style="color: #64748b; letter-spacing: 10px; font-size: 0.7rem; font-weight: 300;">CYBER_TERMINAL_PRO</p>
            <div style="height: 2px; width: 80px; background: #ccff00; margin: 15px auto; box-shadow: 0 0 15px #ccff00;"></div>
        </div>
    """, unsafe_allow_html=True)

    # Box Login simetris di tengah
    _, col2, _ = st.columns([1, 1.2, 1])
    with col2:
        # Gunakan form agar input tidak refresh setiap ngetik satu huruf
        with st.form("login_form", clear_on_submit=False):
            u = st.text_input("OPERATOR ID").strip()
            p = st.text_input("ACCESS KEY", type="password")
            submit = st.form_submit_button("AUTHORIZE ACCESS", use_container_width=True)
            
            if submit:
                if u and p:
                    # Ganti 'check_login_db' dengan nama fungsi login kamu yang asli jika berbeda
                    role = check_login_db(u, p)
                    if role:
                        update_login_info(u)
                        st.session_state["auth"] = {"logged_in": True, "user": u, "role": role}
                        st.success("ACCESS GRANTED. INITIALIZING...")
                        st.rerun()
                    else:
                        st.error("❌ ACCESS DENIED")
                else:
                    st.warning("PLEASE ENTER CREDENTIALS")
    
    st.stop() # Menahan agar konten dashboard tidak muncul sebelum loginTrue)

    # LANJUTKAN DENGAN FORM LOGIN KAMU:
    _, col2, _ = st.columns([1, 1.2, 1])
    with col2:
        with st.form("login_form"):
            u = st.text_input("OPERATOR ID").strip()
            p = st.text_input("ACCESS KEY", type="password")
            if st.form_submit_button("AUTHORIZE ACCESS", use_container_width=True):
                # ... (Logika login kamu tetap sama) ...
                pass
    st.stop()

    # 2. BOX LOGIN (Gunakan kolom agar berada di tengah)
    _, col2, _ = st.columns([1, 1.2, 1]) # Perlebar sedikit col2 agar nyaman
    with col2:
        with st.form("login_form"):
            # Gunakan label uppercase agar senada dengan tema terminal
            u = st.text_input("OPERATOR ID").strip()
            p = st.text_input("ACCESS KEY", type="password")
            
            # Submit button
            if st.form_submit_button("AUTHORIZE ACCESS", use_container_width=True):
                role = check_login_db(u, p)
                if role:
                    update_login_info(u)
                    st.session_state["auth"] = {"logged_in": True, "user": u, "role": role}
                    st.rerun()
                else: 
                    st.error("❌ ACCESS DENIED: INVALID CREDENTIALS")
    
    # Tambahkan footer kecil di bawah box login (Opsional)
    st.markdown("<p style='text-align:center; color:#1e293b; font-size:0.6rem; margin-top:50px;'>SECURE ENCRYPTED CONNECTION ENABLED</p>", unsafe_allow_html=True)
    
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
    if df.empty:
        st.warning("No data available for Mobile View.")
        return

    for _, row in df.iterrows():
        # Penentuan Warna Berdasarkan Perubahan Harga
        chg_val = row.get('CHG%', 0)
        chg_color = "#ccff00" if chg_val > 0 else "#ff4b4b"
        
        # Penentuan Label dan Warna Signal
        sig_label = row.get('REKOMENDASI', 'N/A')
        sig_color = "#ccff00" if "BSJP" in sig_label else "#00ffff"
        
        st.markdown(f"""
        <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.1); 
                    border-left: 4px solid {chg_color}; border-radius: 10px; padding: 12px; margin-bottom: 10px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-size: 1.1rem; font-weight: 800; color: #fff;">{row['TICKER']}</span>
                <span style="background: {sig_color}22; color: {sig_color}; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: bold; border: 1px solid {sig_color}44;">
                    {sig_label}
                </span>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 0.85rem;">
                <div style="color: #888;">Price: <b style="color: #fff;">{int(row['LAST'])}</b> <span style="color: {chg_color};">({chg_val}%)</span></div>
                <div style="color: #888;">Value: <b style="color: #fff;">{row['VAL(M)']}M</b></div>
                <div style="color: #888;">Entry: <b style="color: #00ffff;">{int(row['ENTRY'])}</b></div>
                <div style="color: #888;">Target: <b style="color: #ccff00;">{int(row['TP'])}</b></div>
                <div style="color: #888;">Stop Loss: <b style="color: #ff4b4b;">{int(row['CL'])}</b></div>
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
            # Kita pakai period 100d supaya MA100 bisa terhitung
            data = yf.download(batch, period="100d", interval="1d", group_by='ticker', progress=False, auto_adjust=True)
            for t in batch:
                try:
                    df_t = data[t].dropna() if len(batch) > 1 else data.dropna()
                    if len(df_t) < 50: continue
                    df_t.columns = [c[0] if isinstance(c, tuple) else c for c in df_t.columns]
                    
                    # --- INDIKATOR TREN ---
                    last_close = df_t['Close']
                    ma20 = last_close.rolling(20).mean().iloc[-1]
                    ma50 = last_close.rolling(50).mean().iloc[-1]
                    ma100 = last_close.rolling(100).mean().iloc[-1]

                    last, prev = df_t.iloc[-1], df_t.iloc[-2]
                    c_now, h_now = float(last['Close']), float(last['High'])
                    vol, vol_avg5 = float(last['Volume']), df_t['Volume'].iloc[-6:-1].mean()
                    chg = ((c_now - float(prev['Close'])) / float(prev['Close'])) * 100
                    val = c_now * vol

                    # --- LOGIKA KLASIFIKASI (BSJP vs HOLD) ---
                    sig = "-"
                    # Syarat BSJP: Harga tutup kuat di atas, naik > 4%, volume meledak
                    if c_now >= (h_now * 0.98) and chg > 4 and vol > (vol_avg5 * 1.5):
                        sig = "🚀 BSJP"
                    # Syarat HOLD: Susunan MA rapi (Uptrend)
                    elif c_now > ma50 and ma20 > ma50 and ma50 > ma100:
                        sig = "💎 HOLD"

                    # --- FILTER MODE ---
                    if mode == "Ketat":
                        cond = (val > 1_500_000_000 and chg > 2 and sig != "-")
                    else:
                        cond = (val > 300_000_000 and chg > 1 and sig != "-")

                    if cond:
                        results.append({
                            "TICKER": t.replace(".JK",""), 
                            "LAST": int(c_now), 
                            "CHG%": round(chg, 2), 
                            "REKOMENDASI": sig, 
                            "VAL(M)": round(val/1_000_000, 1), 
                            "ENTRY": int(c_now), 
                            "TP": int(c_now*1.03) if sig=="🚀 BSJP" else int(c_now*1.15),
                            "CL": int(c_now*0.97) if sig=="🚀 BSJP" else int(ma50), 
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

menu_list = ["STRATEGY SCANNER", "FUNDAMENTAL ANALYZER", "TICKER COMPARISON", "MARKET_NEWS", "MONEY MANAGEMENT", "SECURITY SETTINGS"]
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

    # 1. TOMBOL EKSEKUSI
    if st.button("⚡ EXECUTE_DEEP_SCAN", width="stretch"):
        st.session_state.results = run_scan(load_tickers(), mode_scan)
        st.session_state.scan_time = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%H:%M:%S")

    # 2. TAMPILKAN HASIL (Satu blok tunggal agar tidak double)
    # 2. TAMPILKAN HASIL (Versi Fix NameError & Pro Look)
    if 'results' in st.session_state:
        df = st.session_state.results
        if not df.empty:
            st.caption(f"Last Sync: {st.session_state.scan_time} WIB")
            
            # --- 1. TOP PICKS SECTION ---
            st.markdown("### 🌟 ANALYTICS_INSIGHT")
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.markdown("<p style='color:#ccff00; font-weight:bold; margin-bottom:5px;'>🔥 TOP BSJP SCALPING</p>", unsafe_allow_html=True)
                top_bsjp = df[df['REKOMENDASI'] == "🚀 BSJP"].head(2)
                if not top_bsjp.empty:
                    for _, r in top_bsjp.iterrows():
                        st.metric(label=r['TICKER'], value=int(r['LAST']), delta=f"{r['CHG%']}%")
                else:
                    st.caption("No BSJP signal.")

            with col_b:
                st.markdown("<p style='color:#00ffff; font-weight:bold; margin-bottom:5px;'>🏆 TOP HOLD TREND</p>", unsafe_allow_html=True)
                top_hold = df[df['REKOMENDASI'] == "💎 HOLD"].head(2)
                if not top_hold.empty:
                    for _, r in top_hold.iterrows():
                        st.metric(label=r['TICKER'], value=int(r['LAST']), delta=f"{r['CHG%']}%", delta_color="normal")
                else:
                    st.caption("No HOLD trend.")
            
            st.markdown("---")
            
# 2. TAMPILKAN HASIL (Indentasi 4 spasi dari 'if menu')
    if 'results' in st.session_state:
        df = st.session_state.results # (8 spasi)
        if not df.empty: # (8 spasi)
            st.caption(f"Last Sync: {st.session_state.scan_time} WIB") # (12 spasi)
            
            # --- BAGIAN TABEL (DEFINISI TAB) ---
            tab_desk, tab_mob = st.tabs(["🖥️ DESKTOP VIEW", "📱 MOBILE VIEW"]) # (12 spasi)
            
            with tab_desk: # <--- PASTIKAN BARIS INI SEJAJAR DENGAN 'tab_desk, tab_mob' di atas (12 spasi)
                st.dataframe( # (16 spasi)
                    df.drop(columns=['FULL']), 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={
                        "TICKER": st.column_config.TextColumn("Ticker"),
                        "LAST": st.column_config.NumberColumn("Price", format="%d"),
                        "CHG%": st.column_config.NumberColumn("Change", format="%.2f%%"),
                        "VAL(M)": st.column_config.NumberColumn("Value (M)", format="Rp %.1fM"),
                        "REKOMENDASI": st.column_config.TextColumn("Signal"),
                        "ENTRY": st.column_config.NumberColumn("Entry"),
                        "TP": st.column_config.NumberColumn("Target"),
                        "CL": st.column_config.NumberColumn("Stop Loss")
                    }
                )

            with tab_mob: 
                draw_mobile_cards(df)
                
            st.markdown("---")
            # --- 3. LANJUT KE BAGIAN CHART ---
            st.markdown("### 📈 FOCUS_ANALYSIS")
            
            # --- BAGIAN CHART (FOCUS TARGET) ---
            st.markdown("### 📈 FOCUS_TARGET_ANALYSIS")
            sel_t = st.selectbox("SELECT TICKER FOR CHART", df['TICKER'].tolist())
            full_t = df[df['TICKER'] == sel_t]['FULL'].values[0]
            
            # Download data chart
            chart_data = yf.download(full_t, period="6mo", interval="1d", progress=False, auto_adjust=True)
            chart_data.columns = [c[0] if isinstance(c, tuple) else c for c in chart_data.columns]
            
            # Tambahkan Indikator MA & RSI untuk Chart Detail
            chart_data['MA20'] = chart_data['Close'].rolling(20).mean()
            delta = chart_data['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            chart_data['RSI'] = 100 - (100 / (1 + (gain/loss)))

            # Gambar Chart Plotly
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_width=[0.2, 0.15, 0.65])
            fig.add_trace(go.Candlestick(x=chart_data.index, open=chart_data['Open'], high=chart_data['High'], low=chart_data['Low'], close=chart_data['Close'], name="Price"), row=1, col=1)
            fig.add_trace(go.Scatter(x=chart_data.index, y=chart_data['MA20'], line=dict(color='#ffcc00'), name="MA20"), row=1, col=1)
            fig.add_trace(go.Bar(x=chart_data.index, y=chart_data['Volume'], name="Vol", opacity=0.4), row=2, col=1)
            fig.add_trace(go.Scatter(x=chart_data.index, y=chart_data['RSI'], line=dict(color='#ff00ff'), name="RSI"), row=3, col=1)
            
            fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=600, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)

elif menu == "FUNDAMENTAL ANALYZER":
    # --- CUSTOM CSS UNTUK TAMPILAN TERMINAL PRO ---
    st.markdown("""
        <style>
        .reportview-container { background: #0e1117; }
        .stMetric {
            background: rgba(0,255,255,0.05);
            padding: 10px;
            border-radius: 5px;
            border-bottom: 2px solid #00ffff;
        }
        div[data-testid="stExpander"] {
            border: none !important;
            background: rgba(255,255,255,0.02) !important;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("📟 FUNDAMENTAL_TERMINAL_PRO")
    
    # 1. Inisialisasi State (Anti-Refresh)
    if "clicked_analyze" not in st.session_state:
        st.session_state.clicked_analyze = False
    if "last_ticker" not in st.session_state:
        st.session_state.last_ticker = ""

    # Input Section
    col_in1, col_in2 = st.columns([3, 1])
    with col_in1:
        target_f = st.text_input("SYSTEM_TICKER_INPUT", value="BBCA").upper().strip()
    with col_in2:
        st.write("##")
        btn_analyze = st.button("RUN_ANALYSIS", width="stretch")

    full_tk = f"{target_f}.JK" if not target_f.endswith(".JK") else target_f

    # Reset jika ganti ticker
    if target_f != st.session_state.last_ticker:
        st.session_state.clicked_analyze = False

    if btn_analyze:
        st.session_state.clicked_analyze = True
        st.session_state.last_ticker = target_f

    # Fungsi Internal Card Visual
    def draw_pro_card(label, value, subtext, color="#00ffff"):
        st.markdown(f"""
            <div style="background:rgba(255,255,255,0.02); padding:15px; border-radius:10px; border-top:3px solid {color}; height:140px;">
                <p style="margin:0; font-size:11px; color:#666; letter-spacing:1px;">{label.upper()}</p>
                <h2 style="margin:5px 0; color:{color}; font-family:monospace;">{value}</h2>
                <p style="margin:0; font-size:12px; color:#aaa;">{subtext}</p>
            </div>
        """, unsafe_allow_html=True)

    # 2. Main Analysis Logic
    if st.session_state.clicked_analyze:
        with st.spinner("SYNCING_FINANCIAL_DATABASE..."):
            try:
                stock = yf.Ticker(full_tk)
                info = stock.info
                
                # --- DEFINISI VARIABEL (Mencegah NameError & NoneType Error) ---
                current_price = info.get('currentPrice') or info.get('previousClose', 1)
                eps = info.get('trailingEps', 0) or 0
                bvps = info.get('bookValue', 0) or 0
                per = info.get('trailingPE', 0) or 0
                pbv = info.get('priceToBook', 0) or 0
                roe = (info.get('returnOnEquity', 0) or 0) * 100
                der = info.get('debtToEquity', 0) or 0
                target_mean = info.get('targetMeanPrice', current_price) or current_price
                div_yield = (info.get('dividendYield', 0) or 0) * 100
                cr = info.get('currentRatio', 0) or 0
                
                # Header Saham
                st.markdown(f"### 🏢 {info.get('longName', target_f)} <span style='color:#666; font-size:14px;'>| Sector: {info.get('sector', 'N/A')}</span>", unsafe_allow_html=True)
                
                # --- ROW 1: CORE RATIOS ---
                c1, c2, c3, c4 = st.columns(4)
                with c1: st.metric("PE_RATIO", f"{per:,.2f}x")
                with c2: st.metric("PBV_RATIO", f"{pbv:,.2f}x")
                with c3: st.metric("ROE_EFF", f"{roe:,.2f}%")
                with c4: st.metric("DIV_YIELD", f"{div_yield:,.2f}%")

                # --- ROW 2: VALUATION MATRIX ---
                st.markdown("<br>", unsafe_allow_html=True)
                col_v1, col_v2, col_v3 = st.columns(3)
                
                import math
                graham = math.sqrt(22.5 * eps * bvps) if (eps > 0 and bvps > 0) else 0
                fair_pe_val = eps * (15 if roe > 15 else 10)
                
                with col_v1:
                    status_g = "UNDER" if current_price < graham else "OVER"
                    draw_pro_card("Graham_Intrinsic", f"Rp{graham:,.0f}", f"Status: {status_g}VALUED", "#ccff00")
                with col_v2:
                    status_p = "UNDER" if current_price < fair_pe_val else "OVER"
                    draw_pro_card("PE_Fair_Value", f"Rp{fair_pe_val:,.0f}", f"Base: 15x Multiple", "#00ffff")
                with col_v3:
                    upside = ((target_mean - current_price)/current_price)*100
                    draw_pro_card("Analyst_Target", f"Rp{target_mean:,.0f}", f"Upside: {upside:.1f}%", "#ff00ff")

                # --- ROW 3: FINANCIAL PERFORMANCE & CHART ---
                st.markdown("---")
                col_tab, col_cht = st.columns([2, 3])
                
                with col_tab:
                    st.write("📂 **HISTORICAL_LEDGER**")
                    period = st.radio("TIME_FRAME", ["Annual", "Quarterly"], horizontal=True, label_visibility="collapsed")
                    
                    raw_fin = stock.quarterly_financials.T if period == "Quarterly" else stock.financials.T
                    
                    if not raw_fin.empty:
                        # Filter kolom & Miliar IDR
                        available_cols = [c for c in ['Total Revenue', 'Net Income'] if c in raw_fin.columns]
                        df = (raw_fin[available_cols].copy() / 1e9)
                        
                        # Fix Non-Unique Index issue
                        df.index = pd.to_datetime(df.index).strftime('%d-%m-%Y')
                        df = df.groupby(df.index).first().sort_index(ascending=False)
                        
                        try:
                            st.dataframe(df.style.format("{:,.2f}").highlight_max(axis=0, color='#004d4d'), use_container_width=True)
                        except:
                            st.dataframe(df, use_container_width=True)
                
                with col_cht:
                    st.write("📈 **GROWTH_VISUALIZER**")
                    fig = go.Figure()
                    fig.add_trace(go.Bar(x=df.index, y=df['Total Revenue'], name="Rev", marker_color='rgba(0, 255, 255, 0.2)'))
                    fig.add_trace(go.Scatter(x=df.index, y=df['Net Income'], name="Profit", line=dict(color='#ccff00', width=3)))
                    fig.update_layout(template="plotly_dark", height=220, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig, use_container_width=True)

                # --- ROW 4: RISK ASSESSMENT ---
                st.markdown("---")
                st.write("🛡️ **RISK_ASSESSMENT_SYSTEM**")
                
                # Altman Z-Score Safe Calculation
                t_assets = info.get('totalAssets', 1) or 1
                t_debt = info.get('totalDebt', 1) or 1
                z = (1.2 * (info.get('workingCapital',0)/t_assets)) + (3.3 * (info.get('ebitda',0)/t_assets)) + (0.6 * (info.get('marketCap',0)/t_debt))
                
                z_color = "#ccff00" if z > 2.9 else "#ffcc00" if z > 1.8 else "#ff4b4b"
                
                rc1, rc2, rc3 = st.columns(3)
                rc1.metric("Current Ratio", f"{cr:.2f}x", delta="Healthy" if cr > 1.5 else "Weak")
                rc2.metric("Debt to Equity", f"{der:.1f}%", delta="High Risk" if der > 150 else "Safe", delta_color="inverse")
                
                with rc3:
                    st.markdown(f"""
                        <div style="background:{z_color}22; border:1px solid {z_color}; padding:5px 15px; border-radius:10px; text-align:center;">
                            <p style="margin:0; font-size:10px; color:{z_color};">ALTMAN Z-SCORE</p>
                            <h3 style="margin:0; color:{z_color};">{z:.2f}</h3>
                        </div>
                    """, unsafe_allow_html=True)

                # --- ROW 5: SMART_INSIGHTS & VERDICT ---
                st.markdown("<br>", unsafe_allow_html=True)
                with st.expander("💡 SYSTEM_GENERATED_INSIGHTS", expanded=True):
                    ins = []
                    if current_price < graham: ins.append("✅ PRICE_ACTION: Trading below Graham Value.")
                    if roe > 15: ins.append("✅ EFFICIENCY: High ROE Detected.")
                    if z < 1.8: ins.append("🚨 RISK: Low Altman Z-Score (Distress).")
                    if der > 150: ins.append("⚠️ DEBT: High leverage detected.")
                    st.code("\n".join(ins) if ins else "ANALYSIS_COMPLETE: No alerts.")

                    st.markdown("---")
                    if current_price < graham and roe > 12 and z > 1.8:
                        st.success("🟢 VERDICT: POTENTIAL_INVESTMENT")
                    elif z < 1.1:
                        st.error("🔴 VERDICT: HIGH_RISK_SURVIVAL")
                    else:
                        st.warning("🟡 VERDICT: NEUTRAL_WATCHLIST")

            except Exception as e:
                st.error(f"SYSTEM_FAILURE: {e}")

elif menu == "TICKER COMPARISON":
    st.title("⚔️ TICKER_BATTLE_STATION")
    st.markdown("---")

    # 1. Input Dua Ticker
    col_in1, col_in2 = st.columns(2)
    with col_in1:
        tk1 = st.text_input("PRIMARY_TICKER", value="BBCA").upper().strip()
    with col_in2:
        tk2 = st.text_input("RIVAL_TICKER", value="BBRI").upper().strip()

    full_tk1 = f"{tk1}.JK" if not tk1.endswith(".JK") else tk1
    full_tk2 = f"{tk2}.JK" if not tk2.endswith(".JK") else tk2

    if st.button("🚀 EXECUTE_COMPARISON", width="stretch"):
        with st.spinner("CALCULATING_BATTLE_METRICS..."):
            try:
                # Ambil Data Ticker 1 & 2
                s1, s2 = yf.Ticker(full_tk1), yf.Ticker(full_tk2)
                i1, i2 = s1.info, s2.info

                # Helper function untuk ambil data aman
                get_val = lambda d, k: d.get(k, 0) or 0

                # --- HEADER BATTLE ---
                st.markdown(f"""
                    <div style="display: flex; justify-content: space-around; align-items: center; background: rgba(255,255,255,0.02); padding: 20px; border-radius: 15px; border: 1px solid #00ffff44;">
                        <div style="text-align: center;">
                            <h1 style="margin:0; color:#00ffff;">{tk1}</h1>
                            <p style="margin:0; color:#888;">{i1.get('shortName', '')}</p>
                        </div>
                        <h2 style="color: #ff4b4b; font-family: Orbitron;">VS</h2>
                        <div style="text-align: center;">
                            <h1 style="margin:0; color:#ccff00;">{tk2}</h1>
                            <p style="margin:0; color:#888;">{i2.get('shortName', '')}</p>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)

                # --- COMPARISON TABLE ---
                comparison_data = {
                    "METRIC": [
                        "Current Price", "Market Cap (T)", "PE Ratio", "PBV Ratio", 
                        "ROE (%)", "DER (%)", "Div. Yield (%)", "Net Profit Margin (%)"
                    ],
                    tk1: [
                        f"Rp {get_val(i1, 'currentPrice'):,.0f}",
                        f"{get_val(i1, 'marketCap')/1e12:.2f}T",
                        f"{get_val(i1, 'trailingPE'):,.2f}x",
                        f"{get_val(i1, 'priceToBook'):,.2f}x",
                        f"{get_val(i1, 'returnOnEquity')*100:.2f}%",
                        f"{get_val(i1, 'debtToEquity'):,.2f}%",
                        f"{get_val(i1, 'dividendYield')*100:.2f}%",
                        f"{get_val(i1, 'profitMargins')*100:.2f}%"
                    ],
                    tk2: [
                        f"Rp {get_val(i2, 'currentPrice'):,.0f}",
                        f"{get_val(i2, 'marketCap')/1e12:.2f}T",
                        f"{get_val(i2, 'trailingPE'):,.2f}x",
                        f"{get_val(i2, 'priceToBook'):,.2f}x",
                        f"{get_val(i2, 'returnOnEquity')*100:.2f}%",
                        f"{get_val(i2, 'debtToEquity'):,.2f}%",
                        f"{get_val(i2, 'dividendYield')*100:.2f}%",
                        f"{get_val(i2, 'profitMargins')*100:.2f}%"
                    ]
                }

                df_compare = pd.DataFrame(comparison_data)
                st.table(df_compare.set_index("METRIC"))

                # --- VISUAL GROWTH BATTLE (Revenue LTM) ---
                st.subheader("📊 REVENUE_BATTLE (LTM)")
                rev1 = get_val(i1, 'totalRevenue') / 1e12
                rev2 = get_val(i2, 'totalRevenue') / 1e12
                
                fig_battle = go.Figure()
                fig_battle.add_trace(go.Bar(
                    y=[tk1, tk2], x=[rev1, rev2], orientation='h',
                    marker_color=['#00ffff', '#ccff00'],
                    text=[f"{rev1:.2f}T", f"{rev2:.2f}T"], textposition='auto'
                ))
                fig_battle.update_layout(
                    template="plotly_dark", height=200, 
                    margin=dict(l=0,r=0,t=0,b=0),
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig_battle, use_container_width=True)

                # --- WINNER DETERMINATION ---
                st.markdown("---")
                score1 = 0
                if get_val(i1, 'trailingPE') < get_val(i2, 'trailingPE'): score1 += 1
                if get_val(i1, 'returnOnEquity') > get_val(i2, 'returnOnEquity'): score1 += 1
                if get_val(i1, 'dividendYield') > get_val(i2, 'dividendYield'): score1 += 1

                winner = tk1 if score1 >= 2 else tk2
                st.info(f"💡 **TERMINAL_ADVICE**: Berdasarkan metrik inti, **{winner}** menunjukkan posisi statistik yang lebih kuat dalam duel ini.")

            except Exception as e:
                st.error(f"BATTLE_FAILED: {e}")

elif menu == "MARKET_NEWS":
    st.title("📰 FINANCIAL_INTELLIGENCE_FEED")
    st.markdown("---")
    
    import feedparser
    from datetime import datetime

    # Tab untuk filter berita
    t_gen, t_spec = st.tabs(["🌐 GENERAL MARKET", "🔍 SPECIFIC TICKER"])

    with t_gen:
        st.subheader("Top Business Stories (CNBC/Kontan/Bisnis)")
        # RSS Feed Google News untuk Market Indonesia
        rss_url = "https://news.google.com/rss/search?q=saham+indonesia+ihsg&hl=id&gl=ID&ceid=ID:id"
        
        with st.spinner("FETCHING_LATEST_INTELLIGENCE..."):
            feed = feedparser.parse(rss_url)
            for entry in feed.entries[:10]:  # Ambil 10 berita terbaru
                with st.container():
                    col_icon, col_txt = st.columns([0.5, 9.5])
                    col_icon.markdown("📡")
                    with col_txt:
                        st.markdown(f"**[{entry.title}]({entry.link})**")
                        st.caption(f"Source: {entry.source.get('title', 'Unknown')} | Published: {entry.published}")
                    st.markdown("---")

    with t_spec:
        search_t = st.text_input("ENTER_TICKER_FOR_NEWS", value="BBCA").upper().strip()
        if search_t:
            st.subheader(f"Latest Intelligence: {search_t}")
            rss_url_spec = f"https://news.google.com/rss/search?q={search_t}+saham&hl=id&gl=ID&ceid=ID:id"
            
            feed_spec = feedparser.parse(rss_url_spec)
            if not feed_spec.entries:
                st.warning("No specific news found for this ticker.")
            else:
                for entry in feed_spec.entries[:8]:
                    st.markdown(f"🔹 **[{entry.title}]({entry.link})**")
                    st.caption(f"📅 {entry.published}")
                    st.write("")

elif menu == "MONEY MANAGEMENT":
    st.title("💰 MONEY_INTELLIGENCE")
    
    # --- PRIVACY MODE SETUP ---
    privacy_mode = st.checkbox("🕶️ PRIVACY MODE (Hide Balances)", value=False)

    def format_privacy(value, is_currency=True):
        if privacy_mode:
            return "Rp *****" if is_currency else "*****"
        return f"Rp {value:,.0f}" if is_currency else f"{value:,.0f}"

    tab1, tab2 = st.tabs(["📈 ACTIVE PORTFOLIO", "📜 TRADING HISTORY"])
    
    # --- TAB 1: ACTIVE PORTFOLIO ---
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
                        # Fungsi add_to_portfolio dipanggil di sini
                        add_to_portfolio(user_now, t_in, p_in, l_in, 0, 0)
                        st.success(f"Berhasil menambahkan {t_in.upper()}")
                        st.rerun()
                    else:
                        st.error("Isi Ticker dan Harga Beli dengan benar!")

        # Menampilkan Data Portfolio
        df_p = get_user_portfolio(user_now, role)
        if not df_p.empty:
            # Ambil harga live
            tickers_jk = [f"{t}.JK" for t in df_p['ticker'].unique()]
            try:
                live_data = yf.download(tickers_jk, period="1d", progress=False)['Close']
                if len(tickers_jk) > 1:
                    live_prices = live_data.iloc[-1].to_dict()
                else:
                    live_prices = {tickers_jk[0]: live_data.iloc[-1]}
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
            
            # Metrics
            m1, m2, m3 = st.columns(3)
            t_inv = df_p['Cost'].sum()
            t_pl = df_p['P/L'].sum()
            m1.metric("INVESTMENT", format_privacy(t_inv))
            m2.metric("FLOATING P/L", format_privacy(t_pl), f"{(t_pl/t_inv*100 if t_inv!=0 else 0):.2f}%")
            m3.metric("TOTAL VALUE", format_privacy(t_inv + t_pl))

            # Chart Komposisi
            fig_pie = go.Figure(data=[go.Pie(labels=df_p['ticker'], values=df_p['Value'], hole=.3)])
            fig_pie.update_layout(template="plotly_dark", height=300, paper_bgcolor='rgba(0,0,0,0)', showlegend=True)
            st.plotly_chart(fig_pie, use_container_width=True)

            # Tabel (Privacy Mode aware)
            df_display = df_p.copy()
            if privacy_mode:
                for col in ['buy_price', 'Live', 'Cost', 'Value', 'P/L']:
                    df_display[col] = "*****"
            
            st.dataframe(df_display.drop(columns=['username','tp_price','cl_price']), use_container_width=True, hide_index=True)
            
            # Tombol Jual
            # Loop Tampilan Portfolio
        for i, row in df_p.iterrows():
            with st.expander(f"📦 MANAGE {row['ticker']} ({row['lots']} Lot)"):
                # Baris Input
                c1, c2, c3 = st.columns([2, 2, 0.5])
                
                # Input Harga Jual
                s_p = c1.number_input("Harga Jual", value=float(row['Live']), key=f"sp_{row['id']}")
                
                # Input Jumlah Lot yang mau dijual
                s_q = c2.number_input("Lot Dijual", min_value=1, max_value=int(row['lots']), value=int(row['lots']), key=f"sq_{row['id']}")
                
                # Tombol Hapus Data Manual
                if c3.button("🗑️", key=f"del_{row['id']}"):
                    with sqlite3.connect('users.db') as conn:
                        conn.execute("DELETE FROM portfolio WHERE id=?", (row['id'],))
                    st.rerun()

                # Tombol Eksekusi
                if st.button(f"🚀 JUAL {s_q} LOT {row['ticker']}", key=f"btn_{row['id']}", use_container_width=True):
                    # Panggil fungsi yang kita buat di atas
                    sell_position(user_now, row['id'], row['ticker'], row['buy_price'], s_p, s_q, row['lots'])
                    st.success(f"Berhasil! {s_q} Lot {row['ticker']} terjual.")
                    st.rerun()
                
                # Tombol Hapus (Icon Sampah)
                if c3.button("🗑️", key=f"btn_del_port_{row['id']}", use_container_width=True):
                    with sqlite3.connect('users.db') as conn:
                        conn.execute("DELETE FROM portfolio WHERE id=?", (row['id'],))
                    st.rerun()

                # Tombol Eksekusi Jual
                btn_label = f"🚀 SELL {s_qty} LOT" if s_qty < row['lots'] else f"🔥 CLOSE POSITION"
                if st.button(btn_label, key=f"btn_sell_{row['id']}", use_container_width=True):
                    # Memanggil fungsi yang sudah diupdate di atas
                    def sell_position(user_id, portfolio_id, ticker, buy_price, sell_price, sell_qty, current_lots):
    import sqlite3
    from datetime import datetime
    
    # Gunakan nama tabel baru 'history_v3' untuk menghindari error kolom yang lama
    with sqlite3.connect('users.db') as conn:
        cursor = conn.cursor()
        
        # Buat tabel baru yang pasti punya kolom 'lots' dan 'profit'
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS history_v3 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                ticker TEXT,
                buy_price REAL,
                sell_price REAL,
                lots INTEGER,
                profit REAL,
                date TEXT
            )
        """)
        
        # Kalkulasi P/L
        profit = (float(sell_price) - float(buy_price)) * int(sell_qty) * 100
        date_sell = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Simpan ke history baru
        cursor.execute("""
            INSERT INTO history_v3 (user_id, ticker, buy_price, sell_price, lots, profit, date) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, ticker, buy_price, sell_price, int(sell_qty), profit, date_sell))
        
        # LOGIKA POTONG LOT:
        if int(sell_qty) < int(current_lots):
            # Jika jual sebagian, kurangi angka di kolom lots
            cursor.execute("UPDATE portfolio SET lots = lots - ? WHERE id = ?", (int(sell_qty), portfolio_id))
        else:
            # Jika jual semua, hapus barisnya
            cursor.execute("DELETE FROM portfolio WHERE id = ?", (portfolio_id,))
        
        conn.commit()

    # --- TAB 2: TRADING HISTORY ---
    with tab2:
        st.subheader("📜 TRANSACTION_LOG")
        with sqlite3.connect('users.db') as conn:
            df_h = pd.read_sql_query("SELECT * FROM history WHERE username=? ORDER BY date DESC", conn, params=(user_now,))
        
        if not df_h.empty:
            df_h['date'] = pd.to_datetime(df_h['date'])
            
            # Stats History
            total_profit = df_h[df_h['pnl'] > 0]['pnl'].sum()
            total_loss = df_h[df_h['pnl'] <= 0]['pnl'].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("PROFIT", format_privacy(total_profit))
            c2.metric("LOSS", format_privacy(total_loss), delta_color="inverse")
            c3.metric("NET", format_privacy(total_profit + total_loss))

            # Equity Curve
            df_curve = df_h.sort_values('date')
            df_curve['cum_pnl'] = df_curve['pnl'].cumsum()
            fig_curve = go.Figure(go.Scatter(x=df_curve['date'], y=df_curve['cum_pnl'], mode='lines+markers', line=dict(color='#ccff00')))
            fig_curve.update_layout(template="plotly_dark", height=250, paper_bgcolor='rgba(0,0,0,0)', 
                                    yaxis=dict(showticklabels=not privacy_mode))
            st.plotly_chart(fig_curve, use_container_width=True)

            # List History dengan Tombol Hapus
            for idx, h_row in df_h.iterrows():
                with st.expander(f"{h_row['date'].strftime('%Y-%m-%d')} | {h_row['ticker']} | {format_privacy(h_row['pnl'])}"):
                    col_txt, col_btn = st.columns([4,1])
                    col_txt.write(f"Beli: {format_privacy(h_row['buy_price'])} | Jual: {format_privacy(h_row['sell_price'])} | Vol: {h_row['lots']} Lot")
                    if col_btn.button("🗑️ Hapus", key=f"del_h_{h_row['id']}"):
                        with sqlite3.connect('users.db') as conn:
                            conn.execute("DELETE FROM history WHERE id=?", (h_row['id'],))
                        st.rerun()
        else:
            st.info("Belum ada riwayat transaksi.")
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

# ... kode menu-menu sebelumnya ...

elif menu == "SECURITY SETTINGS":
    st.title("🔐 SECURITY_PROTOCOL")
    # (isi kode security settings Anda)

# --- TAMBAHKAN DI SINI ---
elif menu == "FUNDAMENTAL ANALYZER":
    st.title("📊 FUNDAMENTAL_INTELLIGENCE")
    t_input = st.text_input("INPUT TICKER", "BBCA").upper()
    if st.button("RUN ANALYSIS"):
        try:
            with st.spinner("FETCHING DATA..."):
                stock = yf.Ticker(f"{t_input}.JK")
                info = stock.info
                
                # Menampilkan Nama Perusahaan agar lebih informatif
                st.subheader(info.get('longName', t_input))
                
                c1, c2, c3 = st.columns(3)
                c1.metric("PBV", f"{info.get('priceToBook', 0):.2f}x")
                c2.metric("PER", f"{info.get('trailingPE', 0):.2f}x")
                
                # ROE biasanya dalam desimal, jadi dikali 100 untuk persen
                roe = info.get('returnOnEquity', 0)
                c3.metric("ROE", f"{roe*100:.2f}%" if roe else "N/A")
                
                st.success(f"Data fundamental {t_input} berhasil ditarik.")
        except Exception as e:
            st.error(f"Gagal mengambil data: {e}")

