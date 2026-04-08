import json

class GidaYonetimi:
    def __init__(self):
        self.veritabani_dosyasi = "malzemeler.json"
        self.kurlar = {"TL": 1.0, "USD": 32.5, "EUR": 35.0} 
        self.malzemeler = self.verileri_yukle()

    def verileri_yukle(self):
        try:
            with open(self.veritabani_dosyasi, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def verileri_kaydet(self):
        with open(self.veritabani_dosyasi, "w", encoding="utf-8") as f:
            json.dump(self.malzemeler, f, ensure_ascii=False, indent=4)

    def kur_guncelle(self):
        print("\n--- DÖVİZ KURU GÜNCELLEME ---")
        try:
            self.kurlar["USD"] = float(input("1 USD kaç TL? : "))
            self.kurlar["EUR"] = float(input("1 EUR kaç TL? : "))
            print("Kurlar başarıyla güncellendi!")
        except ValueError:
            print("Hata: Lütfen geçerli bir sayı girin.")

    def veri_girisi(self, isim):
        """Besin ve maliyet verilerini kullanıcıdan alan yardımcı fonksiyon"""
        print(f"\n--- {isim.upper()} İÇİN BİLGİLERİ GİRİN ---")
        print("Besin Değerleri (100g/ml için):")
        enerji = float(input("- Enerji (kcal): "))
        yag = float(input("- Yağ (g): "))
        karb = float(input("- Karbonhidrat (g): "))
        seker = float(input("  - Şeker (g): "))
        lif = float(input("- Lif (g): "))
        protein = float(input("- Protein (g): "))
        tuz = float(input("- Tuz (g): "))
        
        print("\nMaliyet Bilgisi:")
        birim_fiyat = float(input("- Fiyat: "))
        birim = input("- Para Birimi (TL/USD/EUR): ").upper()
        
        return {
            "besin": {
                "enerji": enerji, "yag": yag, "karb": karb,
                "seker": seker, "lif": lif, "protein": protein, "tuz": tuz
            },
            "maliyet": {
                "fiyat": birim_fiyat,
                "birim": birim
            }
        }

    def malzeme_ekle(self):
        print("\n--- YENİ MALZEME EKLEME ---")
        isim = input("Malzeme adı: ").strip().lower()
        if isim in self.malzemeler:
            print(f"Hata: '{isim}' zaten kayıtlı. Düzenlemek için 'Düzenle' seçeneğini kullanın.")
            return
        
        self.malzemeler[isim] = self.veri_girisi(isim)
        self.verileri_kaydet()
        print(f"'{isim}' başarıyla listeye eklendi.")

    def malzeme_duzenle(self):
        print("\n--- MALZEME DÜZENLEME ---")
        if not self.malzemeler:
            print("Düzenlenecek malzeme bulunamadı.")
            return

        print("Mevcut Malzemeler:", ", ".join(self.malzemeler.keys()))
        hedef = input("Düzenlemek istediğiniz malzemenin tam adını yazın: ").strip().lower()

        if hedef in self.malzemeler:
            print(f"'{hedef}' güncelleniyor. Yeni değerleri girin:")
            self.malzemeler[hedef] = self.veri_girisi(hedef)
            self.verileri_kaydet()
            print(f"'{hedef}' başarıyla güncellendi.")
        else:
            print("Hata: Bu isimde bir malzeme bulunamadı.")

    def tum_malzemeleri_listele(self):
        if not self.malzemeler:
            print("\nHenüz malzeme eklenmemiş.")
            return

        # Tablo başlığı
        header = f"{'Malzeme Adı':<15} | {'Enerji':<6} | {'Yağ':<5} | {'Karb.':<5} | {'Şeker':<5} | {'Lif':<5} | {'Prot.':<5} | {'Tuz':<5} | {'Maliyet':<8} | {'Döviz':<5} | {'TL Karş.'}"
        print("\n" + "="*len(header))
        print(header)
        print("-" * len(header))
        
        for isim, veri in self.malzemeler.items():
            b = veri["besin"]
            m = veri["maliyet"]
            guncel_tl = m["fiyat"] * self.kurlar.get(m["birim"], 1.0)
            
            row = (f"{isim.capitalize():<15} | {b['enerji']:<6.1f} | {b['yag']:<5.1f} | "
                   f"{b['karb']:<5.1f} | {b['seker']:<5.1f} | {b['lif']:<5.1f} | "
                   f"{b['protein']:<5.1f} | {b['tuz']:<5.1f} | {m['fiyat']:<8.2f} | "
                   f"{m['birim']:<5} | {guncel_tl:<10.2f}")
            print(row)
        print("="*len(header))

# Ana Program Döngüsü
def menu():
    sistem = GidaYonetimi()
    while True:
        print("\n--- COCOA WORKS YÖNETİM PANELİ ---")
        print("1. Yeni Malzeme Ekle")
        print("2. Mevcut Malzemeyi Düzenle")
        print("3. Tüm Malzemeleri Görüntüle (Tablo)")
        print("4. Döviz Kurlarını Güncelle")
        print("5. Çıkış")
        
        secim = input("Seçiminiz: ")
        
        try:
            if secim == "1":
                sistem.malzeme_ekle()
            elif secim == "2":
                sistem.malzeme_duzenle()
            elif secim == "3":
                sistem.tum_malzemeleri_listele()
            elif secim == "4":
                sistem.kur_guncelle()
            elif secim == "5":
                print("Sistemden çıkılıyor... İyi çalışmalar!")
                break
            else:
                print("Geçersiz seçim!")
        except Exception as e:
            print(f"Bir hata oluştu: {e}. Lütfen sayısal değerleri doğru girdiğinizden emin olun.")

if __name__ == "__main__":
    menu()
