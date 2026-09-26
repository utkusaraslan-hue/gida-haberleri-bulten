"""Günlük gıda haberleri bültenini uçtan uca üretir:
haberleri topla -> TMO/TÜRİB fiyat özetini çek -> docx üret -> pdf'e çevir.

Herhangi bir kaynak başarısız olsa da (ağ hatası, rate limit, Browser Use
görevi tamamlanamadı vb.) script elindeki verilerle bülteni üretmeye devam
eder; hiçbir kaynak veri döndürmezse bile boş bültenle çalışır.
"""
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from docx_uret import bulten_olustur
from fetch_haberler import tum_haberleri_topla
from tmo_ozet import fiyat_ozeti_getir

BASE_DIR = Path(__file__).parent


def _soffice_ile_pdfe_cevir(docx_yolu):
    """LibreOffice ile docx -> pdf. skill'in soffice.py yardımcı script'i bulunamazsa
    doğrudan sistem 'soffice' komutunu dener."""
    hedef_klasor = docx_yolu.parent
    try:
        subprocess.run(
            ["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(hedef_klasor), str(docx_yolu)],
            check=True, capture_output=True, timeout=120,
        )
        return hedef_klasor / (docx_yolu.stem + ".pdf")
    except Exception as e:
        print(f"[uyari] PDF dönüşümü başarısız: {e}")
        return None


def bulten_uret(tarih=None):
    tarih = tarih or datetime.now()
    tarih_klasor_adi = tarih.strftime("%-d-%m-%Y")
    cikti_klasoru = BASE_DIR / tarih_klasor_adi
    cikti_klasoru.mkdir(parents=True, exist_ok=True)

    load_dotenv(BASE_DIR / ".env")
    api_key = os.environ.get("BROWSER_USE_API_KEY")

    print("Haberler toplanıyor...")
    haberler = tum_haberleri_topla(api_key=api_key)
    print(f"  -> {len(haberler)} haber toplandı")

    print("TMO/TÜRİB fiyat özeti çekiliyor...")
    tmo_ozet = fiyat_ozeti_getir()
    print(f"  -> {len(tmo_ozet)} ürün/kaynak satırı")

    docx_yolu = cikti_klasoru / f"gunluk_gida_ozet_{tarih_klasor_adi}.docx"
    bulten_olustur(docx_yolu, tarih, haberler, tmo_ozet)
    print(f"Docx üretildi: {docx_yolu}")

    pdf_yolu = _soffice_ile_pdfe_cevir(docx_yolu)
    if pdf_yolu and pdf_yolu.exists():
        print(f"PDF üretildi: {pdf_yolu}")
    else:
        print("[uyari] PDF üretilemedi, docx dosyası hazır.")

    return docx_yolu


if __name__ == "__main__":
    bulten_uret()
