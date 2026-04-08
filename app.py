import streamlit as st
import json
import pandas as pd

# Sayfa Ayarları
st.set_page_config(page_title="Cocoa Works ERP V4", layout="wide")

# Veri Yönetimi
def verileri_yukle():
    try:
        with open("veriler.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "malzemeler": {}, 
            "receteler": {}, 
            "kurlar": {"USD": 44.30, "EUR": 51.95}
        }

def verileri_kaydet(veri):
    with open("veriler.json", "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=4)

if 'data' not in st.session_state:
    st.session_state.data = verileri_yukle()
if 'gecici_icerik' not in st.session_state:
    st.session_state.gecici_icerik = []

data = st.session_state.data

st.title("🍫 Cocoa Works Yönetim Paneli V4")
menu = st.sidebar.radio("İşlem Seçin", 
    ["📦 Malzeme Listesi & Düzenle", "📝 Yeni Malzeme Ekle", "🧪 Reçete Hazırla", "📋 Kayıtlı Reçeteler", "💱 Döviz Kurları"])

# --- 1. MALZEME LİSTESİ & DÜZENLE --- (Aynı şekilde devam ediyor)
if menu == "📦 Malzeme Listesi & Düzenle":
    st.header("Malzeme Envanteri")
    if data["malzemeler"]:
        df = pd.DataFrame.from_dict(data["malzemeler"], orient='index')
        st.dataframe(df, use_container_width=True)
        st.divider()
        st.subheader("🔍 Hızlı Düzenle")
        duzenlenecek = st.selectbox("Düzenlemek istediğiniz malzemeyi seçin", ["Seçiniz..."] + list(data["malzemeler"].keys()))
        if duzenlenecek != "Seçiniz...":
            m_eski = data["malzemeler"][duzenlenecek]
            with st.form("duzenle_form"):
                c1, c2, c3 = st.columns(3)
                n_enerji = c1.number_input("Enerji (kcal)", value=float(m_eski['enerji']))
                n_yag = c2.number_input("Yağ (g)", value=float(m_eski['yag']))
                n_karb = c3.number_input("Karbonhidrat (g)", value=float(m_eski['karb']))
                n_seker = c1.number_input("Şeker (g)", value=float(m_eski['seker']))
                n_lif = c2.number_input("Lif (g)", value=float(m_eski['lif']))
                n_protein = c3.number_input("Protein (g)", value=float(m_eski['protein']))
                n_tuz = c1.number_input("Tuz (g)", value=float(m_eski['tuz']))
                n_fiyat = c2.number_input("Fiyat", value=float(m_eski['fiyat']))
                n_birim = c3.selectbox("Birim", ["TL", "USD", "EUR"], index=["TL", "USD", "EUR"].index(m_eski['birim']))
                if st.form_submit_button("Güncelle"):
                    data["malzemeler"][duzenlenecek] = {"enerji": n_enerji, "yag": n_yag, "karb": n_karb, "seker": n_seker, "lif": n_lif, "protein": n_protein, "tuz": n_tuz, "fiyat": n_fiyat, "birim": n_birim}
                    verileri_kaydet(data)
                    st.success("Güncellendi!")
                    st.rerun()

# --- 2. YENİ MALZEME EKLE --- (Aynı şekilde devam ediyor)
elif menu == "📝 Yeni Malzeme Ekle":
    st.header("Yeni Malzeme Girişi")
    with st.form("yeni_malzeme"):
        ad = st.text_input("Malzeme Adı").lower().strip()
        c1, c2, c3 = st.columns(3)
        en, yg, kb = c1.number_input("Enerji"), c2.number_input("Yağ"), c3.number_input("Karb.")
        sk, lf, pr = c1.number_input("Şeker"), c2.number_input("Lif"), c3.number_input("Protein")
        tz, fj, br = c1.number_input("Tuz"), c2.number_input("Fiyat (kg/lt)"), c3.selectbox("Para Birimi", ["TL", "USD", "EUR"])
        if st.form_submit_button("Sisteme Ekle"):
            if ad:
                data["malzemeler"][ad] = {"enerji":en,"yag":yg,"karb":kb,"seker":sk,"lif":lf,"protein":pr,"tuz":tz,"fiyat":fj,"birim":br}
                verileri_kaydet(data)
                st.success("Kaydedildi!")

# --- 3. REÇETE HAZIRLA (GELİŞTİRİLMİŞ) ---
elif menu == "🧪 Reçete Hazırla":
    st.header("Reçete Hazırlama & Ar-Ge Analizi")
    
    if not data["malzemeler"]: 
        st.warning("Malzeme ekleyin!")
    else:
        r_ad = st.text_input("Ürün Adı")
        
        # Giriş Tipi Seçimi (Gram mı Yüzde mi?)
        giris_tipi = st.radio("Miktar Giriş Tipi", ["Gram Bazlı", "Yüzde (%) Bazlı"], horizontal=True)
        
        col_m, col_v = st.columns([2, 1])
        m_sec = col_m.selectbox("Malzeme", list(data["malzemeler"].keys()))
        
        if giris_tipi == "Gram Bazlı":
            m_miktar = col_v.number_input("Miktar (Gram)", min_value=0.0)
        else:
            m_miktar = col_v.number_input("Miktar (%)", min_value=0.0, max_value=100.0)
            st.caption("Not: Yüzde bazlı giriş yaparken toplam ağırlığı 100g kabul eder veya sonradan çarpanla büyütebilirsiniz.")

        if st.button("Listeye Ekle"):
            st.session_state.gecici_icerik.append({"isim": m_sec, "miktar": m_miktar, "tip": giris_tipi})

        if st.session_state.gecici_icerik:
            # Reçete Tablosu Oluşturma
            df_recete = pd.DataFrame(st.session_state.gecici_icerik)
            
            # Yüzde ve Gram dönüşümlerini hesapla (Basit mantık: Karışık girilirse gramı baz al)
            total_g = df_recete[df_recete['tip'] == "Gram Bazlı"]['miktar'].sum()
            total_p = df_recete[df_recete['tip'] == "Yüzde (%) Bazlı"]['miktar'].sum()
            
            st.subheader("📋 Mevcut Reçete Taslağı")
            st.table(df_recete)
            
            if st.button("🗑️ Listeyi Temizle"):
                st.session_state.gecici_icerik = []
                st.rerun()

            st.divider()
            
            # --- HESAPLAMA MODÜLÜ ---
            if st.button("🧮 ANALİZ ET (Hesapla)"):
                # Gıda mühendisi için detaylı analiz
                analiz = {"enerji":0, "yag":0, "karb":0, "seker":0, "lif":0, "protein":0, "tuz":0, "maliyet":0}
                t_gram = 0
                
                # Önce toplam gramı bulalım
                for kalem in st.session_state.gecici_icerik:
                    if kalem['tip'] == "Gram Bazlı": t_gram += kalem['miktar']
                    else: t_gram += kalem['miktar'] # Yüzdeyi de gram gibi düşün (100g bazlı)

                for kalem in st.session_state.gecici_icerik:
                    m = data["malzemeler"][kalem["isim"]]
                    mikt = kalem["miktar"]
                    oran = mikt / 100
                    
                    analiz["enerji"] += m["enerji"] * oran
                    analiz["yag"] += m["yag"] * oran
                    analiz["karb"] += m["karb"] * oran
                    analiz["seker"] += m["seker"] * oran
                    analiz["lif"] += m["lif"] * oran
                    analiz["protein"] += m["protein"] * oran
                    analiz["tuz"] += m["tuz"] * oran
                    
                    kur = data["kurlar"].get(m["birim"], 1.0)
                    analiz["maliyet"] += (m["fiyat"] * kur / 1000) * mikt

                # Sonuç Gösterimi
                c1, c2, c3 = st.columns(3)
                c1.metric("Toplam Ağırlık", f"{t_gram:.1f} g")
                c2.metric("Toplam Maliyet", f"{analiz['maliyet']:.2f} TL")
                c3.metric("Birim Maliyet (kg)", f"{(analiz['maliyet']/t_gram*1000):.2f} TL")

                st.subheader("🧪 100g İçin Besin Değerleri Tablosu")
                # 100 grama normalize etme
                norm_f = t_gram / 100
                besin_df = pd.DataFrame({
                    "Besin Öğesi": ["Enerji (kcal)", "Yağ (g)", "Karb. (g)", "Şeker (g)", "Lif (g)", "Protein (g)", "Tuz (g)"],
                    "Değer (100g için)": [
                        round(analiz["enerji"]/norm_f, 2),
                        round(analiz["yag"]/norm_f, 2),
                        round(analiz["karb"]/norm_f, 2),
                        round(analiz["seker"]/norm_f, 2),
                        round(analiz["lif"]/norm_f, 2),
                        round(analiz["protein"]/norm_f, 2),
                        round(analiz["tuz"]/norm_f, 2)
                    ]
                })
                st.dataframe(besin_df, use_container_width=True)

            if st.button("💾 REÇETEYİ ARŞİVLE"):
                if r_ad:
                    data["receteler"][r_ad] = st.session_state.gecici_icerik
                    verileri_kaydet(data)
                    st.success(f"'{r_ad}' başarıyla kaydedildi!")
                    st.session_state.gecici_icerik = []
                else: st.error("Lütfen ürün adı girin!")

# --- DİĞER SEKMELER (Aynı Şekilde Devam) ---
elif menu == "📋 Kayıtlı Reçeteler":
    st.header("Reçete Arşivi")
    if data["receteler"]:
        secilen = st.selectbox("Reçete Seç", list(data["receteler"].keys()))
        st.write(f"İçerik: {data['receteler'][secilen]}")
        if st.button("🗑️ Reçeteyi Sil"):
            del data["receteler"][secilen]
            verileri_kaydet(data)
            st.rerun()
    else: st.info("Reçete yok.")

elif menu == "💱 Döviz Kurları":
    st.header("Kur Ayarları")
    usd_val = st.number_input("1 USD (TL)", value=float(data["kurlar"]["USD"]))
    eur_val = st.number_input("1 EUR (TL)", value=float(data["kurlar"]["EUR"]))
    if st.button("Kurları Güncelle"):
        data["kurlar"]["USD"] = usd_val
        data["kurlar"]["EUR"] = eur_val
        verileri_kaydet(data)
        st.success("Kurlar güncellendi!")
