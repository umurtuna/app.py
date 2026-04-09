import streamlit as st

# --- GÜVENLİK AYARLARI ---
# Buradaki şifreyi dilediğin zaman değiştirebilirsin.
ERISIM_SIFRESI = "NMR170" 

# Giriş durumunu kontrol et
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

def check_password():
    """Şifre kontrol fonksiyonu"""
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

# Eğer şifre doğru değilse, uygulamanın geri kalanını çalıştırmayı durdur
if not check_password():
    st.stop()

# --- UYGULAMANIN GERİ KALANI BURADAN İTİBAREN DEVAM EDER ---
# (Daha önce yazdığımız V6 kodlarını buranın altına yapıştırabilirsin)
import streamlit as st
import json
import pandas as pd

# Sayfa Ayarları
st.set_page_config(page_title="Cocoa Works ERP V6", layout="wide")

# --- YARDIMCI FONKSİYONLAR ---
def verileri_yukle():
    try:
        with open("veriler.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"malzemeler": {}, "receteler": {}, "kurlar": {"USD": 32.5, "EUR": 35.0}}

def verileri_kaydet(veri):
    with open("veriler.json", "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=4)

def besin_analizi_yap(df, malzemeler, kurlar):
    """Verilen reçete tablosuna göre toplam ve 100g analizini yapar"""
    analiz = {"enerji":0, "yag":0, "karb":0, "seker":0, "lif":0, "protein":0, "tuz":0, "maliyet":0}
    t_gram = df["Miktar (g)"].sum()
    if t_gram == 0: return analiz, 0
    
    for _, row in df.iterrows():
        m = malzemeler[row["Malzeme"]]
        oran = row["Miktar (g)"] / 100
        for anahtar in ["enerji","yag","karb","seker","lif","protein","tuz"]:
            analiz[anahtar] += m[anahtar] * oran
        kur = kurlar.get(m["birim"], 1.0)
        analiz["maliyet"] += (m["fiyat"] * kur / 1000) * row["Miktar (g)"]
    
    return analiz, t_gram

# --- SESSION STATE BAŞLATMA ---
if 'data' not in st.session_state:
    st.session_state.data = verileri_yukle()
if 'gecici_df' not in st.session_state:
    st.session_state.gecici_df = pd.DataFrame(columns=["Malzeme", "Miktar (g)"])

data = st.session_state.data
besin_kalemleri = ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz"]

st.title("🍫 Cocoa Works Ar-Ge Merkezi V6")
menu = st.sidebar.radio("İşlem Seçin", 
    ["📦 Malzeme Envanteri", "📝 Yeni Malzeme Ekle", "🧪 Reçete Hazırla (Simülasyon)", "🍰 Katmanlı Ürün Oluştur", "📋 Arşiv & Analiz", "💱 Döviz Kurları"])

# --- 1. & 2. MALZEME BÖLÜMLERİ (Öncekiyle aynı, hızlı geçiyorum) ---
if menu == "📦 Malzeme Envanteri":
    st.header("Malzeme Listesi")
    if data["malzemeler"]:
        st.dataframe(pd.DataFrame.from_dict(data["malzemeler"], orient='index'), use_container_width=True)
    else: st.info("Malzeme yok.")

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

# --- 3. REÇETE HAZIRLA (SİMÜLASYON) ---
elif menu == "🧪 Reçete Hazırla (Simülasyon)":
    st.header("Reçete Hazırlama Laboratuvarı")
    
    col_add1, col_add2 = st.columns([3,1])
    yeni_m = col_add1.selectbox("Malzeme Seç", list(data["malzemeler"].keys()))
    if col_add2.button("➕ Listeye Ekle"):
        new_row = pd.DataFrame([{"Malzeme": yeni_m, "Miktar (g)": 0.0}])
        st.session_state.gecici_df = pd.concat([st.session_state.gecici_df, new_row], ignore_index=True)

    st.subheader("Simülasyon Tablosu (Miktarları değiştirip sonuçları anlık izleyin)")
    edited_df = st.data_editor(st.session_state.gecici_df, num_rows="dynamic", use_container_width=True)
    st.session_state.gecici_df = edited_df

    if not edited_df.empty:
        res, t_g = besin_analizi_yap(edited_df, data["malzemeler"], data["kurlar"])
        if t_g > 0:
            st.divider()
            c1, c2, c3 = st.columns(3)
            c1.metric("Toplam Ağırlık", f"{t_g:.1f} g")
            c2.metric("Toplam Maliyet", f"{res['maliyet']:.2f} TL")
            c3.metric("Birim Maliyet (kg)", f"{(res['maliyet']/t_g*1000):.2f} TL")
            
            st.subheader("🧪 100g İçin Tam Besin Analizi")
            analiz_df = pd.DataFrame({
                "Besin Ögesi": ["Enerji (kcal)", "Yağ (g)", "Karb. (g)", "Şeker (g)", "Lif (g)", "Protein (g)", "Tuz (g)"],
                "Değer (100g)": [round(res[k]/(t_g/100), 2) for k in besin_kalemleri]
            })
            st.table(analiz_df)

        r_isim = st.text_input("Reçete Adı")
        if st.button("💾 Reçeteyi Kaydet"):
            data["receteler"][r_isim] = edited_df.to_dict('records')
            verileri_kaydet(data)
            st.success("Reçete arşive eklendi!")

# --- 4. KATMANLI ÜRÜN OLUŞTUR ---
elif menu == "🍰 Katmanlı Ürün Oluştur":
    st.header("Katmanlı Ürün Kompozit Analizi")
    katman_sayisi = st.number_input("Katman Sayısı", 1, 5, 2)
    
    katmanlar = []
    t_oran = 0
    cols = st.columns(katman_sayisi)
    for i in range(katman_sayisi):
        with cols[i]:
            k_ad = st.text_input(f"Ad", value=f"Katman {i+1}", key=f"kname_{i}")
            k_rec = st.selectbox(f"Reçete", list(data["receteler"].keys()), key=f"krec_{i}")
            k_oran = st.number_input(f"Oran (%)", 0.0, 100.0, key=f"kper_{i}")
            katmanlar.append({"ad": k_ad, "recete": k_rec, "oran": k_oran})
            t_oran += k_oran
            
    if t_oran == 100:
        if st.button("🧬 TÜM KATMANLARI ANALİZ ET"):
            final = {k: 0 for k in besin_kalemleri + ["maliyet"]}
            for k in katmanlar:
                r_df = pd.DataFrame(data["receteler"][k["recete"]])
                r_res, r_tg = besin_analizi_yap(r_df, data["malzemeler"], data["kurlar"])
                
                # Katmanın kompozit ürüne katkısı
                pay = k["oran"] / 100
                for b in besin_kalemleri:
                    final[b] += (r_res[b] / (r_tg/100)) * pay
                final["maliyet"] += (r_res["maliyet"] / (r_tg/1000)) * pay # kg bazlı maliyet katkısı

            st.divider()
            st.subheader("🏁 Final Ürün (100g) Besin Tablosu")
            final_df = pd.DataFrame({
                "Besin Ögesi": ["Enerji (kcal)", "Yağ (g)", "Karb. (g)", "Şeker (g)", "Lif (g)", "Protein (g)", "Tuz (g)"],
                "Kompozit Değer (100g)": [round(final[k], 2) for k in besin_kalemleri]
            })
            st.table(final_df)
            st.metric("Final Ürün Toplam Maliyet (kg)", f"{final['maliyet']:.2f} TL")
    else: st.warning(f"Toplam oran %100 olmalı! Şu an: %{t_oran}")

# --- 5. ARŞİV & ANALİZ ---
elif menu == "📋 Arşiv & Analiz":
    st.header("Reçete Arşivi ve Geri Çağırma")
    if data["receteler"]:
        secilen_r = st.selectbox("İncelemek istediğiniz reçeteyi seçin", list(data["receteler"].keys()))
        r_df = pd.DataFrame(data["receteler"][secilen_r])
        
        col_ar1, col_ar2 = st.columns(2)
        with col_ar1:
            st.subheader("Malzeme Oranları")
            st.table(r_df)
            
            # --- AKTAR TUŞU ---
            if st.button("🔄 Bu Reçeteyi Düzenlemek İçin Laboratuvara Aktar"):
                st.session_state.gecici_df = r_df.copy()
                st.success("Reçete 'Reçete Hazırla' sekmesine aktarıldı. Oraya gidip değerleri değiştirebilirsiniz!")
        
        with col_ar2:
            st.subheader("Besin Analizi (100g)")
            a_res, a_tg = besin_analizi_yap(r_df, data["malzemeler"], data["kurlar"])
            a_df = pd.DataFrame({
                "Besin Ögesi": ["Enerji", "Yağ", "Karb.", "Şeker", "Lif", "Protein", "Tuz"],
                "Değer": [round(a_res[k]/(a_tg/100), 2) for k in besin_kalemleri]
            })
            st.table(a_df)
            st.metric("Maliyet (kg)", f"{(a_res['maliyet']/a_tg*1000):.2f} TL")
            
        if st.button("🗑️ Reçeteyi Tamamen Sil"):
            del data["receteler"][secilen_r]
            verileri_kaydet(data)
            st.rerun()
    else: st.info("Henüz reçete kaydedilmemiş.")

elif menu == "💱 Döviz Kurları":
    st.header("Kur Ayarları")
    u = st.number_input("USD/TL", value=float(data["kurlar"]["USD"]))
    e = st.number_input("EUR/TL", value=float(data["kurlar"]["EUR"]))
    if st.button("Kurları Güncelle"):
        data["kurlar"].update({"USD": u, "EUR": e})
        verileri_kaydet(data)
        st.success("Güncellendi!")
