import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import pytz

# 1. KONFIGURASI
st.set_page_config(page_title="StockPro Precision v3.6", layout="wide")
tz = pytz.timezone('Asia/Jakarta')

# --- SIDEBAR: PANEL KONTROL ---
st.sidebar.header("🛠️ Panel Kontrol")
st.sidebar.subheader("📝 Kelola Watchlist")
txt_input = st.sidebar.text_area("Input Kode (Tanpa .JK):", "BBRI, TLKM, ASII, ADRO, GOTO, BMRI, BBNI, UNTR, AMRT, BRIS, BBCA, ANTM, MDKA, PTBA")
manual_list = [f"{t.strip().upper()}.JK" for t in txt_input.split(",") if t.strip()][:30]

st.sidebar.subheader("💰 Filter Harga")
min_h = st.sidebar.number_input("Harga Minimum (Rp):", value=0)
max_h = st.sidebar.number_input("Harga Maksimum (Rp):", value=500000)

st.sidebar.subheader("↕️ Urutan Daftar Pantau")
sort_by = st.sidebar.selectbox("Susun Berdasarkan:", ("Nama Emiten", "Harga", "Perubahan (%)"))
sort_order = st.sidebar.radio("Aturan:", ("Menaik (A-Z / Low-High)", "Menurun (Z-A / High-Low)"))
ascending_logic = True if "Menaik" in sort_order else False
sort_col = {"Perubahan (%)": "Chg%", "Harga": "Harga", "Nama Emiten": "Ticker"}[sort_by]

@st.cache_data(ttl=15)
def get_data_watchlist(tickers):
    combined = []
    for t in tickers:
        try:
            d = yf.download(t, period="2d", interval="1d", progress=False)
            if not d.empty and len(d) >= 2:
                cl_data = d['Close'].values.flatten()
                combined.append({
                    "Ticker": t.replace(".JK", ""), 
                    "Harga": float(cl_data[-1]), 
                    "Chg%": round(((cl_data[-1]-cl_data[-2])/cl_data[-2])*100, 2)
                })
        except: continue
    return pd.DataFrame(combined)

# --- HEADER ---
st.title("🚀 StockPro Precision Intelligence")
st.write(f"🕒 **Update:** {datetime.now(tz).strftime('%d %b %Y | %H:%M:%S')} WIB")

# --- BAGIAN 1: WATCHLIST TERPANTAU (EXPANDABLE LIST) ---
df_w = get_data_watchlist(manual_list)
ticker_list = []

if not df_w.empty:
    df_f = df_w[(df_w['Harga'] >= min_h) & (df_w['Harga'] <= max_h)]
    df_s = df_f.sort_values(by=sort_col, ascending=ascending_logic)
    ticker_list = df_s['Ticker'].tolist()
    
    with st.expander("📋 Lihat Daftar Pantau (Watchlist)", expanded=False):
        if not df_s.empty:
            st.dataframe(
                df_s.style.format({"Harga": "{:,.0f}", "Chg%": "{:+.2f}%"}),
                use_container_width=True, hide_index=True
            )
        else:
            st.info("Tidak ada saham yang sesuai kriteria filter.")

st.divider()

# --- BAGIAN 2: ANALISIS (DUAL INPUT: DROP DOWN & FREE TEXT) ---
st.subheader("🔍 Analisis Teknikal & Prediksi AI")
ca, cb = st.columns([1, 1])

with ca:
    # Gabungan fitur: Bisa pilih dari list atau ketik manual
    # Gunakan session state agar dropdown dan text input sinkron
    if 'ticker_input' not in st.session_state:
        st.session_state.ticker_input = ticker_list[0] if ticker_list else "BBRI"

    # Dropdown untuk memilih dari watchlist
    selected_from_list = st.selectbox("Pilih dari Watchlist:", options=ticker_list, 
                                     index=ticker_list.index(st.session_state.ticker_input) if st.session_state.ticker_input in ticker_list else 0)
    
    # Free Text untuk input manual (sinkron dengan pilihan dropdown)
    target = st.text_input("Atau ketik Manual (Contoh: GOTO):", value=selected_from_list).upper()
    st.session_state.ticker_input = target

