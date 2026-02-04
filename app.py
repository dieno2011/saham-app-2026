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
max_h = st.sidebar.number_input("Harga Maksimum (Rp):", value=100000, step=100)

# C. PILIHAN SORTING (BARU)
st.sidebar.subheader("↕️ Susunan Watchlist")
sort_by = st.sidebar.selectbox("Susun Berdasarkan:", ("Perubahan (%)", "Harga", "Nama Emiten"))
sort_order = st.sidebar.radio("Aturan Susunan:", ("Menurun (High to Low / Z-A)", "Menaik (Low to High / A-Z)"))

ascending_logic = True if sort_order == "Menaik (Low to High / A-Z)" else False
sort_col = {"Perubahan (%)": "Chg%", "Harga": "Harga", "Nama Emiten": "Ticker"}[sort_by]

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
                combined.append({"Ticker": t.replace(".JK", ""), "Harga": curr, "Chg%": round(((curr-prev)/prev)*100, 2)})
        except: continue
    return pd.DataFrame(combined)

# --- HEADER ---
st.title("🚀 StockPro Ultimate 2026")
st.write(f"🕒 **Waktu Realtime (WIB):** {datetime.now(tz).strftime('%d %b %Y | %H:%M:%S')}")

# --- WATCHLIST DENGAN SORTING ---
df_w = get_data_watchlist(manual_list)
if not df_w.empty:
    df_f = df_w[(df_w['Harga'] >= min_h) & (df_w['Harga'] <= max_h)]
    
    # Logik Sorting Baru
    df_s = df_f.sort_values(by=sort_col, ascending=ascending_logic).reset_index(drop=True)
    
    st.subheader(f"🏆 Watchlist (Disusun mengikut {sort_by})")
    cols = st.columns(min(5, len(df_s)) if not df_s.empty else 1)
    for i in range(min(5, len(df_s))):
        with cols[i]:
            st.metric(label=df_s.iloc[i]['Ticker'], value=f"Rp {df_s.iloc[i]['Harga']:,.0f}", delta=f"{df_s.iloc[i]['Chg%']}%")
    with st.expander("📂 Lihat Seluruh Daftar Watchlist"):
        st.dataframe(df_s, use_container_width=True, hide_index=True)

st.divider()

# --- ANALISIS GRAFIK LENGKAP ---
ca, cb = st.columns([1, 1])
with ca:
    target_input = st.text_input("🔍 Kode Saham Analisis:", value=df_s.iloc[0]['Ticker'] if not df_s.empty else "BBRI").upper()
with cb:
    tf = st.selectbox("⏱️ Pilih Timeframe:", ("1 Menit", "60 Menit", "1 Hari"))

tf_m, pd_m = {"1 Menit": "1m", "60 Menit": "60m", "1 Hari": "1d"}, {"1 Menit": "1d", "60 Menit": "1mo", "1 Hari": "1y"}

try:
    df = yf.download(f"{target_input}.JK", period=pd_m[tf], interval=tf_m[tf], progress=False)
    if not df.empty:
        if tf != "1 Hari": df.index = df.index.tz_convert('Asia/Jakarta')
        cl, hi, lo, op, vl = [df[c].values.flatten() for c in ['Close', 'High', 'Low', 'Open', 'Volume']]

        # --- INDIKATOR TEKNIS ---
        ma20 = pd.Series(cl).rolling(20).mean()
        std20 = pd.Series(cl).rolling(20).std()
        u_bb, l_bb = ma20 + (std20 * 2), ma20 - (std20 * 2)
        diff = pd.Series(cl).diff(); gain = (diff.where(diff > 0, 0)).rolling(14).mean(); loss = (-diff.where(diff < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + (gain/loss)))
        e12 = pd.Series(cl).ewm(span=12, adjust=False).mean(); e26 = pd.Series(cl).ewm(span=26, adjust=False).mean()
        macd_line = e12 - e26; signal_line = macd_line.ewm(span=9, adjust=False).mean()

        # --- PREDIKSI SMART (5 PERIODE) ---
        y_last = cl[-20:]
        slope, intercept = np.polyfit(np.arange(len(y_last)), y_last, 1)
        vol_ma20 = pd.Series(vl).rolling(20).mean().iloc[-1]
        vol_ratio = vl[-1] / vol_ma20 if vol_ma20 > 0 else 1
        vol_factor = 0.005 if (vol_ratio > 1.5 and cl[-1] > op[-1]) else -0.005 if (vol_ratio > 1.5 and cl[-1] < op[-1]) else 0
        rsi_factor = (30 - rsi.iloc[-1]) * 0.001 if rsi.iloc[-1] < 30 else (70 - rsi.iloc[-1]) * 0.001 if rsi.iloc[-1] > 70 else 0
        macd_factor = (macd_line.iloc[-1] - signal_line.iloc[-1]) * 0.01
        
        future_prices = []
        last_p = cl[-1]
        for i in range(1, 6):
            adjustment = (last_p * rsi_factor) + (last_p * macd_factor) + (last_p * vol_factor)
            new_p = last_p + slope + adjustment
            future_prices.append(new_p)
            last_p = new_p

        step = (df.index[1] - df.index[0]) if len(df) > 1 else timedelta(minutes=1)
        future_dates = [df.index[-1] + (step * i) for i in range(1, 6)]

        # --- HEADER HARGA ---
        st.markdown(f"### 📈 Live Analysis: {target_input}.JK")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Harga Realtime", f"Rp {cl[-1]:,.0f}", f"{cl[-1]-op[-1]:,.0f}")
        m2.metric("Vol Ratio", f"{vol_ratio:.2f}x")
        m3.metric("RSI (14)", f"{rsi.iloc[-1]:.2f}")
        m4.metric("Target P-5", f"Rp {future_prices[-1]:,.0f}")

        # --- GRAFIK ---
        fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.4, 0.15, 0.2, 0.25],
                           subplot_titles=("Price & Prediction", "Volume", "MACD", "RSI"))
        fig.add_trace(go.Candlestick(x=df.index, open=op, high=hi, low=lo, close=cl, name="Price"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=u_bb, line=dict(color='rgba(255,255,255,0.2)'), name="Upper BB"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=l_bb, line=dict(color='rgba(255,255,255,0.2)'), name="Lower BB", fill='tonexty'), row=1, col=1)
        fig.add_trace(go.Scatter(x=future_dates, y=future_prices, line=dict(color='yellow', width=3, dash='dot'), name="Prediction"), row=1, col=1)
        
        colors = ['red' if c < o else 'green' for c, o in zip(cl, op)]
        fig.add_trace(go.Bar(x=df.index, y=vl, name="Volume", marker_color=colors), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=macd_line, name="MACD", line=dict(color='cyan')), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=signal_line, name="Signal", line=dict(color='red')), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=rsi, name="RSI", line=dict(color='magenta')), row=4, col=1)
        
        fig.update_layout(template="plotly_dark", height=1000, xaxis_rangeslider_visible=False, xaxis4=dict(tickformat="%H:%M\n%d %b"))
        st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

        # --- TABEL ESTIMASI ---
        st.subheader(f"📋 Estimasi Nilai 5 Periode")
        pred_df = pd.DataFrame({
            "Periode": [f"T+{i}" for i in range(1, 6)],
            "Estimasi Waktu": [d.strftime('%H:%M:%S (%d/%m)') for d in future_dates],
            "Ekspektasi Harga": [f"Rp {p:,.2f}" for p in future_prices]
        })
        st.table(pred_df)

except Exception as e:
    st.error(f"Sila semak kod emiten. Info: {e}")
