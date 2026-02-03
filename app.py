import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

# 1. Konfigurasi Halaman
st.set_page_config(page_title="StockPro Ultimate 2026", layout="wide")

st.title("🚀 StockPro Ultimate 2026")
st.write(f"Update Terakhir: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# --- KONFIGURASI EMITEN ---
emiten_list = ["BBRI.JK", "TLKM.JK", "ASII.JK", "ADRO.JK", "GOTO.JK", 
               "BMRI.JK", "BBNI.JK", "UNTR.JK", "AMRT.JK", "BRIS.JK"]

@st.cache_data(ttl=60)
def get_watchlist_data(tickers):
    combined_data = []
    for t in tickers:
        try:
            d = yf.download(t, period="5d", interval="1d", progress=False)
            if not d.empty and len(d) >= 2:
                # Menggunakan flatten untuk hindari TypeError Multi-Index
                price = float(d['Close'].values.flatten()[-1])
                prev = float(d['Close'].values.flatten()[-2])
                change = ((price - prev) / prev) * 100
                combined_data.append({
                    "Ticker": t.replace(".JK", ""),
                    "Harga": price,
                    "Perubahan (%)": round(change, 2)
                })
        except: continue
    df = pd.DataFrame(combined_data)
    return df.sort_values(by="Perubahan (%)", ascending=False) if not df.empty else df

# --- TAMPILAN WATCHLIST ---
df_watch = get_watchlist_data(emiten_list)
if not df_watch.empty:
    cols = st.columns(5)
    for i in range(min(5, len(df_watch))):
        with cols[i]:
            st.metric(label=str(df_watch.iloc[i]['Ticker']), 
                      value=f"Rp {float(df_watch.iloc[i]['Harga']):,.0f}", 
                      delta=f"{float(df_watch.iloc[i]['Perubahan (%)']):.2f}%")

st.divider()

# --- INPUT & TIMEFRAME ---
col_input1, col_input2 = st.columns([1, 1])
with col_input1:
    default_ticker = df_watch.iloc[0]['Ticker'] if not df_watch.empty else "BBRI"
    ticker_input = st.text_input("🔍 Masukkan Kode Saham (contoh: BBCA, ASII):", default_ticker).upper()
with col_input2:
    timeframe = st.selectbox("⏱️ Pilih Timeframe Prediksi:", ("1 Menit", "60 Menit", "1 Hari"))

# Pemetaan interval
tf_map = {"1 Menit": "1m", "60 Menit": "60m", "1 Hari": "1d"}
period_map = {"1 Menit": "1d", "60 Menit": "1mo", "1 Hari": "1y"}

# --- ANALISIS DETAIL & PREDIKSI ---
col_a, col_b = st.columns([2, 1])

ticker_full = f"{ticker_input}.JK"

try:
    df_detail = yf.download(ticker_full, period=period_map[timeframe], interval=tf_map[timeframe], progress=False)
    
    if not df_detail.empty:
        # 1. INFORMASI HARGA TERKINI
        current_price = float(df_detail['Close'].values.flatten()[-1])
        price_diff = current_price - float(df_detail['Open'].values.flatten()[-1])
        
        with col_a:
            st.subheader(f"📊 Detail Harga {ticker_input}")
            st.metric(label="Harga Saat Ini", value=f"Rp {current_price:,.2f}", delta=f"{price_diff:,.2f}")

            # 2. LOGIKA PREDIKSI (Linear Regression 10 Periode)
            y_data = df_detail['Close'].values.flatten()[-20:]
            x_data = np.arange(len(y_data))
            slope, intercept = np.polyfit(x_data, y_data, 1)
            
            # Prediksi 10 periode ke depan
            future_idx = len(y_data) + 10
            pred_price = slope * future_idx + intercept
            pred_pct = ((pred_price - current_price) / current_price) * 100
            
            # 3. SARAN BELI / JUAL
            st.write("### 💡 Saran Strategi")
            if slope > 0:
                st.success(f"**REKOMENDASI: BELI / HOLD** - Tren sedang Naik (Bullish). Potensi ke Rp {pred_price:,.0f} (+{pred_pct:.2f}%)")
            else:
                st.error(f"**REKOMENDASI: JUAL / WAIT** - Tren sedang Turun (Bearish). Potensi ke Rp {pred_price:,.0f} ({pred_pct:.2f}%)")

            # Grafik Candlestick
            fig = go.Figure(data=[go.Candlestick(
                x=df_detail.index, open=df_detail['Open'].values.flatten(),
                high=df_detail['High'].values.flatten(), low=df_detail['Low'].values.flatten(),
                close=df_detail['Close'].values.flatten(), name="Harga"
            )])
            fig.add_trace(go.Scatter(x=df_detail.index[-20:], y=slope * x_data + intercept, 
                                     line=dict(color='yellow', width=2), name="Garis Tren"))
            fig.update_layout(template="plotly_dark", height=450, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.subheader("📰 Berita Sentimen")
        news = yf.Ticker(ticker_full).news
        if news:
            for item in news[:5]:
                st.write(f"**{item['title']}**")
                st.caption(f"[Baca Berita]({item['link']})")
                st.divider()
except Exception as e:
    st.error(f"Emiten {ticker_input} tidak ditemukan atau data error.")
