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

# --- SIDEBAR: PANEL KONTROL ---
st.sidebar.header("🛠️ Panel Kontrol")
st.sidebar.subheader("📝 Kelola Watchlist")
txt_input = st.sidebar.text_area("Input Kode (Tanpa .JK):", 
                                "BBRI, TLKM, ASII, ADRO, GOTO, BMRI, BBNI, UNTR, AMRT, BRIS, BBCA, ANTM, MDKA, PTBA")
manual_list = [f"{t.strip().upper()}.JK" for t in txt_input.split(",") if t.strip()][:30]

st.sidebar.subheader("💰 Filter Harga")
min_h = st.sidebar.number_input("Harga Minimum (Rp):", value=0, step=50)
max_h = st.sidebar.number_input("Harga Maksimum (Rp):", value=500000, step=100)

st.sidebar.subheader("↕️ Susunan Watchlist")
sort_by = st.sidebar.selectbox("Susun Berdasarkan:", ("Perubahan (%)", "Harga", "Nama Emiten"))
sort_order = st.sidebar.radio("Aturan:", ("Menurun", "Menaik"))
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
                curr = float(cl_data[-1])
                prev = float(cl_data[-2])
                combined.append({"Ticker": t.replace(".JK", ""), "Harga": curr, "Chg%": round(((curr-prev)/prev)*100, 2)})
        except: continue
    return pd.DataFrame(combined)

# --- HEADER ---
st.title("🚀 StockPro Precision Intelligence")
st.write(f"🕒 **Waktu Bursa (WIB):** {datetime.now(tz).strftime('%d %b %Y | %H:%M:%S')}")

# --- WATCHLIST ---
df_w = get_data_watchlist(manual_list)
df_s = pd.DataFrame()
if not df_w.empty:
    df_f = df_w[(df_w['Harga'] >= min_h) & (df_w['Harga'] <= max_h)]
    if not df_f.empty:
        df_s = df_f.sort_values(by=sort_col, ascending=ascending_logic).reset_index(drop=True)
        cols = st.columns(min(5, len(df_s)))
        for i in range(min(5, len(df_s))):
            with cols[i]:
                st.metric(label=df_s.iloc[i]['Ticker'], value=f"Rp {df_s.iloc[i]['Harga']:,.0f}", delta=f"{df_s.iloc[i]['Chg%']}%")

st.divider()

# --- ANALISIS GRAFIK ---
ca, cb = st.columns([1, 1])
with ca:
    default_ticker = df_s.iloc[0]['Ticker'] if not df_s.empty else "BBRI"
    target = st.text_input("🔍 Kode Analisis:", value=default_ticker).upper()
with cb:
    tf = st.selectbox("⏱️ Timeframe:", ("1 Menit", "60 Menit", "1 Hari"))

tf_m = {"1 Menit": "1m", "60 Menit": "60m", "1 Hari": "1d"}
pd_m = {"1 Menit": "1d", "60 Menit": "1mo", "1 Hari": "2y"}

