import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import sqlite3
import time
import warnings
import os
import requests 
import pytz 


def get_trend_signals(ticker_list):
    signals = []
    for ticker in ticker_list:
        try:
            # Ambil data 6 bulan terakhir
            df = yf.download(f"{ticker}.JK", period="6mo", interval="1d", progress=False)
            if df.empty: continue
            
            # Hitung MA 20 dan MA 50
            df['MA20'] = ta.sma(df['Close'], length=20)
            df['MA50'] = ta.sma(df['Close'], length=50)
            
            # Ambil nilai terakhir dan sebelumnya
            last_ma20 = df['MA20'].iloc[-1]
            last_ma50 = df['MA50'].iloc[-1]
            prev_ma20 = df['MA20'].iloc[-2]
            prev_ma50 = df['MA50'].iloc[-2]
            
            current_price = df['Close'].iloc[-1]
            
            # Logika Golden Cross: MA20 memotong ke atas MA50
            if prev_ma20 < prev_ma50 and last_ma20 > last_ma50:
                signals.append({"ticker": ticker, "status": "GOLDEN CROSS", "price": current_price, "color": "#00ff00"})
            
            # Logika Dead Cross: MA20 memotong ke bawah MA50
            elif prev_ma20 > prev_ma50 and last_ma20 < last_ma50:
                signals.append({"ticker": ticker, "status": "DEAD CROSS", "price": current_price, "color": "#ff0000"})
                
        except:
            continue
    return signals




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

