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

# CSS untuk UI Modern
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetric"] { background-color: #1e2127; padding: 10px; border-radius: 10px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

# Setting Zona Waktu Jakarta
tz = pytz.timezone('Asia/Jakarta')

# --- SIDEBAR: KONTROL TOTAL ---
st.sidebar.header("🛠️ Panel Kontrol")

# A. INPUT MANUAL WATCHLIST (MAKS 30)
st.sidebar.subheader("📝 Kelola Watchlist")
txt_input = st.sidebar.text_area("Input Kode (Tanpa .JK, pisah koma):", 
                                "BBRI, TLKM, ASII, ADRO, GOTO, BMRI, BBNI, UNTR, AMRT, BRIS, BBCA, ANTM, MDKA, PTBA")
manual_list = [f"{t.strip().upper()}.JK" for t in txt_input.split(",") if t.strip()][:30]

# B. FILTER RANGE HARGA
st.sidebar.subheader("💰 Filter Harga Watchlist")
price_range = st.sidebar.slider("Pilih Range Harga (Rp):", 0, 50000, (50, 20000))

@st.cache_data(ttl=10)
def get_data_watchlist(tickers):
    combined = []
    for t in tickers:
        try:
            d = yf.download(t, period="2d", interval="1d", progress=False)
            if not d.empty:
                cl = d['Close'].values.flatten()
                curr = float(cl[-1])
                prev = float(cl[-2]) if len(cl) > 1 else curr
                combined.append({
                    "Ticker": t.replace(".JK", ""), 
                    "Harga": curr, 
                    "Chg%": round(((curr-prev)/prev)*100, 2)
                })
        except: continue
    return pd.DataFrame(combined)

# --- TAMPILAN HEADER ---
st.title("🚀 StockPro Ultimate 2026")
waktu_live = datetime.now(tz).strftime('%H:%M:%S')
st.write(f"🕒 **Waktu Realtime (WIB):** {waktu_live}")

# --- EKSEKUSI WATCHLIST ---
df_w = get_data_watchlist(manual_list)
if not df_w.empty:
    df_f = df_w[(df_w['Harga'] >= price_range[0]) & (df_w['Harga'] <= price_range[1])]
    df_s = df_f.sort_values(by="Chg%", ascending=False).reset_index(drop=True)
    
    st.subheader(f"🏆 Top Gainers (Filter: Rp{price_range[0]:,} - Rp{price_range[1]:,})")
    cols = st.columns(5)
    for i in range(min(5, len(df_s))):
        with cols[i]:
            st.metric(label=df_s.iloc[i]['Ticker'], value=f"Rp {df_s.iloc[i]['Harga']:,.0f}", delta=f"{df_s.iloc[i]['Chg%']}%")

st.divider()

# --- ANALISIS GRAFIK FLEKSIBEL ---
c1, c2 = st.columns([1, 1])
with c1:
    target = st.text_input("🔍 Ketik Kode Saham (Contoh: BBCA):", value=df_s.iloc[0]['Ticker'] if not df_s.empty else "BBRI").upper()
with c2:
    tf = st.selectbox("⏱️ Timeframe Analisis:", ("1 Menit", "60 Menit", "1 Hari"))

tf_m = {"1 Menit": "1m", "60 Menit": "60m", "1 Hari": "1d"}
pd_m = {"1 Menit": "1d", "60 Menit": "1mo", "1 Hari": "1y"}

try:
    df = yf.download(f"{target}.JK", period=pd_m[tf], interval=tf_m[tf], progress=False)
    
    if not df.empty:
        # Konversi waktu ke WIB agar realtime di grafik
        if tf != "1 Hari":
            df.index = df.index.tz_convert('Asia/Jakarta')
        
        cl = df['Close'].values.flatten()
        hi = df['High'].values.flatten()
        lo = df['Low'].values.flatten()
        op = df['Open'].values.flatten()

        # Prediksi 10 Periode
        y_pred = cl[-20:]
        slope, intercept = np.polyfit(np.arange(len(y_pred)), y_pred, 1)
        future_idx = np.arange(len(y_pred), len(y_pred) + 10)
        future_prices = slope * future_idx + intercept
        
        # Buat Index Waktu Masa Depan
        last_dt = df.index[-1]
        step = (df.index[1] - df.index[0]) if len(df) > 1 else timedelta(minutes=1)
        future_dates = [last_dt + (step * i) for i in range(1, 11)]

        # --- GRAFIK PROFESIONAL (ZOOMABLE) ---
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, row_heights=[0.7, 0.3])
        
        # 1. Candlestick
        fig.add_trace(go.Candlestick(x=df.index, open=op, high=hi, low=lo, close=cl, name="Price"), row=1, col=1)
        
        # 2. Garis Prediksi 10 Periode
        fig.add_trace(go.Scatter(x=future_dates, y=future_prices, line=dict(color='yellow', width=3, dash='dot'), name="Signal Prediksi"), row=1, col=1)

        # 3. Volume
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'].values.flatten(), name="Volume", marker_color='orange'), row=2, col=1)

        # FITUR ZOOM & SCROLL
        fig.update_layout(
            template="plotly_dark", 
            height=750,
            xaxis_rangeslider_visible=True, # Menambahkan Range Slider di bawah
            xaxis_rangeslider_thickness=0.05,
            dragmode='pan', # Default geser tangan (drag)
            xaxis=dict(
                type='date',
                tickformat="%H:%M\n%d %b", # Waktu realtime di sumbu X
                rangeslider=dict(visible=True)
            )
        )
        
        # Konfigurasi agar scroll mouse/touchpad bisa zoom in-out
        config = {'scrollZoom': True, 'displayModeBar': True, 'responsive': True}
        
        # Tampilkan Harga Real-time di Header
        curr_p = cl[-1]
        st.markdown(f"### 📊 Live Chart: {target}.JK | Rp {curr_p:,.0f}")
        
        st.plotly_chart(fig, use_container_width=True, config=config)
        
        st.success(f"🔮 **Prediksi 10 Periode:** Harga diperkirakan menuju Rp {future_prices[-1]:,.0f}")

except Exception as e:
    st.error("Masukkan kode saham dengan benar.")
