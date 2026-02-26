import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import pytz

# 1. KONFIGURASI DASAR
st.set_page_config(page_title="StockPro Precision v4.9", layout="wide")
tz = pytz.timezone('Asia/Jakarta')

if 'ticker' not in st.session_state:
    st.session_state.ticker = "BBRI"

# --- FUNGSI ANALISA TEKNIKAL UNTUK PREDIKSI ---
def calculate_advanced_score(df):
    if len(df) < 50: return 0
    cl = df['Close'].values.flatten()
    hi = df['High'].values.flatten()
    lo = df['Low'].values.flatten()
    
    # Indikator: MA, EMA, RSI, BB, MACD, Stoch, Vol
    ma20 = pd.Series(cl).rolling(20).mean().iloc[-1]
    ema12 = pd.Series(cl).ewm(span=12).mean().iloc[-1]
    # RSI
    diff = pd.Series(cl).diff()
    rsi = 100 - (100 / (1 + (diff.where(diff > 0, 0).rolling(14).mean() / diff.where(diff < 0, 0).abs().rolling(14).mean().replace(0, 0.001)))).iloc[-1]
    # MACD
    macd = pd.Series(cl).ewm(span=12).mean() - pd.Series(cl).ewm(span=26).mean()
    sig = macd.ewm(span=9).mean()
    # BB
    std = pd.Series(cl).rolling(20).std().iloc[-1]
    # Stochastic
    stoch = 100 * ((cl[-1] - pd.Series(lo).rolling(14).min().iloc[-1]) / (pd.Series(hi).rolling(14).max().iloc[-1] - pd.Series(lo).rolling(14).min().iloc[-1]))
    
    score = 0
    if cl[-1] > ma20: score += 1
    if ema12 > ma20: score += 1
    if rsi < 35: score += 1.5
    if rsi > 65: score -= 1.5
    if cl[-1] < (ma20 - 2*std): score += 1
    if macd.iloc[-1] > sig.iloc[-1]: score += 1
    if stoch < 20: score += 1
    if stoch > 80: score -= 1
    return score

@st.cache_data(ttl=30)
def get_watchlist_data(tickers):
    combined = []
    for t in tickers:
        try:
            d = yf.download(t, period="60d", interval="1d", progress=False)
            if not d.empty and len(d) >= 30:
                cl = d['Close'].values.flatten()
                score = calculate_advanced_score(d)
                # Prediksi 5P untuk Watchlist (Daily)
                pred_5 = cl[-1] + (score * (np.std(cl[-20:]) * 0.25))
                combined.append({
                    "Ticker": t.replace(".JK", ""), 
                    "Harga": float(cl[-1]),
                    "Chg%": round(((cl[-1]-cl[-2])/cl[-2])*100, 2),
                    "Signal": "BUY" if score > 1.5 else "SELL" if score < -1.5 else "HOLD",
                    "Prediksi 5P": round(pred_5, 0)
                })
        except: continue
    return pd.DataFrame(combined)

# --- SIDEBAR ---
st.sidebar.header("🛠️ Panel Kontrol")
txt_input = st.sidebar.text_area("Input Kode (Tanpa .JK):", "BBRI, TLKM, ASII, ADRO, GOTO, BMRI, BBNI, UNTR, AMRT, BRIS, BBCA, ANTM, MDKA, PTBA")
manual_list = [f"{t.strip().upper()}.JK" for t in txt_input.split(",") if t.strip()]

# --- HEADER ---
st.title("🚀 StockPro Precision Intelligence v4.9")
st.write(f"🕒 **Update:** {datetime.now(tz).strftime('%d %b %Y | %H:%M:%S')} WIB")

# --- BAGIAN 1: WATCHLIST & PREDIKSI 5P ---
df_w = get_watchlist_data(manual_list)
if not df_w.empty:
    with st.expander("📋 Watchlist: Analisa Teknikal Gabungan & Prediksi 5 Periode", expanded=True):
        df_w['Potensi %'] = ((df_w['Prediksi 5P'] - df_w['Harga']) / df_w['Harga'] * 100).round(2)
        event = st.dataframe(
            df_w.style.format({"Harga": "{:,.0f}", "Chg%": "{:+.2f}%", "Prediksi 5P": "{:,.0f}", "Potensi %": "{:+.2f}%"}),
            use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row"
        )
        if event and event.get("selection") and event["selection"]["rows"]:
            st.session_state.ticker = df_w.iloc[event["selection"]["rows"][0]]['Ticker']
            st.rerun()

