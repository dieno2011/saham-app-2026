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

# Setting Zona Waktu Jakarta
tz = pytz.timezone('Asia/Jakarta')

# --- SIDEBAR: KONTROL TOTAL ---
st.sidebar.header("🛠️ Panel Kontrol")

# A. INPUT MANUAL WATCHLIST
st.sidebar.subheader("📝 Kelola Watchlist")
txt_input = st.sidebar.text_area("Input Kode (Tanpa .JK, pisah koma):", 
                                "BBRI, TLKM, ASII, ADRO, GOTO, BMRI, BBNI, UNTR, AMRT, BRIS, BBCA, ANTM, MDKA, PTBA")
manual_list = [f"{t.strip().upper()}.JK" for t in txt_input.split(",") if t.strip()][:30]

# B. FILTER HARGA MANUAL (PENGGANTI SLIDER)
st.sidebar.subheader("💰 Filter Harga Watchlist")
min_h = st.sidebar.number_input("Harga Minimum (Rp):", value=50, step=50)
max_h = st.sidebar.number_input("Harga Maksimum (Rp):", value=50000, step=100)

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
waktu_live = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')
st.write(f"🕒 **Waktu Realtime (WIB):** {waktu_live}")

# --- EKSEKUSI WATCHLIST ---
df_w = get_data_watchlist(manual_list)
if not df_w.empty:
    df_f = df_w[(df_w['Harga'] >= min_h) & (df_w['Harga'] <= max_h)]
    df_s = df_f.sort_values(by="Chg%", ascending=False).reset_index(drop=True)
    
    st.subheader(f"🏆 Top Gainers (Filter: Rp{min_h:,} - Rp{max_h:,})")
    cols = st.columns(min(5, len(df_s)) if not df_s.empty else 1)
    if not df_s.empty:
        for i in range(min(5, len(df_s))):
            with cols[i]:
                st.metric(label=df_s.iloc[i]['Ticker'], value=f"Rp {df_s.iloc[i]['Harga']:,.0f}", delta=f"{df_s.iloc[i]['Chg%']}%")
    else:
        st.warning("Tidak ada saham dalam rentang harga tersebut.")

st.divider()

# --- ANALISIS GRAFIK LENGKAP ---
ca, cb = st.columns([1, 1])
with ca:
    target = st.text_input("🔍 Ketik Kode Saham Analisis:", value=df_s.iloc[0]['Ticker'] if not df_s.empty else "BBRI").upper()
with cb:
    tf = st.selectbox("⏱️ Timeframe:", ("1 Menit", "60 Menit", "1 Hari"))

tf_m = {"1 Menit": "1m", "60 Menit": "60m", "1 Hari": "1d"}
pd_m = {"1 Menit": "1d", "60 Menit": "1mo", "1 Hari": "1y"}

try:
    df = yf.download(f"{target}.JK", period=pd_m[tf], interval=tf_m[tf], progress=False)
    
    if not df.empty:
        if tf != "1 Hari":
            df.index = df.index.tz_convert('Asia/Jakarta')
        
        cl = df['Close'].values.flatten()
        hi = df['High'].values.flatten()
        lo = df['Low'].values.flatten()
        op = df['Open'].values.flatten()
        vl = df['Volume'].values.flatten()

        # --- KALKULASI INDIKATOR TEKNIS ---
        # 1. Bollinger Bands
        ma20 = pd.Series(cl).rolling(20).mean()
        std20 = pd.Series(cl).rolling(20).std()
        u_bb, l_bb = ma20 + (std20 * 2), ma20 - (std20 * 2)

        # 2. RSI
        diff = pd.Series(cl).diff()
        gain = (diff.where(diff > 0, 0)).rolling(14).mean()
        loss = (-diff.where(diff < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + (gain/loss)))

        # 3. MACD
        e12 = pd.Series(cl).ewm(span=12, adjust=False).mean()
        e26 = pd.Series(cl).ewm(span=26, adjust=False).mean()
        macd_line = e12 - e26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()

        # 4. Prediksi 10 Periode
        y_pred = cl[-20:]
        slope, intercept = np.polyfit(np.arange(len(y_pred)), y_pred, 1)
        step = (df.index[1] - df.index[0]) if len(df) > 1 else timedelta(minutes=1)
        future_dates = [df.index[-1] + (step * i) for i in range(1, 11)]
        future_prices = slope * (np.arange(len(y_pred), len(y_pred) + 10)) + intercept

        # --- LIVE PRICE HEADER ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Harga Realtime", f"Rp {cl[-1]:,.0f}", f"{cl[-1]-op[-1]:,.0f}")
        m2.metric("MACD", f"{macd_line.iloc[-1]:.2f}")
        m3.metric("RSI (14)", f"{rsi.iloc[-1]:.2f}")
        m4.metric("Prediksi Target", f"Rp {future_prices[-1]:,.0f}")

        # --- GRAFIK MULTI-PANEL ---
        fig = make_subplots(rows=4, cols=1, shared_xaxes=True, 
                           vertical_spacing=0.03, row_heights=[0.4, 0.15, 0.2, 0.25],
                           subplot_titles=("Price & Bollinger & Prediction", "Volume", "MACD", "RSI"))

        # Row 1: Candle + BB + Prediksi
        fig.add_trace(go.Candlestick(x=df.index, open=op, high=hi, low=lo, close=cl, name="Price"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=u_bb, line=dict(color='rgba(255,255,255,0.3)'), name="Upper BB"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=l_bb, line=dict(color='rgba(255,255,255,0.3)'), name="Lower BB", fill='tonexty'), row=1, col=1)
        fig.add_trace(go.Scatter(x=future_dates, y=future_prices, line=dict(color='yellow', width=3, dash='dot'), name="Garis Prediksi"), row=1, col=1)

        # Row 2: Volume
        fig.add_trace(go.Bar(x=df.index, y=vl, name="Volume", marker_color='orange'), row=2, col=1)

        # Row 3: MACD
        fig.add_trace(go.Scatter(x=df.index, y=macd_line, name="MACD", line=dict(color='cyan')), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=signal_line, name="Signal", line=dict(color='red')), row=3, col=1)

        # Row 4: RSI
        fig.add_trace(go.Scatter(x=df.index, y=rsi, name="RSI", line=dict(color='magenta')), row=4, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color="red", row=4, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="green", row=4, col=1)

        # Layout & Waktu Realtime
        fig.update_layout(
            template="plotly_dark", height=1000, xaxis_rangeslider_visible=True,
            xaxis4=dict(tickformat="%H:%M\n%d %b", title="Waktu Realtime (WIB)")
        )
        
        config = {'scrollZoom': True, 'displayModeBar': True}
        st.plotly_chart(fig, use_container_width=True, config=config)

except Exception as e:
    st.error(f"Terjadi kesalahan: {e}")
