import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import pytz

# 1. KONFIGURASI
st.set_page_config(page_title="StockPro Precision v3.8", layout="wide")
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
                hi_data = d['High'].values.flatten()
                lo_data = d['Low'].values.flatten()
                combined.append({
                    "Ticker": t.replace(".JK", ""), 
                    "Harga": float(cl_data[-1]),
                    "High": float(hi_data[-1]),
                    "Low": float(lo_data[-1]),
                    "Chg%": round(((cl_data[-1]-cl_data[-2])/cl_data[-2])*100, 2)
                })
        except: continue
    return pd.DataFrame(combined)

# --- HEADER ---
st.title("🚀 StockPro Precision Intelligence")
st.write(f"🕒 **Update:** {datetime.now(tz).strftime('%d %b %Y | %H:%M:%S')} WIB")

# --- BAGIAN 1: WATCHLIST (INTERACTIVE SELECTION) ---
df_w = get_data_watchlist(manual_list)
selected_ticker = "BBRI" 

if not df_w.empty:
    df_f = df_w[(df_w['Harga'] >= min_h) & (df_w['Harga'] <= max_h)]
    df_s = df_f.sort_values(by=sort_col, ascending=ascending_logic)
    
    st.subheader("📋 Daftar Pantau (Klik Baris untuk Analisis)")
    event = st.dataframe(
        df_s.style.format({"Harga": "{:,.0f}", "High": "{:,.0f}", "Low": "{:,.0f}", "Chg%": "{:+.2f}%"}),
        use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row"
    )
    if len(event.selection.rows) > 0:
        selected_ticker = df_s.iloc[event.selection.rows[0]]['Ticker']

st.divider()

# --- BAGIAN 2: ANALISIS & REALTIME DATA ---
st.subheader(f"🔍 Analisis Teknikal: {selected_ticker}")
ca, cb = st.columns([1, 1])

with ca:
    target = st.text_input("📝 Ubah Manual (Contoh: GOTO):", value=selected_ticker).upper()
with cb:
    # TIME FRAME UPDATE
    tf = st.selectbox("⏱️ Timeframe:", 
                      ("1 Menit", "5 Menit", "10 Menit", "15 Menit", "30 Menit", 
                       "60 Menit", "2 Jam", "3 Jam", "1 Hari", "1 Minggu", "1 Bulan"))

