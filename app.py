import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. SAYFA AYARLARI
st.set_page_config(page_title="Cocoa Works ERP V7", layout="wide")

# 2. ŞİFRE SİSTEMİ
ERISIM_SIFRESI = "NMR170" 
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔒 Cocoa Works Güvenli Giriş")
    sifre = st.text_input("Şifre:", type="password")
    if st.button("Giriş"):
        if sifre == ERISIM_SIFRESI:
            st.session_state["authenticated"] = True
            st.rerun()
        else: st.error("Hatalı!")
    st.stop()

# 3. BAĞLANTI VE VERİ YÜKLEME
conn = st.connection("gsheets", type=GSheetsConnection)

def verileri_yukle():
    varsayilan_data = {
        "malzemeler": {}, 
        "receteler_tablo": pd.DataFrame(columns=["recete_ad", "malzeme", "miktar_g"]), 
        "kurlar": {"USD": 32.5, "EUR": 35.0}
    }
    try:
        # MALZEMELER
        malz_df = conn.read(worksheet="malzemeler", ttl=0)
        if malz_df is not None and not malz_df.empty:
            sayisal = ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz", "fiyat"]
            for col in sayisal:
                if col in malz_df.columns:
                    malz_df[col] = malz_df[col].astype(str).str.replace(',', '.', regex=False)
                    malz_df[col] = pd.to_numeric(malz_df[col], errors='coerce').fillna(0)
            malz_dict = malz_df.set_index("ad").to_dict('index')
        else: malz_dict = {}

        # REÇETELER
        try:
            rece_df = conn.read(worksheet="receteler", ttl=0)
            if rece_df is None: rece_df = varsayilan_data["receteler_tablo"]
        except: rece_df = varsayilan_data["receteler_tablo"]

        # KURLAR
        try:
            kur_df = conn.read(worksheet="kurlar", ttl=0)
            kur_dict = kur_df.set_index("doviz")["oran"].to_dict() if (kur_df is not None and not kur_df.empty) else varsayilan_data["kurlar"]
        except: kur_dict = varsayilan_data["kurlar"]

        return {"malzemeler": malz_dict, "receteler_tablo": rece_df, "kurlar": kur_dict}
    except Exception as e:
        st.error(f"Bağlantı Hatası: {e}")
        return varsayilan_data

data = verileri_yukle()
besin_kalemleri = ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz"]

# 4. HESAPLAMA MOTORU
def besin_analizi_yap(df, malzemeler, kurlar):
    analiz = {k: 0 for k in besin_kalemleri + ["maliyet"]}
    t_gram = df["Miktar (g)"].sum()
    if t_gram == 0: return analiz, 0
    for _, row in df.iterrows():
        m_ad = str(row["Malzeme"]).lower().strip()
        if m_ad in malzemeler:
            m = malzemeler[m_ad]
            oran = float(row["Miktar (g)"]) / 100
            for b in besin_kalemleri:
                analiz[b] += float(m[b]) * oran
            k_tipi = m.get("birim", "TRY")
            kur_degeri = float(kurlar.get(k_tipi, 1.0))
            analiz["maliyet"] += (float(m["fiyat"]) * kur_degeri / 1000) * float(row["Miktar (g)"])
    return analiz, t_gram

# 5. ARAYÜZ
st.sidebar.title("Cocoa Works ERP")
menu = st.sidebar.radio("İşlem Seçin", ["📦 Malzeme Envanteri", "🧪 Reçete Hazırla", "🍰 Katmanlı Ürün", "📋 Arşiv"])

if menu == "📦 Malzeme Envanteri":
    st.header("📦 Malzeme Envanteri")
    if data["malzemeler"]:
        st.dataframe(pd.DataFrame.from_dict(data["malzemeler"], orient='index'), use_container_width=True)
    else: st.warning("Excel 'malzemeler' sayfası boş!")

elif menu == "🧪 Reçete Hazırla":
    st.header("🧪 Reçete Hazırlama (Ar-Ge)")
    if not data["malzemeler"]: st.error("Önce Excel'e malzeme girin.")
    else:
        if 'gecici' not in st.session_state: st.session_state.gecici = pd.DataFrame(columns=["Malzeme", "Miktar (g)"])
        m_sec = st.selectbox("Malzeme", list(data["malzemeler"].keys()))
        if st.button("Ekle"):
            st.session_state.gecici = pd.concat([st.session_state.gecici, pd.DataFrame([{"Malzeme": m_sec, "Miktar (g)": 0.0}])], ignore_index=True)
        
        edit_df = st.data_editor(st.session_state.gecici, num_rows="dynamic", use_container_width=True)
        st.session_state.gecici = edit_df
        
        if not edit_df.empty:
            res, tg = besin_analizi_yap(edit_df, data["malzemeler"], data["kurlar"])
            if tg > 0:
                st.divider()
                st.subheader("100g Analizi")
                st.table(pd.DataFrame({k: [round(res[k]/(tg/100), 2)] for k in besin_kalemleri}))
                st.metric("KG Maliyeti", f"{(res['maliyet']/tg*1000):.2f} TL")

elif menu == "🍰 Katmanlı Ürün":
    st.header("🍰 Katmanlı Ürün Oluştur")
    if data["receteler_tablo"].empty: st.warning("Arşivde reçete bulunamadı!")
    else:
        katman_sayisi = st.number_input("Kaç katman?", 1, 5, 2)
        katmanlar = []
        t_oran = 0
        cols = st.columns(katman_sayisi)
        for i in range(int(katman_sayisi)):
            with cols[i]:
                k_ad = st.selectbox(f"Reçete {i+1}", data["receteler_tablo"]["recete_ad"].unique(), key=f"kr_{i}")
                k_oran = st.number_input(f"Oran %", 0.0, 100.0, key=f"ko_{i}")
                katmanlar.append({"ad": k_ad, "oran": k_oran})
                t_oran += k_oran
        
        if t_oran == 100 and st.button("Analiz Et"):
            final = {k: 0 for k in besin_kalemleri + ["maliyet"]}
            for k in katmanlar:
                r_df = data["receteler_tablo"][data["receteler_tablo"]["recete_ad"] == k["ad"]].rename(columns={"malzeme": "Malzeme", "miktar_g": "Miktar (g)"})
                r_res, r_tg = besin_analizi_yap(r_df, data["malzemeler"], data["kurlar"])
                pay = k["oran"] / 100
                for b in besin_kalemleri: final[b] += (r_res[b] / (r_tg/100)) * pay
                final["maliyet"] += (r_res["maliyet"] / (r_tg/1000)) * pay
            st.table(pd.DataFrame({k: [round(final[k], 2)] for k in besin_kalemleri}))
            st.metric("Final KG Maliyeti", f"{final['maliyet']:.2f} TL")

elif menu == "📋 Arşiv":
    st.header("📋 Reçete Arşivi")
    if not data["receteler_tablo"].empty:
        r_isim = st.selectbox("Reçete Seç", data["receteler_tablo"]["recete_ad"].unique())
        r_df = data["receteler_tablo"][data["receteler_tablo"]["recete_ad"] == r_isim].rename(columns={"malzeme": "Malzeme", "miktar_g": "Miktar (g)"})
        st.write(r_df)
        a_res, a_tg = besin_analizi_yap(r_df, data["malzemeler"], data["kurlar"])
        st.table(pd.DataFrame({k: [round(a_res[k]/(a_tg/100), 2)] for k in besin_kalemleri}))
    else: st.info("Arşiv boş.")
