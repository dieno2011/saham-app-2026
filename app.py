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
tz = pytz.timezone('Asia/Jakarta')

# --- SIDEBAR: KONTROL TOTAL ---
st.sidebar.header("🛠️ Panel Kontrol")

# A. INPUT MANUAL WATCHLIST
st.sidebar.subheader("📝 Kelola Watchlist")
txt_input = st.sidebar.text_area("Input Kode (Tanpa .JK, pisah koma):", 
                                "BBRI, TLKM, ASII, ADRO, GOTO, BMRI, BBNI, UNTR, AMRT, BRIS, BBCA, ANTM, MDKA, PTBA, ITMG")
manual_list = [f"{t.strip().upper()}.JK" for t in txt_input.split(",") if t.strip()][:30]

# B. FILTER HARGA MANUAL
st.sidebar.subheader("💰 Filter Harga")
min_h = st.sidebar.number_input("Harga Minimum (Rp):", value=0, step=50)
max_h = st.sidebar.number_input("Harga Maksimum (Rp):", value=200000, step=100)

# C. PILIHAN SORTING
st.sidebar.subheader("↕️ Susunan Watchlist")
sort_by = st.sidebar.selectbox("Susun Berdasarkan:", ("Perubahan (%)", "Harga", "Nama Emiten"))
sort_order = st.sidebar.radio("Aturan Susunan:", ("Menurun (High to Low / Z-A)", "Menaik (Low to High / A-Z)"))

ascending_logic = True if sort_order == "Menaik (Low to High / A-Z)" else False
sort_col = {"Perubahan (%)": "Chg%", "Harga": "Harga", "Nama Emiten": "Ticker"}[sort_by]

@st.cache_data(ttl=15)
def get_data_watchlist(tickers):
    combined = []
    for t in tickers:
        try:
            d = yf.download(t, period="2d", interval="1d", progress=False)
            if not d.empty:
                # Menghindari error Multi-Index
                curr = float(d['Close'].iloc[-1])
                prev = float(d['Close'].iloc[-2]) if len(d) > 1 else curr
                combined.append({"Ticker": t.replace(".JK", ""), "Harga": curr, "Chg%": round(((curr-prev)/prev)*100, 2)})
        except: continue
    return pd.DataFrame(combined)

# --- HEADER ---
st.title("🚀 StockPro Ultimate 2026")
st.write(f"🕒 **Waktu Realtime (WIB):** {datetime.now(tz).strftime('%d %b %Y | %H:%M:%S')}")

# --- WATCHLIST ---
df_w = get_data_watchlist(manual_list)
df_s = pd.DataFrame() # Inisialisasi default

if not df_w.empty:
    df_f = df_w[(df_w['Harga'] >= min_h) & (df_w['Harga'] <= max_h)]
    if not df_f.empty:
        df_s = df_f.sort_values(by=sort_col, ascending=ascending_logic).reset_index(drop=True)
        st.subheader(f"🏆 Watchlist Terpantau")
        cols = st.columns(min(5, len(df_s)))
        for i in range(min(5, len(df_s))):
            with cols[i]:
                st.metric(label=df_s.iloc[i]['Ticker'], value=f"Rp {df_s.iloc[i]['Harga']:,.0f}", delta=f"{df_s.iloc[i]['Chg%']}%")
        with st.expander("📂 Lihat Seluruh Daftar Watchlist"):
            st.dataframe(df_s, use_container_width=True, hide_index=True)

st.divider()

# --- ANALISIS GRAFIK LENGKAP ---
ca, cb = st.columns([1, 1])
with ca:
    default_ticker = df_s.iloc[0]['Ticker'] if not df_s.empty else "BBRI"
    target_input = st.text_input("🔍 Kode Saham Analisis:", value=default_ticker).upper()
with cb:
    tf = st.selectbox("⏱️ Pilih Timeframe:", ("1 Menit", "60 Menit", "1 Hari"))

tf_m, pd_m = {"1 Menit": "1m", "60 Menit": "60m", "1 Hari": "1d"}, {"1 Menit": "1d", "60 Menit": "1mo", "1 Hari": "1y"}

