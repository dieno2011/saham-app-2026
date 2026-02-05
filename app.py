import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import pytz

# 1. KONFIGURASI DASAR
st.set_page_config(page_title="StockPro Precision v4.7", layout="wide")
tz = pytz.timezone('Asia/Jakarta')

if 'ticker' not in st.session_state:
    st.session_state.ticker = "BBRI"

# --- SIDEBAR: PANEL KONTROL ---
st.sidebar.header("🛠️ Panel Kontrol")
st.sidebar.subheader("📝 Kelola Watchlist")
txt_input = st.sidebar.text_area("Input Kode (Tanpa .JK):", "BBRI, TLKM, ASII, ADRO, GOTO, BMRI, BBNI, UNTR, AMRT, BRIS, BBCA, ANTM, MDKA, PTBA")
manual_list = [f"{t.strip().upper()}.JK" for t in txt_input.split(",") if t.strip()][:30]

st.sidebar.subheader("💰 Filter Harga")
min_h = st.sidebar.number_input("Harga Minimum (Rp):", value=0)
max_h = st.sidebar.number_input("Harga Maksimum (Rp):", value=500000)

st.sidebar.subheader("↕️ Urutan Daftar Pantau")
sort_options = {"Nama Emiten": "Ticker", "Harga": "Harga", "Perubahan (%)": "Chg%"}
sort_by_label = st.sidebar.selectbox("Susun Berdasarkan:", list(sort_options.keys()))
sort_order = st.sidebar.radio("Aturan:", ("Menaik (A-Z / Low-High)", "Menurun (Z-A / High-Low)"))
ascending_logic = True if "Menaik" in sort_order else False

@st.cache_data(ttl=30)
def get_watchlist_data(tickers):
    combined = []
    for t in tickers:
        try:
            d = yf.download(t, period="2d", interval="1d", progress=False)
            if not d.empty and len(d) >= 2:
                cl = d['Close'].values.flatten()
                combined.append({
                    "Ticker": t.replace(".JK", ""), 
                    "Harga": float(cl[-1]),
                    "High": float(d['High'].values.flatten()[-1]),
                    "Low": float(d['Low'].values.flatten()[-1]),
                    "Chg%": round(((cl[-1]-cl[-2])/cl[-2])*100, 2)
                })
        except: continue
    return pd.DataFrame(combined)

# --- HEADER ---
st.title("🚀 StockPro Precision Intelligence")
st.write(f"🕒 **Update:** {datetime.now(tz).strftime('%d %b %Y | %H:%M:%S')} WIB")

# --- BAGIAN 1: WATCHLIST (SINKRONISASI KLIK) ---
df_w = get_watchlist_data(manual_list)
if not df_w.empty:
    df_f = df_w[(df_w['Harga'] >= min_h) & (df_w['Harga'] <= max_h)]
    df_s = df_f.sort_values(by=sort_options[sort_by_label], ascending=ascending_logic)
    
    with st.expander("📋 Daftar Pantau (Klik Baris untuk Analisis)", expanded=True):
        event = st.dataframe(
            df_s.style.format({"Harga": "{:,.0f}", "High": "{:,.0f}", "Low": "{:,.0f}", "Chg%": "{:+.2f}%"}),
            use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row"
        )
        if event and event.get("selection") and event["selection"]["rows"]:
            selected_ticker = df_s.iloc[event["selection"]["rows"][0]]['Ticker']
            if selected_ticker != st.session_state.ticker:
                st.session_state.ticker = selected_ticker
                st.rerun()

st.divider()

# --- BAGIAN 2: ANALISIS & TIMEFRAME ---
ca, cb = st.columns([1, 1])
with ca:
    input_manual = st.text_input("📝 Kode Saham Analisis:", value=st.session_state.ticker).upper()
    st.session_state.ticker = input_manual
with cb:
    tf_label = st.selectbox("⏱️ Timeframe:", 
                      ("1 Menit", "5 Menit", "10 Menit", "15 Menit", "30 Menit", 
                       "60 Menit", "2 Jam", "3 Jam", "1 Hari", "1 Minggu", "1 Bulan"), index=8)

# Perbaikan Mapping untuk sinkronisasi interval
tf_map = {"1 Menit":"1m", "5 Menit":"5m", "10 Menit":"10m", "15 Menit":"15m", "30 Menit":"30m", "60 Menit":"60m", "2 Jam":"60m", "3 Jam":"60m", "1 Hari":"1d", "1 Minggu":"1wk", "1 Bulan":"1mo"}
pd_map = {"1 Menit":"1d", "5 Menit":"5d", "10 Menit":"5d", "15 Menit":"5d", "30 Menit":"5d", "60 Menit":"1mo", "2 Jam":"1mo", "3 Jam":"1mo", "1 Hari":"2y", "1 Minggu":"max", "1 Bulan":"max"}

