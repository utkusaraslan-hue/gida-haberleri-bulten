"""GitHub'daki generalgrainrepo reposundan TMO/TÜRİB fiyat verisini indirip
son 2 günün ürün bazlı ortalama fiyat değişimini özetler."""
import sqlite3
import tempfile
from pathlib import Path

import requests

DB_URL = "https://raw.githubusercontent.com/utkusaraslan-hue/generalgrainrepo/main/veri_kaynagi/borsa_verileri.db"


def _db_indir():
    r = requests.get(DB_URL, timeout=60)
    r.raise_for_status()
    tmp = Path(tempfile.gettempdir()) / "borsa_verileri_gida_haberleri.db"
    tmp.write_bytes(r.content)
    return tmp


def fiyat_ozeti_getir(urun_filtre=None):
    """Dönüş: [{kaynak, urun, birim, tarih_son, ort_fiyat_son, tarih_onceki, ort_fiyat_onceki, degisim_yuzde}]

    Karşılaştırma her zaman aynı (kaynak, urun, birim) üçlüsü içinde yapılır —
    kaynaklar arasında birim tutarsızlığı olduğu için (TMO 'TL/ton', borsalar
    'KG' bazında raporluyor, bazı kaynaklarda aynı ürün için birim etiketi bile
    tutarsız) farklı kaynakları aynı ürün adı altında ortalamak yanıltıcı sonuç
    veriyordu (bkz. anomali testleri). Bunun yerine her kaynağın kendi günlük
    serisi kendi içinde takip edilir.
    """
    try:
        db_path = _db_indir()
    except Exception as e:
        print(f"[uyari] TMO/TÜRİB veritabanı indirilemedi: {e}")
        return []

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        # TÜRİB Endeks kaynağı ort_fiyat'ı boş bırakıp değeri min/max/kapanış alanlarına
        # yazıyor (endeks tek bir değer olduğu için min=max=değer); bu yüzden fiyatı
        # COALESCE ile ort_fiyat -> kapanis_fiyat -> min/max ortalaması sırasıyla al.
        sorgu = """
            SELECT kaynak, urun, birim, tarih,
                   AVG(COALESCE(ort_fiyat, kapanis_fiyat, (min_fiyat + max_fiyat) / 2.0)) as ort
            FROM fiyatlar
            WHERE COALESCE(ort_fiyat, kapanis_fiyat, min_fiyat, max_fiyat) IS NOT NULL
                  AND urun IS NOT NULL AND urun != ''
        """
        params = []
        if urun_filtre:
            placeholders = ",".join("?" * len(urun_filtre))
            sorgu += f" AND urun IN ({placeholders})"
            params += urun_filtre
        sorgu += " GROUP BY kaynak, urun, birim, tarih ORDER BY tarih DESC"

        satirlar = conn.execute(sorgu, params).fetchall()
        veri = {}
        for s in satirlar:
            anahtar = (s["kaynak"], s["urun"], s["birim"])
            veri.setdefault(anahtar, {})[s["tarih"]] = s["ort"]

        # TMO gibi kaynaklar diğerlerine göre 1 gün gecikmeli geliyor; global
        # "en son 2 tarih" alırsak bu kaynaklar tamamen dışarıda kalır. Bunun
        # yerine her (kaynak, ürün, birim) serisi kendi en son 2 gününü kullanır.
        sonuc = []
        for (kaynak, urun, birim), gunler in veri.items():
            gun_tarihleri = sorted(gunler.keys(), reverse=True)
            if not gun_tarihleri:
                continue
            son_tarih = gun_tarihleri[0]
            onceki_tarih = gun_tarihleri[1] if len(gun_tarihleri) > 1 else None
            son = gunler[son_tarih]
            onceki = gunler.get(onceki_tarih) if onceki_tarih else None
            degisim = ((son - onceki) / onceki * 100) if onceki else None
            # Aynı kaynak+ürün+birim içinde bile gün içi aşırı sıçrama (>%70)
            # muhtemelen tekil bir veri hatasıdır; gerçek fiyat hareketi gibi
            # sunmak yerine anomali olarak işaretle.
            anomali = degisim is not None and abs(degisim) > 70
            sonuc.append({
                "kaynak": kaynak,
                "urun": urun,
                "birim": birim,
                "tarih_son": son_tarih,
                "ort_fiyat_son": round(son, 2),
                "tarih_onceki": onceki_tarih,
                "ort_fiyat_onceki": round(onceki, 2) if onceki is not None else None,
                "degisim_yuzde": round(degisim, 2) if degisim is not None and not anomali else None,
                "anomali": anomali,
            })
        return sorted(sonuc, key=lambda x: (x["urun"], x["kaynak"]))
    finally:
        conn.close()


if __name__ == "__main__":
    for satir in fiyat_ozeti_getir():
        print(satir)