try:
    tf_m = {"1 Menit": "1m", "5 Menit": "5m", "10 Menit": "10m", "15 Menit": "15m", "30 Menit": "30m", 
            "60 Menit": "60m", "2 Jam": "90m", "3 Jam": "1h", "1 Hari": "1d", "1 Minggu": "1wk", "1 Bulan": "1mo"}
    pd_m = {"1 Menit": "1d", "5 Menit": "5d", "10 Menit": "5d", "15 Menit": "5d", "30 Menit": "5d", 
            "60 Menit": "1mo", "2 Jam": "1mo", "3 Jam": "1mo", "1 Hari": "2y", "1 Minggu": "max", "1 Bulan": "max"}
    
    df = yf.download(f"{target}.JK", period=pd_m[tf], interval=tf_m[tf], progress=False)
    
    if not df.empty and len(df) > 40:
        if tf not in ["1 Hari", "1 Minggu", "1 Bulan"]: 
            df.index = df.index.tz_convert('Asia/Jakarta')
            
        cl, hi, lo, op, vl = [df[c].values.flatten() for c in ['Close', 'High', 'Low', 'Open', 'Volume']]

        # --- HITUNG INDIKATOR ---
        # 1. MACD
        e12 = pd.Series(cl).ewm(span=12).mean(); e26 = pd.Series(cl).ewm(span=26).mean()
        macd = e12 - e26; sig = macd.ewm(span=9).mean()
        # 2. RSI
        diff = pd.Series(cl).diff(); g = (diff.where(diff > 0, 0)).rolling(14).mean(); l_loss = (-diff.where(diff < 0, 0)).rolling(14).mean()
        rsi = (100 - (100 / (1 + (g/(l_loss.replace(0, 0.001)))))).fillna(50)
        # 3. MOVING AVERAGE (MA)
        ma20 = pd.Series(cl).rolling(window=20).mean()
        ma50 = pd.Series(cl).rolling(window=50).mean()
        # 4. STOCHASTIC
        low_min = pd.Series(lo).rolling(window=14).min()
        high_max = pd.Series(hi).rolling(window=14).max()
        stoch_k = 100 * ((pd.Series(cl) - low_min) / (high_max - low_min))
        stoch_d = stoch_k.rolling(window=3).mean()

        # PANEL SUMMARY
        curr_p, curr_h, curr_l = cl[-1], hi[-1], lo[-1]
        last_rsi = rsi.iloc[-1]
        if last_rsi < 30: saran, warna = "KUAT BELI (OVERSOLD)", "green"
        elif last_rsi > 70: saran, warna = "JUAL (OVERBOUGHT)", "red"
        else: saran, warna = "TUNGGU / HOLD", "gray"

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Realtime Price", f"Rp {curr_p:,.0f}")
        m2.metric("High", f"Rp {curr_h:,.0f}")
        m3.metric("Low", f"Rp {curr_l:,.0f}")
        st.markdown(f"**Saran AI:** <span style='color:{warna}; font-size:20px; font-weight:bold;'>{saran}</span>", unsafe_allow_html=True)

        # --- PREDIKSI WEIGHTED ---
        f_prices, f_dates = [], []
        t_cl = list(cl[-40:]); last_dt = df.index[-1]
        step = df.index[-1] - df.index[-2] if len(df) > 1 else timedelta(minutes=1)
        weights = np.exp(np.linspace(-1., 0., 40)); weights /= weights.sum()

        for i in range(1, 11):
            current_window = np.array(t_cl[-40:])
            weighted_mean = np.sum(current_window * weights)
            slope = (current_window[-1] - weighted_mean) / 40
            move = (slope * (1/(1+(i*0.2)))) + (np.random.normal(0, np.std(current_window)*0.05))
            next_p = t_cl[-1] + move
            f_prices.append(next_p); f_dates.append(last_dt + (step * i)); t_cl.append(next_p)

        # --- GRAFIK ---
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05, 
                           row_heights=[0.6, 0.2, 0.2], subplot_titles=(f"Live Chart: {target}", "Stochastic Oscillator", "Volume"))
        
        # Row 1: Candlestick + MA + Predict
        fig.add_trace(go.Candlestick(x=df.index, open=op, high=hi, low=lo, close=cl, name="Price"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=ma20, line=dict(color='blue', width=1), name="MA20", visible='legendonly'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=ma50, line=dict(color='red', width=1), name="MA50", visible='legendonly'), row=1, col=1)
        fig.add_trace(go.Scatter(x=f_dates, y=f_prices, line=dict(color='yellow', width=2, dash='dot'), name="Predict"), row=1, col=1)
        
        # Row 2: Stochastic
        fig.add_trace(go.Scatter(x=df.index, y=stoch_k, line=dict(color='white', width=1), name="Stoch %K"), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=stoch_d, line=dict(color='orange', width=1), name="Stoch %D"), row=2, col=1)
        fig.add_hline(y=80, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=20, line_dash="dash", line_color="green", row=2, col=1)

        # Row 3: Volume
        fig.add_trace(go.Bar(x=df.index, y=vl, marker_color=['red' if c < o else 'green' for c, o in zip(cl, op)], name="Volume"), row=3, col=1)

        fig.update_layout(template="plotly_dark", height=900, xaxis_rangeslider_visible=False, hovermode="x unified", legend=dict(orientation="h", y=1.05))
        st.plotly_chart(fig, use_container_width=True)
        st.table(pd.DataFrame({"Waktu": [d.strftime('%d %b %H:%M') for d in f_dates], "Estimasi": [f"Rp {p:,.2f}" for p in f_prices]}))

except Exception as e:
    st.error(f"Gagal memuat data. Periksa kode atau timeframe. (Detail: {e})")
