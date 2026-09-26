"""Gıda/tarım haberlerini birden fazla kaynaktan toplayıp normalize eder.

Her fetch_* fonksiyonu bağımsız try/except ile çalışır: bir kaynak
başarısız olursa (ağ hatası, rate limit, site değişikliği) diğerleri
etkilenmez ve bülten elindeki verilerle üretilmeye devam eder.
"""
import re
import time
from datetime import datetime, timedelta, timezone

import feedparser
import requests
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
HEADERS = {"User-Agent": UA}

FBN_FEEDS = {
    "Food Business News - Genel": "https://www.foodbusinessnews.net/rss/articles",
    "Food Business News - Tahıl": "https://www.foodbusinessnews.net/rss/topic/120-grain-based",
    "Food Business News - Tedarik Zinciri": "https://www.foodbusinessnews.net/rss/topic/130-supply-chain",
    "Food Business News - Meyve/Sebze": "https://www.foodbusinessnews.net/rss/topic/124-produce",
}

# Türkiye tarım/gıda basınından ek RSS kaynakları — Ali Ekber Yıldırım (Tarım Dünyası),
# Necdet Oral gibi tarım ekonomisi yazarlarının köşe yazılarını da bu siteler taşıyor,
# bu yüzden isim bazlı Browser Use taraması yerine (daha kırılgan) site RSS'i tercih edildi.
TR_TARIM_FEEDS = {
    "Tarım Dünyası": "https://www.tarimdunyasi.net/feed/",
    "Karasaban": "https://www.karasaban.net/feed/",
    "Tarımdan Haber": "https://www.tarimdanhaber.com/rss",
}

REDDIT_SUBS = ["FoodNews", "agriculture", "farming"]

MEYVE_SEBZE_ANAHTAR_KELIMELER = [
    "meyve", "sebze", "domates", "biber", "patates", "soğan", "elma", "portakal",
    "üzüm", "zeytin", "limon", "muz", "çilek", "kiraz", "şeftali", "kavun", "karpuz",
    "patlıcan", "salatalık", "havuç", "lahana", "marul", "fruit", "vegetable", "produce",
    "tomato", "potato", "onion", "apple", "citrus", "grape", "berry", "avocado", "mango",
]


_MEYVE_SEBZE_REGEX = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in MEYVE_SEBZE_ANAHTAR_KELIMELER) + r")\b"
)


def _kategori_belirle(baslik, ozet, varsayilan_kategori=None):
    if varsayilan_kategori:
        return varsayilan_kategori
    metin = f"{baslik} {ozet}".lower()
    # Kelime sınırı (\b) olmadan basit substring araması "temmuz" içinde "muz" gibi
    # yanlış pozitifler üretiyordu; regex ile tam kelime eşleşmesi arıyoruz.
    if _MEYVE_SEBZE_REGEX.search(metin):
        return "meyve_sebze"
    return "hububat_ve_diger"


def _kayit(kaynak, baslik, ozet, link, tarih, kategori=None, gorsel_url=None):
    return {
        "kaynak": kaynak, "baslik": baslik, "ozet": ozet, "link": link, "tarih": tarih,
        "kategori": _kategori_belirle(baslik, ozet, kategori),
        "gorsel_url": gorsel_url,
    }


