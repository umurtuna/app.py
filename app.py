import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json

# Sayfa Ayarları
st.set_page_config(page_title="Cocoa Works ERP V7", layout="wide")

# --- GÜVENLİK ---
ERISIM_SIFRESI = "NMR170" 
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔒 Cocoa Works Güvenli Giriş")
    sifre = st.text_input("Şifre:", type="password")
    if st.button("Giriş"):
        if sifre == ERISIM_SIFRESI:
            st.session_state["authenticated"] = True
            st.rerun()
        else: st.error("Hatalı!")
    st.stop()

# --- GOOGLE SHEETS BAĞLANTISI ---
conn = st.connection("gsheets", type=GSheetsConnection)

def verileri_yukle():
    try:
        malz_df = conn.read(worksheet="malzemeler", ttl=0)
        
        # --- Sayı Düzenleme Yaması ---
        if not malz_df.empty:
            # Sayısal olması gereken kolonlar
            sayisal_kolonlar = ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz", "fiyat"]
            for col in sayisal_kolonlar:
                if col in malz_df.columns:
                    # Virgülleri noktaya çevir ve sayıya dönüştür
                    malz_df[col] = malz_df[col].astype(str).str.replace(',', '.', regex=False)
                    malz_df[col] = pd.to_numeric(malz_df[col], errors='coerce').fillna(0)
        # ----------------------------

        return {
            "malzemeler": malz_df.set_index("ad").to_dict('index') if not malz_df.empty else {},
            "receteler_tablo": conn.read(worksheet="receteler", ttl=0),
            "kurlar": conn.read(worksheet="kurlar", ttl=0).set_index("doviz")["oran"].to_dict()
        }
    except Exception as e:
        st.error(f"Bağlantı Hatası: {e}")
        return {"malzemeler": {}, "receteler_tablo": pd.DataFrame(), "kurlar": {"USD": 32.5, "EUR": 35.0}}

# --- YARDIMCI FONKSİYONLAR ---
def besin_analizi_yap(df, malzemeler, kurlar):
    analiz = {k: 0 for k in ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz", "maliyet"]}
    t_gram = df["Miktar (g)"].sum()
    if t_gram == 0: return analiz, 0
    for _, row in df.iterrows():
        m = malzemeler[row["Malzeme"]]
        oran = row["Miktar (g)"] / 100
        for b in ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz"]:
            analiz[b] += m[b] * oran
        kur = kurlar.get(m["birim"], 1.0)
        analiz["maliyet"] += (m["fiyat"] * kur / 1000) * row["Miktar (g)"]
    return analiz, t_gram

# --- MENÜ ---
st.title("🍫 Cocoa Works Cloud ERP V7")
menu = st.sidebar.radio("Menü", ["📦 Malzeme Envanteri", "📝 Malzeme Ekle", "🧪 Reçete Hazırla", "🍰 Katmanlı Ürün", "📋 Arşiv", "💱 Döviz Kurları"])

if menu == "📦 Malzeme Envanteri":
    st.header("📦 Mevcut Malzemeler")
    if data["malzemeler"]:
        st.dataframe(pd.DataFrame.from_dict(data["malzemeler"], orient='index'), use_container_width=True)
    else: st.info("Tablo henüz boş.")

elif menu == "📝 Malzeme Ekle":
    st.header("📝 Yeni Malzeme Kaydı")
    with st.form("malz_form"):
        ad = st.text_input("Ad").lower().strip()
        c = st.columns(3)
        en, yg, kb = c[0].number_input("Enerji"), c[1].number_input("Yağ"), c[2].number_input("Karb.")
        sk, lf, pr = c[0].number_input("Şeker"), c[1].number_input("Lif"), c[2].number_input("Protein")
        tz, fj, br = c[0].number_input("Tuz"), c[1].number_input("Fiyat"), c[2].selectbox("Birim", ["TL", "USD", "EUR"])
        
        if st.form_submit_button("Buluta Kaydet"):
            # Mevcut listeye ekle ve tabloyu güncelle
            data["malzemeler"][ad] = {"enerji":en, "yag":yg, "karb":kb, "seker":sk, "lif":lf, "protein":pr, "tuz":tz, "fiyat":fj, "birim":br}
            new_df = pd.DataFrame.from_dict(data["malzemeler"], orient='index').reset_index().rename(columns={'index': 'ad'})
            conn.update(worksheet="malzemeler", data=new_df)
            st.success("Veri Google Sheets'e işlendi!")

elif menu == "🧪 Reçete Hazırla":
    st.header("🧪 Ar-Ge Laboratuvarı")
    if not data["malzemeler"]: st.warning("Önce malzeme ekleyin!")
    else:
        if 'gecici_df' not in st.session_state:
            st.session_state.gecici_df = pd.DataFrame(columns=["Malzeme", "Miktar (g)"])
            
        col_add1, col_add2 = st.columns([3,1])
        y_m = col_add1.selectbox("Malzeme Seç", list(data["malzemeler"].keys()))
        if col_add2.button("Ekle"):
            st.session_state.gecici_df = pd.concat([st.session_state.gecici_df, pd.DataFrame([{"Malzeme": y_m, "Miktar (g)": 0.0}])], ignore_index=True)
        
        edited_df = st.data_editor(st.session_state.gecici_df, num_rows="dynamic", use_container_width=True)
        st.session_state.gecici_df = edited_df
        
        if not edited_df.empty:
            res, t_g = besin_analizi_yap(edited_df, data["malzemeler"], data["kurlar"])
            if t_g > 0:
                st.divider()
                st.metric("Toplam Maliyet", f"{res['maliyet']:.2f} TL")
                st.table(pd.DataFrame({k: [round(res[k]/(t_g/100), 2)] for k in ["enerji", "yag", "karb", "seker", "lif", "protein", "tuz"]}))

            r_ad = st.text_input("Reçete Adı")
            if st.button("💾 Reçeteyi Buluta Arşivle"):
                # Reçete tablosuna yeni satırları ekle
                new_rows = edited_df.copy()
                new_rows["recete_ad"] = r_ad
                new_rows = new_rows.rename(columns={"Malzeme": "malzeme", "Miktar (g)": "miktar_g"})
                all_receteler = pd.concat([data["receteler_tablo"], new_rows], ignore_index=True)
                conn.update(worksheet="receteler", data=all_receteler)
                st.success("Reçete kaydedildi!")

elif menu == "💱 Döviz Kurlarını Güncelle":
    st.header("💱 Güncel Kurlar")
    u = st.number_input("USD/TL", value=float(data["kurlar"].get("USD", 32.5)))
    e = st.number_input("EUR/TL", value=float(data["kurlar"].get("EUR", 35.0)))
    if st.button("Kurları Kaydet"):
        new_kurlar = pd.DataFrame([{"doviz": "USD", "oran": u}, {"doviz": "EUR", "oran": e}])
        conn.update(worksheet="kurlar", data=new_kurlar)
        st.success("Kurlar Google Sheets'e kaydedildi!")

# (Diğer sekmeleri de benzer mantıkla güncelleyebilirsin)
