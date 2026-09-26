"""Sadece mekanik veri toplama adımı (LLM gerektirmez): haberleri ve
TMO/TÜRİB fiyat özetini çekip <tarih>/veri.json içine yazar. Paragraf yazımı
ve HTML/PDF üretimi bu script'in dışında, .claude/skills/gunluk-bulten/
altındaki skill talimatına göre canlı bir Claude oturumunda yapılır."""
import json
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from fetch_haberler import tum_haberleri_topla
from tmo_ozet import fiyat_ozeti_getir

BASE_DIR = Path(__file__).parent


def veri_topla_ve_kaydet(tarih=None):
    tarih = tarih or datetime.now()
    tarih_klasor_adi = tarih.strftime("%d-%m-%Y")
    cikti_klasoru = BASE_DIR / "ham-veri" / tarih_klasor_adi
    cikti_klasoru.mkdir(parents=True, exist_ok=True)

    load_dotenv(BASE_DIR / ".env")
    browser_use_key = os.environ.get("BROWSER_USE_API_KEY")

    print("Haberler toplanıyor...")
    haberler = tum_haberleri_topla(api_key=browser_use_key)
    print(f"  -> {len(haberler)} haber toplandı")

    print("TMO/TÜRİB fiyat özeti çekiliyor...")
    tmo_turib_ozet = fiyat_ozeti_getir()
    print(f"  -> {len(tmo_turib_ozet)} satır")

    veri_yolu = cikti_klasoru / "veri.json"
    with open(veri_yolu, "w", encoding="utf-8") as f:
        json.dump(
            {"tarih": tarih_klasor_adi, "haberler": haberler, "fiyat": tmo_turib_ozet},
            f, ensure_ascii=False, indent=2, default=str,
        )
    print(f"Veri kaydedildi: {veri_yolu}")
    return veri_yolu


if __name__ == "__main__":
    veri_topla_ve_kaydet()
