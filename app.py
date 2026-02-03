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

# Gaya UI Dark Mode
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetric"] { background-color: #1e2127; padding: 10px; border-radius: 10px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

# Zona Waktu Jakarta
tz = pytz.timezone('Asia/Jakarta')
waktu_sekarang = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')

st.title("🚀 StockPro Ultimate 2026")
st.write(f"🕒 **Waktu Realtime (WIB):** {waktu_sekarang}")

# --- 2. LIST 30 EMITEN TERPILIH (LQ45 & POPULER) ---
emiten_list = [
    "BBRI.JK", "TLKM.JK", "ASII.JK", "ADRO.JK", "GOTO.JK", 
    "BMRI.JK", "BBNI.JK", "UNTR.JK", "AMRT.JK", "BRIS.JK",
    "BBCA.JK", "CPIN.JK", "UNVR.JK", "ICBP.JK", "INDF.JK",
    "MDKA.JK", "ANAM.JK", "TINS.JK", "PTBA.JK", "ITMG.JK",
    "PGAS.JK", "INKP.JK", "TKIM.JK", "SMGR.JK", "INTP.JK",
    "KLBF.JK", "MIKA.JK", "HEAL.JK", "EXCL.JK", "ISAT.JK"
]

@st.cache_data(ttl=60)
def get_clean_watchlist(tickers):
    combined = []
    for t in tickers:
        try:
            d = yf.download(t, period="5d", interval="1d", progress=False)
            if not d.empty and len(d) >= 2:
                # Menangani Multi-Index secara aman
                close_prices = d['Close'].values.flatten()
                current_p = float(close_prices[-1])
                prev_p = float(close_prices[-2])
                change_p = ((current_p - prev_p) / prev_p) * 100
                combined.append({
                    "Ticker": t.replace(".JK", ""),
                    "Harga": current_p,
                    "Perubahan (%)": round(change_p, 2)
                })
        except: continue
    return pd.DataFrame(combined)

# --- 3. EKSEKUSI WATCHLIST ---
st.subheader("🏆 Top Gainers (Live Watchlist)")
df_watch = get_clean_watchlist(emiten_list)

if not df_watch.empty:
    df_sorted = df_watch.sort_values(by="Perubahan (%)", ascending=False).reset_index(drop=True)
    
    # Menampilkan 5 teratas dalam baris metrik
    cols = st.columns(5)
    for i in range(min(5, len(df_sorted))):
        with cols[i]:
            st.metric(
                label=str(df_sorted.iloc[i]['Ticker']), 
                value=f"Rp {float(df_sorted.iloc[i]['Harga']):,.0f}", 
                delta=f"{float(df_sorted.iloc[i]['Perubahan (%)']):.2f}%"
            )
    
    # Menampilkan sisa emiten dalam tabel yang bisa di-scroll
    with st.expander("📊 Lihat Seluruh 30 Emiten"):
        st.dataframe(df_sorted, use_container_width=True, hide_index=True)
else:
    st.warning("Menghubungkan ke data bursa...")

st.divider()

# --- 4. ANALISIS DETAIL & PREDIKSI ---
col_in1, col_in2 = st.columns([1, 1])
with col_in1:
    default_tk = df_sorted.iloc[0]['Ticker'] if not df_watch.empty else "BBRI"
    user_tk = st.selectbox("🔍 Pilih Saham untuk Analisis:", [t.replace(".JK","") for t in emiten_list])
with col_in2:
    timeframe = st.selectbox("⏱️ Timeframe Analisis:", ("1 Menit", "60 Menit", "1 Hari"))

tf_map = {"1 Menit": "1m", "60 Menit": "60m", "1 Hari": "1d"}
period_map = {"1 Menit": "1d", "60 Menit": "1mo", "1 Hari": "1y"}

# --- PENGAMBILAN DATA DETAIL ---
full_tk = f"{user_tk}.JK"

try:
    df = yf.download(full_tk, period=period_map[timeframe], interval=tf_map[timeframe], progress=False)
    
    if not df.empty:
        # Penanganan Timezone
        if timeframe != "1 Hari":
            df.index = df.index.tz_convert('Asia/Jakarta')

        # Data Flattening
        close_data = df['Close'].values.flatten()
        
        # 1. Bollinger Bands
        ma20 = pd.Series(close_data).rolling(window=20).mean()
        std20 = pd.Series(close_data).rolling(window=20).std()
        upper_bb = ma20 + (std20 * 2)
        lower_bb = ma20 - (std20 * 2)

        # 2. MACD
        ema12 = pd.Series(close_data).ewm(span=12, adjust=False).mean()
        ema26 = pd.Series(close_data).ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()

        # 3. Prediksi Linear 10 Periode
        clean_y = close_data[~np.isnan(close_data)][-20:]
        x_axis = np.arange(len(clean_y))
        slope, intercept = np.polyfit(x_axis, clean_y, 1)
        pred_p = slope * (len(clean_y) + 10) + intercept

        # --- GRAFIK ---
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                           vertical_spacing=0.05, row_heights=[0.5, 0.2, 0.3])

        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'].values.flatten(), 
                                   high=df['High'].values.flatten(), low=df['Low'].values.flatten(), 
                                   close=close_data, name="Price"), row=1, col=1)
        
        fig.add_trace(go.Scatter(x=df.index, y=upper_bb, line=dict(color='gray', width=1), name="Upper BB"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=lower_bb, line=dict(color='gray', width=1), name="Lower BB", fill='tonexty'), row=1, col=1)
        
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'].values.flatten(), name="Volume", marker_color='orange'), row=2, col=1)
        
        fig.add_trace(go.Scatter(x=df.index, y=macd_line, line=dict(color='cyan'), name="MACD"), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=signal_line, line=dict(color='red'), name="Signal"), row=3, col=1)

        fig.update_layout(template="plotly_dark", height=800, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # --- INFO PANEL ---
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Harga Terkini", f"Rp {close_data[-1]:,.0f}")
        with c2:
            st.info(f"🔮 Prediksi 10 Periode: Rp {pred_p:,.0f}")
        with c3:
            saran = "🚀 BELI" if slope > 0 and macd_line.iloc[-1] > signal_line.iloc[-1] else "📉 JUAL / WAIT"
            st.success(f"💡 Saran: {saran}")

except Exception as e:
    st.error(f"Pilih emiten lain atau cek koneksi.")
