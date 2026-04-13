import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re

# 1. SAYFA AYARLARI
st.set_page_config(page_title="Umur Tuna ERP", layout="wide")

# 2. GÜVENLİK
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔒 Umur Tuna ERP Güvenli Giriş")
    s = st.text_input("Şifre:", type="password", key="v20_1_gate")
    if st.button("Giriş"):
        if s == "NMR170":
            st.session_state["authenticated"] = True
            st.rerun()
    st.stop()

# 3. VERİ YÜKLEME VE ZIRHLI SAYI ÇEVİRİCİ
BASE_URL = "https://docs.google.com/spreadsheets/d/1MGFvl8K4Hv1J6HHltgiQFgaE8GX0pG6CbXEHAfNI8Vo/edit"

def zorla_sayi_yap(deger):
    if pd.isna(deger) or deger == "": return 0.0
    try:
        s = str(deger).replace(',', '.').strip()
        s = re.sub(r'[^0-9.-]', '', s)
        return float(s)
    except:
        return 0.0

@st.cache_data(ttl=600)
def verileri_yukle_v20_1():
    data_yapisi = {"malzemeler": {}, "receteler_tablo": pd.DataFrame(), "kurlar": {"TRY": 1.0}}
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        m_df = conn.read(spreadsheet=BASE_URL, worksheet="0", ttl=0)
        if m_df is not None:
            m_df.columns = [c.strip().lower() for c in m_df.columns]
            for col in ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz", "fiyat"]:
                if col in m_df.columns:
                    m_df[col] = m_df[col].apply(zorla_sayi_yap)
            m_df["ad_key"] = m_df["ad"].astype(str).str.strip().str.lower()
            data_yapisi["malzemeler"] = m_df.set_index("ad_key").to_dict('index')
            
        r_df = conn.read(spreadsheet=BASE_URL, worksheet="2130732789", ttl=0)
        if r_df is not None:
            r_df.columns = [c.strip().lower() for c in r_df.columns]
            if "miktar_g" in r_df.columns:
                r_df["miktar_g"] = r_df["miktar_g"].apply(zorla_sayi_yap)
            data_yapisi["receteler_tablo"] = r_df

        k_df = conn.read(spreadsheet=BASE_URL, worksheet="1768374636", ttl=0)
        if k_df is not None:
            k_df.columns = [c.strip().lower() for c in k_df.columns]
            for index, row in k_df.iterrows():
                data_yapisi["kurlar"][str(row['doviz']).upper()] = zorla_sayi_yap(row['oran'])
    except Exception as e:
        st.error(f"⚠️ Bağlantı Hatası: {e}")
    return data_yapisi

if st.sidebar.button("🔄 Verileri Güncelle"):
    st.cache_data.clear()
    st.rerun()

data = verileri_yukle_v20_1()
besin_kalemleri = ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz"]

# --- KRİTİK DÜZELTME: Malzeme listesini burada tanımlıyoruz ki her yer erişsin ---
m_list = sorted([v["ad"] for v in data["malzemeler"].values()])

# 4. HESAPLAMA MOTORU
def besin_analizi_yap(df, malzemeler, kurlar):
    analiz = {k: 0.0 for k in besin_kalemleri + ["maliyet"]}
    df_calc = df.copy()
    if "Miktar (g)" in df_calc.columns:
        df_calc["Miktar (g)"] = df_calc["Miktar (g)"].apply(zorla_sayi_yap)
        t_gram = df_calc["Miktar (g)"].sum()
    else: return analiz, 0
    
    if t_gram == 0: return analiz, 0
    
    for _, row in df_calc.iterrows():
        m_ad = str(row["Malzeme"]).lower().strip()
        miktar = float(row["Miktar (g)"])
        if m_ad in malzemeler:
            m = malzemeler[m_ad]
            oran = miktar / 100
            for b in besin_kalemleri:
                analiz[b] += float(m.get(b, 0)) * oran
            kur = float(data["kurlar"].get(str(m.get("birim", "TRY")).upper(), 1.0))
            analiz["maliyet"] += (float(m.get("fiyat", 0)) * kur / 1000) * miktar
    return analiz, t_gram

# 5. MENÜ
menu = st.sidebar.radio("Menü", ["📦 Hammaddeler", "🧪 Reçete Hazırla", "🍰 Katmanlı Ürün", "🔬 Katmanlı Ürün Deneme", "📋 Arşiv"])

# --- HAMMADDELER ---
if menu == "📦 Hammaddeler":
    st.header("📦 Hammadde Listesi")
    st.dataframe(pd.DataFrame.from_dict(data["malzemeler"], orient='index'), use_container_width=True)

