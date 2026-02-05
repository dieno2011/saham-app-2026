import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import pytz

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="StockPro Precision 2026", layout="wide")
tz = pytz.timezone('Asia/Jakarta')

# --- SIDEBAR: KONTROL TOTAL ---
st.sidebar.header("🛠️ Panel Kontrol")
st.sidebar.subheader("📝 Kelola Watchlist")
txt_input = st.sidebar.text_area("Input Kode:", "BBRI, TLKM, ASII, ADRO, GOTO, BMRI, BBNI, UNTR, AMRT, BRIS, BBCA, ANTM, MDKA, PTBA")
manual_list = [f"{t.strip().upper()}.JK" for t in txt_input.split(",") if t.strip()][:30]

st.sidebar.subheader("💰 Filter Harga")
min_h = st.sidebar.number_input("Harga Minimum:", value=0)
max_h = st.sidebar.number_input("Harga Maksimum:", value=500000)

st.sidebar.subheader("↕️ Susunan Watchlist")
sort_by = st.sidebar.selectbox("Susun Berdasarkan:", ("Perubahan (%)", "Harga", "Nama Emiten"))
sort_order = st.sidebar.radio("Aturan:", ("Menurun", "Menaik"))
ascending_logic = True if sort_order == "Menaik" else False
sort_col = {"Perubahan (%)": "Chg%", "Harga": "Harga", "Nama Emiten": "Ticker"}[sort_by]

@st.cache_data(ttl=15)
def get_data_watchlist(tickers):
    combined = []
    for t in tickers:
        try:
            d = yf.download(t, period="2d", interval="1d", progress=False)
            if not d.empty:
                curr = float(d['Close'].iloc[-1])
                prev = float(d['Close'].iloc[-2]) if len(d) > 1 else curr
                combined.append({"Ticker": t.replace(".JK", ""), "Harga": curr, "Chg%": round(((curr-prev)/prev)*100, 2)})
        except: continue
    return pd.DataFrame(combined)

# --- HEADER ---
st.title("🚀 StockPro Precision Intelligence")
st.write(f"🕒 **Update:** {datetime.now(tz).strftime('%H:%M:%S')} WIB")

# --- WATCHLIST ---
df_w = get_data_watchlist(manual_list)
df_s = pd.DataFrame()
if not df_w.empty:
    df_f = df_w[(df_w['Harga'] >= min_h) & (df_w['Harga'] <= max_h)]
    df_s = df_f.sort_values(by=sort_col, ascending=ascending_logic).reset_index(drop=True)
    cols = st.columns(min(5, len(df_s)))
    for i in range(min(5, len(df_s))):
        with cols[i]:
            st.metric(label=df_s.iloc[i]['Ticker'], value=f"Rp {df_s.iloc[i]['Harga']:,.0f}", delta=f"{df_s.iloc[i]['Chg%']}%")

st.divider()

# --- ANALISIS GRAFIK ---
ca, cb = st.columns([1, 1])
with ca:
    target = st.text_input("🔍 Kode Analisis:", value=df_s.iloc[0]['Ticker'] if not df_s.empty else "BBRI").upper()
with cb:
    tf = st.selectbox("⏱️ Timeframe:", ("1 Menit", "60 Menit", "1 Hari"))

tf_m, pd_m = {"1 Menit": "1m", "60 Menit": "60m", "1 Hari": "1d"}, {"1 Menit": "1d", "60 Menit": "1mo", "1 Hari": "1y"}

