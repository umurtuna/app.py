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

# 3. BAĞLANTI KURMA
conn = st.connection("gsheets", type=GSheetsConnection)

def verileri_yukle():
    # Sayfalar hata verirse uygulamanın çökmemesi için varsayılanlar
    varsayilan_data = {
        "malzemeler": {}, 
        "receteler_tablo": pd.DataFrame(columns=["recete_ad", "malzeme", "miktar_g"]), 
        "kurlar": {"USD": 32.5, "EUR": 35.0}
    }
    
    try:
        # MALZEMELERİ OKU
        try:
            malz_df = conn.read(worksheet="malzemeler", ttl=0)
            if malz_df is not None and not malz_df.empty:
                # Virgül-Nokta Düzeltme
                sayisal = ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz", "fiyat"]
                for col in sayisal:
                    if col in malz_df.columns:
                        malz_df[col] = malz_df[col].astype(str).str.replace(',', '.', regex=False)
                        malz_df[col] = pd.to_numeric(malz_df[col], errors='coerce').fillna(0)
                malz_dict = malz_df.set_index("ad").to_dict('index')
            else: malz_dict = {}
        except: malz_dict = {}

        # REÇETELERİ OKU
        try:
            rece_df = conn.read(worksheet="receteler", ttl=0)
            if rece_df is None or rece_df.empty:
                rece_df = varsayilan_data["receteler_tablo"]
        except:
            rece_df = varsayilan_data["receteler_tablo"]

        # KURLARI OKU
        try:
            kur_df = conn.read(worksheet="kurlar", ttl=0)
            if kur_df is not None and not kur_df.empty:
                kurlar_dict = kur_df.set_index("doviz")["oran"].to_dict()
            else: kurlar_dict = varsayilan_data["kurlar"]
        except:
            kurlar_dict = varsayilan_data["kurlar"]

        return {
            "malzemeler": malz_dict,
            "receteler_tablo": rece_df,
            "kurlar": kurlar_dict
        }
    except Exception as e:
        st.error(f"⚠️ Bağlantı Hatası: {e}")
        return varsayilan_data

# VERİYİ ÇALIŞTIR
data = verileri_yukle()
besin_kalemleri = ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz"]

# 4. HESAPLAMA FONKSİYONU
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
            kur_degeri = float(kurlar.get(m["birim"], 1.0))
            analiz["maliyet"] += (float(m["fiyat"]) * kur_degeri / 1000) * float(row["Miktar (g)"])
    return analiz, t_gram

# 5. ARAYÜZ (MENÜLER)
st.sidebar.title("Cocoa Works ERP")
menu = st.sidebar.radio("İşlem Seçin", ["📦 Malzeme Envanteri", "📝 Yeni Malzeme Ekle", "🧪 Reçete Hazırla", "🍰 Katmanlı Ürün", "📋 Arşiv", "💱 Döviz Kurları"])

if menu == "📦 Malzeme Envanteri":
    st.header("📦 Malzeme Envanteri")
    if data["malzemeler"]:
        df_goster = pd.DataFrame.from_dict(data["malzemeler"], orient='index')
        st.dataframe(df_goster, use_container_width=True)
    else: st.warning("Envanter boş. Lütfen 'malzemeler' sayfasını kontrol edin.")

elif menu == "📝 Yeni Malzeme Ekle":
    st.header("📝 Yeni Malzeme Kaydı")
    with st.form("yeni_m"):
        ad = st.text_input("Malzeme Adı")
        c1, c2, c3 = st.columns(3)
        en = c1.number_input("Enerji")
        yg = c2.number_input("Yağ")
        kb = c3.number_input("Karb.")
        sk = c1.number_input("Şeker")
        lf = c2.number_input("Lif")
        pr = c3.number_input("Protein")
        tz = c1.number_input("Tuz")
        fj = c2.number_input("Fiyat")
        br = c3.selectbox("Birim", ["TRY", "USD", "EUR"])
        if st.form_submit_button("Kaydet"):
            # Mevcut dataframe'e ekle ve güncelle
            yeni_satir = {"ad": ad.lower(), "enerji": en, "yag": yg, "karb": kb, "seker": sk, "lif": lf, "protein": pr, "tuz": tz, "fiyat": fj, "birim": br}
            temp_df = pd.DataFrame.from_dict(data["malzemeler"], orient='index').reset_index().rename(columns={'index': 'ad'})
            temp_df = pd.concat([temp_df, pd.DataFrame([yeni_satir])], ignore_index=True)
            conn.update(worksheet="malzemeler", data=temp_df)
            st.success("Kaydedildi! Sayfayı yenileyin.")

elif menu == "🧪 Reçete Hazırla":
    st.header("🧪 Reçete Hazırlama")
    if not data["malzemeler"]: st.error("Malzeme bulunamadı.")
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
                st.metric("Maliyet (KG)", f"{(res['maliyet']/tg*1000):.2f} TL")
                
                r_isim = st.text_input("Reçete Adı")
                if st.button("Arşivle"):
                    ark_df = edit_df.copy()
                    ark_df["recete_ad"] = r_isim
                    ark_df = ark_df.rename(columns={"Malzeme": "malzeme", "Miktar (g)": "miktar_g"})
                    son_df = pd.concat([data["receteler_tablo"], ark_df], ignore_index=True)
                    conn.update(worksheet="receteler", data=son_df)
                    st.success("Arşivlendi!")

elif menu == "💱 Döviz Kurları":
    st.header("💱 Kur Güncelleme")
    u = st.number_input("USD", value=float(data["kurlar"].get("USD", 32.5)))
    e = st.number_input("EUR", value=float(data["kurlar"].get("EUR", 35.0)))
    if st.button("Güncelle"):
        k_df = pd.DataFrame([{"doviz": "USD", "oran": u}, {"doviz": "EUR", "oran": e}])
        conn.update(worksheet="kurlar", data=k_df)
        st.success("Kurlar güncellendi!")

# Diğer menüler (Arşiv vb.) buraya benzer mantıkla eklenebilir.
