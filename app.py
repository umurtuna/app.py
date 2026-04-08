import streamlit as st
import json
import pandas as pd

# Sayfa Ayarları
st.set_page_config(page_title="Cocoa Works ERP V3", layout="wide")

# Veri Yönetimi
def verileri_yukle():
    try:
        with open("veriler.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "malzemeler": {}, 
            "receteler": {}, 
            "kurlar": {"USD": 32.5, "EUR": 35.0}
        }

def verileri_kaydet(veri):
    with open("veriler.json", "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=4)

if 'data' not in st.session_state:
    st.session_state.data = verileri_yukle()
if 'gecici_icerik' not in st.session_state:
    st.session_state.gecici_icerik = []

data = st.session_state.data

st.title("🍫 Cocoa Works Yönetim Paneli V3")
menu = st.sidebar.radio("İşlem Seçin", 
    ["📦 Malzeme Listesi & Düzenle", "📝 Yeni Malzeme Ekle", "🧪 Reçete Hazırla", "📋 Kayıtlı Reçeteler", "💱 Döviz Kurları"])

# --- 1. MALZEME LİSTESİ & DÜZENLE ---
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
                    data["malzemeler"][duzenlenecek] = {
                        "enerji": n_enerji, "yag": n_yag, "karb": n_karb, "seker": n_seker,
                        "lif": n_lif, "protein": n_protein, "tuz": n_tuz, "fiyat": n_fiyat, "birim": n_birim
                    }
                    verileri_kaydet(data)
                    st.success("Güncellendi!")
                    st.rerun()
    else:
        st.info("Henüz malzeme yok.")

# --- 2. YENİ MALZEME EKLE ---
elif menu == "📝 Yeni Malzeme Ekle":
    st.header("Yeni Malzeme Girişi")
    with st.form("yeni_malzeme"):
        ad = st.text_input("Malzeme Adı").lower().strip()
        c1, c2, c3 = st.columns(3)
        en = c1.number_input("Enerji", min_value=0.0)
        yg = c2.number_input("Yağ", min_value=0.0)
        kb = c3.number_input("Karb.", min_value=0.0)
        sk = c1.number_input("Şeker", min_value=0.0)
        lf = c2.number_input("Lif", min_value=0.0)
        pr = c3.number_input("Protein", min_value=0.0)
        tz = c1.number_input("Tuz", min_value=0.0)
        fj = c2.number_input("Fiyat (kg/lt)", min_value=0.0)
        br = c3.selectbox("Para Birimi", ["TL", "USD", "EUR"])
        
        if st.form_submit_button("Sisteme Ekle"):
            if ad:
                data["malzemeler"][ad] = {"enerji":en,"yag":yg,"karb":kb,"seker":sk,"lif":lf,"protein":pr,"tuz":tz,"fiyat":fj,"birim":br}
                verileri_kaydet(data)
                st.success("Kaydedildi!")
            else: st.error("İsim giriniz!")

# --- 3. REÇETE HAZIRLA ---
elif menu == "🧪 Reçete Hazırla":
    st.header("Reçete Hazırlama & Anlık Hesaplama")
    if not data["malzemeler"]: st.warning("Malzeme ekleyin!")
    else:
        r_ad = st.text_input("Ürün Adı")
        col_m, col_g = st.columns([2, 1])
        m_sec = col_m.selectbox("Malzeme", list(data["malzemeler"].keys()))
        m_gram = col_g.number_input("Miktar (Gram)", min_value=0.0, step=1.0)
        
        if st.button("Listeye Ekle"):
            st.session_state.gecici_icerik.append({"isim": m_sec, "miktar": m_gram})
        
        if st.session_state.gecici_icerik:
            temp_df = pd.DataFrame(st.session_state.gecici_icerik)
            total_g = temp_df['miktar'].sum()
            temp_df['% (Yüzde)'] = (temp_df['miktar'] / total_g * 100).round(2) if total_g > 0 else 0
            st.table(temp_df)
            
            if st.button("🗑️ Listeyi Temizle"):
                st.session_state.gecici_icerik = []
                st.rerun()

            st.divider()
            if st.button("🧮 HESAPLA (Kaydetmeden Gör)"):
                t_en, t_sk, t_mal = 0, 0, 0
                for kalem in st.session_state.gecici_icerik:
                    m = data["malzemeler"][kalem["isim"]]
                    oran = kalem["miktar"] / 100
                    t_en += m["enerji"] * oran
                    t_sk += m["seker"] * oran
                    kur = data["kurlar"].get(m["birim"], 1.0)
                    t_mal += (m["fiyat"] * kur / 1000) * kalem["miktar"]
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Toplam Ağırlık", f"{total_g}g")
                c2.metric("100g Enerji", f"{(t_en/(total_g/100)):.1f} kcal")
                c3.metric("Toplam Maliyet", f"{t_mal:.2f} TL")

            if st.button("💾 REÇETEYİ KAYDET"):
                if r_ad:
                    data["receteler"][r_ad] = st.session_state.gecici_icerik
                    verileri_kaydet(data)
                    st.success("Reçete Arşive Eklendi!")
                    st.session_state.gecici_icerik = []
                else: st.error("Reçete ismi eksik!")

# --- 4. KAYITLI REÇETELER ---
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

# --- 5. DÖVİZ KURLARI ---
elif menu == "💱 Döviz Kurları":
    st.header("Kur Ayarları")
    # State üzerinden değerleri çekiyoruz ki hata vermesin
    usd_val = st.number_input("1 USD (TL)", value=float(data["kurlar"]["USD"]))
    eur_val = st.number_input("1 EUR (TL)", value=float(data["kurlar"]["EUR"]))
    
    if st.button("Kurları Güncelle"):
        data["kurlar"]["USD"] = usd_val
        data["kurlar"]["EUR"] = eur_val
        verileri_kaydet(data)
        st.success("Kurlar sisteme işlendi!")
