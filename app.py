import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. SAYFA AYARLARI
st.set_page_config(page_title="COA Works ERP V11", layout="wide")

# 2. ŞİFRE SİSTEMİ
ERISIM_SIFRESI = "NMR170"
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔒 COA Works Güvenli Giriş")
    s = st.text_input("Şifre:", type="password", key="main_login_pass")
    if st.button("Giriş", key="login_btn"):
        if s == ERISIM_SIFRESI:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Hatalı şifre!")
    st.stop()

# 3. BAĞLANTI
conn = st.connection("gsheets", type=GSheetsConnection)

# VERİ YÜKLEME - ttl=300 ile 5 dakika önbellekleme (hız için kritik!)
def verileri_yukle():
    data_yapisi = {
        "malzemeler": {},
        "receteler_tablo": pd.DataFrame(columns=["recete_ad", "malzeme", "miktar_g"]),
        "kurlar": {"USD": 32.5, "EUR": 35.0},
        "hatalar": []
    }

    # --- MALZEMELER ---
    try:
        malz_df = conn.read(worksheet="malzemeler", ttl=300)
        if malz_df is not None and not malz_df.empty:
            malz_df.columns = [c.strip().lower() for c in malz_df.columns]
            malz_df = malz_df.dropna(subset=["ad"])
            sayisal = ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz", "fiyat"]
            for col in sayisal:
                if col in malz_df.columns:
                    malz_df[col] = malz_df[col].astype(str).str.replace(',', '.', regex=False)
                    malz_df[col] = pd.to_numeric(malz_df[col], errors='coerce').fillna(0)
            # Döviz birimini büyük harfe çevir (USD, EUR, TRY eşleşmesi için)
            if "birim" in malz_df.columns:
                malz_df["birim"] = malz_df["birim"].astype(str).str.strip().str.upper()
            data_yapisi["malzemeler"] = malz_df.set_index("ad").to_dict('index')
    except Exception as e:
        data_yapisi["hatalar"].append(f"Malzemeler sayfası hatası: {e}")

    # --- REÇETELER ---
    try:
        r_df = conn.read(worksheet="receteler", ttl=300)
        if r_df is not None and not r_df.empty:
            r_df.columns = [c.strip().lower() for c in r_df.columns]
            # Beklenen sütunlar: recete_ad, malzeme, miktar_g
            gerekli = ["recete_ad", "malzeme", "miktar_g"]
            eksik = [k for k in gerekli if k not in r_df.columns]
            if eksik:
                data_yapisi["hatalar"].append(
                    f"Reçeteler sayfasında eksik sütun(lar): {eksik}. "
                    f"Mevcut sütunlar: {list(r_df.columns)}"
                )
            else:
                r_df = r_df.dropna(subset=["recete_ad", "malzeme"])
                r_df["miktar_g"] = r_df["miktar_g"].astype(str).str.replace(',', '.', regex=False)
                r_df["miktar_g"] = pd.to_numeric(r_df["miktar_g"], errors='coerce').fillna(0)
                data_yapisi["receteler_tablo"] = r_df
        else:
            data_yapisi["hatalar"].append("Reçeteler sayfası boş veya bulunamadı.")
    except Exception as e:
        data_yapisi["hatalar"].append(f"Reçeteler sayfası hatası: {e}")

    # --- KURLAR ---
    try:
        k_df = conn.read(worksheet="kurlar", ttl=300)
        if k_df is not None and not k_df.empty:
            k_df.columns = [c.strip().lower() for c in k_df.columns]
            k_df["doviz"] = k_df["doviz"].astype(str).str.strip().str.upper()
            k_df["oran"] = k_df["oran"].astype(str).str.replace(',', '.', regex=False)
            k_df["oran"] = pd.to_numeric(k_df["oran"], errors='coerce').fillna(1.0)
            data_yapisi["kurlar"] = k_df.set_index("doviz")["oran"].to_dict()
    except Exception as e:
        data_yapisi["hatalar"].append(f"Kurlar sayfası hatası: {e}")

    return data_yapisi

# Yenile butonu - önbelleği temizler ve sayfayı yeniler
if st.sidebar.button("🔄 Veriyi Yenile"):
    st.cache_data.clear()
    st.rerun()

data = verileri_yukle()

# Hataları göster (geliştirici modu - sorun gidermek için)
if data["hatalar"]:
    with st.sidebar.expander("⚠️ Uyarılar", expanded=False):
        for h in data["hatalar"]:
            st.warning(h)

besin_kalemleri = ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz"]
besin_etiketleri = {
    "enerji": "Enerji (kcal)", "yag": "Yağ (g)", "karb": "Karbonhidrat (g)",
    "seker": "Şeker (g)", "lif": "Lif (g)", "protein": "Protein (g)", "tuz": "Tuz (g)"
}

