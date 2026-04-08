import streamlit as st
import json
import pandas as pd

# Sayfa Ayarları
st.set_page_config(page_title="Cocoa Works ERP V5", layout="wide")

# Veri Yönetimi
def verileri_yukle():
    try:
        with open("veriler.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "malzemeler": {}, 
            "receteler": {}, 
            "katmanli_urunler": {},
            "kurlar": {"USD": 32.5, "EUR": 35.0}
        }

def verileri_kaydet(veri):
    with open("veriler.json", "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=4)

if 'data' not in st.session_state:
    st.session_state.data = verileri_yukle()

# Reçete hazırlama için geçici tabloyu session_state'de tutalım
if 'gecici_df' not in st.session_state:
    st.session_state.gecici_df = pd.DataFrame(columns=["Malzeme", "Miktar (g)"])

data = st.session_state.data

st.title("🍫 Cocoa Works Ar-Ge & Üretim V5")
menu = st.sidebar.radio("İşlem Seçin", 
    ["📦 Malzeme Envanteri", "📝 Yeni Malzeme Ekle", "🧪 Reçete Hazırla (Simülasyon)", "🍰 Katmanlı Ürün Oluştur", "📋 Arşiv & Analiz", "💱 Döviz Kurları"])

# --- 1. MALZEME ENVANTERİ & DÜZENLE ---
if menu == "📦 Malzeme Envanteri":
    st.header("Malzeme Listesi")
    if data["malzemeler"]:
        df_malz = pd.DataFrame.from_dict(data["malzemeler"], orient='index')
        st.write("Tablo üzerinden doğrudan düzenleme yapamazsınız, aşağıdaki 'Düzenle' kısmını kullanın.")
        st.dataframe(df_malz, use_container_width=True)
        
        st.divider()
        duzenlenecek = st.selectbox("Düzenle:", ["Seçiniz..."] + list(data["malzemeler"].keys()))
        if duzenlenecek != "Seçiniz...":
            m = data["malzemeler"][duzenlenecek]
            with st.form("duzenle"):
                c = st.columns(3)
                en = c[0].number_input("Enerji", value=float(m['enerji']))
                sk = c[1].number_input("Şeker", value=float(m['seker']))
                fj = c[2].number_input("Fiyat", value=float(m['fiyat']))
                # ... diğer değerleri buraya ekleyebilirsin ...
                if st.form_submit_button("Güncelle"):
                    data["malzemeler"][duzenlenecek].update({"enerji": en, "seker": sk, "fiyat": fj})
                    verileri_kaydet(data)
                    st.rerun()
    else: st.info("Malzeme yok.")

# --- 2. YENİ MALZEME EKLE --- (Hızlı geçiyorum, V4 ile aynı)
elif menu == "📝 Yeni Malzeme Ekle":
    st.header("Yeni Malzeme Girişi")
    with st.form("yeni"):
        ad = st.text_input("Malzeme Adı").lower().strip()
        c1, c2, c3 = st.columns(3)
        en, yg, kb = c1.number_input("Enerji"), c2.number_input("Yağ"), c3.number_input("Karb.")
        sk, lf, pr = c1.number_input("Şeker"), c2.number_input("Lif"), c3.number_input("Protein")
        tz, fj, br = c1.number_input("Tuz"), c2.number_input("Fiyat"), c3.selectbox("Birim", ["TL", "USD", "EUR"])
        if st.form_submit_button("Kaydet"):
            data["malzemeler"][ad] = {"enerji":en,"yag":yg,"karb":kb,"seker":sk,"lif":lf,"protein":pr,"tuz":tz,"fiyat":fj,"birim":br}
            verileri_kaydet(data)
            st.success("Kaydedildi!")

# --- 3. REÇETE HAZIRLA (ANLIK SİMÜLASYON) ---
elif menu == "🧪 Reçete Hazırla (Simülasyon)":
    st.header("Reçete Simülasyonu (Anlık Düzenleme)")
    
    # Malzeme ekleme butonu
    col_add1, col_add2 = st.columns([3,1])
    yeni_m = col_add1.selectbox("Malzeme Seç", list(data["malzemeler"].keys()))
    if col_add2.button("Listeye Ekle"):
        new_row = pd.DataFrame([{"Malzeme": yeni_m, "Miktar (g)": 0.0}])
        st.session_state.gecici_df = pd.concat([st.session_state.gecici_df, new_row], ignore_index=True)

    # st.data_editor ile interaktif tablo
    st.subheader("Simülasyon Tablosu (Miktarları buradan değiştirebilirsiniz)")
    edited_df = st.data_editor(st.session_state.gecici_df, num_rows="dynamic", use_container_width=True)
    st.session_state.gecici_df = edited_df

    if not edited_df.empty:
        # Analiz Fonksiyonu
        def analiz_et(df):
            analiz = {"enerji":0, "yag":0, "karb":0, "seker":0, "lif":0, "protein":0, "tuz":0, "maliyet":0}
            t_gram = df["Miktar (g)"].sum()
            for _, row in df.iterrows():
                m = data["malzemeler"][row["Malzeme"]]
                oran = row["Miktar (g)"] / 100
                for anahtar in ["enerji","yag","karb","seker","lif","protein","tuz"]:
                    analiz[anahtar] += m[anahtar] * oran
                kur = data["kurlar"].get(m["birim"], 1.0)
                analiz["maliyet"] += (m["fiyat"] * kur / 1000) * row["Miktar (g)"]
            return analiz, t_gram

        res, t_g = analiz_et(edited_df)
        
        if t_g > 0:
            st.divider()
            st.subheader("📊 Anlık Analiz Sonuçları")
            c1, c2, c3 = st.columns(3)
            c1.metric("Toplam Ağırlık", f"{t_g} g")
            c2.metric("Toplam Maliyet", f"{res['maliyet']:.2f} TL")
            c3.metric("100g Enerji", f"{(res['enerji']/(t_g/100)):.1f} kcal")
            
            # Detaylı Besin Tablosu
            besin_data = {k: [round(v/(t_g/100), 2)] for k, v in res.items() if k != 'maliyet'}
            st.table(pd.DataFrame(besin_data, index=["100g Değerleri"]))

        # Kaydetme
        r_isim = st.text_input("Reçeteyi Kaydet (İsim verin)")
        if st.button("💾 Reçeteyi Arşive Gönder"):
            data["receteler"][r_isim] = edited_df.to_dict('records')
            verileri_kaydet(data)
            st.success("Reçete başarıyla arşivlendi!")

# --- 4. KATMANLI ÜRÜN OLUŞTUR (YENİ) ---
elif menu == "🍰 Katmanlı Ürün Oluştur":
    st.header("Katmanlı Ürün Geliştirme")
    st.info("Önce 'Reçete Hazırla' kısmından her bir katmanın (iç dolgu, kaplama vb.) reçetesini oluşturup kaydetmelisiniz.")
    
    katman_sayisi = st.number_input("Kaç katmanlı bir ürün?", min_value=1, max_value=5, value=2)
    
    katmanlar = []
    toplam_yuzde = 0
    
    cols = st.columns(katman_sayisi)
    for i in range(katman_sayisi):
        with cols[i]:
            st.subheader(f"{i+1}. Katman")
            k_ad = st.text_input(f"Katman Adı", value=f"Katman {i+1}", key=f"kad_{i}")
            k_recete = st.selectbox(f"Reçete Seç", list(data["receteler"].keys()), key=f"krec_{i}")
            k_oran = st.number_input(f"Ürün İçindeki Oranı (%)", min_value=0.0, max_value=100.0, key=f"koran_{i}")
            katmanlar.append({"ad": k_ad, "recete": k_recete, "oran": k_oran})
            toplam_yuzde += k_oran
            
    st.write(f"**Toplam Oran: %{toplam_yuzde}**")
    
    if toplam_yuzde != 100:
        st.warning("Katman oranlarının toplamı %100 olmalıdır!")
    else:
        if st.button("🧬 KATMANLI ANALİZİ HESAPLA"):
            st.divider()
            st.subheader("🏁 Son Ürün Analizi (Kompozit)")
            
            final_analiz = {"enerji":0, "yag":0, "karb":0, "seker":0, "lif":0, "protein":0, "tuz":0, "maliyet":0}
            detay_tablo = []

            for k in katmanlar:
                # Katmanın kendi 100g değerlerini hesapla
                r_icerik = data["receteler"][k["recete"]]
                r_df = pd.DataFrame(r_icerik)
                
                # Geçici analiz (V4 mantığıyla)
                temp_analiz = {"enerji":0, "yag":0, "karb":0, "seker":0, "lif":0, "protein":0, "tuz":0, "maliyet":0}
                r_toplam_g = r_df["Miktar (g)"].sum()
                for _, row in r_df.iterrows():
                    m = data["malzemeler"][row["Malzeme"]]
                    oran = row["Miktar (g)"] / 100
                    for anahtar in temp_analiz.keys():
                        if anahtar == "maliyet":
                            kur = data["kurlar"].get(m["birim"], 1.0)
                            temp_analiz["maliyet"] += (m["fiyat"] * kur / 1000) * row["Miktar (g)"]
                        else:
                            temp_analiz[anahtar] += m[anahtar] * oran
                
                # Katmanın son ürüne katkısı (Kendi oranıyla çarpılır)
                katki_orani = k["oran"] / 100
                for anahtar in final_analiz.keys():
                    if anahtar == "maliyet":
                        final_analiz["maliyet"] += (temp_analiz["maliyet"] / (r_toplam_g/1000)) * (k["oran"]/100) / 10 # 100g maliyet katkısı
                    else:
                        final_analiz[anahtar] += (temp_analiz[anahtar] / (r_toplam_g/100)) * (k["oran"]/100)

                detay_tablo.append({"Katman": k["ad"], "Reçete": k["recete"], "Pay": f"%{k['oran']}"})

            st.table(pd.DataFrame(detay_tablo))
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Son Ürün Enerji (100g)", f"{final_analiz['enerji']:.1f} kcal")
            c2.metric("Son Ürün Şeker (100g)", f"{final_analiz['seker']:.1f} g")
            c3.metric("Son Ürün Maliyet (kg)", f"{(final_analiz['maliyet']*10):.2f} TL")
            
            st.write("Daha detaylı döküm için 'Arşiv & Analiz' sekmesini kullanabilirsiniz.")

# --- 5. ARŞİV & ANALİZ ---
elif menu == "📋 Arşiv & Analiz":
    st.header("Kayıtlı Reçete Detayları")
    if data["receteler"]:
        secilen_r = st.selectbox("İncelemek istediğiniz reçeteyi seçin", list(data["receteler"].keys()))
        r_df = pd.DataFrame(data["receteler"][secilen_r])
        
        st.subheader("Malzeme Oranları")
        st.table(r_df)
        
        # Burada V4'teki besin tablosu hesaplamasını tekrar gösteriyoruz
        # (Kod kalabalığı olmasın diye detaylandırılabilir)
    else: st.info("Arşiv boş.")

# --- 6. DÖVİZ KURLARI --- (V4 ile aynı)
elif menu == "💱 Döviz Kurları":
    st.header("Kur Ayarları")
    u = st.number_input("USD/TL", value=float(data["kurlar"]["USD"]))
    e = st.number_input("EUR/TL", value=float(data["kurlar"]["EUR"]))
    if st.button("Kurları Güncelle"):
        data["kurlar"].update({"USD": u, "EUR": e})
        verileri_kaydet(data)
        st.success("Güncellendi!")
