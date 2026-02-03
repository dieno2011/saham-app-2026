import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

# 1. Konfigurasi Halaman
st.set_page_config(page_title="StockPro Ultimate 2026", layout="wide")

# Gaya Tampilan Dark Mode Profesional
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetric"] { background-color: #1e2127; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 StockPro Ultimate 2026")

# --- SIDEBAR ---
st.sidebar.header("⚙️ Konfigurasi Analisis")
tf_option = st.sidebar.selectbox(
    "Pilih Timeframe Prediksi:",
    ("Menit (1m)", "Jam (60m)", "Harian (1d)")
)

tf_map = {
    "Menit (1m)": {"period": "1d", "interval": "1m", "lbl": "Menit"},
    "Jam (60m)": {"period": "1mo", "interval": "60m", "lbl": "Jam"},
    "Harian (1d)": {"period": "1y", "interval": "1d", "lbl": "Hari"}
}

# --- LIST EMITEN ---
emiten_list = ["BBRI.JK", "TLKM.JK", "ASII.JK", "ADRO.JK", "GOTO.JK", 
               "BMRI.JK", "BBNI.JK", "UNTR.JK", "AMRT.JK", "BRIS.JK"]

@st.cache_data(ttl=60)
def get_clean_data(tickers):
    combined = []
    for t in tickers:
        try:
            # Mengambil data 5 hari untuk memastikan perbandingan harga tersedia
            raw = yf.download(t, period="5d", interval="1d", progress=False)
            if not raw.empty and len(raw) >= 2:
                # Menangani Multi-Index jika ada
                close_prices = raw['Close'].values.flatten()
                current_p = float(close_prices[-1])
                prev_p = float(close_prices[-2])
                change_p = ((current_p - prev_p) / prev_p) * 100
                
                combined.append({
                    "Ticker": t.replace(".JK", ""),
                    "Harga": current_p,
                    "Perubahan (%)": round(change_p, 2)
                })
        except: continue
    return pd.DataFrame(combined)

# --- EKSEKUSI DATA WATCHLIST ---
df_watch = get_clean_data(emiten_list)

if not df_watch.empty:
    st.subheader("🏆 Top Performance (Sorted by Gain)")
    df_sorted = df_watch.sort_values(by="Perubahan (%)", ascending=False).reset_index(drop=True)
    
    cols = st.columns(5)
    for i in range(min(5, len(df_sorted))):
        with cols[i]:
            ticker = str(df_sorted.iloc[i]['Ticker'])
            harga = float(df_sorted.iloc[i]['Harga'])
            persen = float(df_sorted.iloc[i]['Perubahan (%)'])
            st.metric(label=ticker, value=f"Rp {harga:,.0f}", delta=f"{persen:.2f}%")
else:
    st.error("Gagal memuat data. Periksa koneksi internet atau server Yahoo Finance.")

st.divider()

# --- DETAIL ANALISIS & PREDIKSI ---
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader(f"🔍 Prediksi Tren ({tf_option})")
    default_tk = df_sorted.iloc[0]['Ticker'] if not df_watch.empty else "BBRI"
    user_tk = st.text_input("Cari Kode Saham (Tanpa .JK):", default_tk).upper()
    full_tk = f"{user_tk}.JK"
    
    try:
        c = tf_map[tf_option]
        data_dtl = yf.download(full_tk, period=c['period'], interval=c['interval'], progress=False)
        
        if not data_dtl.empty:
            # Logika Regresi untuk Prediksi
            prices = data_dtl['Close'].values.flatten()
            prices = prices[~np.isnan(prices)] # Hapus NaN
            
            if len(prices) > 10:
                y = prices[-20:] # Ambil 20 data terakhir
                x = np.arange(len(y))
                slope, intercept = np.polyfit(x, y, 1)
                
                # Proyeksi 3 langkah ke depan
                future_val = slope * (len(y) + 3) + intercept
                current_val = float(y[-1])
                pct_pred = ((future_val - current_val) / current_val) * 100
                
                m1, m2 = st.columns(2)
                if slope > 0:
                    m1.success("🚀 SENTIMEN: BULLISH (NAIK)")
                    m2.metric(f"Estimasi 3 {c['lbl']}", f"{pct_pred:.2f}%", delta=f"{future_val-current_val:,.2f}")
                else:
                    m1.error("📉 SENTIMEN: BEARISH (TURUN)")
                    m2
