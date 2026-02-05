import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import pytz

# 1. KONFIGURASI
st.set_page_config(page_title="StockPro Precision v3", layout="wide")
tz = pytz.timezone('Asia/Jakarta')

# --- SIDEBAR ---
st.sidebar.header("🛠️ Panel Kontrol")
txt_input = st.sidebar.text_area("Input Kode (Tanpa .JK):", "BBRI, TLKM, ASII, ADRO, GOTO, BMRI, BBNI")
manual_list = [f"{t.strip().upper()}.JK" for t in txt_input.split(",") if t.strip()][:30]

min_h = st.sidebar.number_input("Harga Minimum (Rp):", value=0)
max_h = st.sidebar.number_input("Harga Maksimum (Rp):", value=500000)

@st.cache_data(ttl=15)
def get_data_watchlist(tickers):
    combined = []
    for t in tickers:
        try:
            d = yf.download(t, period="2d", interval="1d", progress=False)
            if not d.empty and len(d) >= 2:
                cl_data = d['Close'].values.flatten()
                combined.append({"Ticker": t.replace(".JK", ""), "Harga": float(cl_data[-1]), 
                                 "Chg%": round(((cl_data[-1]-cl_data[-2])/cl_data[-2])*100, 2)})
        except: continue
    return pd.DataFrame(combined)

# --- HEADER ---
st.title("🚀 StockPro Precision Intelligence")
st.write(f"🕒 **Update:** {datetime.now(tz).strftime('%H:%M:%S')} WIB")

# --- WATCHLIST ---
df_w = get_data_watchlist(manual_list)
if not df_w.empty:
    df_s = df_w[(df_w['Harga'] >= min_h) & (df_w['Harga'] <= max_h)]
    cols = st.columns(min(5, len(df_s)))
    for i in range(min(5, len(df_s))):
        with cols[i]:
            st.metric(label=df_s.iloc[i]['Ticker'], value=f"Rp {df_s.iloc[i]['Harga']:,.0f}", delta=f"{df_s.iloc[i]['Chg%']}%")

st.divider()

# --- ANALISIS ---
ca, cb = st.columns([1, 1])
with ca:
    target = st.text_input("🔍 Kode Analisis:", value="BBRI").upper()
with cb:
    tf = st.selectbox("⏱️ Timeframe:", ("1 Menit", "60 Menit", "1 Hari"))

tf_m = {"1 Menit": "1m", "60 Menit": "60m", "1 Hari": "1d"}
pd_m = {"1 Menit": "1d", "60 Menit": "1mo", "1 Hari": "2y"}

try:
    df = yf.download(f"{target}.JK", period=pd_m[tf], interval=tf_m[tf], progress=False)
    
    if not df.empty and len(df) > 40:
        if tf != "1 Hari": df.index = df.index.tz_convert('Asia/Jakarta')
        cl, hi, lo, op, vl = [df[c].values.flatten() for c in ['Close', 'High', 'Low', 'Open', 'Volume']]

        # HITUNG INDIKATOR
        # MACD
        e12 = pd.Series(cl).ewm(span=12).mean(); e26 = pd.Series(cl).ewm(span=26).mean()
        macd = e12 - e26; sig = macd.ewm(span=9).mean()
        # RSI
        diff = pd.Series(cl).diff(); g = (diff.where(diff > 0, 0)).rolling(14).mean(); l_loss = (-diff.where(diff < 0, 0)).rolling(14).mean()
        rsi = (100 - (100 / (1 + (g/(l_loss.replace(0, 0.001)))))).fillna(50)

        # --- FORMULA PREDIKSI (MENGACU POLA 40 PERIODE) ---
        f_prices, f_dates = [], []
        t_cl = list(cl[-40:]); t_op = list(op[-40:]); t_hi = list(hi[-40:]); t_lo = list(lo[-40:])
        step = df.index[-1] - df.index[-2] if len(df) > 1 else timedelta(minutes=1)
        last_dt = df.index[-1]

        for i in range(1, 11):
            decay = 1 / (1 + (i * 0.1))
            # Slope Harga
            slope, _ = np.polyfit(np.arange(40), np.array(t_cl[-40:]), 1)
            # Sentimen Candlestick (Body vs Range)
            sent = np.mean([((t_cl[j]-t_op[j])/(t_hi[j]-t_lo[j] if t_hi[j]!=t_lo[j] else 1)) for j in range(len(t_cl))])
            
            # Perubahan harga berbasis momentum pola
            move = (slope * decay) + (t_cl[-1] * sent * 0.01)
            move = np.clip(move, -t_cl[-1]*0.01, t_cl[-1]*0.01)
            
            next_p = t_cl[-1] + move
            f_prices.append(next_p)
            f_dates.append(last_dt + (step * i))
            # Update lookback window
            t_cl.append(next_p); t_op.append(t_cl[-2]); t_hi.append(max(next_p, t_cl[-2])); t_lo.append(min(next_p, t_cl[-2]))

        # --- GRAFIK ---
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, 
                           row_heights=[0.8, 0.2], subplot_titles=("Main Chart (Price & Indicators)", "Volume"))
        
        # 1. Candlestick & Prediksi
        fig.add_trace(go.Candlestick(x=df.index, open=op, high=hi, low=lo, close=cl, name="Price"), row=1, col=1)
        fig.add_trace(go.Scatter(x=f_dates, y=f_prices, line=dict(color='yellow', width=3, dash='dot'), name="Pattern Predict"), row=1, col=1)

        # 2. MACD Group (Satu Tombol Legend)
        fig.add_trace(go.Scatter(x=df.index, y=macd + cl[-1], line=dict(color='cyan', width=1.5), 
                                 name="MACD Group", legendgroup="macd", visible='legendonly'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=sig + cl[-1], line=dict(color='orange', width=1, dash='dot'), 
                                 name="MACD Signal", legendgroup="macd", showlegend=False, visible='legendonly'), row=1, col=1)

        # 3. RSI Overlay (Skala disesuaikan ke area harga)
        rsi_scaled = (rsi / 100) * (cl.max() - cl.min()) + cl.min()
        fig.add_trace(go.Scatter(x=df.index, y=rsi_scaled, line=dict(color='magenta', width=1.5), 
                                 name="RSI Overlay", visible='legendonly'), row=1, col=1)

        # 4. Volume
        colors = ['red' if c < o else 'green' for c, o in zip(cl, op)]
        fig.add_trace(go.Bar(x=df.index, y=vl, marker_color=colors, name="Volume"), row=2, col=1)

        # --- FIX SUMBU X REALTIME ---
        fig.update_xaxes(showticklabels=True, tickformat="%H:%M\n%d %b", row=1, col=1)
        fig.update_xaxes(showticklabels=True, tickformat="%H:%M\n%d %b", row=2, col=1)
        
        fig.update_layout(template="plotly_dark", height=800, xaxis_rangeslider_visible=False, 
                          hovermode="x unified", legend=dict(orientation="h", y=1.1))
        
        st.plotly_chart(fig, use_container_width=True)

        # TABEL
        st.subheader("📋 Proyeksi 10 Periode Selanjutnya")
        st.table(pd.DataFrame({"Waktu": [d.strftime('%H:%M (%d %b)') for d in f_dates], "Estimasi Harga": [f"Rp {p:,.2f}" for p in f_prices]}))

except Exception as e:
    st.error(f"Error: {e}")
