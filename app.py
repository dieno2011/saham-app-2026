import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh # Pastikan install: pip install streamlit-autorefresh

# 1. Konfigurasi Halaman
st.set_page_config(page_title="StockPro Ultimate 2026", layout="wide")

# Auto-refresh setiap 30 detik
st_autorefresh(interval=30 * 1000, key="datarefresh")

# Setting Zona Waktu Jakarta
tz = pytz.timezone('Asia/Jakarta')
waktu_sekarang = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')

st.title("🚀 StockPro Ultimate 2026")
st.write(f"🕒 **Waktu Realtime (WIB):** {waktu_sekarang}")

# --- KONFIGURASI EMITEN ---
emiten_list = ["BBRI.JK", "TLKM.JK", "ASII.JK", "ADRO.JK", "GOTO.JK", 
               "BMRI.JK", "BBNI.JK", "UNTR.JK", "AMRT.JK", "BRIS.JK"]

@st.cache_data(ttl=10)
def get_watchlist_data(tickers):
    combined_data = []
    for t in tickers:
        try:
            d = yf.download(t, period="5d", interval="1d", progress=False)
            if not d.empty:
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
col_in1, col_in2 = st.columns([1, 1])
with col_in1:
    default_ticker = df_sorted.iloc[0]['Ticker'] if not df_sorted.empty else "BBRI"
    ticker_input = st.text_input("🔍 Kode Saham:", default_ticker).upper()
with col_in2:
    timeframe = st.selectbox("⏱️ Timeframe Analisis:", ("1 Menit", "60 Menit", "1 Hari"))

tf_map = {"1 Menit": "1m", "60 Menit": "60m", "1 Hari": "1d"}
period_map = {"1 Menit": "1d", "60 Menit": "1mo", "1 Hari": "1y"}

# --- PENGAMBILAN DATA DETAIL ---
ticker_full = f"{ticker_input}.JK"

try:
    df = yf.download(ticker_full, period=period_map[timeframe], interval=tf_map[timeframe], progress=False)
    
    if not df.empty:
        # Konversi Zona Waktu
        if timeframe != "1 Hari":
            df.index = df.index.tz_convert('Asia/Jakarta')

        # --- KALKULASI INDIKATOR ---
        # 1. Bollinger Bands (20 periods)
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['STD20'] = df['Close'].rolling(window=20).std()
        df['Upper'] = df['MA20'] + (df['STD20'] * 2)
        df['Lower'] = df['MA20'] - (df['STD20'] * 2)

        # 2. MACD (12, 26, 9)
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['Hist'] = df['MACD'] - df['Signal']

        # 3. Prediksi Linear Regression (10 periode)
        y_val = df['Close'].values.flatten()[-20:]
        x_val = np.arange(len(y_val))
        slope, intercept = np.polyfit(x_val, y_val, 1)
        pred_price = slope * (len(y_val) + 10) + intercept

        # --- LAYOUT GRAFIK ---
        st.subheader(f"📊 Advanced Analysis: {ticker_input}")
        
        # Buat Subplots: Row 1 (Candle + BB), Row 2 (Volume), Row 3 (MACD)
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                           vertical_spacing=0.05, 
                           row_heights=[0.5, 0.2, 0.3])

        # Candlestick
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], 
                                   low=df['Low'], close=df['Close'], name="Price"), row=1, col=1)
        
        # Bollinger Bands
        fig.add_trace(go.Scatter(x=df.index, y=df['Upper'], line=dict(color='rgba(173, 216, 230, 0.4)'), name="BB Upper"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['Lower'], line=dict(color='rgba(173, 216, 230, 0.4)'), name="BB Lower", fill='tonexty'), row=1, col=1)

        # Volume
        colors = ['red' if row['Open'] > row['Close'] else 'green' for index, row in df.iterrows()]
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="Volume", marker_color=colors), row=2, col=1)

        # MACD
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], line=dict(color='blue'), name="MACD"), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['Signal'], line=dict(color='orange'), name="Signal"), row=3, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df['Hist'], name="Histogram"), row=3, col=1)

        # Update Layout
        fig.update_layout(template="plotly_dark", height=800, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # --- INFO PANEL ---
        c1, c2, c3 = st.columns(3)
        with c1:
            st.info(f"💡 **Prediksi Target:** Rp {pred_price:,.0f}")
        with c2:
            signal_txt = "BELI" if slope > 0 and df['MACD'].iloc[-1] > df['Signal'].iloc[-1] else "TUNGGU/JUAL"
            st.warning(f"🎯 **Sinyal Gabungan:** {signal_txt}")
        with c3:
            st.success(f"📈 **Trend Slope:** {round(slope, 2)}")

except Exception as e:
    st.error(f"Pilih emiten lain atau cek koneksi. Info: {e}")