try:
    # Mengambil data yang cukup untuk look-back 30 periode
    df = yf.download(f"{target_input}.JK", period="2y" if tf=="1 Hari" else "5d", interval=tf_m[tf], progress=False)
    
    if len(df) > 30:
        if tf != "1 Hari": df.index = df.index.tz_convert('Asia/Jakarta')
        
        # Flattening data untuk menghindari error index
        cl = df['Close'].values.flatten()
        hi = df['High'].values.flatten()
        lo = df['Low'].values.flatten()
        op = df['Open'].values.flatten()
        vl = df['Volume'].values.flatten()

        # --- INDIKATOR TEKNIS ---
        ma20 = pd.Series(cl).rolling(20).mean()
        std20 = pd.Series(cl).rolling(20).std()
        u_bb, l_bb = ma20 + (std20 * 2), ma20 - (std20 * 2)
        diff = pd.Series(cl).diff(); gain = (diff.where(diff > 0, 0)).rolling(14).mean(); loss = (-diff.where(diff < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + (gain/loss)))
        e12 = pd.Series(cl).ewm(span=12, adjust=False).mean(); e26 = pd.Series(cl).ewm(span=26, adjust=False).mean()
        macd_line = e12 - e26; signal_line = macd_line.ewm(span=9, adjust=False).mean()

        # --- PREDIKSI 10 PERIODE (LOOK-BACK 30P) ---
        future_prices, future_dates = [], []
        sim_cl, sim_vl = list(cl[-30:]), list(vl[-30:])
        last_dt = df.index[-1]
        
        # Penentuan step waktu
        if len(df) > 1: step = df.index[-1] - df.index[-2]
        else: step = timedelta(minutes=1)

        for i in range(1, 11):
            y_lookback = np.array(sim_cl[-30:])
            slope, _ = np.polyfit(np.arange(30), y_lookback, 1)
            
            vol_avg = np.mean(sim_vl[-30:])
            vol_ratio = sim_vl[-1] / vol_avg if vol_avg > 0 else 1
            
            # Momentum weight
            curr_rsi = rsi.iloc[-1] if not np.isnan(rsi.iloc[-1]) else 50
            rsi_w = (35 - curr_rsi) * 0.002 if curr_rsi < 35 else (65 - curr_rsi) * 0.002 if curr_rsi > 65 else 0
            
            vol_impact = (sim_cl[-1] * 0.0005 * vol_ratio) if sim_cl[-1] > sim_cl[-2] else -(sim_cl[-1] * 0.0005 * vol_ratio)
            
            next_p = sim_cl[-1] + slope + (sim_cl[-1] * rsi_w) + vol_impact
            future_prices.append(next_p)
            future_dates.append(last_dt + (step * i))
            
            sim_cl.append(next_p)
            sim_vl.append(vol_avg)

        # --- DISPLAY METRICS ---
        st.markdown(f"### 📈 Live: {target_input}.JK")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Harga Terkini", f"Rp {cl[-1]:,.0f}", f"{cl[-1]-op[-1]:,.0f}")
        m2.metric("MACD Status", "Bullish" if macd_line.iloc[-1] > signal_line.iloc[-1] else "Bearish")
        m3.metric("RSI (14)", f"{rsi.iloc[-1]:.2f}")
        m4.metric("Prediksi T+10", f"Rp {future_prices[-1]:,.0f}")

        # --- GRAFIK ---
        fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.4, 0.15, 0.2, 0.25],
                           subplot_titles=("Price & Predictive Intelligence (10P)", "Volume", "MACD", "RSI"))
        
        fig.add_trace(go.Candlestick(x=df.index, open=op, high=hi, low=lo, close=cl, name="Price"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=u_bb, line=dict(color='rgba(255,255,255,0.2)'), name="Upper BB"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=l_bb, line=dict(color='rgba(255,255,255,0.2)'), name="Lower BB", fill='tonexty'), row=1, col=1)
        fig.add_trace(go.Scatter(x=future_dates, y=future_prices, line=dict(color='yellow', width=3, dash='dot'), name="Prediction 10P"), row=1, col=1)
        
        vol_colors = ['red' if c < o else 'green' for c, o in zip(cl, op)]
        fig.add_trace(go.Bar(x=df.index, y=vl, name="Volume", marker_color=vol_colors), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=macd_line, name="MACD", line=dict(color='cyan')), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=signal_line, name="Signal", line=dict(color='red')), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=rsi, name="RSI", line=dict(color='magenta')), row=4, col=1)
        
        fig.update_layout(template="plotly_dark", height=1000, xaxis_rangeslider_visible=False, xaxis4=dict(tickformat="%H:%M\n%d %b"))
        st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

        # --- TABEL PREDIKSI ---
        st.subheader("📋 Estimasi Harga 10 Periode Ke Depan")
        pred_df = pd.DataFrame({
            "Periode": [f"T+{i}" for i in range(1, 11)],
            "Waktu Estimasi": [d.strftime('%H:%M:%S (%d %b)') for d in future_dates],
            "Harga Proyeksi": [f"Rp {p:,.2f}" for p in future_prices]
        })
        st.table(pred_df)
    else:
        st.warning("Data tidak cukup untuk melakukan analisa teknikal (minimal 30 bar).")

except Exception as e:
    st.error(f"Gagal memproses data emiten {target_input}. Pastikan kode benar. (Detail: {e})")
