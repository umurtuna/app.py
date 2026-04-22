import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re

# 1. AYARLAR & GÜVENLİK
st.set_page_config(page_title="Umur Tuna ERP V24.2", layout="wide")
if "authenticated" not in st.session_state: st.session_state["authenticated"] = False
if not st.session_state["authenticated"]:
    st.title("🔒 Umur Tuna ERP")
    s = st.text_input("Şifre:", type="password", key="v24_2_gate")
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
def verileri_yukle_v24_2():
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

data = verileri_yukle_v24_2()
besin_kalemleri = ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz"]
m_list = sorted([str(v["ad"]) for v in data["malzemeler"].values() if v.get("ad")])

# --- HATA ÇÖZÜMÜ: r_lib için ZIRHLI SIRALAMA ---
if not data["receteler_tablo"].empty and "recete_ad" in data["receteler_tablo"].columns:
    # unique() değerleri al, her birini stringe çevir, boş olanları temizle ve öyle sırala
    raw_names = data["receteler_tablo"]["recete_ad"].unique()
    clean_names = [str(x).strip() for x in raw_names if pd.notna(x) and str(x).strip().lower() != "nan" and str(x).strip() != ""]
    r_lib = sorted(clean_names)
else:
    r_lib = []

# 4. ANALİZ MOTORU
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

# --- 5. MENÜ VE DİĞER SAYFALAR (V24 İLE AYNI) ---
menu = st.sidebar.radio("Menü", ["📦 Hammaddeler", "🧪 Reçete Hazırla", "🍰 Katmanlı Ürün", "🔬 Katmanlı Ürün Deneme", "📋 Arşiv"])

if menu == "📦 Hammaddeler":
    st.header("📦 Hammadde Listesi")
    st.dataframe(pd.DataFrame.from_dict(data["malzemeler"], orient='index'), use_container_width=True)

elif menu == "🧪 Reçete Hazırla":
    st.header("🧪 Reçete Hazırlama")
    if 'v24_2_rec' not in st.session_state: st.session_state.v24_2_rec = pd.DataFrame(columns=["Malzeme", "Miktar (g)"])
    full_opts = sorted(list(set(m_list + r_lib)))
    c1, c2 = st.columns([3, 1])
    sec = c1.selectbox("Seç", full_opts)
    if c2.button("➕ Ekle"):
        st.session_state.v24_2_rec = pd.concat([st.session_state.v24_2_rec, pd.DataFrame([{"Malzeme": sec, "Miktar (g)": 0.0}])], ignore_index=True)
        st.rerun()
    ed = st.data_editor(st.session_state.v24_2_rec, num_rows="dynamic", use_container_width=True, key="v24_2_ed")
    st.session_state.v24_2_rec = ed
    if not ed.empty:
        res, tg, ic = analiz_et(ed, data["malzemeler"], data["kurlar"], data["receteler_tablo"])
        if tg > 0:
            st.divider()
            cols = st.columns(7)
            for i, b in enumerate(besin_kalemleri): cols[i].metric(b.capitalize(), f"{res[b]/(tg/100):.1f}")
            st.metric("💰 KG Maliyeti", f"{(res['maliyet']/tg*1000):.2f} TL")
            st.subheader("📜 İçerik: " + ", ".join([n for n, g in sorted(ic.items(), key=lambda x:x[1], reverse=True)]))
            st.divider()
            name = st.text_input("Ürün İsmi:", "urun_01")
            if st.button("📥 Excel Formatı"):
                st.text_area("Yapıştır:", "".join([f"{name}\t{r['Malzeme']}\t{str(r['Miktar (g)']).replace('.', ',')}\n" for _, r in ed.iterrows()]))

