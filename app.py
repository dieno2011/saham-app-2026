import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import pytz

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="StockPro Ultimate 2026", layout="wide")

# Setting Zona Waktu
tz = pytz.timezone('Asia/Jakarta')

# --- SIDEBAR: KONTROL TOTAL ---
st.sidebar.header("🛠️ Panel Kontrol")

# A. INPUT MANUAL WATCHLIST
st.sidebar.subheader("📝 Kelola Watchlist")
txt_input = st.sidebar.text_area("Input Kode (Max 30, pisah koma):", 
                                "BBRI, TLKM, ASII, ADRO, GOTO, BMRI, BBNI, UNTR, AMRT, BRIS, BBCA, ANTM, MDKA, PTBA, ITMG")
manual_list = [f"{t.strip().upper()}.JK" for t in txt_input.split(",") if t.strip()][:30]

# B. FILTER RANGE HARGA
st.sidebar.subheader("💰 Filter Harga Watchlist")
price_range = st.sidebar.slider("Pilih Range Harga (Rp):", 0, 50000, (50, 20000))

@st.cache_data(ttl=30)
def get_data_watchlist(tickers):
    combined = []
    for t in tickers:
        try:
            d = yf.download(t, period="5d", interval="1d", progress=False)
            if not d.empty:
                # Meratakan data agar tidak error Multi-Index
                cl = d['Close'].values.flatten()
                curr = float(cl[-1])
                prev = float(cl[-2])
                combined.append({"Ticker": t.replace(".JK", ""), "Harga": curr, "Chg%": round(((curr-prev)/prev)*100, 2)})
        except: continue
    return pd.DataFrame(combined)

# --- TAMPILAN WATCHLIST ---
st.title("🚀 StockPro Ultimate 2026")
df_w = get_data_watchlist(manual_list)

if not df_w.empty:
    # Terapkan Filter Slider
    df_f = df_w[(df_w['Harga'] >= price_range[0]) & (df_w['Harga'] <= price_range[1])]
    df_s = df_f.sort_values(by="Chg%", ascending=False).reset_index(drop=True)
    
    st.subheader(f"🏆 Top Performance (Filter: Rp{price_range[0]} - Rp{price_range[1]})")
    cols = st.columns(5)
    for i in range(min(5, len(df_s))):
        with cols[i]:
            st.metric(label=df_s.iloc[i]['Ticker'], value=f"Rp{df_s.iloc[i]['Harga']:,}", delta=f"{df_s.iloc[i]['Chg%']}%")
    
    with st.expander("📂 Klik untuk Lihat Semua 30 Emiten"):
        st.dataframe(df_s, use_container_width=True)

st.divider()

# --- ANALISIS GRAFIK & PREDIKSI ---
c1, c2 = st.columns([1, 1])
with c1:
    target = st.text_input("🔍 Ketik Kode Saham Analisis:", value=df_s.iloc[0]['Ticker'] if not df_s.empty else "BBRI").upper()
with c2:
    tf = st.selectbox("⏱️ Timeframe:", ("1 Menit", "60 Menit", "1 Hari"))

tf_m = {"1 Menit": "1m", "60 Menit": "60m", "1 Hari": "1d"}
pd_m = {"1 Menit": "1d", "60 Menit": "1mo", "1 Hari": "1y"}

try:
    df = yf.download(f"{target}.JK", period=pd_m[tf], interval=tf_m[tf], progress=False)
    if not df.empty:
        if tf != "1 Hari": df.index = df.index.tz_convert('Asia/Jakarta')
        
        # Flatten Data
        cl = df['Close'].values.flatten()
        hi = df['High'].values.flatten()
        lo = df['Low'].values.flatten()
        op = df['Open'].values.flatten()

        # INDIKATOR
        ma20 = pd.Series(cl).rolling(20).mean()
        std20 = pd.Series(cl).rolling(20).std()
        u_bb, l_bb = ma20 + (std20 * 2), ma20 - (std20 * 2)

        # PREDIKSI 10 PERIODE KE DEPAN
        y_pred = cl[-20:]
        x_pred = np.arange(len(y_pred))
        slope, intercept = np.polyfit(x_pred, y_pred, 1)
        
        # Membuat Index Masa Depan
        last_date = df.index[-1]
        future_dates = []
        for i in range(1, 11):
            if tf == "1 Menit": delta = timedelta(minutes=i)
            elif tf == "60 Menit": delta = timedelta(hours=i)
            else: delta = timedelta(days=i)
            future_dates.append(last_date + delta)
        
        future_prices = slope * (np.arange(len(y_pred), len(y_pred) + 10)) + intercept

        # GRAFIK
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, row_heights=[0.7, 0.3])
        
        # 1. Candlestick
        fig.add_trace(go.Candlestick(x=df.index, open=op, high=hi, low=lo, close=cl, name="Price"), row=1, col=1)
        
        # 2. Garis Sinyal Prediksi (Kuning Putus-putus)
        fig.add_trace(go.Scatter(x=future_dates, y=future_prices, 
                                 line=dict(color='yellow', width=3, dash='dot'), name="Prediksi 10P"), row=1, col=1)
        
        # 3. Bollinger Bands
        fig.add_trace(go.Scatter(x=df.index, y=u_bb, line=dict(color='rgba(255,255,255,0.2)'), name="Upper BB"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=l_bb, line=dict(color='rgba(255,255,255,0.2)'), name="Lower BB", fill='tonexty'), row=1, col=1)

        # 4. Volume
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'].values.flatten(), name="Volume"), row=2, col=1)

        fig.update_layout(template="plotly_dark", height=700, xaxis_rangeslider_visible=False,
                          xaxis=dict(tickformat="%H:%M\n%d %b")) # Format Waktu
        st.plotly_chart(fig, use_container_width=True)

        st.success(f"💡 **Prediksi Harga {target} (10 periode ke depan):** Rp {future_prices[-1]:,.0f}")
except Exception as e:
    st.error(f"Error: {e}")
