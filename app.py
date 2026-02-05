import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import pytz

# 1. KONFIGURASI HALAMAN
st.set_page_config(page_title="StockPro Intelligence v2", layout="wide")
tz = pytz.timezone('Asia/Jakarta')

# --- SIDEBAR ---
st.sidebar.header("🛠️ Panel Kontrol")
txt_input = st.sidebar.text_area("Input Kode:", "BBRI, TLKM, ASII, ADRO, GOTO, BMRI, BBNI, UNTR, AMRT, BRIS, BBCA, ANTM, MDKA, PTBA")
manual_list = [f"{t.strip().upper()}.JK" for t in txt_input.split(",") if t.strip()][:30]

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

st.title("🚀 StockPro Precision Intelligence")
st.write(f"🕒 **Update:** {datetime.now(tz).strftime('%H:%M:%S')} WIB")

# --- WATCHLIST ---
df_w = get_data_watchlist(manual_list)
df_s = pd.DataFrame()
if not df_w.empty:
    df_s = df_w.sort_values(by=sort_col, ascending=ascending_logic).reset_index(drop=True)
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
    df = yf.download(f"{target}.JK", period="10d" if tf != "1 Hari" else "2y", interval=tf_m[tf], progress=False)
    
    if len(df) > 40:
        if tf != "1 Hari": df.index = df.index.tz_convert('Asia/Jakarta')
        cl, hi, lo, op, vl = [df[c].values.flatten() for c in ['Close', 'High', 'Low', 'Open', 'Volume']]

        # INDIKATOR TEKNIKAL
        ma20 = pd.Series(cl).rolling(20).mean()
        std20 = pd.Series(cl).rolling(20).std()
        u_bb, l_bb = ma20 + (std20 * 2), ma20 - (std20 * 2)
        diff = pd.Series(cl).diff(); g = (diff.where(diff > 0, 0)).rolling(14).mean(); l = (-diff.where(diff < 0, 0)).rolling(14).mean()
        rsi = (100 - (100 / (1 + (g/l)))).fillna(50)
        e12 = pd.Series(cl).ewm(span=12).mean(); e26 = pd.Series(cl).ewm(span=26).mean()
        macd = e12 - e26; sig = macd.ewm(span=9).mean()

        # --- ALGORITMA PREDIKSI BERDASARKAN POLA CANDLESTICK (LOOKBACK 40) ---
        f_prices, f_dates = [], []
        temp_cl = list(cl[-40:])
        temp_op = list(op[-40:])
        temp_hi = list(hi[-40:])
        temp_lo = list(lo[-40:])
        
        last_dt = df.index[-1]
        step = df.index[-1] - df.index[-2] if len(df) > 1 else timedelta(minutes=1)

        # 1. Analisa Sentimen 40 Candle Terakhir
        candle_sentiment = []
        for j in range(len(temp_cl)):
            body = temp_cl[j] - temp_op[j]
            total_range = temp_hi[j] - temp_lo[j] if temp_hi[j] != temp_lo[j] else 1
            sentiment = body / total_range
            candle_sentiment.append(sentiment)
        
        avg_sentiment = np.mean(candle_sentiment) # Kekuatan arah pola
        volatility = np.std(cl[-40:]) / np.mean(cl[-40:]) # Volatilitas relatif

        for i in range(1, 11):
            # Proyeksi Berulang
            decay = 1 / (1 + (i * 0.15)) # Redaman agar tidak liar
            
            # Komponen 1: Tren Pola (Slope 40p)
            slope, _ = np.polyfit(np.arange(40), np.array(temp_cl[-40:]), 1)
            
            # Komponen 2: Sentimen Candlestick (Mean Reversion + Momentum)
            # Menghitung jarak ke Mean Bollinger
            dist_to_mean = (ma20.iloc[-1] - temp_cl[-1]) / temp_cl[-1]
            
            # Rumus gabungan pergerakan per periode
            price_change = (slope * decay) + (temp_cl[-1] * avg_sentiment * volatility) + (temp_cl[-1] * dist_to_mean * 0.05)
            
            # Limitasi logis (max 1.5% per periode prediksi)
            cap = temp_cl[-1] * 0.015
            price_change = np.clip(price_change, -cap, cap)
            
            next_p = temp_cl[-1] + price_change
            f_prices.append(next_p)
            f_dates.append(last_dt + (step * i))
            temp_cl.append(next_p) # Masukkan ke lookback untuk hitung periode berikutnya

        # --- UI METRICS ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Harga Terakhir", f"Rp {cl[-1]:,.0f}")
        m2.metric("Pola 40P", "Bullish Dominant" if avg_sentiment > 0 else "Bearish Dominant")
        m3.metric("RSI (14)", f"{rsi.iloc[-1]:.1f}")
        m4.metric("Prediksi T+10", f"Rp {f_prices[-1]:,.0f}")

        # --- GRAFIK ---
        
        fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.4, 0.1, 0.2, 0.2])
        fig.add_trace(go.Candlestick(x=df.index, open=op, high=hi, low=lo, close=cl, name="History"), row=1, col=1)
        fig.add_trace(go.Scatter(x=f_dates, y=f_prices, line=dict(color='yellow', width=3, dash='dot'), name="Pattern Prediction"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=u_bb, line=dict(color='rgba(255,255,255,0.1)'), name="Upper BB"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=l_bb, line=dict(color='rgba(255,255,255,0.1)'), name="Lower BB", fill='tonexty'), row=1, col=1)
        
        v_colors = ['red' if c < o else 'green' for c, o in zip(cl, op)]
        fig.add_trace(go.Bar(x=df.index, y=vl, marker_color=v_colors, name="Volume"), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=macd, line=dict(color='cyan'), name="MACD"), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=sig, line=dict(color='orange'), name="Signal"), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=rsi, line=dict(color='magenta'), name="RSI"), row=4, col=1)
        
        fig.update_layout(template="plotly_dark", height=900, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # --- TABEL ---
        st.subheader("📋 Analisis Proyeksi 10 Periode (Pattern Based)")
        st.table(pd.DataFrame({
            "Periode": [f"T+{i}" for i in range(1, 11)],
            "Estimasi Waktu": [d.strftime('%H:%M (%d %b)') for d in f_dates],
            "Harga": [f"Rp {p:,.2f}" for p in f_prices]
        }))
except Exception as e:
    st.info(f"Pilih emiten valid. Catatan: {e}")