# 4. HESAPLAMA MOTORU
def besin_analizi_yap(df, malzemeler, kurlar):
    analiz = {k: 0 for k in besin_kalemleri + ["maliyet"]}
    df = df.copy()
    df["Miktar (g)"] = pd.to_numeric(df["Miktar (g)"], errors='coerce').fillna(0)
    t_gram = df["Miktar (g)"].sum()
    if t_gram == 0:
        return analiz, 0
    for _, row in df.iterrows():
        m_ad = str(row["Malzeme"]).lower().strip()
        miktar = float(row["Miktar (g)"])
        if m_ad in malzemeler and miktar > 0:
            m = malzemeler[m_ad]
            oran_100g = miktar / 100
            for b in besin_kalemleri:
                analiz[b] += float(m.get(b, 0)) * oran_100g
            # Döviz çevirimi: birim TRY ise kur=1, USD/EUR ise kurdan çek
            birim = str(m.get("birim", "TRY")).strip().upper()
            kur = float(kurlar.get(birim, 1.0))
            fiyat_tl_kg = float(m.get("fiyat", 0)) * kur  # TL/kg cinsine çevir
            analiz["maliyet"] += (fiyat_tl_kg / 1000) * miktar  # TL/g * gram
    return analiz, t_gram

# 5. ARAYÜZ VE MENÜLER
st.sidebar.title("COA Works ERP")
menu = st.sidebar.radio(
    "İşlem Seçin",
    ["📦 Envanter", "🧪 Reçete Hazırla", "🍰 Katmanlı Ürün", "📋 Arşiv"],
    key="sidebar_menu"
)

# ─────────────────────────────────────────────────────────────────────────────
# ENVANTER
# ─────────────────────────────────────────────────────────────────────────────
if menu == "📦 Envanter":
    st.header("📦 Malzeme Envanteri")
    if data["malzemeler"]:
        df_env = pd.DataFrame.from_dict(data["malzemeler"], orient='index')
        df_env.index.name = "Malzeme"
        st.dataframe(df_env, use_container_width=True)
        st.caption(f"Toplam {len(df_env)} malzeme listelendi.")
    else:
        st.warning("Google Sheets 'malzemeler' sayfası okunamadı. Soldaki Uyarılar bölümünü kontrol edin.")

# ─────────────────────────────────────────────────────────────────────────────
# REÇETE HAZIRLA
# ─────────────────────────────────────────────────────────────────────────────
elif menu == "🧪 Reçete Hazırla":
    st.header("🧪 Reçete Hazırlama")
    if not data["malzemeler"]:
        st.error("Malzeme listesi yüklenemedi. Lütfen Google Sheets bağlantısını kontrol edin.")
    else:
        if 'gecici' not in st.session_state:
            st.session_state.gecici = pd.DataFrame(columns=["Malzeme", "Miktar (g)"])

        c1, c2 = st.columns([3, 1])
        m_sec = c1.selectbox("Malzeme Seç", sorted(data["malzemeler"].keys()), key="sel_malz_new")
        if c2.button("➕ Ekle", key="add_btn_new"):
            yeni_satir = pd.DataFrame([{"Malzeme": m_sec, "Miktar (g)": 0.0}])
            st.session_state.gecici = pd.concat(
                [st.session_state.gecici, yeni_satir], ignore_index=True
            )

        if st.button("🗑️ Reçeteyi Temizle", key="clear_btn"):
            st.session_state.gecici = pd.DataFrame(columns=["Malzeme", "Miktar (g)"])
            st.rerun()

        edit_df = st.data_editor(
            st.session_state.gecici,
            num_rows="dynamic",
            use_container_width=True,
            key="main_editor"
        )
        st.session_state.gecici = edit_df

        if not edit_df.empty:
            res, tg = besin_analizi_yap(edit_df, data["malzemeler"], data["kurlar"])
            if tg > 0:
                st.divider()
                st.subheader(f"📊 Analiz — Toplam: {tg:.1f}g")

                # Besin değerleri (100g başına)
                cols_b = st.columns(len(besin_kalemleri))
                for i, k in enumerate(besin_kalemleri):
                    cols_b[i].metric(besin_etiketleri[k], f"{res[k]/(tg/100):.2f}")

                col_m1, col_m2 = st.columns(2)
                col_m1.metric("💰 Toplam Maliyet", f"{res['maliyet']:.2f} TL")
                col_m2.metric("💰 KG Maliyeti", f"{res['maliyet']/tg*1000:.2f} TL")

                st.divider()
                st.subheader("📋 Excel'e Aktar")
                st.caption(
                    "Aşağıdaki metni kopyalayıp Google Sheets'teki **receteler** "
                    "sayfasına yapıştırın. Sütun sırası: recete_ad | malzeme | miktar_g"
                )
                r_isim = st.text_input("Reçete Adı", "yeni_recete", key="input_recete_ad_aktar")
                tablo_metni = ""
                for _, row in edit_df.iterrows():
                    if str(row['Malzeme']).strip():
                        miktar_str = str(row['Miktar (g)']).replace('.', ',')
                        tablo_metni += f"{r_isim}\t{row['Malzeme']}\t{miktar_str}\n"
                st.text_area("Kopyalanacak metin:", tablo_metni, height=180, key="copy_area_new")