# Konversi label ke timedelta untuk sinkronisasi tabel proyeksi
delta_map = {
    "1 Menit": timedelta(minutes=1), "5 Menit": timedelta(minutes=5), "10 Menit": timedelta(minutes=10),
    "15 Menit": timedelta(minutes=15), "30 Menit": timedelta(minutes=30), "60 Menit": timedelta(hours=1),
    "2 Jam": timedelta(hours=2), "3 Jam": timedelta(hours=3), "1 Hari": timedelta(days=1),
    "1 Minggu": timedelta(weeks=1), "1 Bulan": timedelta(days=30)
}

try:
    df = yf.download(f"{st.session_state.ticker}.JK", period=pd_map[tf_label], interval=tf_map[tf_label], progress=False)
    
    if not df.empty and len(df) > 30:
        if tf_label not in ["1 Hari", "1 Minggu", "1 Bulan"]: 
            df.index = df.index.tz_convert('Asia/Jakarta')
            
        cl, hi, lo, op, vl = [df[c].values.flatten() for c in ['Close', 'High', 'Low', 'Open', 'Volume']]

        # --- INDIKATOR ---
        ma20 = pd.Series(cl).rolling(20).mean()
        ma50 = pd.Series(cl).rolling(50).mean()
        l14, h14 = pd.Series(lo).rolling(14).min(), pd.Series(hi).rolling(14).max()
        stoch_k = 100 * ((pd.Series(cl) - l14) / (h14 - l14))
        stoch_d = stoch_k.rolling(3).mean()
        diff = pd.Series(cl).diff(); g = (diff.where(diff > 0, 0)).rolling(14).mean(); l_loss = (-diff.where(diff < 0, 0)).rolling(14).mean()
        rsi = (100 - (100 / (1 + (g/(l_loss.replace(0, 0.001)))))).fillna(50)

        # --- PREDIKSI & SINKRONISASI WAKTU TABEL ---
        f_prices, f_dates = [], []
        t_cl = list(cl[-40:])
        last_dt = df.index[-1]
        
        # Gunakan delta_map agar step waktu sinkron 100% dengan pilihan user
        step = delta_map[tf_label]
        
        weights = np.exp(np.linspace(-1., 0., 40)); weights /= weights.sum()

        for i in range(1, 11):
            window = np.array(t_cl[-40:])
            slope = (window[-1] - np.sum(window * weights)) / 40
            move = (slope * (1/(1+i*0.1))) + (np.random.normal(0, np.std(window[-10:])*0.05))
            next_p = t_cl[-1] + move
            f_prices.append(next_p)
            f_dates.append(last_dt + (step * i))
            t_cl.append(next_p)

        # --- GRAFIK ---
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, 
                           row_heights=[0.6, 0.2, 0.2], subplot_titles=(f"Analisis: {st.session_state.ticker}", "Stochastic (14,3,3)", "Volume"))
        
        fig.add_trace(go.Candlestick(x=df.index, open=op, high=hi, low=lo, close=cl, name="Price"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=ma20, line=dict(color='#00FFFF', width=1.5), name="MA20"), row=1, col=1)
        fig.add_trace(go.Scatter(x=f_dates, y=f_prices, line=dict(color='yellow', width=2, dash='dot'), name="Predict"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=stoch_k, line=dict(color='white', width=1), name="%K"), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=stoch_d, line=dict(color='orange', width=1), name="%D"), row=2, col=1)
        fig.add_trace(go.Bar(x=df.index, y=vl, marker_color=['#FF4B4B' if c < o else '#00FF7F' for c, o in zip(cl, op)], name="Volume"), row=3, col=1)

        fig.update_layout(template="plotly_dark", height=950, xaxis_rangeslider_visible=False, hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

        # --- TABEL PROYEKSI (SINKRON 100% DENGAN TIMEFRAME) ---
        st.subheader(f"📊 Tabel Estimasi Harga (Interval {tf_label})")
        fmt = '%d %b %H:%M' if tf_label not in ["1 Hari", "1 Minggu", "1 Bulan"] else '%d %b %Y'
        df_res = pd.DataFrame({
            "Periode": [f"+{i} ({tf_label})" for i in range(1, 11)],
            "Waktu Estimasi": [d.strftime(fmt) for d in f_dates],
            "Prediksi Harga": [f"Rp {p:,.2f}" for p in f_prices],
            "Potensi Chg (%)": [f"{((p - cl[-1])/cl[-1])*100:+.2f}%" for p in f_prices]
        })
        st.table(df_res)

except Exception as e:
    st.info("Pilih emiten atau masukkan kode saham untuk memulai.")
