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
st.sidebar.subheader("📝 Kelola Watchlist")
txt_input = st.sidebar.text_area("Input Kode (Tanpa .JK, pisah koma):", 
                                "BBRI, TLKM, ASII, ADRO, GOTO, BMRI, BBNI, UNTR, AMRT, BRIS, BBCA, ANTM, MDKA, PTBA")
manual_list = [f"{t.strip().upper()}.JK" for t in txt_input.split(",") if t.strip()][:30]

st.sidebar.subheader("💰 Filter Harga Watchlist")
price_range = st.sidebar.slider("Pilih Range Harga (Rp):", 0, 50000, (50, 30000))

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
waktu_sekarang = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')
st.write(f"🕒 **Waktu Sistem (WIB):** {waktu_sekarang}")

# --- EKSEKUSI WATCHLIST ---
df_w = get_data_watchlist(manual_list)
if not df_w.empty:
    df_f = df_w[(df_w['Harga'] >= price_range[0]) & (df_w['Harga'] <= price_range[1])]
    df_s = df_f.sort_values(by="Chg%", ascending=False).reset_index(drop=True)
    
    st.subheader(f"🏆 Top Gainers (Live Watchlist)")
    cols = st.columns(min(5, len(df_s)))
    for i in range(min(5, len(df_s))):
        with cols[i]:
            st.metric(label=df_s.iloc[i]['Ticker'], value=f"Rp {df_s.iloc[i]['Harga']:,.0f}", delta=f"{df_s.iloc[i]['Chg%']}%")
    with st.expander("📂 Lihat Seluruh Daftar Watchlist (30 Emiten)"):
        st.dataframe(df_s, use_container_width=True)

st.divider()

# --- ANALISIS GRAFIK FLEKSIBEL ---
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
        # PENTING: Konversi Zona Waktu untuk Sumbu X
        if tf != "1 Hari":
            df.index = df.index.tz_convert('Asia/Jakarta')
        
        cl = df['Close'].values.flatten()
        hi = df['High'].values.flatten()
        lo = df['Low'].values.flatten()
        op = df['Open'].values.flatten()
        vl = df['Volume'].values.flatten()

        # --- TAMPILAN HARGA REAL TERKINI ---
        current_real_price = float(cl[-1])
        open_price = float(op[-1])
        selisih = current_real_price - open_price
        pct_selisih = (selisih / open_price) * 100

        st.markdown(f"### 📈 Analisis: {target}.JK")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Harga Realtime", f"Rp {current_real_price:,.0f}", f"{selisih:,.0f} ({pct_selisih:.2f}%)")
        m2.metric("High (Bar)", f"Rp {hi[-1]:,.0f}")
        m3.metric("Low (Bar)", f"Rp {lo[-1]:,.0f}")
        m4.metric("Volume", f"{vl[-1]:,.0f}")

        # Prediksi 10 Periode
        y_pred = cl[-20:]
        slope, intercept = np.polyfit(np.arange(len(y_pred)), y_pred, 1)
        
        # Index Waktu Masa Depan
        last_dt = df.index[-1]
        step = (df.index[1] - df.index[0]) if len(df) > 1 else timedelta(minutes=1)
        future_dates = [last_dt + (step * i) for i in range(1, 11)]
        future_prices = slope * (np.arange(len(y_pred), len(y_pred) + 10)) + intercept

        # --- GRAFIK PROFESIONAL ---
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, row_heights=[0.7, 0.3])
        
        # Candlestick
        fig.add_trace(go.Candlestick(x=df.index, open=op, high=hi, low=lo, close=cl, name="Price"), row=1, col=1)
        
        # Garis Prediksi 10P (Kuning)
        fig.add_trace(go.Scatter(x=future_dates, y=future_prices, line=dict(color='yellow', width=3, dash='dot'), name="Prediksi 10P"), row=1, col=1)
        
        # Volume
        fig.add_trace(go.Bar(x=df.index, y=vl, name="Volume", marker_color='orange'), row=2, col=1)

        # Update Layout & Sumbu Waktu
        fig.update_layout(
            template="plotly_dark", 
            height=750,
            xaxis_rangeslider_visible=True,
            dragmode='pan',
            xaxis=dict(
                tickformat="%H:%M\n%d %b", # Memaksa Jam & Tanggal Muncul
                title="Waktu Realtime (WIB)"
            )
        )
        
        # Konfigurasi Scroll & Zoom
        config = {'scrollZoom': True, 'displayModeBar': True}
        st.plotly_chart(fig, use_container_width=True, config=config)
        
        st.success(f"🔮 **Target Harga:** Estimasi 10 periode ke depan adalah Rp {future_prices[-1]:,.0f}")

except Exception as e:
    st.error("Gagal memuat data. Periksa kode saham (contoh: BBCA, TLKM).")