# ─────────────────────────────────────────────────────────────────────────────
# KATMANLI ÜRÜN
# ─────────────────────────────────────────────────────────────────────────────
elif menu == "🍰 Katmanlı Ürün":
    st.header("🍰 Katmanlı Ürün Analizi")

    if data["receteler_tablo"].empty:
        st.warning("⚠️ Reçeteler sayfası okunamadı veya boş.")
        st.info(
            "Google Sheets'te **receteler** adında bir sekme açın. "
            "Sütunlar şu şekilde olmalı:\n\n"
            "| recete_ad | malzeme | miktar_g |\n"
            "|-----------|---------|----------|\n"
            "| cikolata  | kakao   | 200      |"
        )
        if data["hatalar"]:
            st.error("Tespit edilen hata: " + " | ".join(data["hatalar"]))
    else:
        recete_listesi = sorted(data["receteler_tablo"]["recete_ad"].dropna().unique())
        st.success(f"✅ {len(recete_listesi)} reçete yüklendi: {', '.join(recete_listesi)}")

        k_sayisi = st.number_input("Katman Sayısı", 1, 5, 2, key="katman_count")
        katmanlar = []
        t_oran = 0.0
        cols = st.columns(int(k_sayisi))
        for i in range(int(k_sayisi)):
            with cols[i]:
                k_ad = st.selectbox(f"Katman {i+1} Reçetesi", recete_listesi, key=f"kat_sel_{i}")
                k_o = st.number_input(f"Oran % (Katman {i+1})", 0.0, 100.0, step=5.0, key=f"kat_ora_{i}")
                katmanlar.append({"ad": k_ad, "oran": k_o})
                t_oran += k_o

        if abs(t_oran - 100) > 0.01:
            st.warning(f"⚠️ Toplam oran: **{t_oran:.1f}%** — 100% olmalı")
        else:
            st.success("✅ Toplam oran: 100%")

        if abs(t_oran - 100) <= 0.01 and st.button("🔍 Analiz Yap", key="btn_kompozit"):
            final = {k: 0.0 for k in besin_kalemleri + ["maliyet"]}
            hata_var = False
            for k in katmanlar:
                r_df = data["receteler_tablo"][
                    data["receteler_tablo"]["recete_ad"] == k["ad"]
                ].copy()
                r_df = r_df.rename(columns={"malzeme": "Malzeme", "miktar_g": "Miktar (g)"})
                r_res, r_tg = besin_analizi_yap(r_df, data["malzemeler"], data["kurlar"])
                if r_tg == 0:
                    st.error(f"'{k['ad']}' reçetesi hesaplanamadı (toplam gram = 0).")
                    hata_var = True
                    continue
                pay = k["oran"] / 100
                for b in besin_kalemleri:
                    final[b] += (r_res[b] / (r_tg / 100)) * pay
                final["maliyet"] += (r_res["maliyet"] / (r_tg / 1000)) * pay

            if not hata_var:
                st.divider()
                st.subheader("📊 Final Ürün Analizi (100g başına)")
                cols_f = st.columns(len(besin_kalemleri))
                for i, k in enumerate(besin_kalemleri):
                    cols_f[i].metric(besin_etiketleri[k], f"{final[k]:.2f}")
                st.metric("💰 Final KG Maliyeti", f"{final['maliyet']:.2f} TL")

# ─────────────────────────────────────────────────────────────────────────────
# ARŞİV
# ─────────────────────────────────────────────────────────────────────────────
elif menu == "📋 Arşiv":
    st.header("📋 Reçete Arşivi")
    if data["receteler_tablo"].empty:
        st.info("Arşiv boş. Reçeteler sayfasını doldurun.")
    else:
        recete_listesi = sorted(data["receteler_tablo"]["recete_ad"].dropna().unique())
        r_isim_arsiv = st.selectbox("Reçete Seç", recete_listesi, key="sel_arsiv")
        r_df_arsiv = data["receteler_tablo"][
            data["receteler_tablo"]["recete_ad"] == r_isim_arsiv
        ].rename(columns={"malzeme": "Malzeme", "miktar_g": "Miktar (g)"})

        st.dataframe(r_df_arsiv[["Malzeme", "Miktar (g)"]].reset_index(drop=True), use_container_width=True)

        a_res, a_tg = besin_analizi_yap(r_df_arsiv, data["malzemeler"], data["kurlar"])
        if a_tg > 0:
            st.subheader(f"📊 Besin Analizi — Toplam: {a_tg:.1f}g")
            cols_a = st.columns(len(besin_kalemleri))
            for i, k in enumerate(besin_kalemleri):
                cols_a[i].metric(besin_etiketleri[k], f"{a_res[k]/(a_tg/100):.2f}")
            col_a1, col_a2 = st.columns(2)
            col_a1.metric("💰 Toplam Maliyet", f"{a_res['maliyet']:.2f} TL")
            col_a2.metric("💰 KG Maliyeti", f"{a_res['maliyet']/a_tg*1000:.2f} TL")
