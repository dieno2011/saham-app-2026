import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime
import pytz

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="StockPro Pro 2026", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetric"] { background-color: #1e2127; padding: 10px; border-radius: 10px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

tz = pytz.timezone('Asia/Jakarta')
st.title("🚀 StockPro Ultimate 2026")
st.write(f"🕒 **Waktu Realtime (WIB):** {datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')}")

# --- 2. SIDEBAR: INPUT MANUAL WATCHLIST ---
st.sidebar.header("📋 Kelola Watchlist")
st.sidebar.info("Masukkan kode saham tanpa '.JK'. Maksimal 30 emiten.")
default_list = "BBRI, TLKM, ASII, ADRO, GOTO, BMRI, BBNI, UNTR, AMRT, BRIS"
user_watchlist_input = st.sidebar.text_area("Input Kode Saham (Pisahkan dengan koma):", default_list)

# Proses input manual menjadi list
manual_list = [t.strip().upper() for t in user_watchlist_input.split(",") if t.strip()][:30]
emiten_list = [f"{t}.JK" for t in manual_list]

# --- 3. FILTER HARGA (TOP & BOTTOM) ---
st.sidebar.header("💰 Filter Harga Watchlist")
min_h = st.sidebar.number_input("Harga Minimum (Rp):", value=50, step=50)
max_h = st.sidebar.number_input("Harga Maksimum (Rp):", value=100000, step=500)

@st.cache_data(ttl=60)
def get_clean_watchlist(tickers):
    combined = []
    for t in tickers:
        try:
            d = yf.download(t, period="5d", interval="1d", progress=False)
            if not d.empty and len(d) >= 2:
                close_prices = d['Close'].values.flatten()
                current_p = float(close_prices[-1])
                prev_p = float(close_prices[-2])
                change_p = ((current_p - prev_p) / prev_p) * 100
                combined.append({"Ticker": t.replace(".JK", ""), "Harga": current_p, "Perubahan (%)": round(change_p, 2)})
        except: continue
    return pd.DataFrame(combined)

# --- 4. EKSEKUSI WATCHLIST & FILTER ---
df_watch = get_clean_watchlist(emiten_list)

if not df_watch.empty:
    # Terapkan Filter Harga
    df_filtered = df_watch[(df_watch['Harga'] >= min_h) & (df_watch['Harga'] <= max_h)]
    df_sorted = df_filtered.sort_values(by="Perubahan (%)", ascending=False).reset_index(drop=True)
    
    st.subheader(f"🏆 Performa Watchlist (Filter: Rp {min_h:,} - Rp {max_h:,})")
    
    if not df_sorted.empty:
        cols = st.columns(min(5, len(df_sorted)))
        for i in range(min(5, len(df_sorted))):
            with cols[i]:
                st.metric(label=df_sorted.iloc[i]['Ticker'], 
                          value=f"Rp {df_sorted.iloc[i]['Harga']:,.0f}", 
                          delta=f"{df_sorted.iloc[i]['Perubahan (%)']:.2f}%")
        
        with st.expander("📊 Lihat Detail Seluruh Emiten"):
            st.dataframe(df_sorted, use_container_width=True, hide_index=True)
    else:
        st.warning("Tidak ada saham dalam rentang harga tersebut.")
else:
    st.error("Gagal memuat data. Periksa kode saham atau koneksi.")

st.divider()

# --- 5. ANALISIS DETAIL (MANUAL INPUT) ---
st.subheader("🔍 Analisis Teknikal Mendalam")
c1, c2 = st.columns([1, 1])
with c1:
    default_analisa = df_sorted.iloc[0]['Ticker'] if not df_sorted.empty else "BBRI"
    user_tk = st.text_input("Ketik Kode Saham Analisis (Tanpa .JK):", default_analisa).upper()
with c2:
    timeframe = st.selectbox("⏱️ Timeframe Analisis:", ("1 Menit", "60 Menit", "1 Hari"))

tf_map = {"1 Menit": "1m", "60 Menit": "60m", "1 Hari": "1d"}
period_map = {"1 Menit": "1d", "60 Menit": "1mo", "1 Hari": "1y"}

# --- PENGAMBILAN DATA ANALISIS ---
try:
    df = yf.download(f"{user_tk}.JK", period=period_map[timeframe], interval=tf_map[timeframe], progress=False)
    if not df.empty:
        if timeframe != "1 Hari": df.index = df.index.tz_convert('Asia/Jakarta')
        close_data = df['Close'].values.flatten()
        
        # INDIKATOR: BB, MACD, RSI
        ma20 = pd.Series(close_data).rolling(window=20).mean()
        std20 = pd.Series(close_data).rolling(window=20).std()
        upper_bb, lower_bb = ma20 + (std20 * 2), ma20 - (std20 * 2)
        
        delta = pd.Series(close_data).diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        # MACD
        ema12 = pd.Series(close_data).ewm(span=12, adjust=False).mean()
        ema26 = pd.Series(close_data).ewm(span=26, adjust=False).mean()
        df['MACD'] = ema12 - ema26
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

        # Prediksi 10 Periode
        clean_y = close_data[~np.isnan(close_data)][-20:]
        slope, intercept = np.polyfit(np.arange(len(clean_y)), clean_y, 1)
        pred_p = slope * (len(clean_y) + 10) + intercept

        # GRAFIK 4-BARIS (Price, Volume, MACD, RSI)
        fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.4, 0.15, 0.2, 0.25])
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Price"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=upper_bb, line=dict(color='gray', width=1), name="Upper BB"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=lower_bb, line=dict(color='gray', width=1), name="Lower BB", fill='tonexty'), row=1, col=1)
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="Volume", marker_color='orange'), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], name="MACD", line=dict(color='cyan')), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['Signal'], name="Signal", line=dict(color='red')), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name="RSI", line=dict(color='magenta')), row=4, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color="red", row=4, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="green", row=4, col=1)
        
        fig.update_layout(template="plotly_dark", height=1000, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # PANEL KEPUTUSAN
        p1, p2, p3 = st.columns(3)
        with p1: st.metric("Harga Terkini", f"Rp {close_data[-1]:,.0f}")
        with p2: st.info(f"🔮 Target 10 Periode: Rp {pred_p:,.0f}")
        with p3:
            # Sinyal Gabungan (Trend + RSI)
            rsi_now = df['RSI'].iloc[-1]
            saran = "🚀 BELI (Oversold)" if rsi_now < 35 and slope > 0 else "📉 JUAL (Overbought)" if rsi_now > 65 else "⚖️ WAIT / HOLD"
            st.success(f"💡 Saran: {saran}")
except: st.error("Emiten tidak ditemukan.")