def sell_position(u, row_id, ticker, buy_p, sell_p, total_lots, sold_lots):
    pnl = (sell_p - buy_p) * sold_lots * 100
    with sqlite3.connect('users.db') as conn:
        # 1. Catat ke History
        conn.execute("INSERT INTO history (username, ticker, buy_price, sell_price, lots, pnl, date) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (u, ticker, buy_p, sell_p, sold_lots, pnl, datetime.now().strftime("%Y-%m-%d")))
        
        # 2. Update atau Hapus di Portfolio
        remaining_lots = total_lots - sold_lots
        if remaining_lots > 0:
            # Jika masih ada sisa, update jumlah lot
            conn.execute("UPDATE portfolio SET lots = ? WHERE id = ?", (remaining_lots, row_id))
            return f"✅ PARTIAL_SELL: {sold_lots} Lots of {ticker} Sold!"
        else:
            # Jika habis, hapus dari portfolio
            conn.execute("DELETE FROM portfolio WHERE id = ?", (row_id,))
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

# --- 1. PRO CYBER STYLING (ULTIMATE UPGRADE) ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Orbitron:wght@400;700;900&display=swap');

/* ===== BACKGROUND & BASE ===== */
.stApp {
    background: radial-gradient(circle at center, #0a1321, #05070a);
    background-attachment: fixed;
    font-family: 'JetBrains Mono', monospace;
    color: #e0e0e0;
}

/* ===== HEADER CLEAN ===== */
header {background: transparent !important;}
[data-testid="stHeaderActionElements"], .stDeployButton, #MainMenu {
    display: none !important;
}

/* ===== TITLE & TEXT ===== */
h1 {
    font-family: 'Orbitron', sans-serif;
    font-weight: 900;
    background: linear-gradient(90deg, #ccff00, #00ffff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-transform: uppercase;
    letter-spacing: 3px;
}
h2, h3 { color: #00ffff; font-family: 'Orbitron', sans-serif; }

/* ===== LOGIN SCREEN CUSTOM ===== */
/* Kotak Form Login */
div[data-testid="stForm"] {
    border: 2px solid rgba(0, 255, 255, 0.2) !important;
    box-shadow: 0 0 20px rgba(0, 255, 255, 0.05);
    background: rgba(10, 20, 30, 0.8) !important;
    padding: 30px !important;
}

/* Label Input (ID / PASSWORD) */
div[data-testid="stForm"] label p {
    font-family: 'Orbitron', sans-serif !important;
    color: #ccff00 !important;
    font-size: 0.8rem !important;
    letter-spacing: 2px;
}

/* Kotak Input Login */
div[data-testid="stForm"] input {
    background: rgba(0, 0, 0, 0.5) !important;
    border: 1px solid rgba(0, 255, 255, 0.3) !important;
    color: #00ffff !important;
    font-family: 'JetBrains Mono', monospace !important;
    height: 45px;
}
div[data-testid="stForm"] input:focus {
    border-color: #ccff00 !important;
    box-shadow: 0 0 10px rgba(204, 255, 0, 0.2);
}

/* ===== SIDEBAR MENU ===== */
[data-testid="stSidebar"] {
    background: rgba(5, 12, 25, 0.98);
    border-right: 1px solid rgba(0,255,255,0.1);
}

/* Menu Radio Button */
div[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(0, 255, 255, 0.05);
    margin-bottom: 8px;
    border-radius: 8px;
    padding: 12px !important;
    transition: 0.3s ease;
    display: flex !important; /* Tambahan agar teks sejajar */
}

div[data-testid="stSidebar"] .stRadio label p {
    font-family: 'Orbitron', sans-serif !important;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    font-size: 0.8rem !important;
    color: #666 !important;
    display: block !important; /* Tambahan agar teks TIDAK HILANG */
    opacity: 1 !important;    /* Tambahan agar teks terlihat jelas */
}

/* Menu Active */
div[data-testid="stSidebar"] .stRadio div[role="radiogroup"] [aria-checked="true"] {
    background: rgba(0, 255, 255, 0.1) !important;
    border: 1px solid #ccff00 !important; /* Ganti ke Neon Lime */
}

div[data-testid="stSidebar"] .stRadio div[role="radiogroup"] [aria-checked="true"] p {
    color: #ccff00 !important; /* Ganti ke Neon Lime */
    text-shadow: 0 0 8px rgba(204, 255, 0, 0.8);
}

/* Hilangkan Dot Radio */
/* Gunakan selektor spesifik agar hanya bulatan yang hilang, teks tetap ada */
div[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label div:first-child {
    display: none !important;
}

/* ===== UNIVERSAL COMPONENT ===== */
div[data-testid="stMetric"], .stDataFrame, .stTabs, div[data-testid="stExpander"] {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(0,255,255,0.15) !important;
    border-radius: 12px !important;
}

/* Button Global */
.stButton>button {
    background: linear-gradient(90deg, #00ffff, #ccff00);
    color: #000 !important;
    border-radius: 6px;
    border: none;
    font-family: 'Orbitron', sans-serif;
    font-weight: bold;
    text-transform: uppercase;
    transition: 0.3s;
}
.stButton>button:hover {
    transform: translateY(-2px);
    box-shadow: 0 5px 15px rgba(0, 255, 255, 0.4);
}

/* Scrollbar */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-thumb { background: #00ffff; border-radius: 10px; }

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
            u = st.text_input("ID").strip()
            p = st.text_input("PASSWORD", type="password")
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
        # 1. LOGIKA DETEKSI WARNA
        chg = row.get('CHG%', 0)
        chg_color = "#ccff00" if chg > 0 else "#ff4b4b"

        # 2. FIX PENAMAAN KOLOM (Seringkali beda antara TP1 vs TP 1)
        # Kita buat variabel cadangan agar jika kolom pakai spasi tetap terbaca
        val_last  = row.get('LAST', '-')
        val_entry = row.get('ENTRY', row.get('Entry', val_last)) # Default entry = last price
        val_tp1   = row.get('TP1', row.get('TP 1', '-'))
        val_tp2   = row.get('TP2', row.get('TP 2', '-'))
        val_cl    = row.get('CL', row.get('EXIT/CL', row.get('STOP LOSS', '-')))
        val_m     = row.get('VAL(M)', row.get('VALUE', 0))

        st.markdown(f"""
        <div style="background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(204, 255, 0, 0.2); 
                    border-radius: 12px; padding: 15px; margin-bottom: 12px; border-left: 5px solid {chg_color};">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <b style="font-size: 1.2rem; color: #ccff00;">{row.get('TICKER','-')}</b>
                <span style="color: {chg_color}; font-weight: bold;">
                    {chg}% {row.get('VOL_S','')}
                </span>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 10px; font-size: 0.85rem; color: #bbb;">
                <div>Last: <b style="color:#fff;">{val_last}</b></div>
                <div>Value: <b style="color:#fff;">{val_m}M</b></div>
                <div style="color: #00ffff; font-weight: bold;">Entry: {val_entry}</div>
                <div style="color: #00ff00; font-weight: bold;">TP1: {val_tp1}</div>
                <div style="color: #00ff00; font-weight: bold;">TP2: {val_tp2}</div>
                <div style="color: #ff4b4b; font-weight: bold;">CL: {val_cl}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

def run_scan(tickers, mode):
    import pandas as pd
    import yfinance as yf
    from datetime import datetime
    import streamlit as st

    # 1. Pastikan Ticker Unik (Cegah Duplikasi dari Input)
    tickers = list(set(tickers))
    results = []

    # 2. Parameter Berdasarkan Mode
    if mode == "Santai":
        min_chg, min_rsi, min_val, vol_m = 1.5, 45, 100_000_000, 1.1
    elif mode == "Profesional":
        min_chg, min_rsi, min_val, vol_m = 2.5, 55, 1_000_000_000, 1.4
    elif mode == "Pro":
        min_chg, min_rsi, min_val, vol_m = 4.0, 60, 2_000_000_000, 1.8
    else:
        min_chg, min_rsi, min_val, vol_m = 2.0, 50, 500_000_000, 1.3

    # 3. UI Progress
    progress = st.progress(0, text="📡 Menghubungkan ke Server Bursa...")
    
    # 4. Download Data sekaligus (Batch) untuk mempercepat
    try:
        data = yf.download(tickers, period="1mo", interval="1d", group_by="ticker", threads=True, progress=False)
    except Exception as e:
        st.error(f"Gagal mendownload data: {e}")
        return pd.DataFrame()

    total = len(tickers)

    # 5. Loop Analisis
    for i, t in enumerate(tickers):
        try:
            # Update Progress Bar
            percent = int((i + 1) / total * 100)
            progress.progress(percent, text=f"🔍 Menganalisis {t} ({percent}%)")

            # Ambil DataFrame per ticker
            df = data[t].copy() if len(tickers) > 1 else data.copy()
            
            # Fix Multi-Index Column
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            if df.empty or len(df) < 15: continue

            # Ambil data harga terakhir & sebelumnya
            c_now = df['Close'].iloc[-1]
            c_prev = df['Close'].iloc[-2]
            
            if pd.isna(c_now) or pd.isna(c_prev): continue

            # Kalkulasi Indikator
            chg = ((c_now - c_prev) / c_prev) * 100
            val_tr = df['Volume'].iloc[-1] * c_now
            ma20 = df['Close'].rolling(20).mean().iloc[-1]
            
            # RSI 14
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain.iloc[-1] / loss.iloc[-1] if loss.iloc[-1] != 0 else 0
            rsi = 100 - (100 / (1 + rs))

            # Breakout Logic
            high_20 = df['High'].rolling(20).max().iloc[-2]
            vol_avg = df['Volume'].rolling(20).mean().iloc[-1]
            is_breakout = (c_now > high_20) and (df['Volume'].iloc[-1] > vol_avg * vol_m)

# --- FILTER UTAMA ---
            # Jika tidak masuk kriteria minimal, lewati (Cegah Tabel Dobel/Sampah)
            if chg < min_chg or val_tr < min_val:
                continue

            # --- KALKULASI TRADING PLAN (TAMBAHAN BARU) ---
            # TP 1: Target Profit 1 (+3% dari harga sekarang)
            # TP 2: Target Profit 2 (+7% dari harga sekarang)
            # EXIT/CL: Batas Rugi (-3% dari harga sekarang)
            tp1 = int(c_now * 1.03)
            tp2 = int(c_now * 1.07)
            cl = int(c_now * 0.97)

            # Scoring AI
            score = (chg * 0.4) + (rsi * 0.2) + ((val_tr / 1e9) * 0.2) + (10 if is_breakout else 0)

            # --- PENYUSUNAN HASIL ---
            results.append({
                "TICKER": t.replace(".JK", ""),
                "LAST": int(c_now),
                "CHG%": round(chg, 2),
                "RSI": round(rsi, 1),
                "VAL(M)": round(val_tr / 1_000_000, 1),
                "AI_SCORE": round(score, 2),
                "BREAKOUT": "YES" if is_breakout else "NO",
                "REKOMENDASI": "🚀 BSJP" if chg > 4 else "💎 HOLD" if c_now > ma20 else "🔎 WATCH",
                
                # Masukkan data TP & CL ke list
                "TP 1": tp1,
                "TP 2": tp2,
                "EXIT/CL": cl,
                
                "FULL": t
            })
        except:
            continue

    progress.empty() # Hilangkan progress bar setelah selesai

    # 6. Return DataFrame Final (Hanya 1 Tabel Bersih)
    df_result = pd.DataFrame(results)
    if not df_result.empty:
        return df_result.sort_values(by="AI_SCORE", ascending=False).drop_duplicates(subset=['TICKER'])
    
    return pd.DataFrame()

# --- 4. NAVIGATION ---
role = st.session_state["auth"]["role"]
user_now = st.session_state["auth"]["user"]
last_l, ip_l, loc_l = get_sidebar_log(user_now)

# CSS KHUSUS UNTUK MEMUNCULKAN TEKS & WARNA NEON LIME
st.sidebar.markdown("""
<style>
    /* 1. Judul COMMAND CENTER */
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
        color: #ccff00 !important;
        font-family: 'Orbitron', sans-serif !important;
        text-transform: uppercase;
        letter-spacing: 2px;
        font-weight: bold;
    }

    /* 2. Kotak Menu Radio */
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(0, 255, 255, 0.1) !important;
        border-radius: 8px !important;
        padding: 10px 15px !important;
        margin-bottom: 8px !important;
        display: flex !important;
        align-items: center !important;
        min-height: 45px !important;
    }

    /* 3. MEMAKSA TEKS MENU MUNCUL JELAS */
    /* Kita targetkan div pembungkus teksnya langsung */
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p {
        color: #888888 !important; /* Warna abu-abu saat tidak dipilih */
        font-family: 'Orbitron', sans-serif !important;
        font-size: 0.85rem !important;
        text-transform: uppercase !important;
        margin-left: 0px !important;
        visibility: visible !important;
        display: block !important;
    }

    /* 4. WARNA AKTIF (NEON LIME) */
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:has(input:checked) {
        border: 1px solid #ccff00 !important;
        background: rgba(204, 255, 0, 0.1) !important;
        box-shadow: 0 0 10px rgba(204, 255, 0, 0.2);
    }

    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p {
        color: #ccff00 !important; /* Teks jadi Hijau Neon */
        text-shadow: 0 0 8px rgba(204, 255, 0, 0.8) !important;
        font-weight: bold !important;
    }

    /* 5. SEMBUNYIKAN HANYA BULATANNYA (Bukan Teksnya) */
    /* Cara paling aman: buat ukurannya 0 agar tidak memakan tempat */
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label > div:first-child {
        width: 0px !important;
        height: 0px !important;
        margin: 0px !important;
        padding: 0px !important;
        visibility: hidden !important;
    }
</style>
""", unsafe_allow_html=True)

# Profile Card di Sidebar
st.sidebar.markdown(f"""
    <div style='padding:15px; border:1px solid #ccff0033; border-radius:10px; background:rgba(204,255,0,0.05); margin-bottom:10px;'>
        <h3 style='margin:0; color:#ccff00; font-family:Orbitron;'>{user_now.upper()}</h3>
        <p style='margin:0; font-size:10px; color:#888;'>NODE ACTIVE | {role.upper()}</p>
        <hr style='border:0.1px solid #ccff0022; margin:10px 0;'>
        <p style='font-size:10px; color:#888;'>LST: {last_l}</p>
        <p style='font-size:10px; color:#888;'>IP : {ip_l}</p>
        <p style='font-size:10px; color:#888;'>LOC: {loc_l}</p>
    </div>
    """, unsafe_allow_html=True)

# List Menu
menu_list = ["SCANNER", "STRATEGY SCANNER", "FUNDAMENTAL", "MARKET_NEWS", "SECURITY SETTINGS"]
if role == "admin": 
    menu_list.insert(1, "USER MANAGEMENT")

# Panggil Radio Button (Gunakan label kosong "" agar judul COMMAND CENTER tidak double)
########st.sidebar.markdown("<p style='color:#ccff00; font-weight:bold; letter-spacing:2px; margin-bottom:-15px;'>COMMAND CENTER</p>", unsafe_allow_html=True)
menu = st.sidebar.radio("Menu", menu_list, label_visibility="collapsed")

st.sidebar.write("---")
if st.sidebar.button("🔴 TERMINATE SESSION", use_container_width=True):
    st.session_state["auth"] = {"logged_in": False}
    st.rerun()

# --- 5. CONTENT AREA: SCANNER ---
if menu == "SCANNER":
    st.title("🛰️ MARKET_INTELLIGENCE")
    st.info("📊 Scan optimal saat jam market (09:00 - 15:00 WIB)")

    # 1. INISIALISASI SESSION STATE
    if 'results' not in st.session_state:
        st.session_state.results = None
    if 'scan_time' not in st.session_state:
        st.session_state.scan_time = "Ready"

    # 🔍 LOAD TICKERS
    tickers = load_tickers()
    
    # =========================
    # 1. IHSG MONITOR
    # =========================
    try:
        ihsg_hist = yf.Ticker("^JKSE").history(period="2d")
        if len(ihsg_hist) >= 2:
            curr_c = ihsg_hist['Close'].iloc[-1]
            diff = curr_c - ihsg_hist['Close'].iloc[-2]
            clr = "#ccff00" if diff >= 0 else "#ff4b4b"
            st.markdown(f"""
                <div style='border-left: 5px solid {clr}; padding:10px; background:rgba(255,255,255,0.05); margin-bottom:20px;'>
                    IHSG: <span style='color:{clr}; font-weight:bold;'>{curr_c:,.2f} ({diff:+.2f})</span>
                </div>
            """, unsafe_allow_html=True)
    except:
        pass

    # =========================
    # 2. CONTROL PANEL
    # =========================
    c1, c2 = st.columns([4,1])
    with c1:
        mode_scan = st.radio("ALGO_SENSITIVITY", ["Santai", "Profesional", "Pro"], horizontal=True, key="ms_main")
    with c2:
        if st.button("🔄 REFRESH", use_container_width=True):
            st.rerun()

    # =========================
    # 3. BUTTON SCAN
    # =========================
    if st.button("⚡ EXECUTE_DEEP_SCAN", use_container_width=True):
        res = run_scan(tickers, mode_scan)
        if res is not None and not res.empty:
            st.session_state.results = res
            st.session_state.scan_time = datetime.now().strftime("%H:%M:%S")
            st.rerun()
        else:
            st.warning("Scan selesai, tapi tidak ada saham yang lolos filter.")

    # =========================
    # 4. HASIL ANALISIS (PROTECTED BLOCK)
    # =========================
    if st.session_state.results is not None:
        df = st.session_state.results
        
        # --- AI STATUS HEADER ---
        st.markdown(f"""
        <div style='background: rgba(0,255,0,0.05); padding:15px; border-left:5px solid #00ff00; margin-bottom:20px; border-radius:0 10px 10px 0;'>
            <span style='color:#00ff00; font-weight:bold;'>🧠 AI STATUS: SCAN COMPLETE</span><br>
            <span style='font-size:12px; color:#888;'>⏱ TIME: {st.session_state.scan_time} | 📊 DATA: {len(df)} STOCKS ANALYZED</span>
        </div>
        """, unsafe_allow_html=True)

        if df.empty:
            st.warning("⚠️ Tidak ada saham lolos filter (coba mode Santai / jam market)")
        else:
            # --- AI SCORING CALCULATION ---
            for col in ['CHG%', 'RSI', 'VAL(M)']:
                if col not in df.columns: df[col] = 0
            
            df['AI_SCORE'] = (df['CHG%'] * 0.4 + df['RSI'] * 0.3 + (df['VAL(M)']/100) * 0.3)

            # --- AI TOP PICKS & BREAKOUT ---
            col_picks, col_bo = st.columns(2)
            with col_picks:
                st.markdown("### 🧠 AI TOP PICKS")
                top3 = df.sort_values(by='AI_SCORE', ascending=False).head(3)
                st.dataframe(top3[['TICKER', 'LAST', 'AI_SCORE']], use_container_width=True, hide_index=True)
            
            with col_bo:
                st.markdown("### 🔥 BREAKOUT")
                if 'BREAKOUT' in df.columns:
                    df_bo = df[df['BREAKOUT'] == "YES"].head(3)
                    if not df_bo.empty:
                        st.dataframe(df_bo[['TICKER', 'LAST', 'CHG%']], use_container_width=True, hide_index=True)
                    else:
                        st.info("No breakout")

            # --- STRATEGY INSIGHT (METRICS) ---
            st.markdown("### 🌟 STRATEGY_INSIGHT")
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("<p style='color:#ccff00; font-weight:bold;'>🚀 TOP BUY</p>", unsafe_allow_html=True)
                df_buy = df[df['REKOMENDASI'].str.contains("BUY|BSJP", na=False)].head(3)
                if not df_buy.empty:
                    m_cols = st.columns(len(df_buy))
                    for idx, (_, r) in enumerate(df_buy.iterrows()):
                        m_cols[idx].metric(r['TICKER'], int(r['LAST']), f"{r['CHG%']}%")
                else: st.info("No strong buy")

            with col_b:
                st.markdown("<p style='color:#00ffff; font-weight:bold;'>💎 TOP HOLD</p>", unsafe_allow_html=True)
                df_hold = df[df['REKOMENDASI'].str.contains("HOLD", na=False)].head(3)
                if not df_hold.empty:
                    m_cols = st.columns(len(df_hold))
                    for idx, (_, r) in enumerate(df_hold.iterrows()):
                        m_cols[idx].metric(r['TICKER'], int(r['LAST']), f"RSI {r['RSI']}")
                else: st.info("No hold trend")

            # --- VIEW TABS ---
            st.markdown("---")
            tab1, tab2, tab3 = st.tabs(["🖥️ DESKTOP", "📱 MOBILE", "📈 CHART"])

            with tab1:
                st.dataframe(df.drop(columns=['FULL'], errors='ignore'), use_container_width=True, hide_index=True)

            with tab2:
                draw_mobile_cards(df)

            with tab3:
                st.markdown("### 📈 FOCUS_TARGET_ANALYSIS")
                sel_t = st.selectbox("PILIH SAHAM", df['TICKER'].tolist())
                full_t = df[df['TICKER'] == sel_t]['FULL'].values[0]
                c_data = yf.download(full_t, period="6mo", interval="1d", progress=False)
                if not c_data.empty:
                    c_data.columns = [c[0] if isinstance(c, tuple) else c for c in c_data.columns]
                    fig = go.Figure(data=[go.Candlestick(
                        x=c_data.index, open=c_data['Open'], high=c_data['High'],
                        low=c_data['Low'], close=c_data['Close']
                    )])
                    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False)
                    st.plotly_chart(fig, use_container_width=True)

elif menu == "STRATEGY SCANNER":
    st.markdown("<h2 style='color:#ccff00;'>⚡ AUTOMATIC STRATEGY SCANNER</h2>", unsafe_allow_html=True)
    st.write("Sistem ini mendeteksi perpotongan Moving Average (MA20 vs MA50) secara Real-Time.")
    
    # Daftar saham yang mau dipantau (Bisa kamu tambah sendiri)
    watchlist = ["BBCA", "BBRI", "BMRI", "ASII", "TLKM", "GOTO", "ADRO", "UNVR", "AMMN", "BBNI"]
    
    if st.button("🚀 MULAI SCANNING SEKARANG"):
        with st.spinner("Sedang menganalisa chart..."):
            results = get_trend_signals(watchlist)
            
            if results:
                for res in results:
                    st.markdown(f"""
                    <div style="border: 1px solid {res['color']}; padding: 15px; border-radius: 10px; margin-bottom: 10px;">
                        <h3 style="color:{res['color']}; margin:0;">{res['status']} Detected!</h3>
                        <p style="margin:5px 0;">Saham: <b>{res['ticker']}</b> | Harga: Rp {res['price']:,.0f}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                if any(r['status'] == "GOLDEN CROSS" for r in results):
                    st.balloons()
            else:
                st.info("Belum ada sinyal Golden Cross atau Dead Cross hari ini pada Watchlist kamu.")
    
    st.caption("Tips: Golden Cross sering dianggap sebagai awal dari tren naik jangka panjang.")


elif menu == "FUNDAMENTAL":
    st.markdown("""
        <style>
        /* Mengubah warna Metric agar senada dengan Neon Lime */
        [data-testid="stMetricSimpleValue"] {
            color: #ccff00 !important;
        }
        .stMetric {
            background: rgba(204, 255, 0, 0.03) !important;
            border-radius: 10px !important;
            border: 1px solid rgba(204, 255, 0, 0.1) !important;
            border-left: 5px solid #ccff00 !important; /* Aksen garis di kiri */
        }
        /* Menghaluskan tampilan Expander */
        .streamlit-expanderHeader {
            color: #ccff00 !important;
            background-color: transparent !important;
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
                # Menggunakan threads=True agar lebih cepat untuk banyak ticker
                live_data = yf.download(tickers_jk, period="1d", progress=False, threads=True)['Close']
                if len(tickers_jk) > 1:
                    live_prices = live_data.iloc[-1].to_dict()
                else:
                    live_prices = {tickers_jk[0]: live_data.iloc[-1]}
            except:
                live_prices = {}

            def calc_active(row):
                tk = f"{row['ticker']}.JK"
                # Fallback ke buy_price jika harga live gagal fetch
                curr = live_prices.get(tk, row['buy_price'])
                if isinstance(curr, (pd.Series, pd.DataFrame)): 
                    curr = curr.iloc[-1] if not curr.empty else row['buy_price']
                
                cost = float(row['buy_price'] * row['lots'] * 100)
                val = float(curr * row['lots'] * 100)
                return pd.Series([float(curr), cost, val, (val-cost)])

            df_p[['Live', 'Cost', 'Value', 'P/L']] = df_p.apply(calc_active, axis=1)
            
            # Metrics (Top Row)
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

            # Tabel Ringkasan
            df_display = df_p.copy()
            if privacy_mode:
                for col in ['buy_price', 'Live', 'Cost', 'Value', 'P/L']:
                    df_display[col] = "*****"
            
            st.dataframe(df_display.drop(columns=['username','tp_price','cl_price']), use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.subheader("🛠️ POSITION MANAGER")
            
            # Fitur Jual (PARTIAL SELL SUPPORT)
            for i, row in df_p.iterrows():
                with st.expander(f"📦 {row['ticker']} | {int(row['lots'])} Lots Available"):
                    c_price, c_lots, c_btn = st.columns([2, 2, 1])
                    
                    # 1. Input Harga Jual
                    s_price = c_price.number_input(f"Sell Price", value=float(row['Live']), key=f"s_prc_{row['id']}")
                    
                    # 2. Input Jumlah Lot (Maksimal sebanyak yang dimiliki)
                    s_lots = c_lots.number_input(f"Lots to Sell", min_value=1, max_value=int(row['lots']), value=int(row['lots']), key=f"s_lot_{row['id']}")
                    
                    # 3. Tombol Eksekusi
                    st.write("") # Spacer
                    if c_btn.button(f"EXECUTE SELL", key=f"btn_s_{row['id']}", use_container_width=True):
                        # Panggil fungsi sell_position dengan parameter sold_lots baru
                        msg = sell_position(user_now, row['id'], row['ticker'], row['buy_price'], s_price, row['lots'], s_lots)
                        st.toast(msg) # Notifikasi kecil di pojok
                        time.sleep(1)
                        st.rerun()
                    
                    # Tombol Delete (Hapus tanpa hitung P/L)
                    if st.button(f"🗑️ Delete Data {row['ticker']}", key=f"btn_del_{row['id']}"):
                        with sqlite3.connect('users.db') as conn:
                            conn.execute("DELETE FROM portfolio WHERE id=?", (row['id'],))
                        st.rerun()
        else:
            st.info("Portfolio kosong. Mulai dengan menambahkan posisi baru!")

    # --- TAB 2: TRADING HISTORY ---
   ### with tab2:
    ##    # Implementasi Trading History kamu di sini
     #   st.subheader("📜 TRADING_LOG")
    #    with sqlite3.connect('users.db') as conn:
     #       df_hist = pd.read_sql_query("SELECT * FROM history WHERE username=?", conn, params=(user_now,))
      #      if not df_hist.empty:
      #          st.dataframe(df_hist.sort_values('date', ascending=False), use_container_width=True, hide_index=True)
      #      else:
            #    st.write("Belum ada riwayat transaksi.")

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
        new_p = st.text_input("NEW PASSWROD", type="password")
        if st.form_submit_button("UPDATE"):
            if update_password_db(user_now, new_p): st.success("Updated")

