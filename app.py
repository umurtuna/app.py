import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. AYARLAR
st.set_page_config(page_title="Cocoa Works ERP V8", layout="wide")

# 2. ŞİFRE
ERISIM_SIFRESI = "Cocoa2026!" 
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔒 Cocoa Works Güvenli Giriş")
    s = st.text_input("Şifre:", type="password")
    if st.button("Giriş"):
        if s == ERISIM_SIFRESI:
            st.session_state["authenticated"] = True
            st.rerun()
        else: st.error("Hatalı!")
    st.stop()

# 3. BAĞLANTI (ALTERNATİF OKUMA MODU)
conn = st.connection("gsheets", type=GSheetsConnection)

def verileri_yukle():
    data_yapisi = {
        "malzemeler": {}, 
        "receteler_tablo": pd.DataFrame(columns=["recete_ad", "malzeme", "miktar_g"]), 
        "kurlar": {"USD": 32.5, "EUR": 35.0}
    }
    
    try:
        # Sayfayı 'worksheet' ismiyle değil, 'sayfa adı' olarak okumayı dene
        df = conn.read(ttl=0) # Tüm spreadsheet'i oku (varsayılan ilk sayfa)
        
        # Eğer malzemeler ilk sayfada değilse ismini belirterek zorla oku
        try:
            malz_df = conn.read(worksheet="malzemeler", ttl=0)
        except Exception as e:
            st.error(f"⚠️ Google Sheets 'malzemeler' ismini tanıyamıyor: {e}")
            return data_yapisi

        if malz_df is not None and not malz_df.empty:
            # Sütun isimlerini temizle (Başında sonunda boşluk varsa temizler)
            malz_df.columns = [c.strip().lower() for c in malz_df.columns]
            
            # Sayısal çevrim
            sayisal = ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz", "fiyat"]
            for col in sayisal:
                if col in malz_df.columns:
                    malz_df[col] = malz_df[col].astype(str).str.replace(',', '.', regex=False)
                    malz_df[col] = pd.to_numeric(malz_df[col], errors='coerce').fillna(0)
            
            if 'ad' in malz_df.columns:
                malz_dict = malz_df.set_index("ad").to_dict('index')
            else:
                st.error("❌ 'ad' sütunu bulunamadı! Lütfen A1 hücresine 'ad' yazdığınızdan emin olun.")
                return data_yapisi
        else:
            st.warning("⚠️ 'malzemeler' sayfası boş görünüyor.")
            return data_yapisi

        # Kurlar ve Reçeteler (Hata alsa da devam et)
        try:
            r_df = conn.read(worksheet="receteler", ttl=0)
            if r_df is not None: data_yapisi["receteler_tablo"] = r_df
        except: pass
        
        try:
            k_df = conn.read(worksheet="kurlar", ttl=0)
            if k_df is not None and not k_df.empty:
                k_df.columns = [c.strip().lower() for c in k_df.columns]
                data_yapisi["kurlar"] = k_df.set_index("doviz")["oran"].to_dict()
        except: pass

        data_yapisi["malzemeler"] = malz_dict
        return data_yapisi

    except Exception as general_e:
        st.error(f"🚨 KRİTİK BAĞLANTI HATASI: {general_e}")
        return data_yapisi

data = verileri_yukle()

# --- ARAYÜZ ---
st.sidebar.title("Cocoa Works ERP")
menu = st.sidebar.radio("Menü", ["📦 Malzeme Envanteri", "🧪 Reçete Hazırla", "📋 Arşiv"])

if menu == "📦 Malzeme Envanteri":
    st.header("📦 Malzeme Envanteri")
    if data["malzemeler"]:
        st.success("✅ Veriler başarıyla yüklendi!")
        st.dataframe(pd.DataFrame.from_dict(data["malzemeler"], orient='index'), use_container_width=True)
    else:
        st.info("Bağlantı kuruldu ama malzeme listesi işlenemedi.")
