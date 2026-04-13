import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. SAYFA AYARLARI
st.set_page_config(page_title="COA Works ERP V12", layout="wide")

# 2. ŞİFRE SİSTEMİ
ERISIM_SIFRESI = "NMR170"
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔒 COA Works Güvenli Giriş")
    # Anahtar kelimeyi (key) tamamen benzersiz yapıyoruz
    s = st.text_input("Şifre:", type="password", key="unique_login_key_2026")
    if st.button("Giriş", key="unique_login_btn"):
        if s == ERISIM_SIFRESI:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Hatalı şifre!")
    st.stop()

# 3. BAĞLANTI VE VERİ YÜKLEME
conn = st.connection("gsheets", type=GSheetsConnection)

def verileri_yukle():
    data_yapisi = {
        "malzemeler": {},
        "receteler_tablo": pd.DataFrame(columns=["recete_ad", "malzeme", "miktar_g"]),
        "kurlar": {"USD": 32.5, "EUR": 35.0},
        "hatalar": []
    }

    try:
        # MALZEMELER
        malz_df = conn.read(worksheet="malzemeler", ttl=0) # Test aşamasında ttl=0 en iyisidir
        if malz_df is not None and not malz_df.empty:
            malz_df.columns = [c.strip().lower() for c in malz_df.columns]
            malz_df = malz_df.dropna(subset=["ad"])
            sayisal = ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz", "fiyat"]
            for col in sayisal:
                if col in malz_df.columns:
                    malz_df[col] = malz_df[col].astype(str).str.replace(',', '.', regex=False)
                    malz_df[col] = pd.to_numeric(malz_df[col], errors='coerce').fillna(0)
            if "birim" in malz_df.columns:
                malz_df["birim"] = malz_df["birim"].astype(str).str.strip().str.upper()
            data_yapisi["malzemeler"] = malz_df.set_index("ad").to_dict('index')
    except Exception as e:
        data_yapisi["hatalar"].append(f"Malzemeler hatası: {e}")

    try:
        # REÇETELER
        r_df = conn.read(worksheet="receteler", ttl=0)
        if r_df is not None and not r_df.empty:
            r_df.columns = [c.strip().lower() for c in r_df.columns]
            r_df = r_df.dropna(subset=["recete_ad", "malzeme"])
            r_df["miktar_g"] = r_df["miktar_g"].astype(str).str.replace(',', '.', regex=False)
            r_df["miktar_g"] = pd.to_numeric(r_df["miktar_g"], errors='coerce').fillna(0)
            data_yapisi["receteler_tablo"] = r_df
    except Exception as e:
        data_yapisi["hatalar"].append(f"Reçeteler hatası: {e}")

    try:
        # KURLAR
        k_df = conn.read(worksheet="kurlar", ttl=0)
        if k_df is not None and not k_df.empty:
            k_df.columns = [c.strip().lower() for c in k_df.columns]
            k_df["oran"] = k_df["oran"].astype(str).str.replace(',', '.', regex=False)
            k_df["oran"] = pd.to_numeric(k_df["oran"], errors='coerce').fillna(1.0)
            data_yapisi["kurlar"] = k_df.set_index("doviz")["oran"].to_dict()
    except Exception as e:
        pass # Kurlar sayfası olmazsa varsayılan kurlar kullanılır

    return data_yapisi

data = verileri_yukle()
besin_kalemleri = ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz"]
besin_etiketleri = {"enerji": "Enerji", "yag": "Yağ", "karb": "Karb.", "seker": "Şeker", "lif": "Lif", "protein": "Prot.", "tuz": "Tuz"}

# 4. HESAPLAMA MOTORU
def besin_analizi_yap(df, malzemeler, kurlar):
    analiz = {k: 0 for k in besin_kalemleri + ["maliyet"]}
    t_gram = df["Miktar (g)"].sum()
    if t_gram == 0: return analiz, 0
    for _, row in df.iterrows():
        m_ad = str(row["Malzeme"]).lower().strip()
        miktar = float(row["Miktar (g)"])
        if m_ad in malzemeler:
            m = malzemeler[m_ad]
            oran = miktar / 100
            for b in besin_kalemleri:
                analiz[b] += float(m.get(b, 0)) * oran
            kur = float(kurlar.get(str(m.get("birim", "TRY")).upper(), 1.0))
            analiz["maliyet"] += (float(m.get("fiyat", 0)) * kur / 1000) * miktar
    return analiz, t_gram

# 5. MENÜ
st.sidebar.title("COA Works ERP")
if st.sidebar.button("🔄 Veriyi Yenile"):
    st.cache_data.clear()
    st.rerun()

menu = st.sidebar.radio("İşlem Seçin", ["📦 Envanter", "🧪 Reçete Hazırla", "🍰 Katmanlı Ürün", "📋 Arşiv"], key="main_nav_radio")

if menu == "📦 Envanter":
    st.header("📦 Malzeme Envanteri")
    if data["malzemeler"]:
        st.dataframe(pd.DataFrame.from_dict(data["malzemeler"], orient='index'), use_container_width=True)
    else:
        st.error("Veri bulunamadı. Lütfen Excel'deki 'malzemeler' sayfasını kontrol edin.")

