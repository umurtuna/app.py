import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. SAYFA AYARLARI
st.set_page_config(page_title="COA Works ERP V14", layout="wide")

# 2. ŞİFRE SİSTEMİ
ERISIM_SIFRESI = "NMR170"
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔒 COA Works Güvenli Giriş")
    s = st.text_input("Şifre:", type="password", key="v14_login_input")
    if st.button("Giriş", key="v13_login_btn"):
        if s == ERISIM_SIFRESI:
            st.session_state["authenticated"] = True
            st.rerun()
    st.stop()

# 3. BAĞLANTI VE NOKTA ATIŞI VERİ ÇEKME
# Secrets'taki ana linki kullanıyoruz
BASE_URL = "https://docs.google.com/spreadsheets/d/1MGFvl8K4Hv1J6HHltgiQFgaE8GX0pG6CbXEHAfNI8Vo/edit"

def verileri_yukle():
    data_yapisi = {
        "malzemeler": {}, 
        "receteler_tablo": pd.DataFrame(columns=["recete_ad", "malzeme", "miktar_g"]), 
        "kurlar": {"USD": 32.5, "EUR": 35.0}
    }
    
    conn = st.connection("gsheets", type=GSheetsConnection)

    # --- MALZEMELER (GID 0) ---
    try:
        m_df = conn.read(spreadsheet=BASE_URL, worksheet="0", ttl=0)
        if m_df is not None and not m_df.empty:
            m_df.columns = [c.strip().lower() for c in m_df.columns]
            sayisal = ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz", "fiyat"]
            for col in sayisal:
                if col in m_df.columns:
                    m_df[col] = m_df[col].astype(str).str.replace(',', '.', regex=False)
                    m_df[col] = pd.to_numeric(m_df[col], errors='coerce').fillna(0)
            data_yapisi["malzemeler"] = m_df.set_index("ad").to_dict('index')
    except Exception as e:
        st.sidebar.error(f"Malzeme Hatası: {e}")

    # --- REÇETELER (GID 2130732789) ---
    try:
        r_df = conn.read(spreadsheet=BASE_URL, worksheet="2130732789", ttl=0)
        if r_df is not None:
            r_df.columns = [c.strip().lower() for c in r_df.columns]
            data_yapisi["receteler_tablo"] = r_df
    except:
        pass

    # --- KURLAR (GID 1768374636) ---
    try:
        k_df = conn.read(spreadsheet=BASE_URL, worksheet="1768374636", ttl=0)
        if k_df is not None and not k_df.empty:
            k_df.columns = [c.strip().lower() for c in k_df.columns]
            k_df["oran"] = k_df["oran"].astype(str).str.replace(',', '.', regex=False)
            k_df["oran"] = pd.to_numeric(k_df["oran"], errors='coerce').fillna(1.0)
            data_yapisi["kurlar"] = k_df.set_index("doviz")["oran"].to_dict()
    except:
        pass

    return data_yapisi

data = verileri_yukle()
besin_kalemleri = ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz"]

# --- ARAYÜZ ---
st.sidebar.title("COA Works ERP")
if st.sidebar.button("🔄 Veriyi Yenile"):
    st.cache_data.clear()
    st.rerun()

menu = st.sidebar.radio("İşlem Seçin", ["📦 Envanter", "🧪 Reçete Hazırla", "🍰 Katmanlı Ürün", "📋 Arşiv"])

# ENVANTER GÖSTERİMİ
if menu == "📦 Envanter":
    st.header("📦 Malzeme Envanteri")
    if data["malzemeler"]:
        st.dataframe(pd.DataFrame.from_dict(data["malzemeler"], orient='index'), use_container_width=True)
    else:
        st.error("Veri hala çekilemedi. Lütfen bağlantı ayarlarını ve Sheets paylaşımını kontrol et.")

# REÇETE HAZIRLAMA (Excel Kopyalama Formatlı)
elif menu == "🧪 Reçete Hazırla":
    st.header("🧪 Reçete Hazırlama")
    if not data["malzemeler"]:
        st.warning("Envanter boş görünüyor.")
    else:
        if 'gecici_v14' not in st.session_state:
            st.session_state.gecici_v14 = pd.DataFrame(columns=["Malzeme", "Miktar (g)"])
        
        c1, c2 = st.columns([3, 1])
        m_sec = c1.selectbox("Malzeme Seç", sorted(data["malzemeler"].keys()), key="v14_m_sec")
        if c2.button("➕ Ekle", key="v14_add_btn"):
            st.session_state.gecici_v14 = pd.concat([st.session_state.gecici_v14, pd.DataFrame([{"Malzeme": m_sec, "Miktar (g)": 0.0}])], ignore_index=True)
        
        edit_df = st.data_editor(st.session_state.gecici_v14, num_rows="dynamic", use_container_width=True, key="v14_editor")
        st.session_state.gecici_v14 = edit_df
        
        if not edit_df.empty:
            # Analiz ve KG Maliyeti hesaplama fonksiyonları burada...
            # (V12'deki hesaplama motoruyla aynı şekilde devam eder)
            st.info("Reçeteyi tamamladığınızda aşağıdan kopyalayıp Excel'e yapıştırabilirsiniz.")
            r_isim = st.text_input("Reçete Adı:", "yeni_ürün", key="v14_r_name")
            tablo_metni = ""
            for _, row in edit_df.iterrows():
                if str(row['Malzeme']).strip():
                    m_str = str(row['Miktar (g)']).replace('.', ',')
                    tablo_metni += f"{r_isim}\t{row['Malzeme']}\t{m_str}\n"
            st.text_area("Excel'e Yapıştırılacak Metin:", tablo_metni, height=150, key="v14_copy_area")

# KATMANLI ÜRÜN VE ARŞİV BÖLÜMLERİ...
# (Kodun geri kalanını bu gid bazlı veri çekme yapısına göre V12 ile birleştirebiliriz)