with cb:
    tf = st.selectbox("⏱️ Timeframe:", ("1 Menit", "60 Menit", "1 Hari"))

tf_m = {"1 Menit": "1m", "60 Menit": "60m", "1 Hari": "1d"}
pd_m = {"1 Menit": "1d", "60 Menit": "1mo", "1 Hari": "2y"}

try:
    df = yf.download(f"{target}.JK", period=pd_m[tf], interval=tf_m[tf], progress=False)
    
    if not df.empty and len(df) > 40:
        if tf != "1 Hari": df.index = df.index.tz_convert('Asia/Jakarta')
        cl, hi, lo, op, vl = [df[c].values.flatten() for c in ['Close', 'High', 'Low', 'Open', 'Volume']]

        # --- INDIKATOR ---
        e12 = pd.Series(cl).ewm(span=12).mean(); e26 = pd.Series(cl).ewm(span=26).mean()
        macd = e12 - e26; sig = macd.ewm(span=9).mean()
        diff = pd.Series(cl).diff(); g = (diff.where(diff > 0, 0)).rolling(14).mean(); l_loss = (-diff.where(diff < 0, 0)).rolling(14).mean()
        rsi = (100 - (100 / (1 + (g/(l_loss.replace(0, 0.001)))))).fillna(50)

        # --- PREDIKSI WEIGHTED ---
        f_prices, f_dates = [], []
        t_cl = list(cl[-40:])
        last_dt = df.index[-1]
        step = df.index[-1] - df.index[-2] if len(df) > 1 else timedelta(minutes=1)
        weights = np.exp(np.linspace(-1., 0., 40)); weights /= weights.sum()

        for i in range(1, 11):
            current_window = np.array(t_cl[-40:])
            weighted_mean = np.sum(current_window * weights)
            slope = (current_window[-1] - weighted_mean) / 40
            decay = 1 / (1 + (i * 0.2))
            move = (slope * decay) + (np.random.normal(0, np.std(current_window)*0.1) * 0.05)
            next_p = t_cl[-1] + move
            f_prices.append(next_p); f_dates.append(last_dt + (step * i)); t_cl.append(next_p)

        # --- GRAFIK ---
        
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, 
                           row_heights=[0.8, 0.2], subplot_titles=(f"Analisis: {target}", "Volume"))
        
        fig.add_trace(go.Candlestick(x=df.index, open=op, high=hi, low=lo, close=cl, name="Price"), row=1, col=1)
        fig.add_trace(go.Scatter(x=f_dates, y=f_prices, line=dict(color='yellow', width=3, dash='dot'), name="Predict"), row=1, col=1)

        # Indikator Overlay
        fig.add_trace(go.Scatter(x=df.index, y=macd + cl[-1], line=dict(color='cyan', width=1.5), name="MACD Group", legendgroup="macd", visible='legendonly'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=sig + cl[-1], line=dict(color='orange', width=1, dash='dot'), name="MACD Signal", legendgroup="macd", showlegend=False, visible='legendonly'), row=1, col=1)
        rsi_scaled = (rsi / 100) * (cl.max() - cl.min()) + cl.min()
        fig.add_trace(go.Scatter(x=df.index, y=rsi_scaled, line=dict(color='magenta', width=1.5), name="RSI Overlay", visible='legendonly'), row=1, col=1)

        fig.add_trace(go.Bar(x=df.index, y=vl, marker_color=['red' if c < o else 'green' for c, o in zip(cl, op)], name="Volume"), row=2, col=1)

        fig.update_xaxes(showticklabels=True, tickformat="%H:%M\n%d %b", row=1, col=1)
        fig.update_xaxes(showticklabels=True, tickformat="%H:%M\n%d %b", row=2, col=1)
        fig.update_layout(template="plotly_dark", height=800, xaxis_rangeslider_visible=False, hovermode="x unified", legend=dict(orientation="h", y=1.1))
        
        st.plotly_chart(fig, use_container_width=True)
        st.table(pd.DataFrame({"Waktu": [d.strftime('%H:%M (%d %b)') for d in f_dates], "Estimasi": [f"Rp {p:,.2f}" for p in f_prices]}))

except Exception as e:
    st.error(f"Masukkan kode yang valid atau tunggu data memuat. (Detail: {e})")
