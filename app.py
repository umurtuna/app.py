import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re

# 1. AYARLAR
st.set_page_config(page_title="Umur Tuna ERP V23", layout="wide")

# 2. GÜVENLİK
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔒 Umur Tuna ERP Güvenli Giriş")
    s = st.text_input("Şifre:", type="password", key="v23_gate")
    if st.button("Giriş"):
        if s == "NMR170":
            st.session_state["authenticated"] = True
            st.rerun()
    st.stop()

# 3. YARDIMCI FONKSİYONLAR
def zorla_sayi_yap(deger):
    if pd.isna(deger) or deger == "": return 0.0
    try:
        s = str(deger).replace(',', '.').strip()
        s = re.sub(r'[^0-9.-]', '', s)
        return float(s)
    except: return 0.0

# 4. VERİ YÜKLEME
BASE_URL = "https://docs.google.com/spreadsheets/d/1MGFvl8K4Hv1J6HHltgiQFgaE8GX0pG6CbXEHAfNI8Vo/edit"

@st.cache_data(ttl=600)
def verileri_yukle_v23():
    data_yapisi = {"malzemeler": {}, "receteler_tablo": pd.DataFrame(), "yarimamul_tablo": pd.DataFrame(), "kurlar": {"TRY": 1.0}}
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        # Hammaddeler (GID: 0)
        m_df = conn.read(spreadsheet=BASE_URL, worksheet="0", ttl=0)
        if m_df is not None:
            m_df.columns = [c.strip().lower() for c in m_df.columns]
            for col in ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz", "fiyat"]:
                if col in m_df.columns: m_df[col] = m_df[col].apply(zorla_sayi_yap)
            m_df["ad_key"] = m_df["ad"].astype(str).str.strip().str.lower()
            data_yapisi["malzemeler"] = m_df.set_index("ad_key").to_dict('index')
            
        # Reçeteler (GID: 2130732789)
        r_df = conn.read(spreadsheet=BASE_URL, worksheet="2130732789", ttl=0)
        if r_df is not None:
            r_df.columns = [c.strip().lower() for c in r_df.columns]
            if "miktar_g" in r_df.columns: r_df["miktar_g"] = r_df["miktar_g"].apply(zorla_sayi_yap)
            data_yapisi["receteler_tablo"] = r_df

        # Kurlar (GID: 1768374636)
        k_df = conn.read(spreadsheet=BASE_URL, worksheet="1768374636", ttl=0)
        if k_df is not None:
            k_df.columns = [c.strip().lower() for c in k_df.columns]
            for _, row in k_df.iterrows():
                data_yapisi["kurlar"][str(row['doviz']).upper()] = zorla_sayi_yap(row['oran'])
    except Exception as e:
        st.error(f"⚠️ Veri çekme hatası: {e}")
    return data_yapisi

data = verileri_yukle_v23()
besin_kalemleri = ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz"]
m_list = sorted([v["ad"] for v in data["malzemeler"].values()])

# 5. HESAPLAMA MOTORU (İçerik Dağılım Destekli)
def analiz_et(df, malzemeler, kurlar, receteler_tablo):
    analiz = {k: 0.0 for k in besin_kalemleri + ["maliyet"]}
    icerik_dagilim = {} # Etiket deklarasyonu için
    
    df_calc = df.copy()
    if "Miktar (g)" not in df_calc.columns: return analiz, 0, {}
    df_calc["Miktar (g)"] = df_calc["Miktar (g)"].apply(zorla_sayi_yap)
    t_gram = df_calc["Miktar (g)"].sum()
    if t_gram == 0: return analiz, 0, {}

    for _, row in df_calc.iterrows():
        ad = str(row["Malzeme"]).strip()
        miktar = float(row["Miktar (g)"])
        if miktar <= 0: continue
        
        # EĞER BU BİR YARI MAMULSE (Reçeteler tablosunda varsa)
        is_recete = receteler_tablo[receteler_tablo["recete_ad"] == ad]
        
        if not is_recete.empty:
            # Yarı mamulü parçalarına ayırarak hesapla (Recursive mantık)
            sub_df = is_recete.rename(columns={"malzeme": "Malzeme", "miktar_g": "Miktar (g)"})
            sub_res, sub_tg, sub_map = analiz_et(sub_df, malzemeler, kurlar, receteler_tablo)
            if sub_tg > 0:
                oran = miktar / sub_tg
                for b in besin_kalemleri + ["maliyet"]: analiz[b] += sub_res[b] * oran
                for hammadde, gr in sub_map.items():
                    icerik_dagilim[hammadde] = icerik_dagilim.get(hammadde, 0) + (gr * oran)
        else:
            # DOĞRUDAN HAMMADDEYSE
            m_key = ad.lower()
            icerik_dagilim[ad] = icerik_dagilim.get(ad, 0) + miktar
            if m_key in malzemeler:
                m = malzemeler[m_key]
                oran = miktar / 100
                for b in besin_kalemleri: analiz[b] += float(m.get(b, 0)) * oran
                kur = float(kurlar.get(str(m.get("birim", "TRY")).upper(), 1.0))
                analiz["maliyet"] += (float(m.get("fiyat", 0)) * kur / 1000) * miktar
                
    return analiz, t_gram, icerik_dagilim

# 6. MENÜ
menu = st.sidebar.radio("Menü", ["📦 Hammaddeler", "🧪 Reçete Hazırla", "🍰 Katmanlı Ürün Deneme", "📋 Arşiv"])

# --- HAMMADDELER ---
if menu == "📦 Hammaddeler":
    st.header("📦 Hammadde Listesi")
    st.dataframe(pd.DataFrame.from_dict(data["malzemeler"], orient='index'), use_container_width=True)