st.divider()

# --- BAGIAN 2: DETAIL ANALISIS ---
ca, cb = st.columns([1, 1])
with ca:
    target = st.text_input("🔍 Fokus Analisis Saham:", value=st.session_state.ticker).upper()
    st.session_state.ticker = target
with cb:
    tf_label = st.selectbox("⏱️ Timeframe Prediksi:", 
                      ("1 Menit", "5 Menit", "15 Menit", "30 Menit", "60 Menit", "1 Hari", "1 Minggu"), index=5)

# Mapping Timeframe
delta_map = {"1 Menit": timedelta(minutes=1), "5 Menit": timedelta(minutes=5), "15 Menit": timedelta(minutes=15), 
             "30 Menit": timedelta(minutes=30), "60 Menit": timedelta(hours=1), "1 Hari": timedelta(days=1), "1 Minggu": timedelta(weeks=1)}
tf_api = {"1 Menit":"1m", "5 Menit":"5m", "15 Menit":"15m", "30 Menit":"30m", "60 Menit":"60m", "1 Hari":"1d", "1 Minggu":"1wk"}
pd_api = {"1 Menit":"1d", "5 Menit":"5d", "15 Menit":"5d", "30 Menit":"5d", "60 Menit":"1mo", "1 Hari":"2y", "1 Minggu":"max"}

try:
    df = yf.download(f"{st.session_state.ticker}.JK", period=pd_api[tf_label], interval=tf_api[tf_label], progress=False)
    if not df.empty and len(df) > 30:
        cl, hi, lo, op, vl = [df[c].values.flatten() for c in ['Close', 'High', 'Low', 'Open', 'Volume']]
        
        # Hitung Score untuk Prediksi
        current_score = calculate_advanced_score(df)
        
        # --- LOGIKA PREDIKSI 5 PERIODE (Sesuai Timeframe) ---
        f_prices, f_dates = [], []
        last_p = cl[-1]
        last_dt = df.index[-1]
        step = delta_map[tf_label]
        vol = np.std(cl[-15:])
        
        for i in range(1, 6): # Tampilkan 5 prediksi
            # Prediksi berdasarkan score teknikal + trend slope
            move = (current_score * (vol * 0.15)) / (1 + i*0.1)
            next_p = last_p + move + np.random.normal(0, vol*0.02)
            f_prices.append(next_p)
            f_dates.append(last_dt + (step * i))
            last_p = next_p

        # --- GRAFIK ---
        
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, 
                           row_heights=[0.6, 0.2, 0.2], subplot_titles=("Price & Technical Prediction", "Stochastic & RSI", "Volume"))
        
        fig.add_trace(go.Candlestick(x=df.index, open=op, high=hi, low=lo, close=cl, name="Price"), row=1, col=1)
        fig.add_trace(go.Scatter(x=f_dates, y=f_prices, line=dict(color='yellow', width=3, dash='dot'), name="AI Predict 5P"), row=1, col=1)
        
        # Indikator Tambahan di Chart
        ma20_plot = pd.Series(cl).rolling(20).mean()
        fig.add_trace(go.Scatter(x=df.index, y=ma20_plot, line=dict(color='cyan', width=1), name="MA20"), row=1, col=1)

        # Plot Indikator Bawah
        fig.add_trace(go.Scatter(x=df.index, y=pd.Series(cl).rolling(14).std(), name="Volatility", line=dict(color='orange')), row=2, col=1)
        fig.add_trace(go.Bar(x=df.index, y=vl, name="Volume", marker_color='gray'), row=3, col=1)

        fig.update_layout(template="plotly_dark", height=800, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # --- TABEL ESTIMASI ---
        st.subheader(f"📊 Detail Prediksi 5 Periode ({tf_label})")
        df_res = pd.DataFrame({
            "Periode": [f"T+{i}" for i in range(1, 6)],
            "Estimasi Waktu": [d.strftime('%d %b %H:%M') for d in f_dates],
            "Prediksi Harga": [f"Rp {p:,.2f}" for p in f_prices],
            "Analisa": ["Bullish" if current_score > 0 else "Bearish" if current_score < 0 else "Sideways" for _ in range(5)]
        })
        st.table(df_res)

except Exception as e:
    st.error(f"Terjadi kesalahan atau data tidak tersedia untuk {st.session_state.ticker}")
