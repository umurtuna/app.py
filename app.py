import streamlit as st

st.set_page_config(page_title="Gıda Hesaplayıcı", layout="centered")

st.title("🧪 Gıda Reçete & Maliyet Hesaplayıcı")

# Basit Veri Sözlüğü (Hafıza)
if 'materials' not in st.session_state:
    st.session_state.materials = {
        "Yağ": {"kcal": 900, "fiyat": 100},
        "Şeker": {"kcal": 400, "fiyat": 10}
    }

# Sol Panel: Hammadde Ekleme
with st.sidebar:
    st.header("📦 Malzeme Ekle")
    name = st.text_input("Malzeme Adı")
    cal = st.number_input("Kalori (kcal/100g)", value=0.0)
    price = st.number_input("Fiyat (TL/kg)", value=0.0)
    if st.button("Listeye Ekle"):
        st.session_state.materials[name] = {"kcal": cal, "fiyat": price}
        st.success(f"{name} eklendi!")

# Ana Panel: Reçete
st.subheader("📋 Reçete Oluştur")
mats = list(st.session_state.materials.keys())
selected = st.multiselect("Malzemeleri Seç", mats)

total_cal = 0
total_cost = 0
total_pct = 0

if selected:
    for m in selected:
        pct = st.number_input(f"{m} Oranı (%)", min_value=0.0, max_value=100.0)
        total_pct += pct
        total_cal += (st.session_state.materials[m]["kcal"] * (pct / 100))
        total_cost += (st.session_state.materials[m]["fiyat"] * (pct / 100))

    if st.button("HESAPLA"):
        if total_pct != 100:
            st.error(f"Toplam oran %100 olmalı! (Şu an: %{total_pct})")
        else:
            st.success(f"### Sonuç (100g için)\n**Enerji:** {total_cal} kcal  \n**Maliyet:** {total_cost} TL")
