import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import pytz

# 1. KONFIGURASI DASAR
st.set_page_config(page_title="StockPro Multi-Indicator v4.8", layout="wide")
tz = pytz.timezone('Asia/Jakarta')

if 'ticker' not in st.session_state:
    st.session_state.ticker = "BBRI"

# --- FUNGSI ANALISA TEKNIKAL KOMPLEKS ---
def get_technical_signal(df):
    """Menghasilkan skor prediksi berdasarkan gabungan 7 indikator"""
    if len(df) < 50: return 0
    
    cl = df['Close'].values.flatten()
    hi = df['High'].values.flatten()
    lo = df['Low'].values.flatten()
    vl = df['Volume'].values.flatten()
    
    # 1. MA & EMA
    ma20 = pd.Series(cl).rolling(20).mean().iloc[-1]
    ema12 = pd.Series(cl).ewm(span=12, adjust=False).mean().iloc[-1]
    
    # 2. RSI
    diff = pd.Series(cl).diff()
    gain = (diff.where(diff > 0, 0)).rolling(14).mean()
    loss = (-diff.where(diff < 0, 0)).rolling(14).mean()
    rs = gain / (loss.replace(0, 0.001))
    rsi = 100 - (100 / (1 + rs)).iloc[-1]
    
    # 3. Bollinger Bands
    std20 = pd.Series(cl).rolling(20).std().iloc[-1]
    upper_bb = ma20 + (2 * std20)
    lower_bb = ma20 - (2 * std20)
    
    # 4. MACD
    ema26 = pd.Series(cl).ewm(span=26, adjust=False).mean()
    macd_line = (pd.Series(cl).ewm(span=12, adjust=False).mean() - ema26)
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    macd_val = macd_line.iloc[-1] - signal_line.iloc[-1]
    
    # 5. Stochastic
    l14 = pd.Series(lo).rolling(14).min()
    h14 = pd.Series(hi).rolling(14).max()
    stoch_k = (100 * ((cl[-1] - l14.iloc[-1]) / (h14.iloc[-1] - l14.iloc[-1])))
    
    # 6. Volume Analysis
    vol_ma = pd.Series(vl).rolling(10).mean().iloc[-1]
    vol_signal = 1 if vl[-1] > vol_ma else -1
    
    # SCORING (Total maks +7, min -7)
    score = 0
    if cl[-1] > ma20: score += 1 # MA
    if cl[-1] > ema12: score += 1 # EMA
    if rsi < 40: score += 1 # RSI (Oversold)
    if rsi > 60: score -= 1 # RSI (Overbought)
    if cl[-1] < lower_bb: score += 1 # BB (Bottom)
    if cl[-1] > upper_bb: score -= 1 # BB (Top)
    if macd_val > 0: score += 1 # MACD Bullish
    if stoch_k < 20: score += 1 # Stoch Oversold
    if vol_signal > 0 and cl[-1] > cl[-2]: score += 1 # Vol Confirmation
    
    return score

@st.cache_data(ttl=30)
def get_watchlist_full(tickers):
    combined = []
    for t in tickers:
        try:
            # Ambil data lebih panjang (60 hari) untuk indikator
            d = yf.download(t, period="60d", interval="1d", progress=False)
            if not d.empty and len(d) >= 30:
                cl = d['Close'].values.flatten()
                score = get_technical_signal(d)
                
                # Proyeksi 5 Periode sederhana berdasarkan Skor Teknikal
                # Skor tinggi = Prediksi naik, Skor rendah = Prediksi turun
                current_p = cl[-1]
                volatility = np.std(cl[-10:])
                pred_5 = current_p + (score * (volatility * 0.2)) # Estimasi gerak 5 hari
                
                combined.append({
                    "Ticker": t.replace(".JK", ""), 
                    "Harga": current_p,
                    "Chg%": round(((cl[-1]-cl[-2])/cl[-2])*100, 2),
                    "Signal": "BUY" if score >= 2 else "SELL" if score <= -2 else "HOLD",
                    "Score": score,
                    "Prediksi 5P": round(pred_5, 0)
                })
        except: continue
    return pd.DataFrame(combined)

# --- SIDEBAR & HEADER ---
st.sidebar.header("🛠️ Panel Kontrol")
txt_input = st.sidebar.text_area("Input Kode (Tanpa .JK):", "BBRI, TLKM, ASII, ADRO, GOTO, BMRI, BBNI, UNTR, AMRT, BRIS, BBCA, ANTM, MDKA, PTBA")
manual_list = [f"{t.strip().upper()}.JK" for t in txt_input.split(",") if t.strip()]

st.title("🚀 StockPro Intelligence v4.8")
st.write(f"🕒 **Analisa Terpadu:** MACD, RSI, BB, MA, EMA, Stochastic, Volume")

# --- BAGIAN 1: WATCHLIST DENGAN PREDIKSI ---
df_w = get_watchlist_full(manual_list)

if not df_w.empty:
    with st.expander("📋 Watchlist & Prediksi 5 Periode (Analisa Teknikal Gabungan)", expanded=True):
        # Tambahkan kolom persentase prediksi
        df_w['Potensi %'] = ((df_w['Prediksi 5P'] - df_w['Harga']) / df_w['Harga'] * 100).round(2)
        
        # Styling tabel
        def color_signal(val):
            color = '#00FF00' if val == "BUY" else '#FF0000' if val == "SELL" else '#AAAAAA'
            return f'color: {color}; font-weight: bold'

        event = st.dataframe(
            df_w.style.format({
                "Harga": "{:,.0f}", "Chg%": "{:+.2f}%", 
                "Prediksi 5P": "{:,.0f}", "Potensi %": "{:+.2f}%"
            }).applymap(color_signal, subset=['Signal']),
            use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row"
        )
        
        if event and event.get("selection") and event["selection"]["rows"]:
            st.session_state.ticker = df_w.iloc[event["selection"]["rows"][0]]['Ticker']
            st.rerun()

st.divider()

# --- BAGIAN 2: DETAIL ANALISIS (GRAFIK) ---
# (Logika timeframe dan grafik tetap sama seperti v4.7 namun menggunakan ticker dari state)
target = st.text_input("🔍 Fokus Analisis Saham:", value=st.session_state.ticker).upper()
st.session_state.ticker = target

# ... (Kode grafik teknikal v4.7 dilanjutkan di sini untuk detail visual) ...
# Note: Bagian visualisasi grafik tetap menggunakan f_prices dari formula v4.7 
# agar sinkron antara tabel bawah dan chart.
