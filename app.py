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
txt_input = st.sidebar.text_area("Input Kode (Max 30, pisah koma):", 
                                "BBRI, TLKM, ASII, ADRO, GOTO, BMRI, BBNI, UNTR, AMRT, BRIS, BBCA, ANTM, MDKA, PTBA, ITMG")
manual_list = [f"{t.strip().upper()}.JK" for t in txt_input.split(",") if t.strip()][:30]

# B. FILTER RANGE HARGA
st.sidebar.subheader("💰 Filter Harga Watchlist")
price_range = st.sidebar.slider("Pilih Range Harga (Rp):", 0, 50000, (50, 30000))

@st.cache_data(ttl=10) # Cache sangat singkat agar harga watchlist tetap segar
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
                    "Chg%": round(((curr-prev)/prev)*100, 2) if curr != prev else 0.0
                })
        except: continue
    return pd.DataFrame(combined)

# --- TAMPILAN WATCHLIST ---
st.title("🚀 StockPro Ultimate 2026")
st.write(f"🕒 **Waktu Sistem:** {datetime.now(tz).strftime('%H:%M:%S')} WIB")

df_w = get_data_watchlist(manual_list)

if not df_w.empty:
    df_f = df_w[(df_w['Harga'] >= price_range[0]) & (df_w['Harga'] <= price_range[1])]
    df_s = df_f.sort_values(by="Chg%", ascending=False).reset_index(drop=True)
    
    st.subheader(f"🏆 Top Watchlist (Rp{price_range[0]:,} - Rp{price_range[1]:,})")
    cols = st.columns(5)
    for i in range(min(5, len(df_s))):
        with cols[i]:
            st.metric(label=df_s.iloc[i]['Ticker'], 
                      value=f"Rp {df_s.iloc[i]['Harga']:,.0f}", 
                      delta=f"{df_s.iloc[i]['Chg%']}%")
    
    with st.expander("📂 Lihat Seluruh Daftar (Hingga 30 Emiten)"):
        st.dataframe(df_s, use_container_width=True)

st.divider()

# --- ANALISIS GRAFIK & HARGA REAL-TIME ---
c1, c2 = st.columns([1, 1])
with c1:
    target = st.text_input("🔍 Ketik Kode Saham Analisis:", value=df_s.iloc[0]['Ticker'] if not df_s.empty else "BBRI").upper()
with c2:
    tf = st.selectbox("⏱️ Timeframe:", ("1 Menit", "60 Menit", "1 Hari"))

tf_m = {"1 Menit": "1m", "60 Menit": "60m", "1 Hari": "1d"}
pd_m = {"1 Menit": "1d", "60 Menit": "1mo", "1 Hari": "1y"}

try:
    # Mengambil data detail
    df = yf.download(f"{target}.JK", period=pd_m[tf], interval=tf_m[tf], progress=False)
    
    if not df.empty:
        if tf != "1 Hari": df.index = df.index.tz_convert('Asia/Jakarta')
        
        # Penanganan Data (Flatten)
        cl = df['Close'].values.flatten()
        hi = df['High'].values.flatten()
        lo = df['Low'].values.flatten()
        op = df['Open'].values.flatten()
        vl = df['Volume'].values.flatten()
        
        # --- INFORMASI HARGA REAL-TIME (UPDATE FIX) ---
        live_price = float(cl[-1])
        open_price = float(op[-1])
        price_chg = live_price - open_price
        pct_chg = (price_chg / open_price) * 100

        st.markdown(f"### 📈 Live: {target}.JK")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Harga Terkini", f"Rp {live_price:,.0f}", f"{price_chg:,.0f} ({pct_chg:.2f}%)")
        m2.metric("High", f"Rp {float(hi[-1]):,.0f}")
        m3.metric("Low", f"Rp {float(lo[-1]):,.0f}")
        m4.metric("Volume", f"{vl[-1]:,.0f}")

        # --- KALKULASI INDIKATOR ---
        # 1. Bollinger Bands
        ma20 = pd.Series(cl).rolling(20).mean()
        std20 = pd.Series(cl).rolling(20).std()
        u_bb, l_bb = ma20 + (std20 * 2), ma20 - (std20 * 2)

        # 2. RSI
        diff = pd.Series(cl).diff()
        gain = (diff.where(diff > 0, 0)).rolling(14).mean()
        loss = (-diff.where(diff < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + (gain/loss)))

        # 3. Prediksi 10 Periode (Garis Signal Kuning)
        y_pred = cl[-20:]
        x_pred = np.arange(len(y_pred))
        slope, intercept = np.polyfit(x_pred, y_pred, 1)
        
        # Membuat Index Masa Depan untuk Grafik
        last_date = df.index[-1]
        future_dates = [last_date + (df.index[1]-df.index[0])*i for i in range(1, 11)]
        future_prices = slope * (np.arange(len(y_pred), len(y_pred) + 10)) + intercept

        # --- GRAFIK PROFESIONAL ---
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.5, 0.2, 0.3])
        
        # Candle + BB + Prediksi
        fig.add_trace(go.Candlestick(x=df.index, open=op, high=hi, low=lo, close=cl, name="Price"), row=1, col=1)
        fig.add_trace(go.Scatter(x=future_dates, y=future_prices, line=dict(color='yellow', width=3, dash='dot'), name="Signal Prediksi 10P"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=u_bb, line=dict(color='rgba(255,255,255,0.2)'), name="Upper BB"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=l_bb, line=dict(color='rgba(255,255,255,0.2)'), name="Lower BB", fill='tonexty'), row=1, col=1)

        # Volume
        fig.add_trace(go.Bar(x=df.index, y=vl, name="Volume", marker_color='orange'), row=2, col=1)
        
        # RSI
        fig.add_trace(go.Scatter(x=df.index, y=rsi, name="RSI", line=dict(color='magenta')), row=3, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color="red", row=3, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="green", row=3, col=1)

        fig.update_layout(template="plotly_dark", height=800, xaxis_rangeslider_visible=False,
                          xaxis=dict(tickformat="%H:%M\n%d %b"))
        st.plotly_chart(fig, use_container_width=True)

        st.info(f"💡 **Analisis Strategi:** Target harga 10 periode ke depan diperkirakan berada di kisaran **Rp {future_prices[-1]:,.0f}**. RSI saat ini di level **{rsi.iloc[-1]:.2f}**.")
        
except Exception as e:
    st.error(f"Ketik kode saham dengan benar (Contoh: BBCA, ASII, ANTM).")
