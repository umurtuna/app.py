import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Cocoa Works ERP V9", layout="wide")

# 1. GÜVENLİK
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔒 Cocoa Works Güvenli Giriş")
    s = st.text_input("Şifre:", type="password")
    if st.button("Giriş"):
        if s == "Cocoa2026!":
            st.session_state["authenticated"] = True
            st.rerun()
    st.stop()

# 2. BAĞLANTI (NO-NAME MODU)
conn = st.connection("gsheets", type=GSheetsConnection)

def verileri_yukle():
    data_yapisi = {
        "malzemeler": {}, 
        "receteler_tablo": pd.DataFrame(columns=["recete_ad", "malzeme", "miktar_g"]), 
        "kurlar": {"USD": 32.5, "EUR": 35.0}
    }
    
    try:
        # İSİM KULLANMADAN OKUMA (SADECE SIRALAMA)
        # conn.read() parametresiz çağrıldığında varsayılan olarak ilk sekmeyi (index=0) okur.
        all_dfs = []
        
        # 1. SEKME: MALZEMELER
        try:
            malz_df = conn.read(ttl=0) # İlk sekme
            if malz_df is not None and not malz_df.empty:
                malz_df.columns = [c.strip().lower() for c in malz_df.columns]
                sayisal = ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz", "fiyat"]
                for col in sayisal:
                    if col in malz_df.columns:
                        malz_df[col] = malz_df[col].astype(str).str.replace(',', '.', regex=False)
                        malz_df[col] = pd.to_numeric(malz_df[col], errors='coerce').fillna(0)
                data_yapisi["malzemeler"] = malz_df.set_index("ad").to_dict('index')
        except Exception as e:
            st.warning(f"⚠️ İlk sekme (Malzemeler) okunamadı: {e}")

        # 2. ve 3. SEKMELER İÇİN (Eğer isimle okuma hala 400 veriyorsa bunları boş geçer)
        try:
            r_df = conn.read(worksheet="receteler", ttl=0)
            if r_df is not None: data_yapisi["receteler_tablo"] = r_df
        except: pass
        
        try:
            k_df = conn.read(worksheet="kurlar", ttl=0)
            if k_df is not None:
                k_df.columns = [c.strip().lower() for c in k_df.columns]
                data_yapisi["kurlar"] = k_df.set_index("doviz")["oran"].to_dict()
        except: pass

        return data_yapisi

    except Exception as e:
        st.error(f"🚨 Bağlantı Hatası: {e}")
        return data_yapisi

data = verileri_yukle()

# --- ARAYÜZ ---
st.sidebar.title("Cocoa Works ERP")
menu = st.sidebar.radio("Menü", ["📦 Malzeme Envanteri", "🧪 Reçete Hazırla", "🍰 Katmanlı Ürün", "📋 Arşiv"])

if menu == "📦 Malzeme Envanteri":
    st.header("📦 Malzeme Envanteri")
    if data["malzemeler"]:
        st.success("✅ Veriler ilk sekmeden başarıyla çekildi!")
        st.dataframe(pd.DataFrame.from_dict(data["malzemeler"], orient='index'), use_container_width=True)
    else:
        st.error("Maalesef ilk sekme boş veya 'ad' sütunu bulunamadı.")
        st.info("İpucu: Malzeme sayfanızın Excel'de EN SOLDAKİ ilk sayfa olduğundan emin olun.")

elif menu == "🧪 Reçete Hazırla":
    st.header("🧪 Reçete Hazırlama")
    # ... (Buraya daha önce verdiğim Reçete Hazırlama kodunu ekleyebilirsin)