# --- REÇETE HAZIRLA ---
elif menu == "🧪 Reçete Hazırla":
    st.header("🧪 Reçete Hazırlama")
    if 'gecici_v23' not in st.session_state: st.session_state.gecici_v23 = pd.DataFrame(columns=["Malzeme", "Miktar (g)"])
    
    # Seçim listesine hem hammaddeleri hem de varsa diğer reçeteleri (yarı mamul olarak) ekliyoruz
    r_list = sorted(data["receteler_tablo"]["recete_ad"].unique()) if not data["receteler_tablo"].empty else []
    full_list = sorted(list(set(m_list + r_list)))
    
    c1, c2 = st.columns([3, 1])
    secilen = c1.selectbox("Malzeme veya Yarı Mamul Seç", full_list)
    if c2.button("➕ Ekle"):
        st.session_state.gecici_v23 = pd.concat([st.session_state.gecici_v23, pd.DataFrame([{"Malzeme": secilen, "Miktar (g)": 0.0}])], ignore_index=True)
        st.rerun()

    edit_df = st.data_editor(st.session_state.gecici_v23, num_rows="dynamic", use_container_width=True, key="v23_editor")
    st.session_state.gecici_v23 = edit_df

    if not edit_df.empty:
        res, tg, icerik = analiz_et(edit_df, data["malzemeler"], data["kurlar"], data["receteler_tablo"])
        if tg > 0:
            st.divider()
            c = st.columns(7)
            for i, b in enumerate(besin_kalemleri): c[i].metric(b.capitalize(), f"{res[b]/(tg/100):.1f}")
            st.metric("💰 KG Maliyeti", f"{(res['maliyet']/tg*1000):.2f} TL")
            
            # İÇERİK DEKLARASYONU
            st.subheader("📜 İçerik Listesi (Azalan Sırada)")
            sorted_i = sorted(icerik.items(), key=lambda x: x[1], reverse=True)
            st.success(", ".join([f"{n}" for n, g in sorted_i if g > 0]))

            st.divider()
            st.subheader("📋 Arşivle")
            r_adi = st.text_input("Ürün İsmi:", value="urun_01")
            if st.button("📥 Excel Formatı"):
                tablo_text = "".join([f"{r_adi}\t{row['Malzeme']}\t{str(row['Miktar (g)']).replace('.', ',')}\n" for _, row in edit_df.iterrows()])
                st.text_area("Kopyala-Yapıştır:", tablo_text, height=150)

# --- KATMANLI ÜRÜN DENEME ---
elif menu == "🍰 Katmanlı Ürün Deneme":
    st.header("🍰 Katmanlı Ürün Deneme")
    k_sayisi = st.number_input("Katman Sayısı", 1, 5, 2)
    
    # Mevcut reçeteleri yarı mamul olarak kullanabilmek için liste
    r_list = sorted(data["receteler_tablo"]["recete_ad"].unique()) if not data["receteler_tablo"].empty else []
    
    final_res = {k: 0.0 for k in besin_kalemleri + ["maliyet"]}
    total_map = {}
    t_yuzde = 0.0
    
    cols = st.columns(int(k_sayisi))
    for i in range(int(k_sayisi)):
        with cols[i]:
            st.subheader(f"Katman {i+1}")
            kat_recete = st.selectbox(f"Reçete Seç", r_list, key=f"v23_k_r_{i}")
            kat_oran = st.number_input(f"Oran %", 0.0, 100.0, key=f"v23_k_o_{i}")
            t_yuzde += kat_oran
            
            if kat_recete:
                r_df = data["receteler_tablo"][data["receteler_tablo"]["recete_ad"] == kat_recete].copy().rename(columns={"malzeme": "Malzeme", "miktar_g": "Miktar (g)"})
                k_res, k_tg, k_map = analiz_et(r_df, data["malzemeler"], data["kurlar"], data["receteler_tablo"])
                
                if k_tg > 0:
                    p = kat_oran / 100
                    for b in besin_kalemleri + ["maliyet"]: final_res[b] += (k_res[b] / (k_tg/100 if b != "maliyet" else k_tg/1000)) * p
                    for mat, gr in k_map.items():
                        total_map[mat] = total_map.get(mat, 0) + (gr / k_tg) * kat_oran

    if abs(t_yuzde - 100) < 0.1:
        st.divider()
        st.subheader("🧪 Karma Sonuç")
        st.table(pd.DataFrame({k.capitalize(): [round(final_res[k], 2)] for k in besin_kalemleri}))
        st.metric("Final KG Maliyeti", f"{final_res['maliyet']:.2f} TL")
        
        st.subheader("📜 Birleşik İçerik Listesi")
        sorted_final = sorted(total_map.items(), key=lambda x: x[1], reverse=True)
        st.success(", ".join([f"{n}" for n, g in sorted_final if g > 0]))
    else:
        st.warning(f"Toplam oran %100 olmalı (Şu an: %{t_yuzde})")

# --- ARŞİV ---
elif menu == "📋 Arşiv":
    st.header("📋 Reçete Arşivi")
    if not data["receteler_tablo"].empty:
        sec = st.selectbox("Seç", sorted(data["receteler_tablo"]["recete_ad"].unique()))
        df_a = data["receteler_tablo"][data["receteler_tablo"]["recete_ad"] == sec].copy().rename(columns={"malzeme": "Malzeme", "miktar_g": "Miktar (g)"})
        st.dataframe(df_a[["Malzeme", "Miktar (g)"]], use_container_width=True)
        res_a, tg_a, map_a = analiz_et(df_a, data["malzemeler"], data["kurlar"], data["receteler_tablo"])
        st.metric("KG Maliyeti", f"{res_a['maliyet']/tg_a*1000:.2f} TL")