elif menu == "🔬 Katmanlı Ürün Deneme":
    st.header("🔬 Katmanlı Ürün Deneme İstasyonu")
    k_say = st.number_input("Reçete Sayısı", 1, 3, 2)
    final_res = {k: 0.0 for k in besin_kalemleri + ["maliyet"]}
    total_ic = {}
    t_y = 0.0
    for i in range(int(k_say)):
        with st.expander(f"🛠️ Deneme Reçetesi {i+1}", expanded=True):
            y = st.number_input(f"Karışım %", 0.0, 100.0, key=f"v24_2_y_{i}")
            t_y += y
            if f'v24_2_den_{i}' not in st.session_state: st.session_state[f'v24_2_den_{i}'] = pd.DataFrame(columns=["Malzeme", "Miktar (g)"])
            c1, c2 = st.columns([3, 1])
            s = c1.selectbox(f"Malzeme Seç", m_list, key=f"v24_2_ms_{i}")
            if c2.button(f"Ekle", key=f"v24_2_eb_{i}"):
                st.session_state[f'v24_2_den_{i}'] = pd.concat([st.session_state[f'v24_2_den_{i}'], pd.DataFrame([{"Malzeme": s, "Miktar (g)": 0.0}])], ignore_index=True)
                st.rerun()
            ded = st.data_editor(st.session_state[f'v24_2_den_{i}'], num_rows="dynamic", use_container_width=True, key=f"v24_2_ded_{i}")
            st.session_state[f'v24_2_den_{i}'] = ded
            d_res, d_tg, d_ic = analiz_et(ded, data["malzemeler"], data["kurlar"], data["receteler_tablo"])
            if d_tg > 0:
                p = y / 100
                for b in besin_kalemleri + ["maliyet"]: final_res[b] += (d_res[b] / (d_tg/100 if b != "maliyet" else d_tg/1000)) * p
                for m, g in d_ic.items(): total_ic[m] = total_ic.get(m, 0) + (g / d_tg) * y
    if abs(t_y - 100) < 0.1:
        st.divider()
        st.subheader("🧪 Karma Analiz")
        st.table(pd.DataFrame({k.capitalize(): [round(final_res[k], 2)] for k in besin_kalemleri}))
        st.metric("Final KG Maliyeti", f"{final_res['maliyet']:.2f} TL")
        st.subheader("📜 Birleşik İçerik: " + ", ".join([n for n, g in sorted(total_ic.items(), key=lambda x:x[1], reverse=True)]))

elif menu == "🍰 Katmanlı Ürün":
    st.header("🍰 Kayıtlı Katmanlı Ürün")
    if data["receteler_tablo"].empty: st.warning("Arşiv boş.")
    else:
        ks = st.number_input("Katman Sayısı", 1, 5, 2)
        final_k = {k: 0.0 for k in besin_kalemleri + ["maliyet"]}
        t_ok = 0.0
        tic_k = {}
        cols = st.columns(int(ks))
        for i in range(int(ks)):
            with cols[i]:
                ka = st.selectbox(f"Reçete {i+1}", r_lib, key=f"v24_2_ka_{i}")
                ko = st.number_input(f"Oran %", 0.0, 100.0, key=f"v24_2_ko_{i}")
                t_ok += ko
                if ka:
                    rdf = data["receteler_tablo"][data["receteler_tablo"]["recete_ad"] == ka].copy().rename(columns={"malzeme": "Malzeme", "miktar_g": "Miktar (g)"})
                    kr, ktg, km = analiz_et(rdf, data["malzemeler"], data["kurlar"], data["receteler_tablo"])
                    if ktg > 0:
                        p = ko / 100
                        for b in besin_kalemleri + ["maliyet"]: final_k[b] += (kr[b] / (ktg/100 if b != "maliyet" else ktg/1000)) * p
                        for m, g in km.items(): tic_k[m] = tic_k.get(m, 0) + (g / ktg) * ko
        if abs(t_ok - 100) < 0.1:
            st.table(pd.DataFrame({k.capitalize(): [round(final_k[k], 2)] for k in besin_kalemleri}))
            st.metric("Final KG Maliyeti", f"{final_k['maliyet']:.2f} TL")
            st.subheader("📜 İçerik: " + ", ".join([n for n, g in sorted(tic_k.items(), key=lambda x:x[1], reverse=True)]))

elif menu == "📋 Arşiv":
    st.header("📋 Reçete Arşivi")
    if not data["receteler_tablo"].empty:
        s = st.selectbox("Seç", r_lib)
        dfa = data["receteler_tablo"][data["receteler_tablo"]["recete_ad"] == s].copy().rename(columns={"malzeme": "Malzeme", "miktar_g": "Miktar (g)"})
        st.dataframe(dfa[["Malzeme", "Miktar (g)"]], use_container_width=True)
        ar, atg, am = analiz_et(dfa, data["malzemeler"], data["kurlar"], data["receteler_tablo"])
        st.metric("KG Maliyeti", f"{ar['maliyet']/atg*1000:.2f} TL")
