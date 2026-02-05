import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import pytz

# 1. KONFIGURASI DASAR
st.set_page_config(page_title="StockPro Precision v4.4", layout="wide")
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

# --- BAGIAN 1: WATCHLIST (INTERAKTIF) ---
df_w = get_watchlist_data(manual_list)
if not df_w.empty:
    df_f = df_w[(df_w['Harga'] >= min_h) & (df_w['Harga'] <= max_h)]
    df_s = df_f.sort_values(by=sort_options[sort_by_label], ascending=ascending_logic)
    
    with st.expander("📋 Daftar Pantau (Klik Baris untuk Analisis)", expanded=True):
        selection = st.dataframe(
            df_s.style.format({"Harga": "{:,.0f}", "High": "{:,.0f}", "Low": "{:,.0f}", "Chg%": "{:+.2f}%"}),
            use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row"
        )
        if selection and selection.selection.rows:
            new_selection = df_s.iloc[selection.selection.rows[0]]['Ticker']
            if new_selection != st.session_state.ticker:
                st.session_state.ticker = new_selection
                st.rerun()

st.divider()

# --- BAGIAN 2: ANALISIS ---
ca, cb = st.columns([1, 1])
with ca:
    target = st.text_input("📝 Kode Saham Analisis:", value=st.session_state.ticker).upper()
    st.session_state.ticker = target
with cb:
    tf_label = st.selectbox("⏱️ Timeframe:", 
                      ("1 Menit", "5 Menit", "10 Menit", "15 Menit", "30 Menit", 
                       "60 Menit", "2 Jam", "3 Jam", "1 Hari", "1 Minggu", "1 Bulan"), index=8)

tf_map = {"1 Menit":"1m", "5 Menit":"5m", "10 Menit":"10m", "15 Menit":"15m", "30 Menit":"30m", "60 Menit":"60m", "2 Jam":"60m", "3 Jam":"60m", "1 Hari":"1d", "1 Minggu":"1wk", "1 Bulan":"1mo"}
pd_map = {"1 Menit":"1d", "5 Menit":"5d", "10 Menit":"5d", "15 Menit":"5d", "30 Menit":"5d", "60 Menit":"1mo", "2 Jam":"1mo", "3 Jam":"1mo", "1 Hari":"2y", "1 Minggu":"max", "1 Bulan":"max"}

try:
    df = yf.download(f"{st.session_state.ticker}.JK", period=pd_map[tf_label], interval=tf_map[tf_label], progress=False)
    
    if not df.empty and len(df) > 50:
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

        # --- SUMMARY ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Live Price", f"Rp {cl[-1]:,.0f}")
        m2.metric("High", f"Rp {hi.max():,.0f}")
        m3.metric("Low", f"Rp {lo.min():,.0f}")
        saran = "STRONG BUY" if rsi.iloc[-1] < 30 else "STRONG SELL" if rsi.iloc[-1] > 70 else "HOLD"
        m4.markdown(f"**Saran AI:** `{saran}`")

        # --- FORMULA PREDIKSI TERBARU (DI-PERBAIKI) ---
        f_prices, f_dates = [], []
        t_cl = list(cl[-40:])
        last_dt = df.index[-1]
        step = df.index[-1] - df.index[-2] if len(df) > 1 else timedelta(minutes=1)
        
        # Bobot Eksponensial: Fokus pada data paling baru
        weights = np.exp(np.linspace(-1., 0., 40))
        weights /= weights.sum()

        for i in range(1, 11):
            window = np.array(t_cl[-40:])
            weighted_mean = np.sum(window * weights)
            # Slope: Arah tren berdasarkan selisih harga terakhir dengan rata-rata berbobot
            slope = (window[-1] - weighted_mean) / 40
            # Faktor peluruhan (decay) agar prediksi tidak "terbang" terlalu jauh
            decay = 1 / (1 + (i * 0.1))
            move = (slope * decay) + (np.random.normal(0, np.std(window[-10:]) * 0.05))
            next_p = t_cl[-1] + move
            f_prices.append(next_p)
            f_dates.append(last_dt + (step * i))
            t_cl.append(next_p)

        # --- GRAFIK ---
        
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, 
                           row_heights=[0.6, 0.2, 0.2], subplot_titles=("Price & Prediction", "Stochastic Oscillator", "Volume"))
        
        fig.add_trace(go.Candlestick(x=df.index, open=op, high=hi, low=lo, close=cl, name="Price"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=ma20, line=dict(color='#00FFFF', width=1), name="MA20"), row=1, col=1)
        fig.add_trace(go.Scatter(x=f_dates, y=f_prices, line=dict(color='yellow', width=2, dash='dot'), name="AI Predict"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=stoch_k, line=dict(color='white', width=1), name="%K"), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=stoch_d, line=dict(color='orange', width=1), name="%D"), row=2, col=1)
        fig.add_trace(go.Bar(x=df.index, y=vl, marker_color=['#FF3131' if c < o else '#00D100' for c, o in zip(cl, op)], name="Volume"), row=3, col=1)

        fig.update_layout(template="plotly_dark", height=900, xaxis_rangeslider_visible=False, hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.info("Sistem siap. Silakan pilih saham atau ketik kode.")