elif menu == "🧪 Reçete Hazırla":
    st.header("🧪 Reçete Hazırlama")
    if not data["malzemeler"]:
        st.error("Envanter yüklenemedi.")
    else:
        if 'gecici_v12' not in st.session_state:
            st.session_state.gecici_v12 = pd.DataFrame(columns=["Malzeme", "Miktar (g)"])

        c1, c2 = st.columns([3, 1])
        m_sec = c1.selectbox("Malzeme Seç", sorted(data["malzemeler"].keys()), key="recipe_mat_select")
        if c2.button("➕ Ekle", key="recipe_add_btn"):
            yeni = pd.DataFrame([{"Malzeme": m_sec, "Miktar (g)": 0.0}])
            st.session_state.gecici_v12 = pd.concat([st.session_state.gecici_v12, yeni], ignore_index=True)

        edit_df = st.data_editor(st.session_state.gecici_v12, num_rows="dynamic", use_container_width=True, key="recipe_data_editor")
        st.session_state.gecici_v12 = edit_df

        if not edit_df.empty:
            res, tg = besin_analizi_yap(edit_df, data["malzemeler"], data["kurlar"])
            if tg > 0:
                st.divider()
                st.subheader(f"📊 Analiz ({tg:.1f}g)")
                col_met = st.columns(len(besin_kalemleri))
                for idx, b in enumerate(besin_kalemleri):
                    col_met[idx].metric(besin_etiketleri[b], f"{res[b]/(tg/100):.1f}")
                st.metric("💰 KG Maliyeti", f"{res['maliyet']/tg*1000:.2f} TL")

                st.divider()
                st.subheader("📋 Excel Kayıt")
                r_isim_aktar = st.text_input("Reçete Adı:", "yeni_recete", key="final_recipe_name_input")
                tablo_metni = ""
                for _, row in edit_df.iterrows():
                    if str(row['Malzeme']).strip():
                        m_str = str(row['Miktar (g)']).replace('.', ',')
                        tablo_metni += f"{r_isim_aktar}\t{row['Malzeme']}\t{m_str}\n"
                st.text_area("Kopyalayıp Excel'e yapıştırın:", tablo_metni, height=150, key="final_copy_area")

elif menu == "🍰 Katmanlı Ürün":
    st.header("🍰 Katmanlı Ürün")
    if data["receteler_tablo"].empty:
        st.warning("Arşivde reçete bulunamadı. Lütfen önce Excel 'receteler' sayfasını doldurun.")
    else:
        k_sayisi = st.number_input("Katman Sayısı", 1, 5, 2, key="layer_count_input")
        recete_list = sorted(data["receteler_tablo"]["recete_ad"].unique())
        katmanlar = []
        t_oran = 0
        cols = st.columns(int(k_sayisi))
        for i in range(int(k_sayisi)):
            with cols[i]:
                k_ad = st.selectbox(f"Katman {i+1}", recete_list, key=f"layer_sel_{i}")
                k_o = st.number_input(f"Oran %", 0.0, 100.0, step=10.0, key=f"layer_ora_{i}")
                katmanlar.append({"ad": k_ad, "oran": k_o})
                t_oran += k_o
        
        if abs(t_oran - 100) < 0.1:
            if st.button("🧬 Hesapla", key="layer_calc_btn"):
                final = {k: 0.0 for k in besin_kalemleri + ["maliyet"]}
                for k in katmanlar:
                    r_df = data["receteler_tablo"][data["receteler_tablo"]["recete_ad"] == k["ad"]].copy()
                    r_df = r_df.rename(columns={"malzeme": "Malzeme", "miktar_g": "Miktar (g)"})
                    r_res, r_tg = besin_analizi_yap(r_df, data["malzemeler"], data["kurlar"])
                    if r_tg > 0:
                        pay = k["oran"] / 100
                        for b in besin_kalemleri: final[b] += (r_res[b] / (r_tg / 100)) * pay
                        final["maliyet"] += (r_res["maliyet"] / (r_tg / 1000)) * pay
                st.table(pd.DataFrame({besin_etiketleri[k]: [round(final[k], 2)] for k in besin_kalemleri}))
                st.metric("Final KG Maliyeti", f"{final['maliyet']:.2f} TL")
        else:
            st.error(f"Toplam oran %100 olmalı! (Şu an: %{t_oran})")

elif menu == "📋 Arşiv":
    st.header("📋 Reçete Arşivi")
    if not data["receteler_tablo"].empty:
        rec_list = sorted(data["receteler_tablo"]["recete_ad"].unique())
        secilen = st.selectbox("Reçete Seç", rec_list, key="archive_select")
        arsiv_df = data["receteler_tablo"][data["receteler_tablo"]["recete_ad"] == secilen].rename(columns={"malzeme": "Malzeme", "miktar_g": "Miktar (g)"})
        st.dataframe(arsiv_df[["Malzeme", "Miktar (g)"]], use_container_width=True)
        res, tg = besin_analizi_yap(arsiv_df, data["malzemeler"], data["kurlar"])
        if tg > 0:
            st.subheader("Besin Analizi (100g)")
            st.table(pd.DataFrame({besin_etiketleri[k]: [round(res[k]/(tg/100), 2)] for k in besin_kalemleri}))