def fetch_dunya_tarim(limit=15):
    """Dünya Gazetesi tarım sayfasını scrape eder (RSS yok, sayfa SPA olduğu için
    HTML'de gömülü olan haber kartlarını arıyoruz)."""
    sonuclar = []
    try:
        r = requests.get("https://www.dunya.com/sektorler/tarim", headers=HEADERS, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        gorulen = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            baslik = a.get_text(strip=True)
            if not baslik or len(baslik) < 15:
                continue
            if not re.search(r"-haberi-\d+$", href):
                continue
            if baslik in gorulen:
                continue
            gorulen.add(baslik)
            link = href if href.startswith("http") else f"https://www.dunya.com{href}"
            # Başlık ile teaser metni araya boşluk konmadan bitişik geliyor
            # (ör. "...düştüTürkiye'de..."); küçük harften büyük harfe geçişte ayır.
            parcalar = re.split(r"(?<=[a-zçğıöşü])(?=[A-ZÇĞİÖŞÜ])", baslik, maxsplit=1)
            gercek_baslik = parcalar[0]
            ozet = parcalar[1] if len(parcalar) > 1 else ""
            img = a.find("img")
            gorsel = img["src"] if img and img.get("src") else None
            sonuclar.append(_kayit("Dünya Gazetesi - Tarım", gercek_baslik, ozet[:300], link, "", gorsel_url=gorsel))
            if len(sonuclar) >= limit:
                break
    except Exception as e:
        print(f"[uyari] Dünya Gazetesi tarım sayfası çekilemedi: {e}")
    return sonuclar


def fetch_food_business_news(gun_sayisi=2):
    sonuclar = []
    esik = datetime.now(timezone.utc) - timedelta(days=gun_sayisi)
    for ad, url in FBN_FEEDS.items():
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            d = feedparser.parse(r.content)
            for e in d.entries:
                tarih_str = e.get("published", "")
                dahil_et = True
                if getattr(e, "published_parsed", None):
                    tarih = datetime(*e.published_parsed[:6], tzinfo=timezone.utc)
                    dahil_et = tarih >= esik
                if dahil_et:
                    zorunlu_kategori = "meyve_sebze" if "Meyve/Sebze" in ad else None
                    gorsel = next(
                        (l["href"] for l in e.get("links", []) if l.get("rel") == "enclosure" and "image" in l.get("type", "")),
                        None,
                    )
                    sonuclar.append(_kayit(ad, e.title, e.get("summary", "")[:300], e.link, tarih_str, kategori=zorunlu_kategori, gorsel_url=gorsel))
        except Exception as e:
            print(f"[uyari] {ad} feed'i çekilemedi: {e}")
    return sonuclar


def fetch_tr_tarim_siteleri(gun_sayisi=3):
    """Ali Ekber Yıldırım (Tarım Dünyası), Necdet Oral (Karasaban) gibi tarım
    ekonomisi yazarlarının köşe yazılarını da içeren Türkçe tarım/gıda haber
    sitelerinden RSS ile toplar."""
    sonuclar = []
    esik = datetime.now(timezone.utc) - timedelta(days=gun_sayisi)
    for ad, url in TR_TARIM_FEEDS.items():
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            d = feedparser.parse(r.content)
            for e in d.entries:
                tarih_str = e.get("published", "")
                dahil_et = True
                if getattr(e, "published_parsed", None):
                    tarih = datetime(*e.published_parsed[:6], tzinfo=timezone.utc)
                    dahil_et = tarih >= esik
                if dahil_et:
                    gorsel = next(
                        (l["href"] for l in e.get("links", []) if l.get("rel") == "enclosure" and "image" in l.get("type", "")),
                        None,
                    )
                    sonuclar.append(_kayit(ad, e.title, e.get("summary", "")[:300], e.link, tarih_str, gorsel_url=gorsel))
        except Exception as e:
            print(f"[uyari] {ad} feed'i çekilemedi: {e}")
    return sonuclar


def fetch_reddit(gun_sayisi=2, bekleme_sn=25):
    """Reddit sıkı rate-limit uyguluyor; istekler arasında bilinçli bekleme var."""
    sonuclar = []
    esik = datetime.now(timezone.utc) - timedelta(days=gun_sayisi)
    for i, sub in enumerate(REDDIT_SUBS):
        if i > 0:
            time.sleep(bekleme_sn)
        try:
            url = f"https://www.reddit.com/r/{sub}/.rss"
            r = requests.get(url, headers=HEADERS, timeout=20)
            if r.status_code == 429:
                print(f"[uyari] r/{sub} rate-limit (429), atlanıyor")
                continue
            r.raise_for_status()
            d = feedparser.parse(r.content)
            for e in d.entries:
                dahil_et = True
                if getattr(e, "updated_parsed", None):
                    tarih = datetime(*e.updated_parsed[:6], tzinfo=timezone.utc)
                    dahil_et = tarih >= esik
                if dahil_et:
                    sonuclar.append(_kayit(f"Reddit r/{sub}", e.title, "", e.link, e.get("updated", "")))
        except Exception as e:
            print(f"[uyari] r/{sub} çekilemedi: {e}")
    return sonuclar


def _browser_use_gorev_calistir(api_key, gorev):
    """Tek bir Browser Use Cloud API görevini çalıştırıp metin çıktısını döndürür.
    Görev tamamlanamazsa None döner (çağıran taraf try/except ile ele alır)."""
    headers = {"X-Browser-Use-API-Key": api_key, "Content-Type": "application/json"}
    resp = requests.post(
        "https://api.browser-use.com/api/v3/sessions",
        headers=headers,
        json={"task": gorev},
        timeout=30,
    )
    resp.raise_for_status()
    session_id = resp.json().get("id") or resp.json().get("session_id")
    if not session_id:
        return None

    sonuc = None
    for _ in range(30):
        time.sleep(15)
        durum = requests.get(
            f"https://api.browser-use.com/api/v3/sessions/{session_id}",
            headers=headers,
            timeout=20,
        )
        durum.raise_for_status()
        veri = durum.json()
        if veri.get("status") in ("finished", "completed", "stopped", "failed"):
            sonuc = veri
            break
    if not sonuc or sonuc.get("status") == "failed":
        return None
    return sonuc.get("output") or sonuc.get("result") or ""


def _gorevleri_calistir_ve_kayit_yap(api_key, gorevler):
    """{kaynak_adi: gorev_metni} sözlüğündeki her görevi AYRI bir Browser Use
    session'ı olarak sırayla çalıştırır, her biri için bir _kayit() döndürür.
    Görevleri tek görevde birleştirmek 5 dakikalık polling penceresini aşıp
    zaman aşımına uğruyordu (doğrulandı) — bu yüzden her kaynak kendi görevi."""
    sonuclar = []
    for kaynak_adi, gorev in gorevler.items():
        try:
            cikti = _browser_use_gorev_calistir(api_key, gorev)
            if cikti is None:
                print(f"[uyari] Browser Use görevi tamamlanamadı ({kaynak_adi})")
                continue
            sonuclar.append(_kayit(kaynak_adi, kaynak_adi, str(cikti)[:1500], "", ""))
        except Exception as e:
            print(f"[uyari] Browser Use adımı başarısız ({kaynak_adi}): {e}")
    return sonuclar


def fetch_linkedin_bloomberg_journalists(api_key):
    """Browser Use Cloud API ile bot-engelli platformlardaki (LinkedIn, Bloomberg HT)
    belirli isimlerin son paylaşımlarını çeker. api_key None ise atlanır."""
    sonuclar = []
    if not api_key:
        print("[uyari] BROWSER_USE_API_KEY yok, LinkedIn/Bloomberg adımı atlanıyor")
        return sonuclar

    kisiler = ["İrfan Donat", "Ali Ekber Yıldırım"]
    for kisi in kisiler:
        try:
            gorev = (
                f"LinkedIn ve Bloomberg HT'de '{kisi}' isimli gazetecinin son 3 gündeki "
                f"gıda/tarım/emtia piyasası ile ilgili paylaşımlarını bul. Her paylaşım için "
                f"başlık/özet ve varsa link ver. JSON listesi olarak döndür: "
                f"[{{\"baslik\": ..., \"ozet\": ..., \"link\": ...}}]"
            )
            cikti = _browser_use_gorev_calistir(api_key, gorev)
            if cikti is None:
                print(f"[uyari] Browser Use görevi tamamlanamadı ({kisi})")
                continue
            sonuclar.append(_kayit(f"LinkedIn/Bloomberg - {kisi}", f"{kisi} son paylaşımlar", str(cikti)[:1500], "", ""))
        except Exception as e:
            print(f"[uyari] Browser Use adımı başarısız ({kisi}): {e}")
    return sonuclar


def fetch_kuresel_endeksler(api_key):
    """Browser Use Cloud API ile, plain requests'in Cloudflare/login engeline takıldığı
    (doğrudan denendi, 403/login-gate doğrulandı) küresel tahıl/navlun endekslerini çeker:
    FAO Gıda Fiyat Endeksi, IGC Tahıl ve Yağlı Tohum Endeksi (GOI), USDA WASDE son rapor
    öne çıkanları, ve navlun endeksleri (Baltic Dry, Baltic Panamax, Black Sea Wheat Index).

    Her kaynak AYRI bir Browser Use görevi olarak gönderilir — 3 siteyi tek görevde
    birleştirmek denendi, agent 5 dakikalık polling penceremizi aşıp zaman aşımına
    uğradı (görev teknik olarak devam ediyordu ama biz "tamamlanamadı" diye pes ettik).
    Tek-kaynaklı görevler tipik olarak ~45 saniyede bitiyor (doğrulandı: Baltic Dry
    Index testi 3 poll'de, "stopped" status ile, output dolu döndü).

    api_key None ise atlanır."""
    sonuclar = []
    if not api_key:
        print("[uyari] BROWSER_USE_API_KEY yok, küresel endeks adımı atlanıyor")
        return sonuclar

    gorevler = {
        "FAO Gıda Fiyat Endeksi": (
            "fao.org/worldfoodsituation/foodpricesindex sayfasından FAO Gıda Fiyat "
            "Endeksi'nin son ay değerini ve bir önceki aya göre değişimini bul ve raporla."
        ),
        "IGC Tahıl ve Yağlı Tohum Endeksi (GOI)": (
            "igc.int üzerindeki herkese açık/özet sayfasından IGC (International Grains "
            "Council) Grains and Oilseeds Index (GOI) son değerini ve haftalık/aylık "
            "değişimini bul ve raporla. Alt endeksler (buğday, mısır, pirinç, soya) varsa "
            "onları da ekle."
        ),
        "USDA WASDE Son Rapor": (
            "fas.usda.gov/data/wasde sayfasından en son WASDE raporunun buğday/mısır/soya "
            "için öne çıkan üretim/stok/fiyat tahminlerini bul ve özetle."
        ),
        "Baltic Dry Index": (
            "investing.com/indices/baltic-dry sayfasından Baltic Dry Index güncel değerini, "
            "günlük değişimini ve tarihini bul ve raporla."
        ),
        "Baltic Panamax Index": (
            "investing.com/indices/baltic-panamax sayfasından Baltic Panamax Index güncel "
            "değerini, günlük değişimini ve tarihini bul ve raporla."
        ),
        "Black Sea Wheat Index": (
            "investing.com/indices/wheat-fob-black-sea-index sayfasından Wheat Index FOB "
            "Black Sea region (Black Sea Wheat Index) güncel değerini, günlük değişimini "
            "ve tarihini bul ve raporla."
        ),
    }
    return _gorevleri_calistir_ve_kayit_yap(api_key, gorevler)


def fetch_borsa_futures_verileri(api_key):
    """Browser Use Cloud API ile büyük emtia/vadeli işlem borsalarından güncel
    fiyat verisi çeker (hepsi plain requests ile denendi, 403 ile engelliyor —
    LME/CME/Bursa Malaysia doğrulandı, ICE ve DCE de aynı korumaya sahip).
    Kullanıcı isteği: LME, Baltic Exchange, ICE Futures (US/Europe), CME,
    DCE (Dalian), Bursa Malaysia Derivatives. api_key None ise atlanır."""
    sonuclar = []
    if not api_key:
        print("[uyari] BROWSER_USE_API_KEY yok, borsa futures adımı atlanıyor")
        return sonuclar

    gorevler = {
        "CME Buğday/Mısır/Soya Futures": (
            "cmegroup.com üzerinden CBOT Buğday (Wheat/ZW), Mısır (Corn/ZC) ve Soya "
            "Fasulyesi (Soybean/ZS) vadeli işlem sözleşmelerinin güncel/en yakın vade "
            "fiyatlarını ve günlük değişimlerini bul ve raporla."
        ),
        "ICE Futures - Şeker/Kahve/Kakao/Pamuk": (
            "theice.com (ICE Futures US ve Europe) üzerinden Şeker No.11 (Sugar), Kahve C "
            "(Coffee), Kakao (Cocoa) ve Pamuk (Cotton No.2) vadeli işlem sözleşmelerinin "
            "güncel fiyatlarını ve günlük değişimlerini bul ve raporla."
        ),
        "Dalian Ticaret Borsası (DCE) - Mısır/Soya/Palm Yağı": (
            "Dalian Commodity Exchange (DCE, english.dce.com.cn) üzerinden Mısır (Corn), "
            "Soya Fasulyesi (Soybean), Soya Küspesi (Soybean Meal) ve Palm Yağı (Palm Oil) "
            "vadeli işlem sözleşmelerinin güncel fiyatlarını (CNY) bul ve raporla."
        ),
        "Bursa Malaysia - Ham Palm Yağı (FCPO)": (
            "Bursa Malaysia Derivatives üzerinden Ham Palm Yağı (Crude Palm Oil/FCPO) "
            "vadeli işlem sözleşmesinin güncel fiyatını (MYR/ton), günlük değişimini ve "
            "tarihini bul ve raporla."
        ),
        "London Metal Exchange (LME)": (
            "London Metal Exchange (lme.com) üzerinden temel metal fiyatlarını (Bakır/"
            "Copper, Alüminyum/Aluminium, Çinko/Zinc gibi) - LME Reference Prices "
            "sayfasından güncel değerleri ve günlük değişimleri bul ve raporla."
        ),
        "Baltic Exchange - Resmi Navlun Endeksleri": (
            "balticexchange.com üzerinden resmi Baltic Dry Index, Baltic Capesize Index "
            "(BCI), Baltic Panamax Index (BPI) ve Baltic Supramax Index (BSI) güncel "
            "değerlerini (herkese açık kısımdan) bul ve raporla."
        ),
    }
    return _gorevleri_calistir_ve_kayit_yap(api_key, gorevler)


def tum_haberleri_topla(api_key=None):
    haberler = []
    haberler += fetch_dunya_tarim()
    haberler += fetch_tr_tarim_siteleri()
    haberler += fetch_food_business_news()
    haberler += fetch_reddit()
    haberler += fetch_linkedin_bloomberg_journalists(api_key)
    haberler += fetch_kuresel_endeksler(api_key)
    haberler += fetch_borsa_futures_verileri(api_key)
    return haberler


if __name__ == "__main__":
    for h in tum_haberleri_topla():
        print(f"[{h['kaynak']}] {h['baslik']}")