# --- REÇETE HAZIRLA ---
elif menu == "🧪 Reçete Hazırla":
    st.header("🧪 Reçete Hazırlama")
    if 'gecici_v20_1' not in st.session_state: st.session_state.gecici_v20_1 = pd.DataFrame(columns=["Malzeme", "Miktar (g)"])
    
    c1, c2 = st.columns([3, 1])
    secilen_m = c1.selectbox("Malzeme Seç", m_list, key="v20_1_m_sel")
    if c2.button("➕ Ekle"):
        st.session_state.gecici_v20_1 = pd.concat([st.session_state.gecici_v20_1, pd.DataFrame([{"Malzeme": secilen_m, "Miktar (g)": 0.0}])], ignore_index=True)
        st.rerun()

    edited_data = st.data_editor(st.session_state.gecici_v20_1, num_rows="dynamic", use_container_width=True, key="v20_1_editor")
    st.session_state.gecici_v20_1 = edited_data

    if not edited_data.empty:
        res, tg = besin_analizi_yap(edited_data, data["malzemeler"], data["kurlar"])
        if tg > 0:
            st.divider()
            c = st.columns(7)
            etiketler = ["Enerji", "Yağ", "Karb", "Şeker", "Lif", "Prot", "Tuz"]
            keys = ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz"]
            for i in range(7):
                c[i].metric(etiketler[i], f"{res[keys[i]]/(tg/100):.1f}")
            st.metric("💰 KG Maliyeti", f"{(res['maliyet']/tg*1000):.2f} TL")
            
            st.divider()
            st.subheader("📋 Arşivle")
            c_name, c_btn = st.columns([3, 1])
            r_adi = c_name.text_input("Ürün İsmi:", value="urun_01")
            if c_btn.button("📥 Excel Formatı"):
                tablo_text = ""
                for _, row in edited_data.iterrows():
                    if str(row['Malzeme']).strip():
                        tablo_text += f"{r_adi}\t{row['Malzeme']}\t{str(row['Miktar (g)']).replace('.', ',')}\n"
                st.text_area("Kopyala ve Yapıştır:", value=tablo_text, height=200)

# --- KATMANLI ÜRÜN DENEME ---
elif menu == "🔬 Katmanlı Ürün Deneme":
    st.header("🔬 Katmanlı Ürün Deneme")
    deneme_sayisi = st.number_input("Kaç farklı reçete birleşecek?", 1, 3, 2)
    final_analiz = {k: 0.0 for k in besin_kalemleri + ["maliyet"]}
    toplam_yuzde = 0.0
    
    for i in range(int(deneme_sayisi)):
        with st.expander(f"🛠️ Deneme Reçetesi {i+1}", expanded=True):
            yuzde = st.number_input(f"Karışım Oranı % (R{i+1})", 0.0, 100.0, key=f"v20_1_y_{i}", step=10.0)
            toplam_yuzde += yuzde
            
            if f'v20_1_deneme_{i}' not in st.session_state:
                st.session_state[f'v20_1_deneme_{i}'] = pd.DataFrame(columns=["Malzeme", "Miktar (g)"])
            
            cm, cb = st.columns([3, 1])
            # ARTIK m_list HATASI ALMAYACAK
            m_sec = cm.selectbox(f"Malzeme Seç", m_list, key=f"v20_1_m_trial_{i}")
            if cb.button(f"Ekle", key=f"v20_1_btn_{i}"):
                st.session_state[f'v20_1_deneme_{i}'] = pd.concat([st.session_state[f'v20_1_deneme_{i}'], pd.DataFrame([{"Malzeme": m_sec, "Miktar (g)": 0.0}])], ignore_index=True)
                st.rerun()
            
            d_edit = st.data_editor(st.session_state[f'v20_1_deneme_{i}'], num_rows="dynamic", use_container_width=True, key=f"v20_1_ed_{i}")
            st.session_state[f'v20_1_deneme_{i}'] = d_edit
            
            d_res, d_tg = besin_analizi_yap(d_edit, data["malzemeler"], data["kurlar"])
            if d_tg > 0:
                p = yuzde / 100
                for b in besin_kalemleri: final_analiz[b] += (d_res[b] / (d_tg / 100)) * p
                final_analiz["maliyet"] += (d_res["maliyet"] / (d_tg / 1000)) * p

    st.divider()
    if abs(toplam_yuzde - 100) < 0.1:
        st.subheader("🧪 Final Karışım Sonucu (100g)")
        st.table(pd.DataFrame({k.capitalize(): [round(final_analiz[k], 2)] for k in besin_kalemleri}))
        st.metric("Final KG Maliyeti", f"{final_analiz['maliyet']:.2f} TL")
    else:
        st.warning(f"Toplam oran %100 olmalı. Şu an: %{toplam_yuzde}")

# --- KAYITLI KATMANLI VE ARŞİV (V20 ile aynı) ---
