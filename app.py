import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. AYARLAR
st.set_page_config(page_title="COA Works ERP V17.1", layout="wide")

# 2. GÜVENLİK
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔒 COA Works Güvenli Giriş")
    s = st.text_input("Şifre:", type="password", key="v17_gate")
    if st.button("Giriş"):
        if s == "NMR170":
            st.session_state["authenticated"] = True
            st.rerun()
    st.stop()

# 3. VERİ YÜKLEME (ÖNBELLEKLİ)
BASE_URL = "https://docs.google.com/spreadsheets/d/1MGFvl8K4Hv1J6HHltgiQFgaE8GX0pG6CbXEHAfNI8Vo/edit"

@st.cache_data(ttl=600) # 10 dakika boyunca Excel'e gitmez, çok hızlı çalışır.
def verileri_yukle_v17():
    data_yapisi = {"malzemeler": {}, "receteler_tablo": pd.DataFrame(), "kurlar": {"USD": 32.5, "EUR": 35.0}}
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        m_df = conn.read(spreadsheet=BASE_URL, worksheet="0", ttl=0)
        if m_df is not None:
            m_df.columns = [c.strip().lower() for c in m_df.columns]
            for col in ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz", "fiyat"]:
                if col in m_df.columns:
                    m_df[col] = pd.to_numeric(m_df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
            data_yapisi["malzemeler"] = m_df.set_index("ad").to_dict('index')
            
        r_df = conn.read(spreadsheet=BASE_URL, worksheet="2130732789", ttl=0)
        if r_df is not None:
            r_df.columns = [c.strip().lower() for c in r_df.columns]
            data_yapisi["receteler_tablo"] = r_df

        k_df = conn.read(spreadsheet=BASE_URL, worksheet="1768374636", ttl=0)
        if k_df is not None:
            k_df.columns = [c.strip().lower() for c in k_df.columns]
            data_yapisi["kurlar"] = k_df.set_index("doviz")["oran"].to_dict()
    except: pass
    return data_yapisi

if st.sidebar.button("🔄 Verileri Güncelle (Excel'den Çek)"):
    st.cache_data.clear()
    st.rerun()

data = verileri_yukle_v17()
besin_kalemleri = ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz"]

# 4. HESAPLAMA MOTORU
def besin_analizi_yap(df, malzemeler, kurlar):
    analiz = {k: 0.0 for k in besin_kalemleri + ["maliyet"]}
    df_calc = df.copy()
    df_calc["Miktar (g)"] = pd.to_numeric(df_calc["Miktar (g)"], errors='coerce').fillna(0.0)
    t_gram = df_calc["Miktar (g)"].sum()
    if t_gram == 0: return analiz, 0
    for _, row in df_calc.iterrows():
        m_ad = str(row["Malzeme"]).lower().strip()
        miktar = float(row["Miktar (g)"])
        if m_ad in malzemeler:
            m = malzemeler[m_ad]
            oran = miktar / 100
            for b in besin_kalemleri: analiz[b] += float(m.get(b, 0)) * oran
            kur = float(kurlar.get(str(m.get("birim", "TRY")).upper(), 1.0))
            analiz["maliyet"] += (float(m.get("fiyat", 0)) * kur / 1000) * miktar
    return analiz, t_gram

# 5. MENÜ
menu = st.sidebar.radio("Menü", ["📦 Envanter", "🧪 Reçete Hazırla", "🍰 Katmanlı Ürün", "📋 Arşiv"])

if menu == "🧪 Reçete Hazırla":
    st.header("🧪 Reçete Hazırlama")
    
    if 'gecici_v17' not in st.session_state:
        st.session_state.gecici_v17 = pd.DataFrame(columns=["Malzeme", "Miktar (g)"])

    col1, col2 = st.columns([3, 1])
    m_list = sorted(data["malzemeler"].keys())
    secilen_m = col1.selectbox("Malzeme Seç", m_list)
    
    if col2.button("➕ Listeye Ekle"):
        yeni = pd.DataFrame([{"Malzeme": secilen_m, "Miktar (g)": 0.0}])
        st.session_state.gecici_v17 = pd.concat([st.session_state.gecici_v17, yeni], ignore_index=True)
        st.rerun()

    # VERİ EDİTÖRÜ
    edited_data = st.data_editor(
        st.session_state.gecici_v17,
        num_rows="dynamic",
        use_container_width=True,
        key="v17_editor"
    )
    st.session_state.gecici_v17 = edited_data

    if not edited_data.empty:
        res, tg = besin_analizi_yap(edited_data, data["malzemeler"], data["kurlar"])
        if tg > 0:
            st.divider()
            st.subheader(f"📊 Analiz Değerleri ({tg:.1f}g)")
            c = st.columns(7)
            etiketler = ["Enerji", "Yağ", "Karb", "Şeker", "Lif", "Prot", "Tuz"]
            keys = ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz"]
            for i in range(7):
                c[i].metric(etiketler[i], f"{res[keys[i]]/(tg/100):.1f}")
            st.metric("💰 KG Maliyeti", f"{(res['maliyet']/tg*1000):.2f} TL")

            st.divider()
            st.subheader("📋 Excel Arşivleme")
            # İsim kutusuna 'value' atayarak anlık güncellenmesini garantiye alıyoruz
            r_adi = st.text_input("Ürün İsmi:", key="v17_pname", value="urun_01")
            
            tablo_text = ""
            for _, row in edited_data.iterrows():
                if str(row['Malzeme']).strip() and str(row['Malzeme']) != "None":
                    m_str = str(row['Miktar (g)']).replace('.', ',')
                    tablo_text += f"{r_adi}\t{row['Malzeme']}\t{m_str}\n"
            
            st.text_area("Bu alanı kopyalayıp Excel'e yapıştırın:", value=tablo_text, height=180, key="v17_copy")

# Diğer sekmeler aynen korundu
elif menu == "📦 Envanter":
    st.header("📦 Malzeme Envanteri")
    st.dataframe(pd.DataFrame.from_dict(data["malzemeler"], orient='index'), use_container_width=True)

elif menu == "🍰 Katmanlı Ürün":
    st.header("🍰 Katmanlı Ürün Analizi")
    if data["receteler_tablo"].empty: st.warning("Reçete bulunamadı.")
    else:
        k_sayisi = st.number_input("Katman Sayısı", 1, 5, 2)
        r_list = sorted(data["receteler_tablo"]["recete_ad"].unique())
        k_verileri = []
        t_oran = 0.0
        cols = st.columns(int(k_sayisi))
        for i in range(int(k_sayisi)):
            with cols[i]:
                k_ad = st.selectbox(f"Reçete {i+1}", r_list, key=f"k_s_{i}")
                k_o = st.number_input(f"Oran %", 0.0, 100.0, key=f"k_o_{i}")
                k_verileri.append({"ad": k_ad, "oran": k_o})
                t_oran += k_o
        if abs(t_oran - 100) < 0.1 and st.button("🧬 Hesapla"):
            final = {k: 0.0 for k in besin_kalemleri + ["maliyet"]}
            for k in k_verileri:
                r_df = data["receteler_tablo"][data["receteler_tablo"]["recete_ad"] == k["ad"]].copy()
                r_df = r_df.rename(columns={"malzeme": "Malzeme", "miktar_g": "Miktar (g)"})
                r_res, r_tg = besin_analizi_yap(r_df, data["malzemeler"], data["kurlar"])
                if r_tg > 0:
                    p = k["oran"] / 100
                    for b in besin_kalemleri: final[b] += (r_res[b] / (r_tg / 100)) * p
                    final["maliyet"] += (r_res["maliyet"] / (r_tg / 1000)) * p
            st.table(pd.DataFrame({k: [round(final[k], 2)] for k in besin_kalemleri}))
            st.metric("Final KG Maliyeti", f"{final['maliyet']:.2f} TL")

elif menu == "📋 Arşiv":
    st.header("📋 Reçete Arşivi")
    if not data["receteler_tablo"].empty:
        r_list = sorted(data["receteler_tablo"]["recete_ad"].unique())
        sec = st.selectbox("Reçete Seç", r_list)
        df_arsiv = data["receteler_tablo"][data["receteler_tablo"]["recete_ad"] == sec].rename(columns={"malzeme": "Malzeme", "miktar_g": "Miktar (g)"})
        st.dataframe(df_arsiv[["Malzeme", "Miktar (g)"]], use_container_width=True)
        res, tg = besin_analizi_yap(df_arsiv, data["malzemeler"], data["kurlar"])
        if tg > 0:
            st.subheader("Besin Analizi (100g)")
            c = st.columns(7)
            for i, b in enumerate(besin_kalemleri):
                c[i].metric(b.capitalize(), f"{res[b]/(tg/100):.2f}")
            st.metric("Maliyet (KG)", f"{res['maliyet']/tg*1000:.2f} TL")
