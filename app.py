import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

# 1. Konfigurasi Halaman & Tema
st.set_page_config(page_title="StockPro Ultimate 2026", layout="wide")

# Custom CSS untuk tampilan mobile yang lebih bersih
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetric"] { background-color: #1e2127; padding: 10px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 StockPro Ultimate 2026")

# --- SIDEBAR: PENGATURAN ANALISIS ---
st.sidebar.header("⚙️ Pengaturan Analisis")
timeframe = st.sidebar.selectbox(
    "Pilih Timeframe Prediksi:",
    ("Menit (1m)", "Jam (60m)", "Harian (1d)")
)

# Pemetaan interval untuk Yahoo Finance
tf_map = {
    "Menit (1m)": {"period": "1d", "interval": "1m", "label": "Menit"},
    "Jam (60m)": {"period": "1mo", "interval": "60m", "label": "Jam"},
    "Harian (1d)": {"period": "1y", "interval": "1d", "label": "Hari"}
}

# --- KONFIGURASI 10 EMITEN ---
emiten_list = ["BBRI.JK", "TLKM.JK", "ASII.JK", "ADRO.JK", "GOTO.JK", 
               "BMRI.JK", "BBNI.JK", "UNTR.JK", "AMRT.JK", "BRIS.JK"]

@st.cache_data(ttl=60) 
def get_watchlist_data(tickers):
    combined_data = []
    for t in tickers:
        try:
            d = yf.download(t, period="5d", interval="1d", progress=False)
            if not d.empty and len(d) >= 2:
                price = float(d['Close'].iloc[-1])
                prev = float(d['Close'].iloc[-2])
                change = ((price - prev) / prev) * 100
                combined_data.append({
                    "Ticker": t.replace(".JK", ""),
                    "Harga": price,
                    "Perubahan (%)": round(change, 2)
                })
        except: continue
    df = pd.DataFrame(combined_data)
    if not df.empty:
        return df.sort_values(by="Perubahan (%)", ascending=False).reset_index(drop=True)
    return df

# --- TAMPILAN WATCHLIST ---
st.subheader("🏆 Top Performance")
df_watch = get_watchlist_data(emiten_list)
if not df_watch.empty:
    cols = st.columns(5)
    for i in range(min(5, len(df_watch))):
        with cols[i]:
            st.metric(
                label=str(df_watch.iloc[i]['Ticker']), 
                value=f"Rp {float(df_watch.iloc[i]['Harga']):,.0f}", 
                delta=f"{float(df_watch.iloc[i]['Perubahan (%)']):.2f}%"
            )
else:
    st.warning("Data sedang memuat atau bursa tutup.")

st.divider()

# --- ANALISIS DETAIL DENGAN TIMEFRAME DINAMIS ---
col_a, col_b = st.columns([2, 1])

with col_a:
    st.subheader(f"🔍 Prediksi Tren ({timeframe})")
    default_ticker = df_watch.iloc[0]['Ticker'] if not df_watch.empty else "BBRI"
    ticker_input = st.text_input("Ketik Kode Saham:", default_ticker).upper()
    ticker_full = f"{ticker_input}.JK"

    try:
        conf = tf_map[timeframe]
        df_detail = yf.download(ticker_full, period=conf['
