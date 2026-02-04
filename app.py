import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime
import pytz

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="StockPro Ultimate 2026", layout="wide")

# Custom CSS agar tampilan metrik rapi
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetric"] { background-color: #1e2127; padding: 10px; border-radius: 10px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

tz = pytz.timezone('Asia/Jakarta')
st.title("🚀 StockPro Ultimate 2026")
st.write(f"🕒 **Waktu Realtime (WIB):** {datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')}")

# --- 2. SIDEBAR: KONTROL INPUT & FILTER ---
st.sidebar.header("🛠️ Kontrol Watchlist")

# Fitur Input Manual
st.sidebar.subheader("📝 Input Manual")
txt_input = st.sidebar.text_area("Masukkan Kode (Tanpa .JK, pisah koma):", 
                                "BBRI, TLKM, ASII, ADRO, GOTO, BMRI, BBNI, UNTR, AMRT, BRIS")
manual_list = [t.strip().upper() for t in txt_input.split(",") if t.strip()][:30]
emiten_full = [f"{t}.JK" for t in manual_list]

# Fitur Filter Harga
st.sidebar.subheader("💰 Filter Harga")
min_h = st.sidebar.number_input("Harga Min:", value=50, step=50)
max_h = st.sidebar.number_input("Harga Max:", value=100000, step=1000)

@st.cache_data(ttl=30)
def get_data_watchlist(tickers):
    combined = []
    for t in tickers:
        try:
            d = yf.download(t, period="5d", interval="1d", progress=False)
            if not d.empty:
                # Perbaikan: Flattening data untuk cegah TypeError
                c_prices = d['Close'].values.flatten()
                curr = float(c_prices[-1])
                prev = float(c_prices[-2])
                chg = ((curr - prev) / prev) * 100
                combined.append({"Ticker": t.replace(".JK", ""), "Harga": curr, "Perubahan (%)": round(chg, 2)})
        except: continue
    return pd.DataFrame(combined)

# --- 3. TAMPILAN WATCHLIST ---
df_watch = get_data_watchlist(emiten_full)

if not df_watch.empty:
    # Filter harga berdasarkan input sidebar
    df_filtered = df_watch[(df_watch['Harga'] >= min_h) & (df_watch['Harga'] <= max_h)]
    df_sorted = df_filtered.sort_values(by="Perubahan (%)", ascending=False).reset_index(drop=True)
    
    st.subheader(f"🏆 Performa Saham (Filter: Rp {min_h:,} - Rp {max_h:,})")
    
    if not df_sorted.empty:
        # Menampilkan Metrik 5 Teratas
        cols = st.columns(min(5, len(df_sorted)))
        for i in range(min(5, len(df_sorted))):
            with cols[i]:
                st.metric(label=df_sorted.iloc[i]['Ticker'], 
                          value=f"Rp {df_sorted.iloc[i]['Harga']:,.0f}", 
                          delta=f"{df_sorted.iloc[i]['Perubahan (%)']:.2f}%")
        
        with st.expander("📊 Lihat Tabel Lengkap 30 Emiten"):
            st.dataframe(df_sorted, use_container_width=True, hide_index=True)
    else:
        st.warning("Tidak ada saham di rentang harga tersebut.")
else:
    st.error("Data tidak ditemukan. Pastikan format kode benar (Contoh: BBRI, BBCA).")

st.divider()

# --- 4. ANALISIS DETAIL (MANUAL INPUT) ---
st.subheader("🔍 Analisis Teknikal & Prediksi")
ca, cb = st.columns([1, 1])
with ca:
    # Bisa isi manual apa saja
    target_tk = st.text_input("Ketik Kode Saham untuk Grafik (Contoh: BBCA):", 
                              value=df_sorted.iloc[0]['Ticker'] if not df_sorted.empty else "BBRI").upper()
with cb:
    tf = st.selectbox("Pilih Timeframe:", ("1 Menit", "60 Menit", "1 Hari"))

