import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import sqlite3
import warnings
import hashlib

# --- 0. CONFIG & DATABASE SETUP ---
warnings.filterwarnings("ignore", category=FutureWarning)
st.set_page_config(page_title="IDX CYBER TERMINAL PRO", page_icon="⚡", layout="wide")

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def init_db():
    with sqlite3.connect('users.db') as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users 
                     (username TEXT PRIMARY KEY, password TEXT, role TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS portfolio 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      username TEXT, ticker TEXT, buy_price REAL, 
                      lots INTEGER, date TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS history 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      username TEXT, ticker TEXT, buy_price REAL, 
                      sell_price REAL, lots INTEGER, pnl REAL, date TEXT)''')
        admin_pass = hash_password('admin123')
        c.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES ('admin', ?, 'admin')", (admin_pass,))
        conn.commit()

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

# --- 1. CYBER STYLING ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono&family=Orbitron:wght@400;700&display=swap');
    .stApp { background-color: #05070a; font-family: 'JetBrains Mono', monospace; color: #e0e0e0; }
    h1, h2, h3 { font-family: 'Orbitron', sans-serif; color: #ccff00; text-shadow: 0 0 10px #ccff0055; }
    div[data-testid="stMetric"] { background: rgba(204, 255, 0, 0.05); border: 1px solid #ccff0033; border-radius: 10px; padding: 15px; }
    .stButton>button { background-color: #ccff00; color: black; font-weight: bold; border-radius: 5px; border: none; }
    .stButton>button:hover { background-color: #e6ff80; color: black; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. AUTHENTICATION ---
if "auth" not in st.session_state:
    st.session_state["auth"] = {"logged_in": False, "user": None, "role": None}

if not st.session_state["auth"]["logged_in"]:
    _, col, _ = st.columns([1, 1.5, 1])
    with col:
        st.markdown("<h1 style='text-align:center;'>IDX LOGIN</h1>", unsafe_allow_html=True)
        u_in = st.text_input("OPERATOR ID")
        p_in = st.text_input("ACCESS KEY", type="password")
        if st.button("AUTHORIZE", use_container_width=True):
            hp = hash_password(p_in)
            with sqlite3.connect('users.db') as conn:
                c = conn.cursor()
                c.execute("SELECT role FROM users WHERE username=? AND password=?", (u_in, hp))
                res = c.fetchone()
            if res:
                st.session_state["auth"] = {"logged_in": True, "user": u_in, "role": res[0]}
                st.rerun()
            else: st.error("ACCESS DENIED")
    st.stop()

# --- 3. MAIN INTERFACE ---
user_now = st.session_state["auth"]["user"]
role = st.session_state["auth"]["role"]
menu = st.sidebar.radio("COMMAND CENTER", ["SCANNER PRO", "MONEY MANAGEMENT", "SECURITY"])

if st.sidebar.button("🔴 TERMINATE"):
    st.session_state["auth"] = {"logged_in": False}; st.rerun()

# --- MENU: SCANNER PRO ---
if menu == "SCANNER PRO":
    st.title("🛰️ STRATEGY_SCANNER_PRO")
    c_cfg, c_info = st.columns([1, 2])
    with c_cfg:
        min_miliar = st.number_input("Min Turnover (Miliar)", value=5.0)
        min_up = st.slider("Min Price Up (%)", 0.5, 10.0, 2.0)
    
    if st.button("🚀 EXECUTE MULTI-STRATEGY SCAN", use_container_width=True):
        # List Saham Potensial IDX (Bisa ditambah sesuai kebutuhan)
        watch = ['BBCA.JK','BBRI.JK','BMRI.JK','TLKM.JK','ASII.JK','GOTO.JK','ADRO.JK','ITMG.JK','AMRT.JK','UNTR.JK','PTBA.JK','AKRA.JK','BRIS.JK','ANTM.JK','BBNI.JK','BRMS.JK','DEWA.JK','BUMI.JK','MEDC.JK','TPIA.JK']
        results = []
        bar = st.progress(0)
        
        for idx, t in enumerate(watch):
            try:
                df = yf.download(t, period="100d", progress=False)
                if len(df) < 50: continue
                
                # Indikator Teknikal
                df['MA20'] = df['Close'].rolling(window=20).mean()
                df['MA50'] = df['Close'].rolling(window=50).mean()
                delta = df['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                df['RSI'] = 100 - (100 / (1 + (gain/loss)))
                
                # Variabel Harga
                p_now = float(df['Close'].iloc[-1])
                p_prev = float(df['Close'].iloc[-2])
                p_high = float(df['High'].iloc[-1])
                v_now = float(df['Volume'].iloc[-1])
                v_avg = float(df['Volume'].iloc[-20:-1].mean())
                ma20 = float(df['MA20'].iloc[-1])
                ma50 = float(df['MA50'].iloc[-1])
                rsi = float(df['RSI'].iloc[-1])
                turnover = (p_now * v_now) / 1_000_000_000
                change = ((p_now - p_prev) / p_prev) * 100
                
                # --- LOGIKA PENENTUAN STRATEGI ---
                action = ""
                # Syarat BSJP: Harga ditutup sangat dekat dengan High harian (>99% dari High)
                is_closing_strong = p_now >= (p_high * 0.995)
                
                # Syarat Uptrend Jangka Menengah: MA20 > MA50
                is_uptrend_strong = ma20 > ma50
                
                if is_closing_strong and is_uptrend_strong:
                    action = "🔥 SUPER SIGNAL (BSJP + HOLD)"
                elif is_closing_strong:
                    action = "🚀 BSJP (Beli Sore Jual Pagi)"
                elif is_uptrend_strong and p_now > ma20:
                    action = "💎 HOLD (Strong Uptrend)"
                else:
                    action = "🔎 MONITOR (Wait & See)"

                # FILTER UTAMA
                if p_now > ma20 and 40 < rsi < 75 and turnover >= min_miliar and change >= min_up:
                    results.append({
                        "Ticker": t.replace(".JK",""), 
                        "Price": f"{p_now:,.0f}", 
                        "Change": f"{change:.2f}%", 
                        "Action": action,
                        "Turnover": f"{turnover:.1f}B",
                        "RSI": f"{rsi:.1f}"
                    })
            except: pass
            bar.progress((idx+1)/len(watch))
        
        if results:
            st.success(f"Scan Complete: {len(results)} Opportunities Found!")
            st.table(pd.DataFrame(results))
        else:
            st.warning("No valid signals. Market is neutral.")

# --- MENU: MONEY MANAGEMENT ---
elif menu == "MONEY MANAGEMENT":
    st.title("💰 MONEY_INTELLIGENCE")
    priv = st.checkbox("🕶️ PRIVACY MODE", value=False)
    
    def fmt(v, curr=True):
        if priv: return "Rp *****" if curr else "*****"
        return f"Rp {v:,.0f}" if curr else f"{v:,.0f}"

    t1, t2 = st.tabs(["📈 ACTIVE PORTFOLIO", "📜 TRADING HISTORY"])
    
    with t1:
        with st.expander("➕ ADD NEW POSITION"):
            with st.form("add_p", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                tk = c1.text_input("Ticker")
                bp = c2.number_input("Average Price", min_value=0)
                lt = c3.number_input("Total Lots", min_value=1)
                if st.form_submit_button("SAVE POSITION"):
                    add_to_portfolio(user_now, tk, bp, lt); st.rerun()

        with sqlite3.connect('users.db') as conn:
            df_p = pd.read_sql_query("SELECT * FROM portfolio WHERE username=?", conn, params=(user_now,))
        
        if not df_p.empty:
            tickers = [f"{x}.JK" for x in df_p['ticker']]
            try:
                live = yf.download(tickers, period="1d", progress=False)['Close']
                def calc(r):
                    px = live[f"{r['ticker']}.JK"].iloc[-1] if len(tickers)>1 else live.iloc[-1]
                    cost = r['buy_price'] * r['lots'] * 100
                    val = px * r['lots'] * 100
                    return pd.Series([px, cost, val, val-cost])
                
                df_p[['Live', 'Cost', 'Value', 'P/L']] = df_p.apply(calc, axis=1)
                
                m1, m2, m3 = st.columns(3)
                inv_total = df_p['Cost'].sum()
                pl_total = df_p['P/L'].sum()
                m1.metric("TOTAL INVESTMENT", fmt(inv_total))
                m2.metric("FLOATING P/L", fmt(pl_total), f"{(pl_total/inv_total*100):.2f}%")
                m3.metric("CURRENT VALUE", fmt(inv_total + pl_total))
                
                fig = go.Figure(data=[go.Pie(labels=df_p['ticker'], values=df_p['Value'], hole=.4)])
                fig.update_layout(template="plotly_dark", height=350, paper_bgcolor='rgba(0,0,0,0)', showlegend=True)
                st.plotly_chart(fig, use_container_width=True)
                
                for i, r in df_p.iterrows():
                    with st.expander(f"MANAGE {r['ticker']} | P/L: {fmt(r['P/L'])}"):
                        c_s, c_d = st.columns([3,1])
                        sp = c_s.number_input(f"Sell Price {r['ticker']}", value=float(r['Live']), key=f"s{r['id']}")
                        if c_s.button(f"EXECUTE SELL {r['ticker']}", key=f"bs{r['id']}", use_container_width=True):
                            sell_position(user_now, r['id'], r['ticker'], r['buy_price'], sp, r['lots']); st.rerun()
                        if c_d.button("🗑️", key=f"bd{r['id']}", use_container_width=True, help="Delete without history"):
                            with sqlite3.connect('users.db') as conn: conn.execute("DELETE FROM portfolio WHERE id=?", (r['id'],))
                            st.rerun()
            except: st.error("Error fetching live data. Check your internet.")
        else: st.info("No active positions found.")

    with t2:
        with sqlite3.connect('users.db') as conn:
            df_h = pd.read_sql_query("SELECT * FROM history WHERE username=? ORDER BY date DESC", conn, params=(user_now,))
        
        if not df_h.empty:
            df_h['date'] = pd.to_datetime(df_h['date'])
            # Performance Stats
            tp, tl = df_h[df_h['pnl']>0]['pnl'].sum(), df_h[df_h['pnl']<=0]['pnl'].sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("TOTAL PROFIT", fmt(tp))
            c2.metric("TOTAL LOSS", fmt(tl), delta_color="inverse")
            c3.metric("NET PERFORMANCE", fmt(tp+tl))

            # Equity Curve
            df_c = df_h.sort_values('date')
            df_c['cum'] = df_c['pnl'].cumsum()
            fig_c = go.Figure(go.Scatter(x=df_c['date'], y=df_c['cum'], mode='lines+markers', line=dict(color='#ccff00', width=3), fill='tozeroy', fillcolor='rgba(204,255,0,0.1)'))
            fig_c.update_layout(title="Capital Growth Curve", template="plotly_dark", height=300, paper_bgcolor='rgba(0,0,0,0)', yaxis=dict(showticklabels=not priv))
            st.plotly_chart(fig_c, use_container_width=True)
            
            for i, h in df_h.iterrows():
                with st.expander(f"📅 {h['date'].strftime('%d %b %Y')} | {h['ticker']} | {fmt(h['pnl'])}"):
                    if st.button("🗑️ PURGE RECORD", key=f"dh{h['id']}", use_container_width=True):
                        with sqlite3.connect('users.db') as conn: conn.execute("DELETE FROM history WHERE id=?", (h['id'],))
                        st.rerun()
        else: st.info("No trading history available.")

# --- MENU: SECURITY ---
elif menu == "SECURITY":
    st.title("🔒 SECURITY_VAULT")
    new_key = st.text_input("New Operator Access Key", type="password")
    if st.button("ENCRYPT & UPDATE"):
        if new_key:
            with sqlite3.connect('users.db') as conn:
                conn.execute("UPDATE users SET password=? WHERE username=?", (hash_password(new_key), user_now))
            st.success("Access Key Updated Successfully!")
        else: st.error("Field cannot be empty.")
