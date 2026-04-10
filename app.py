import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. SAYFA AYARLARI
st.set_page_config(page_title="Cocoa Works Cloud ERP V7", layout="wide")

# 2. GÜVENLİK GİRİŞİ
ERISIM_SIFRESI = "NMR170" # Şifren

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

def check_password():
    if st.session_state["authenticated"]:
        return True
    
    st.title("🔒 Cocoa Works Güvenli Giriş")
    sifre_input = st.text_input("Lütfen erişim şifresini girin:", type="password")
    if st.button("Giriş Yap"):
        if sifre_input == ERISIM_SIFRESI:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("❌ Hatalı şifre! Erişim reddedildi.")
    return False

if not check_password():
    st.stop()

# 3. GOOGLE SHEETS BAĞLANTISI VE VERİ YÜKLEME
conn = st.connection("gsheets", type=GSheetsConnection)

def verileri_yukle():
    try:
        # Sayfaları oku (ttl=0 anlık veri çekmeyi sağlar)
        malz_df = conn.read(worksheet="malzemeler", ttl=0)
        rece_df = conn.read(worksheet="receteler", ttl=0)
        kur_df = conn.read(worksheet="kurlar", ttl=0)
        
        # --- Sayı Düzenleme Yaması (Virgüllü sayıları Python'un anlayacağı noktaya çevirir) ---
        if not malz_df.empty:
            sayisal_kolonlar = ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz", "fiyat"]
            for col in sayisal_kolonlar:
                if col in malz_df.columns:
                    # Virgülleri noktaya çevir, metinleri sayıya dönüştür
                    malz_df[col] = malz_df[col].astype(str).str.replace(',', '.', regex=False)
                    malz_df[col] = pd.to_numeric(malz_df[col], errors='coerce').fillna(0)
        
        # Verileri yapılandırılmış sözlük olarak döndür
        return {
            "malzemeler": malz_df.set_index("ad").to_dict('index') if not malz_df.empty else {},
            "receteler_tablo": rece_df if not rece_df.empty else pd.DataFrame(columns=["recete_ad", "malzeme", "miktar_g"]),
            "kurlar": kur_df.set_index("doviz")["oran"].to_dict() if not kur_df.empty else {"USD": 32.5, "EUR": 35.0}
        }
    except Exception as e:
        st.error(f"⚠️ Bulut Bağlantı Hatası: {e}")
        return {"malzemeler": {}, "receteler_tablo": pd.DataFrame(), "kurlar": {"USD": 32.5, "EUR": 35.0}}

# VERİYİ BAŞLAT (NameError almamak için burada tanımlıyoruz)
data = verileri_yukle()
besin_kalemleri = ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz"]

# 4. YARDIMCI ANALİZ FON