tf_map = {"1 Menit": "1m", "60 Menit": "60m", "1 Hari": "1d"}
pd_map = {"1 Menit": "1d", "60 Menit": "1mo", "1 Hari": "1y"}

# --- PENGAMBILAN DATA GRAFIK ---
try:
    df_chart = yf.download(f"{target_tk}.JK", period=pd_map[tf], interval=tf_map[tf], progress=False)
    
    if not df_chart.empty:
        # Sinkronisasi Waktu
        if tf != "1 Hari": df_chart.index = df_chart.index.tz_convert('Asia/Jakarta')
        
        # Ekstrak data mentah (Flatten)
        cl = df_chart['Close'].values.flatten()
        op = df_chart['Open'].values.flatten()
        hi = df_chart['High'].values.flatten()
        lo = df_chart['Low'].values.flatten()
        vl = df_chart['Volume'].values.flatten()

        # KALKULASI INDIKATOR
        # 1. Bollinger Bands
        ma20 = pd.Series(cl).rolling(20).mean()
        std20 = pd.Series(cl).rolling(20).std()
        u_bb, l_bb = ma20 + (std20 * 2), ma20 - (std20 * 2)

        # 2. RSI
        diff = pd.Series(cl).diff()
        g = (diff.where(diff > 0, 0)).rolling(14).mean()
        l = (-diff.where(diff < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + (g/l)))

        # 3. MACD
        e12 = pd.Series(cl).ewm(span=12).mean()
        e26 = pd.Series(cl).ewm(span=26).mean()
        macd = e12 - e26
        sig = macd.ewm(span=9).mean()

        # 4. Prediksi 10 Periode
        clean_y = cl[~np.isnan(cl)][-20:]
        slp, inter = np.polyfit(np.arange(len(clean_y)), clean_y, 1)
        target_p = slp * (len(clean_y) + 10) + inter

        # --- PLOTTING ---
        fig = make_subplots(rows=4, cols=1, shared_xaxes=True, 
                           vertical_spacing=0.02, row_heights=[0.4, 0.1, 0.2, 0.2],
                           subplot_titles=("Price & BB", "Volume", "MACD", "RSI"))

        # Row 1: Candle
        fig.add_trace(go.Candlestick(x=df_chart.index, open=op, high=hi, low=lo, close=cl, name="Price"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_chart.index, y=u_bb, line=dict(color='white', width=1), name="Upper BB"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_chart.index, y=l_bb, line=dict(color='white', width=1), name="Lower BB", fill='tonexty'), row=1, col=1)
        
        # Row 2: Volume
        fig.add_trace(go.Bar(x=df_chart.index, y=vl, name="Volume", marker_color='orange'), row=2, col=1)
        
        # Row 3: MACD
        fig.add_trace(go.Scatter(x=df_chart.index, y=macd, name="MACD", line=dict(color='cyan')), row=3, col=1)
        fig.add_trace(go.Scatter(x=df_chart.index, y=sig, name="Signal", line=dict(color='red')), row=3, col=1)
        
        # Row 4: RSI
        fig.add_trace(go.Scatter(x=df_chart.index, y=rsi, name="RSI", line=dict(color='yellow')), row=4, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color="red", row=4, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="green", row=4, col=1)

        fig.update_layout(template="plotly_dark", height=900, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # INFO BOX
        m1, m2, m3 = st.columns(3)
        m1.metric("Harga Live", f"Rp {cl[-1]:,.0f}")
        m2.info(f"🔮 Target 10 {tf}: Rp {target_p:,.0f}")
        
        # Logika Sinyal
        rsi_val = rsi.iloc[-1]
        if rsi_val < 35: status = "🔥 BELI (Oversold)"
        elif rsi_val > 65: status = "⚠️ JUAL (Overbought)"
        else: status = "⚖️ HOLD / WAIT"
        m3.success(f"Sinyal RSI: {status}")

except Exception as e:
    st.error(f"Gagal memuat grafik. Pastikan kode saham benar. (Error: {e})")
