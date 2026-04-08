import streamlit as st
import json

# Sayfa Yapılandırması
st.set_page_config(page_title="Cocoa Works ERP", layout="wide")

def verileri_yukle():
    try:
        with open("veriler.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"malzemeler": {}, "receteler": {}, "kurlar": {"USD": 32.5, "EUR": 35.0}}

def verileri_kaydet(veri):
    with open("veriler.json", "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=4)

# Veriyi başlat
if 'data' not in st.session_state:
    st.session_state.data = verileri_yukle()

data = st.session_state.data

st.title("🍫 Cocoa Works ERP V2")

# Yan Menü (Sidebar)
menu = st.sidebar.selectbox("İşlem Seçin", 
    ["Malzeme Listesi", "Yeni Malzeme Ekle", "Reçete Oluştur", "Kayıtlı Reçeteler", "Döviz Kurları"])

if menu == "Malzeme Listesi":
    st.header("Mevcut Malzemeler")
    if data["malzemeler"]:
        st.table(data["malzemeler"])
    else:
        st.info("Henüz malzeme eklenmemiş.")

elif menu == "Yeni Malzeme Ekle":
    st.header("Yeni Malzeme Girişi")
    with st.form("malzeme_form"):
        ad = st.text_input("Malzeme Adı")
        c1, c2 = st.columns(2)
        enerji = c1.number_input("Enerji (kcal)", min_value=0.0)
        seker = c2.number_input("Şeker (g)", min_value=0.0)
        fiyat = c1.number_input("Birim Fiyat", min_value=0.0)
        para_birimi = c2.selectbox("Para Birimi", ["TL", "USD", "EUR"])
        
        if st.form_submit_button("Kaydet"):
            data["malzemeler"][ad.lower()] = {
                "enerji": enerji, "seker": seker, 
                "fiyat": fiyat, "birim": para_birimi
            }
            verileri_kaydet(data)
            st.success(f"{ad} kaydedildi!")

elif menu == "Döviz Kurları":
    st.header("Kur Güncelleme")
    usd = st.number_input("1 USD kaç TL?", value=data["kurlar"]["USD"])
    eur = st.number_input("1 EUR kaç TL?", value=data["kurlar"]["EUR"])
    if st.button("Kurları Güncelle"):
        data["kurlar"]["USD"] = usd
        data["kurlar"]["EUR"] = eur
        verileri_kaydet(data)
        st.success("Kurlar güncellendi!")

# Diğer menüler de benzer şekilde st. formları ile eklenebilir.
