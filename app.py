import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import pytz

# 1. Konfigurasi Halaman
st.set_page_config(page_title="StockPro Ultimate 2026", layout="wide")

# Setting Zona Waktu Jakarta
tz = pytz.timezone('Asia/Jakarta')
waktu_sekarang = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')

st.title("🚀 StockPro Ultimate 2026")
st.write(f"🕒 **Waktu Realtime (WIB):** {waktu_sekarang}")

# --- KONFIGURASI EMITEN ---
emiten_list = ["BBRI.JK", "TLKM.JK", "ASII.JK", "ADRO.JK", "GOTO.JK", 
               "BMRI.JK", "BBNI.JK", "UNTR.JK", "AMRT.JK", "BRIS.JK"]

# Cache dikurangi ke 10 detik agar terasa realtime
@st.cache_data(ttl=10)
def get_watchlist_data(tickers):
    combined_data = []
    for t in tickers:
        try:
            d = yf.download(t, period="5d", interval="1d", progress=False)
            if not d.empty:
                # Ambil nilai terakhir dengan aman
                price = float(d['Close'].values.flatten()[-1])
                prev = float(d['Close'].values.flatten()[-2])
                change = ((price - prev) / prev) * 100
                combined_data.append({
                    "Ticker": t.replace(".JK", ""),
                    "Harga": price,
                    "Perubahan (%)": round(change, 2)
                })
        except: continue
    return pd.DataFrame(combined_data)

# --- TAMPILAN WATCHLIST ---
df_watch = get_watchlist_data(emiten_list)
if not df_watch.empty:
    cols = st.columns(5)
    df_sorted = df_watch.sort_values(by="Perubahan (%)", ascending=False).reset_index(drop=True)
    for i in range(min(5, len(df_sorted))):
        with cols[i]:
            st.metric(label=str(df_sorted.iloc[i]['Ticker']), 
                      value=f"Rp {float(df_sorted.iloc[i]['Harga']):,.0f}", 
                      delta=f"{float(df_sorted.iloc[i]['Perubahan (%)']):.2f}%")

st.divider()

# --- INPUT & TIMEFRAME ---
col_input1, col_input2 = st.columns([1, 1])
with col_input1:
    default_ticker = df_sorted.iloc[0]['Ticker'] if not df_sorted.empty else "BBRI"
    ticker_input = st.text_input("🔍 Kode Saham:", default_ticker).upper()
with col_input2:
    timeframe = st.selectbox("⏱️ Timeframe Analisis:", ("1 Menit", "60 Menit", "1 Hari"))

# Pemetaan interval
tf_map = {"1 Menit": "1m", "60 Menit": "60m", "1 Hari": "1d"}
period_map = {"1 Menit": "1d", "60 Menit": "1mo", "1 Hari": "1y"}

# --- ANALISIS DETAIL & PREDIKSI ---
ticker_full = f"{ticker_input}.JK"

try:
    # Mengambil data terbaru tanpa cache yang lama
    df_detail = yf.download(ticker_full, period=period_map[timeframe], interval=tf_map[timeframe], progress=False)
    
    if not df_detail.empty:
        # Konversi index waktu ke WIB (Terutama untuk Menit/Jam)
        if timeframe != "1 Hari":
            df_detail.index = df_detail.index.tz_convert('Asia/Jakarta')
        
        current_price = float(df_detail['Close'].values.flatten()[-1])
        
        col_a, col_b = st.columns([2, 1])
        
        with col_a:
            st.subheader(f"📊 Live Chart: {ticker_input}")
            st.metric("Harga Terkini", f"Rp {current_price:,.2f}")

            # Logika Prediksi 10 Periode
            y_data = df_detail['Close'].values.flatten()[-20:]
            x_data = np.arange(len(y_data))
            slope, intercept = np.polyfit(x_data, y_data, 1)
            
            future_idx = len(y_data) + 10
            pred_price = slope * future_idx + intercept
            
            # Saran Strategi
            if slope > 0:
                st.success(f"**REKOMENDASI: BELI** | Estimasi Target: Rp {pred_price:,.0f}")
            else:
                st.error(f"**REKOMENDASI: JUAL** | Estimasi Target: Rp {pred_price:,.0f}")

            # Grafik Candlestick
            fig = go.Figure(data=[go.Candlestick(
                x=df_detail.index, 
                open=df_detail['Open'].values.flatten(),
                high=df_detail['High'].values.flatten(), 
                low=df_detail['Low'].values.flatten(),
                close=df_detail['Close'].values.flatten(), 
                name="Market"
            )])
            
            # Garis Tren
            fig.add_trace(go.Scatter(x=df_detail.index[-20:], y=slope * x_data + intercept, 
                                     line=dict(color='yellow', width=2), name="Trend Line"))
            
            fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

        with col_b:
            st.subheader("📰 Kabar Emiten")
            news = yf.Ticker(ticker_full).news
            for item in news[:5]:
                st.write(f"**{item['title']}**")
                st.caption(f"[Sumber Berita]({item['link']})")
                st.divider()

except Exception as e:
    st.error(f"Data tidak tersedia untuk emiten {ticker_input} pada timeframe ini.")
