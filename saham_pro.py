import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from streamlit_gsheets import GSheetsConnection # Library Baru
import warnings
import os
import requests 
import pytz 

# --- 0. CONFIG & G-SHEETS SETUP ---
warnings.filterwarnings("ignore", category=FutureWarning)
st.set_page_config(page_title="IDX CYBER TERMINAL", page_icon="⚡", layout="wide")

# Inisialisasi Koneksi Google Sheets
conn_gs = st.connection("gsheets", type=GSheetsConnection)

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
    df = conn_gs.read(worksheet="users")
    df.loc[df['username'] == u, ['last_login', 'ip_address', 'location']] = [now, ip, loc]
    conn_gs.update(worksheet="users", data=df)

def get_sidebar_log(u):
    df = conn_gs.read(worksheet="users")
    res = df[df['username'] == u]
    if not res.empty:
        return res.iloc[0]['last_login'], res.iloc[0]['ip_address'], res.iloc[0]['location']
    return "-", "-", "-"

def check_login_db(u, p):
    df = conn_gs.read(worksheet="users")
    res = df[(df['username'] == u) & (df['password'].astype(str) == str(p))]
    return res.iloc[0]['role'] if not res.empty else None

def add_to_portfolio(u, t, p, l, tp, cl):
    df = conn_gs.read(worksheet="portfolio")
    new_id = int(df['id'].max() + 1) if not df.empty else 1
    new_row = pd.DataFrame([{
        "id": new_id, "username": u, "ticker": t.upper().strip(), 
        "buy_price": p, "lots": l, "tp_price": tp, "cl_price": cl, 
        "date": datetime.now().strftime("%Y-%m-%d")
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    conn_gs.update(worksheet="portfolio", data=df)

def sell_position(u, row_id, ticker, buy_p, sell_p, lots):
    pnl = (sell_p - buy_p) * lots * 100
    date_now = datetime.now().strftime("%Y-%m-%d")
    # Add to History
    df_h = conn_gs.read(worksheet="history")
    new_id_h = int(df_h['id'].max() + 1) if not df_h.empty else 1
    new_h = pd.DataFrame([{
        "id": new_id_h, "username": u, "ticker": ticker, "buy_price": buy_p, 
        "sell_price": sell_p, "lots": lots, "pnl": pnl, "date": date_now
    }])
    df_h = pd.concat([df_h, new_h], ignore_index=True)
    conn_gs.update(worksheet="history", data=df_h)
    # Remove from Portfolio
    df_p = conn_gs.read(worksheet="portfolio")
    df_p = df_p[df_p['id'] != row_id]
    conn_gs.update(worksheet="portfolio", data=df_p)

def get_user_portfolio(u, r):
    df = conn_gs.read(worksheet="portfolio")
    if df.empty: return df
    return df if r == 'admin' else df[df['username'] == u]

def add_user_db(u, p, r):
    df = conn_gs.read(worksheet="users")
    if u in df['username'].values: return False
    new_u = pd.DataFrame([{"username": u, "password": p, "role": r, "last_login": "-", "ip_address": "-", "location": "-"}])
    df = pd.concat([df, new_u], ignore_index=True)
    conn_gs.update(worksheet="users", data=df)
    return True

def delete_user_db(u):
    if u == 'admin': return False
    df = conn_gs.read(worksheet="users")
    df = df[df['username'] != u]
    conn_gs.update(worksheet="users", data=df)
    return True

def update_password_db(u, new_p):
    df = conn_gs.read(worksheet="users")
    df.loc[df['username'] == u, 'password'] = new_p
    conn_gs.update(worksheet="users", data=df)
    return True

# --- SISANYA KODE UI ANDA (STYLE, AUTH, CONTENT) TETAP SAMA ---
