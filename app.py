import streamlit as st

st.set_page_config(page_title="Gıda Reçete Analizi", layout="centered")

st.title("🧪 Gıda Reçete & Maliyet Hesaplayıcı")

# Veri Yapısı (Hafıza)
if 'materials' not in st.session_state:
    st.session_state.materials = {
        "Yağ": {"kcal": 900, "fiyat": 100},
        "Şeker": {"kcal": 400, "fiyat": 10}
    }

# Sol Panel: Hammadde Ekleme
with st.sidebar:
    st.header("📦 Yeni Malzeme")
    name = st.text_input("Malzeme Adı")
    cal = st.number_input("Enerji (kcal/100g)", value=0.0)
    price = st.number_input("Fiyat (TL/kg)", value=0.0)
    if st.button("Listeye Ekle"):
        if name:
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
        pct = st.number_input(f"{m} Oranı (%)", min_value=0.0, max_value=100.0, key=f"input_{m}")
        total_pct += pct
        total_cal += (st.session_state.materials[m]["kcal"] * (pct / 100))
        total_cost += (st.session_state.materials[m]["fiyat"] * (pct / 100))

    if st.button("HESAPLA"):
        if total_pct != 100:
            st.error(f"Toplam oran %100 olmalı! (Şu an: %{total_pct})")
        else:
            st.divider()
            st.success(f"### Analiz Sonucu (100g için)")
            col1, col2 = st.columns(2)
            col1.metric("Enerji", f"{round(total_cal, 2)} kcal")
            col2.metric("Maliyet", f"{round(total_cost, 2)} TL")
