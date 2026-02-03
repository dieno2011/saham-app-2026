import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# 1. Konfigurasi Halaman
st.set_page_config(page_title="StockPro Ultimate 2026", layout="wide")

st.title("🚀 StockPro Ultimate 2026")
st.write(f"Update Terakhir: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")

# --- KONFIGURASI 10 EMITEN REKOMENDASI ---
emiten_list = [
    "BBRI.JK", "TLKM.JK", "ASII.JK", "ADRO.JK", "GOTO.JK",
    "BMRI.JK", "BBNI.JK", "UNTR.JK", "AMRT.JK", "BRIS.JK"
]

@st.cache_data(ttl=300) 
def get_watchlist_data(tickers):
    combined_data = []
    for t in tickers:
        try:
            # Mengambil periode lebih panjang (5d) untuk memastikan data tidak kosong
            d = yf.download(t, period="5d", interval="1d", progress=False)
            if not d.empty and len(d) >= 2:
                # Perbaikan: Memastikan data diambil sebagai angka tunggal (float)
                price = float(d['Close'].iloc[-1])
                prev = float(d['Close'].iloc[-2])
                change = ((price - prev) / prev) * 100
                combined_data.append({
                    "Ticker": t.replace(".JK", ""),
                    "Harga": price,
                    "Perubahan (%)": round(change, 2)
                })
        except:
            continue
    
    df = pd.DataFrame(combined_data)
    if not df.empty:
        return df.sort_values(by="Perubahan (%)", ascending=False)
    return df

# --- 2. PENGAMBILAN DATA ---
st.subheader("🏆 Top 10 Rekomendasi Hari Ini")
df_watch = get_watchlist_data(emiten_list)

# --- 3. TAMPILAN WATCHLIST ---
if not df_watch.empty:
    # Menampilkan 5 teratas dalam kolom
    top_cols = st.columns(5)
    for i in range(min(5, len(df_watch))):
        with top_cols[i]:
            try:
                # Perbaikan: Menggunakan keyword arguments secara konsisten untuk hindari SyntaxError
                st.metric(
                    label=str(df_watch.iloc[i]['Ticker']), 
                    value=f"Rp {float(df_watch.iloc[i]['Harga']):,.0f}", 
                    delta=f"{float(df_watch.iloc[i]['Perubahan (%)']):.2f}%"
                )
            except:
                st.error("Data Error")
    
    st.write("### Daftar Lengkap (Urutan Performa)")
    st.dataframe(df_watch, use_container_width=True, hide_index=True)
else:
    st.warning("Data tidak tersedia atau bursa sedang tutup.")

st.divider()

# --- 4. ANALISIS DETAIL & BERITA ---
col_a, col_b = st.columns([2, 1])

with col_a:
    st.subheader("🔍 Analisis Teknikal Detail")
    # Perbaikan: Mengambil ticker pertama dari df_watch agar sinkron dengan watchlist
    default_ticker = df_watch.iloc[0]['Ticker'] if not df_watch.empty else "BBRI"
    ticker_input = st.text_input("Ketik Kode Saham:", default_ticker).upper()
    ticker_full = f"{ticker_input}.JK"
    
    try:
        df_detail = yf.download(ticker_full, period="1y", interval="1d", progress=False)
        if not df_detail.empty:
            fig = go.Figure(data=[go.Candlestick(
                x=df_detail.index,
                open=df_detail['Open'], 
                high=df_detail['High'],
                low=df_detail['Low'], 
                close=df_detail['Close'], 
                name="Candlestick"
            )])
            fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("Data detail emiten tidak ditemukan.")
    except:
        st.error("Gagal memuat grafik.")

with col_b:
    st.subheader("📰 Berita Sentimen")
    try:
        saham_news = yf.Ticker(ticker_full)
        news = saham_news.news
        if news:
            for item in news[:5]:
                st.write(f"**{item['title']}**")
                st.caption(f"Sumber: {item['publisher']} | [Baca Berita]({item['link']})")
                st.divider()
        else:
            st.info("Tidak ada berita terbaru untuk emiten ini.")
    except:
        st.write("Berita tidak tersedia.")