try:
    # Mengambil data yang cukup untuk mendukung lookback 40
    df = yf.download(f"{target}.JK", period="7d" if tf != "1 Hari" else "2y", interval=tf_m[tf], progress=False)
    
    if len(df) > 40:
        if tf != "1 Hari": df.index = df.index.tz_convert('Asia/Jakarta')
        cl, hi, lo, op, vl = [df[c].values.flatten() for c in ['Close', 'High', 'Low', 'Open', 'Volume']]

        # INDIKATOR
        ma20 = pd.Series(cl).rolling(20).mean()
        std20 = pd.Series(cl).rolling(20).std()
        u_bb, l_bb = ma20 + (std20 * 2), ma20 - (std20 * 2)
        diff = pd.Series(cl).diff(); g = (diff.where(diff > 0, 0)).rolling(14).mean(); l = (-diff.where(diff < 0, 0)).rolling(14).mean()
        rsi = (100 - (100 / (1 + (g/l)))).fillna(50)
        e12 = pd.Series(cl).ewm(span=12).mean(); e26 = pd.Series(cl).ewm(span=26).mean()
        macd = e12 - e26; sig = macd.ewm(span=9).mean()

        # --- ALGORITMA PREDIKSI PRESISI (10P) DENGAN LOOKBACK 40 ---
        f_prices, f_dates = [], []
        temp_cl, temp_vl = list(cl[-40:]), list(vl[-40:]) # Lookback 40
        last_dt = df.index[-1]
        step = df.index[-1] - df.index[-2] if len(df) > 1 else timedelta(minutes=1)

        for i in range(1, 11):
            # 1. Slope Calculation (Regression) berbasis 40 periode
            x = np.arange(40)
            y = np.array(temp_cl[-40:])
            slope, _ = np.polyfit(x, y, 1)
            
            # 2. Advanced Weighting (Volume & Momentum) berbasis 40 periode
            v_avg = np.mean(temp_vl[-40:])
            v_ratio = temp_vl[-1] / v_avg if v_avg > 0 else 1
            curr_rsi = rsi.iloc[-1]
            
            # Reversal adjustment (RSI)
            rsi_adj = (40 - curr_rsi) * 0.003 if curr_rsi < 35 else (60 - curr_rsi) * 0.003 if curr_rsi > 65 else 0
            # Volatility impulse
            vol_impulse = (slope * 0.1 * v_ratio)
            
            # Next Price Calculation
            next_p = temp_cl[-1] + slope + (temp_cl[-1] * rsi_adj) + vol_impulse
            f_prices.append(next_p)
            f_dates.append(last_dt + (step * i))
            
            # Update buffers untuk recursive simulation
            temp_cl.append(next_p)
            temp_vl.append(v_avg)

        # UI METRICS
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Harga Real", f"Rp {cl[-1]:,.0f}")
        m2.metric("Signal", "BUY" if macd.iloc[-1] > sig.iloc[-1] else "SELL")
        m3.metric("RSI (40-Lookback)", f"{rsi.iloc[-1]:.1f}")
        m4.metric("Prediksi T+10", f"Rp {f_prices[-1]:,.0f}")

        # GRAFIK
        
        fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.4, 0.1, 0.2, 0.2])
        fig.add_trace(go.Candlestick(x=df.index, open=op, high=hi, low=lo, close=cl, name="Price"), row=1, col=1)
        fig.add_trace(go.Scatter(x=f_dates, y=f_prices, line=dict(color='yellow', width=3, dash='dot'), name="AI Prediction (40P Lookback)"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=u_bb, line=dict(color='rgba(255,255,255,0.1)'), name="Upper BB"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=l_bb, line=dict(color='rgba(255,255,255,0.1)'), name="Lower BB", fill='tonexty'), row=1, col=1)
        
        v_colors = ['red' if c < o else 'green' for c, o in zip(cl, op)]
        fig.add_trace(go.Bar(x=df.index, y=vl, marker_color=v_colors, name="Volume"), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=macd, line=dict(color='cyan'), name="MACD"), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=sig, line=dict(color='orange'), name="Signal"), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=rsi, line=dict(color='magenta'), name="RSI"), row=4, col=1)
        
        fig.update_layout(template="plotly_dark", height=900, xaxis_rangeslider_visible=False, xaxis4=dict(tickformat="%H:%M\n%d %b"))
        st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

        # TABEL
        st.subheader("📋 Detail Proyeksi Harga (Lookback 40 Periode)")
        st.table(pd.DataFrame({
            "Periode": [f"T+{i}" for i in range(1, 11)],
            "Waktu": [d.strftime('%H:%M (%d %b)') for d in f_dates],
            "Estimasi Harga": [f"Rp {p:,.2f}" for p in f_prices]
        }))
    else:
        st.warning("Data historis tidak mencukupi untuk jendela look-back 40 periode.")
except Exception as e:
    st.info("Pilih emiten yang valid untuk memulai analisis.")
