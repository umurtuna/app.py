import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re

# 1. AYARLAR & GÜVENLİK
st.set_page_config(page_title="Umur Tuna ERP V24.1", layout="wide")
if "authenticated" not in st.session_state: st.session_state["authenticated"] = False
if not st.session_state["authenticated"]:
    st.title("🔒 Umur Tuna ERP")
    s = st.text_input("Şifre:", type="password", key="v24_1_gate")
    if st.button("Giriş"):
        if s == "NMR170":
            st.session_state["authenticated"] = True
            st.rerun()
    st.stop()

# 2. ZIRHLI SAYI ÇEVİRİCİ
def zorla_sayi(deger):
    if pd.isna(deger) or deger == "": return 0.0
    try:
        s = str(deger).replace(',', '.').strip()
        s = re.sub(r'[^0-9.-]', '', s)
        return float(s)
    except: return 0.0

# 3. VERİ YÜKLEME
BASE_URL = "https://docs.google.com/spreadsheets/d/1MGFvl8K4Hv1J6HHltgiQFgaE8GX0pG6CbXEHAfNI8Vo/edit"

@st.cache_data(ttl=600)
def verileri_yukle_v24_1():
    data_yapisi = {"malzemeler": {}, "receteler_tablo": pd.DataFrame(), "kurlar": {"TRY": 1.0}}
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        # Hammaddeler
        m_df = conn.read(spreadsheet=BASE_URL, worksheet="0", ttl=0)
        if m_df is not None:
            m_df.columns = [c.strip().lower() for c in m_df.columns]
            for col in ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz", "fiyat"]:
                if col in m_df.columns: m_df[col] = m_df[col].apply(zorla_sayi)
            m_df["ad_key"] = m_df["ad"].astype(str).str.strip().str.lower()
            data_yapisi["malzemeler"] = m_df.set_index("ad_key").to_dict('index')
            
        # Reçeteler (GID: 2130732789)
        r_df = conn.read(spreadsheet=BASE_URL, worksheet="2130732789", ttl=0)
        if r_df is not None and not r_df.empty:
            r_df.columns = [c.strip().lower() for c in r_df.columns]
            if "miktar_g" in r_df.columns: r_df["miktar_g"] = r_df["miktar_g"].apply(zorla_sayi)
            # HATA ÇÖZÜMÜ: Reçete isimlerini zorla string yap ve boş olanları at
            r_df["recete_ad"] = r_df["recete_ad"].astype(str).str.strip()
            r_df = r_df[r_df["recete_ad"] != "nan"] # Boş hücreleri temizle
            data_yapisi["receteler_tablo"] = r_df

        # Kurlar
        k_df = conn.read(spreadsheet=BASE_URL, worksheet="1768374636", ttl=0)
        if k_df is not None:
            k_df.columns = [c.strip().lower() for c in k_df.columns]
            for _, row in k_df.iterrows():
                data_yapisi["kurlar"][str(row['doviz']).upper()] = zorla_sayi(row['oran'])
    except: pass
    return data_yapisi

if st.sidebar.button("🔄 Verileri Güncelle"):
    st.cache_data.clear()
    st.rerun()

data = verileri_yukle_v24_1()
besin_kalemleri = ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz"]
m_list = sorted([v["ad"] for v in data["malzemeler"].values()])

# --- HATA ÇÖZÜMÜ: r_lib için güvenli sıralama ---
if not data["receteler_tablo"].empty:
    r_lib = sorted([x for x in data["receteler_tablo"]["recete_ad"].unique() if x and x != "nan"])
else:
    r_lib = []

# 4. ANALİZ MOTORU (Recursive/İç İçe Destekli)
def analiz_et(df, malzemeler, kurlar, r_tablo):
    res = {k: 0.0 for k in besin_kalemleri + ["maliyet"]}
    icerik = {}
    df["Miktar (g)"] = df["Miktar (g)"].apply(zorla_sayi)
    t_g = df["Miktar (g)"].sum()
    if t_g == 0: return res, 0, {}

    for _, row in df.iterrows():
        ad = str(row["Malzeme"]).strip()
        mik = float(row["Miktar (g)"])
        if mik <= 0: continue
        
        # Yarı Mamul Kontrolü (Hata önleyici sorgu)
        sub_r = r_tablo[r_tablo["recete_ad"] == ad] if not r_tablo.empty else pd.DataFrame()
        
        if not sub_r.empty:
            s_df = sub_r.rename(columns={"malzeme": "Malzeme", "miktar_g": "Miktar (g)"})
            s_res, s_tg, s_map = analiz_et(s_df, malzemeler, kurlar, r_tablo)
            oran = mik / s_tg
            for k in besin_kalemleri + ["maliyet"]: res[k] += s_res[k] * oran
            for m, g in s_map.items(): icerik[m] = icerik.get(m, 0) + (g * oran)
        else:
            m_key = ad.lower()
            icerik[ad] = icerik.get(ad, 0) + mik
            if m_key in malzemeler:
                m = malzemeler[m_key]
                o = mik / 100
                for k in besin_kalemleri: res[k] += float(m.get(k, 0)) * o
                kur = float(kurlar.get(str(m.get("birim", "TRY")).upper(), 1.0))
                res["maliyet"] += (float(m.get("fiyat", 0)) * kur / 1000) * mik
    return res, t_g, icerik

# --- 5. MENÜ VE DİĞER SAYFALAR (V24 ile aynı şekilde devam eder) ---
# (Kodun geri kalanını V24'ten buraya kopyalayabilirsin, yukarıdaki r_lib düzeltmesi hatayı çözer)