try:
    df = yf.download(f"{target}.JK", period=pd_m[tf], interval=tf_m[tf], progress=False)
    
    if not df.empty and len(df) > 40:
        if tf != "1 Hari": df.index = df.index.tz_convert('Asia/Jakarta')
        cl, hi, lo, op, vl = [df[c].values.flatten() for c in ['Close', 'High', 'Low', 'Open', 'Volume']]

        # --- HITUNG INDIKATOR ---
        ma20 = pd.Series(cl).rolling(20).mean()
        std20 = pd.Series(cl).rolling(20).std()
        u_bb, l_bb = ma20 + (std20 * 2), ma20 - (std20 * 2)
        diff = pd.Series(cl).diff()
        g = (diff.where(diff > 0, 0)).rolling(14).mean()
        l_loss = (-diff.where(diff < 0, 0)).rolling(14).mean()
        rsi = (100 - (100 / (1 + (g/(l_loss.replace(0, 0.001)))))).fillna(50)
        e12 = pd.Series(cl).ewm(span=12).mean(); e26 = pd.Series(cl).ewm(span=26).mean()
        macd = e12 - e26; sig = macd.ewm(span=9).mean()

        # --- LOGIKA PREDIKSI ---
        f_prices, f_dates = [], []
        t_cl, t_op, t_hi, t_lo = list(cl[-40:]), list(op[-40:]), list(hi[-40:]), list(lo[-40:])
        step = df.index[-1] - df.index[-2] if len(df) > 1 else timedelta(minutes=1)
        last_dt = df.index[-1]

        for i in range(1, 11):
            decay = 1 / (1 + (i * 0.15))
            slope, _ = np.polyfit(np.arange(40), np.array(t_cl[-40:]), 1)
            sent_list = [((t_cl[j]-t_op[j])/(t_hi[j]-t_lo[j] if t_hi[j]!=t_lo[j] else 1)) for j in range(len(t_cl))]
            candle_sent = np.mean(sent_list)
            volat = np.std(cl[-40:]) / np.mean(cl[-40:])
            dist_mean = (ma20.iloc[-1] - t_cl[-1]) / t_cl[-1] if not np.isnan(ma20.iloc[-1]) else 0
            change = (slope * decay) + (t_cl[-1] * candle_sent * volat) + (t_cl[-1] * dist_mean * 0.05)
            change = np.clip(change, -t_cl[-1]*0.015, t_cl[-1]*0.015)
            next_p = t_cl[-1] + change
            f_prices.append(next_p)
            f_dates.append(last_dt + (step * i))
            t_cl.append(next_p); t_op.append(t_cl[-2]); t_hi.append(next_p); t_lo.append(next_p)

        # --- GRAFIK TERPADU (OVERLAY) ---
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, 
                           row_heights=[0.8, 0.2], subplot_titles=(f"Chart {target} - Multi Indicator Overlay", "Volume"))
        
        # 1. Candlestick & Prediction
        fig.add_trace(go.Candlestick(x=df.index, open=op, high=hi, low=lo, close=cl, name="Candle"), row=1, col=1)
        fig.add_trace(go.Scatter(x=f_dates, y=f_prices, line=dict(color='yellow', width=3, dash='dot'), name="AI Predict"), row=1, col=1)
        
        # 2. Bollinger Bands (Overlay)
        fig.add_trace(go.Scatter(x=df.index, y=u_bb, line=dict(color='rgba(173,216,230,0.3)'), name="BB Upper", visible='legendonly'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=l_bb, line=dict(color='rgba(173,216,230,0.3)'), name="BB Lower", fill='tonexty', visible='legendonly'), row=1, col=1)

        # 3. MACD (Overlay - di skala harga)
        # Kita normalisasi sedikit agar MACD bisa terlihat di chart harga utama atau gunakan sumbu y2 jika perlu.
        # Untuk kemudahan baca, kita taruh di chart utama dengan status 'visible=legendonly'
        fig.add_trace(go.Scatter(x=df.index, y=macd + cl[-1], line=dict(color='cyan', width=1), name="MACD (Offset)", visible='legendonly'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=sig + cl[-1], line=dict(color='orange', width=1), name="MACD Signal", visible='legendonly'), row=1, col=1)

        # 4. RSI (Overlay - Skala 0-100 tapi diletakkan di area harga)
        # Tips: Klik legend RSI untuk memunculkan garis pink di grafik
        fig.add_trace(go.Scatter(x=df.index, y=(rsi * (cl.max()/100)), line=dict(color='magenta', width=1), name="RSI (Scaled)", visible='legendonly'), row=1, col=1)

        # 5. Volume (Panel Bawah)
        v_colors = ['red' if c < o else 'green' for c, o in zip(cl, op)]
        fig.add_trace(go.Bar(x=df.index, y=vl, marker_color=v_colors, name="Volume"), row=2, col=1)

        # --- FIX: AKTIFKAN WAKTU PADA SUMBU X ---
        fig.update_xaxes(showticklabels=True, tickformat="%H:%M\n%d %b", tickangle=0, row=1, col=1)
        fig.update_xaxes(showticklabels=True, tickformat="%H:%M\n%d %b", tickangle=0, row=2, col=1)
        
        fig.update_layout(
            template="plotly_dark", 
            height=850, 
            xaxis_rangeslider_visible=False, 
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        st.info("💡 Klik nama indikator di bagian Legend atas untuk memunculkan/menyembunyikan MACD, RSI, atau BB.")
        st.plotly_chart(fig, use_container_width=True)

        # --- TABEL ---
        st.subheader("📋 Data Proyeksi")
        st.table(pd.DataFrame({
            "Periode": [f"T+{i}" for i in range(1,11)],
            "Waktu": [d.strftime('%H:%M (%d %b)') for d in f_dates],
            "Harga": [f"Rp {p:,.2f}" for p in f_prices]
        }))

except Exception as e:
    st.error(f"Terjadi error: {e}")
