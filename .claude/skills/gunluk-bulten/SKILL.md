---
name: gunluk-bulten
description: "Sarıaslan Ticaret için günlük gıda/tarım haberleri + TMO/TÜRİB fiyat bültenini üretir. 'günlük bülten', 'günlük özet', 'bugünkü bülteni hazırla' gibi isteklerde kullan."
---

# Günlük Gıda ve Tarım Haberleri Bülteni

Bu skill, bu proje klasöründeki (`gida-haberleri/`) script'leri kullanarak
Sarıaslan Ticaret'in web sitesiyle aynı tasarım dilinde bir PDF bülten üretir.
Aşağıdaki talimatlar önceki bir Claude Code oturumunda kullanıcıyla birlikte
netleştirilen tüm kararları içeriyor — bu dosya tek başına yeterli olmalı,
başka bir konuşma geçmişine ihtiyaç duymamalısın.

Rapor metnini de (paragraflar) SEN yazacaksın — API anahtarı/kredi
gerektirmez, bu Claude Chat/Code oturumunun kendisi editörlük yapıyor.

## Kapsam ve kaynaklar

**Haberler** (`fetch_haberler.py`, `tum_haberleri_topla()`):
- Dünya Gazetesi Tarım sayfası (scrape, RSS yok)
- Türkçe tarım/gıda siteleri RSS: Tarım Dünyası (Ali Ekber Yıldırım'ın kendi
  sitesi), Karasaban (Necdet Oral gibi eleştirel tarım ekonomisi yazarları),
  Tarımdan Haber — isim bazlı Browser Use taraması yerine site RSS'i tercih
  edildi (daha az kırılgan, isim yanlış yazma riski yok)
- Food Business News RSS feed'leri (Genel, Tahıl, Tedarik Zinciri, Meyve/Sebze)
- Reddit (r/FoodNews, r/agriculture, r/farming) — sıkı rate-limit var, istekler
  arasında bilinçli bekleme var, bazen 429 ile bir/iki kaynak atlanabilir, sorun değil
- Browser Use Cloud API ile LinkedIn/Bloomberg HT'den iki gazetecinin son
  paylaşımları: **İrfan Donat** ve **Ali Ekber Yıldırım** (dikkat: "Elif Ekber
  Yıldırım" YANLIŞ isim, kullanıcı bunu düzeltti — doğrusu Ali Ekber Yıldırım)
- Browser Use Cloud API ile küresel endeksler (`fetch_kuresel_endeksler()`) —
  bunlar `requests` ile denendi, hepsi 403/login-gate ile engelliyor (Cloudflare
  veya subscriber-only sayfa), bu yüzden Browser Use şart. HER KAYNAK AYRI
  görev olarak gönderilir (bkz. aşağıdaki "Browser Use görev sayısı" notu):
  - FAO Gıda Fiyat Endeksi, IGC Tahıl ve Yağlı Tohum Endeksi (GOI), USDA WASDE
    son rapor öne çıkanları
  - Navlun endeksleri: Baltic Dry Index, Baltic Panamax Index, Black Sea Wheat
    Index/WHFOB (investing.com)
- Browser Use Cloud API ile büyük emtia/vadeli işlem borsaları
  (`fetch_borsa_futures_verileri()`) — kullanıcı isteğiyle eklendi, aynı
  şekilde plain requests 403 ile engelliyor:
  - CME (CBOT Buğday/Mısır/Soya futures), ICE Futures US/Europe (Şeker/Kahve/
    Kakao/Pamuk), Dalian Ticaret Borsası/DCE (Mısır/Soya/Soya Küspesi/Palm
    Yağı, Çin referans fiyatları), Bursa Malaysia Derivatives (Ham Palm Yağı/
    FCPO — küresel yenilebilir yağ fiyatlarında kritik), London Metal Exchange
    (temel metal fiyatları — gıda dışı ama genel emtia bağlamı için),
    Baltic Exchange (resmi navlun endeksleri, investing.com'daki yansımasının
    tamamlayıcısı)

**Browser Use görev sayısı**: toplamda artık 2 (gazeteci) + 6 (küresel
endeks) + 6 (borsa futures) = 14 ayrı Browser Use session'ı çalışıyor, hepsi
SIRAYLA (paralel değil). Her biri tipik olarak 45sn-2dk sürüyor ama bazıları
(DCE gibi Çince/karmaşık sayfalar) daha uzun sürebilir — toplam veri toplama
adımı 15-25 dakikaya çıkabilir. Bu normaldir, kesme; `run_in_background` ile
çalıştır. Görevleri TEK GÖREVDE BİRLEŞTİRME — denendi, agent 5 dakikalık
polling penceresini aşıp zaman aşımına uğruyor (bkz. `_browser_use_gorev_calistir`
docstring'i).

**Fiyat verisi** (`tmo_ozet.py`, `fiyat_ozeti_getir()`):
- `github.com/utkusaraslan-hue/generalgrainrepo` reposundaki
  `veri_kaynagi/borsa_verileri.db` SQLite dosyasından (raw GitHub URL'den
  indirilir, repo klonlamaya gerek yok)
- Her (kaynak, ürün, birim) üçlüsü KENDİ en son 2 gününü kullanır — TMO diğer
  kaynaklara göre 1 gün gecikmeli geldiği için global "en son 2 tarih" almak
  TMO'yu tamamen dışarıda bırakırdı, bu yüzden per-source date pairing var
- TÜRİB Endeks kaynağı `ort_fiyat` yerine `kapanis_fiyat`/`min_fiyat`/`max_fiyat`
  alanlarına yazıyor — `fiyat_ozeti_getir()` bunu COALESCE ile zaten hallediyor
- `anomali: true` işaretli satırlar (gün içi >%70 sıçrama — kaynak veride
  birim/ölçek tutarsızlığı, ör. TL/ton vs TL/kg karışması) tabloya DAHİL EDİLMEZ

## Akış

### 1. Veri topla (mekanik, script) — ÖNCE VAR MI DİYE BAK

Bugünün tarihiyle `ham-veri/<GG-AA-YYYY>/` klasörü zaten varsa (ör. kullanıcı
"bülteni hazırla" deyip aynı gün az önce de istemiş olabilir), o klasörü
DOĞRUDAN KULLAN — `veri_topla.py`'yi tekrar çalıştırma. Reddit + Browser Use
adımları birkaç dakika sürüyor, veri zaten varsa bunu tekrarlamak gereksiz
bekleme yaratır. Kullanıcı özellikle "yeniden çek/güncelle" derse o zaman
tekrar çalıştır.

```bash
cd gida-haberleri
ls "ham-veri/$(date +%d-%m-%Y)/tarih.json" 2>/dev/null && echo "VAR, tekrar çekme" || python3 veri_topla.py
```

`ham-veri/<GG-AA-YYYY>/` klasörünü, tek bir json yerine ayrı dosyalar halinde üretir:
- `haberler.json`: liste, her öğe `{kaynak, baslik, ozet, link, tarih, kategori,
  gorsel_url, gorsel_dosya}` — `kategori` ya `"hububat_ve_diger"` ya
  `"meyve_sebze"` (anahtar kelime + regex word-boundary ile otomatik
  etiketlenmiş — "temmuz" gibi kelimelerin içinde geçen "muz" gibi yanlış
  eşleşmelere karşı zaten düzeltildi, ekstra kontrol gerekmez)
- `fiyatlar.xlsx`: TÜM borsa kaynaklarının fiyat karşılaştırması (Kaynak, Ürün,
  Birim, önceki/bugünkü tarih+fiyat, Değişim %, Anomali sütunları) — ama
  bültende SADECE TÜRİB (`kaynak.startswith("TURIB")`) ve TMO
  (`kaynak == "TMO"`) satırları kullanılıyor; Konya/ETB/Bandırma/TDAG/
  Kırklareli bu bültenin kapsamı dışında
- `gorseller/`: haberlerin kapak görselleri (dosya adı haberler.json'daki
  `gorsel_dosya` alanıyla eşleşir), tasarım/ilham veya bültene görsel eklemek
  istersen kullanabilirsin
- `tarih.json`: `{"tarih": "GG-AA-YYYY"}` — sadece "bu klasör bugüne mi ait"
  kontrolü için

Reddit + Browser Use (artık 14 ayrı görev: 2 gazeteci + 6 küresel endeks +
6 borsa futures, hepsi sırayla) nedeniyle toplam 15-25 dakikaya kadar
sürebilir, sabırlı ol — uzun sürüyor diye kesme, `run_in_background` ile
çalıştırıp bekleyebilirsin.

### 2. Paragrafları SEN yaz (editoryal — bu asıl senin işin)

`veri.json`'daki `haberler`'i oku, 4 kategori için **TAM OLARAK 2'şer
paragraf** akıcı Türkçe düz yazı yaz. Bu bir haber bülteni editörlüğü —
başlıkları madde madde sıralama, gerçek bağlam kurarak sentezle.

Kategoriler (kaynak ülkesi × ürün tipi, 2 boyutlu ayrım):
- `global_hububat`: Global kaynaklı (FBN, Reddit, FAO/IGC/USDA endeksleri,
  Baltic Dry/Panamax/Black Sea Wheat navlun endeksleri, CME/ICE/DCE/Bursa
  Malaysia/LME borsa futures verileri) hububat/tahıl/genel gıda
- `global_meyve_sebze`: Global kaynaklı meyve-sebze
- `turkiye_hububat`: Türkiye kaynaklı (Dünya Gazetesi, Tarım Dünyası, Karasaban,
  Tarımdan Haber, İrfan Donat/Ali Ekber Yıldırım) hububat/tahıl/genel tarım-gıda
- `turkiye_meyve_sebze`: Türkiye kaynaklı meyve-sebze

FAO/IGC/USDA endeksleri, navlun endeksleri (Baltic Dry/Panamax, Black Sea
Wheat, Baltic Exchange) ve borsa futures verileri (CME, ICE, DCE, Bursa
Malaysia, LME) haber değil ham veri niteliğinde — paragraf yazarken bunları
rakamsal bağlam/gerekçe olarak kullan (ör. "navlun endekslerindeki yükseliş
X'i etkiliyor", "CBOT buğday vadelilerindeki hareket Y'ye işaret ediyor"),
ayrı bir "endeksler" bölümü açma; kaynak adını (borsa/site adı, ör. "FAO",
"IGC", "CME", "Baltic Exchange/investing.com") metinde geçirmek serbest, bu
gazeteci-ismi-gizleme kuralının kapsamı dışında.

Kurallar:
- Sadece `veri.json`'daki gerçek haberlerden bilgi kullan, rakam/olay uydurma.
- **Ayrıntılı ve dengeli yaz (kullanıcı isteği, 26-09-2026):** `haberler.json`'daki
  HER haber ve endeks/borsa kalemi (FAO, IGC, USDA, CME, ICE, DCE, Bursa Malaysia,
  LME, Baltic vb.) en az bir kısa cümleyle geçmeli, bilgi atlama. Ama metin sayı
  listesi olmamalı: her kalemde en fazla 1-2 anahtar sayı ver, gerisini sözle
  anlat (artış/düşüş/yatay). Uzun ve dolu paragraflar serbest; sayı yığını değil.
- İngilizce haberleri (FBN, Reddit) Türkçeye çevirip sentezle.
- **Reddit adını metinde ASLA geçirme** (r/farming, r/FoodNews vb. de yok):
  "yurt dışında konuşulan", "yabancı sosyal medyada dönen", "yurt dışı tarım
  çevrelerinde tartışılan" gibi ifadeler kullan (kullanıcı isteği).
- **Gazetecileri isimle anma** (İrfan Donat, Ali Ekber Yıldırım vb.):
  "tarım gazetecileri", "sektörü takip eden gazeteciler" de.
- Site/yayın adı vermek serbest (Dünya Gazetesi, Bloomberg HT, Food Business
  News, CBC News gibi).
- Bir kategoride haber azsa/yoksa dürüstçe belirt (fabrikasyon yapma);
  gerekirse ilgili genel gıda fiyat/politika haberine köprü kurarak bağla.
- Bölüm sırası önemli: raporda önce **Türkiye**, sonra **Global Piyasa** gelir
  (kullanıcı bunu özellikle istedi — yerel piyasa önce).
- Eski "Özet Değerlendirme" (genel giriş) bölümü YOK — kullanıcı bunu
  "alakasız kalmış" diyerek kaldırttı, tekrar ekleme.

```python
paragraflar = {
    "global_hububat": ["...", "..."],
    "global_meyve_sebze": ["...", "..."],
    "turkiye_hububat": ["...", "..."],
    "turkiye_meyve_sebze": ["...", "..."],
}
```

### 3. HTML/PDF üret (mekanik)

`html_uret.py`'deki `bulten_html_olustur()` + `pdf_uret()` fonksiyonlarını
kullan (Bash ile inline Python):

```python
import json
from pathlib import Path
import openpyxl
from html_uret import bulten_html_olustur, pdf_uret

tarih = "<GG-AA-YYYY>"
ham_klasor = Path("ham-veri") / tarih

haberler = json.load(open(ham_klasor / "haberler.json", encoding="utf-8"))

def _sayfa_oku(ws, alanlar):
    return [dict(zip(alanlar, row)) for row in ws.iter_rows(min_row=2, values_only=True)]

wb = openpyxl.load_workbook(ham_klasor / "fiyatlar.xlsx")
ozet_alanlari = ["kaynak", "urun", "birim", "tarih_onceki", "ort_fiyat_onceki",
                  "tarih_son", "ort_fiyat_son", "degisim_yuzde", "anomali_ham"]
fiyat = _sayfa_oku(wb["Fiyatlar (özet)"], ozet_alanlari)
for r in fiyat:
    r["anomali"] = r.pop("anomali_ham") == "EVET"
turib_ozet = [r for r in fiyat if r["kaynak"].startswith("TURIB")]
tmo_ozet = [r for r in fiyat if r["kaynak"] == "TMO"]

il_ilce_alanlari = ["il", "ilce", "urun", "birim", "tarih_onceki", "ort_fiyat_onceki",
                     "tarih_son", "ort_fiyat_son", "degisim_yuzde", "anomali_ham"]
tmo_il_ilce = _sayfa_oku(wb["TMO İl-İlçe"], il_ilce_alanlari)
for r in tmo_il_ilce:
    r["anomali"] = r.pop("anomali_ham") == "EVET"

paragraflar = { ... }  # adım 2

html_metni = bulten_html_olustur(tarih, "logo.png", paragraflar, turib_ozet, tmo_ozet, haberler, tmo_il_ilce=tmo_il_ilce)
# Nihai bülten ham-veri/'nin DIŞINDA, kendi tarihli klasöründe tutulur
cikti_klasoru = Path(tarih)
cikti_klasoru.mkdir(exist_ok=True)
pdf_yolu = cikti_klasoru / f"gunluk_gida_ozet_{tarih}.pdf"
pdf_uret(html_metni, pdf_yolu, cikti_klasoru)
print("PDF:", pdf_yolu)
```

`bulten_html_olustur`'a verilen `tmo_il_ilce` parametresi, TMO Fiyatları
bölümünün altına ürün bazlı özetin YANINA, il/ilçe kırılımında TÜM TMO
fiyatlarını listeleyen ikinci bir tablo ekler (kullanıcı isteği: "il il ilçe
ilçe ne varsa" tüm TMO fiyatları görünsün, sadece özet değil).

`html_uret.py` playwright kullanıyor — chromium kurulu olmalı (gerekirse
`playwright install chromium`). Bülten sırası: 1) Türkiye (Hububat/Genel +
Meyve-Sebze alt bölümleri), 2) Global Piyasa (aynı alt bölümler), 3) TÜRİB
Fiyatları (grafik + tablo), 4) TMO Fiyatları (grafik + tablo), 5) Kaynakça
(sadece site adları, link/başlık yok; Reddit "Yurt dışı sosyal medya ve sektör
forumları" olarak geçer). Alt bilgi (GitHub linki, "Hazırlayan") YOK.

### 4. Doğrula ve raporla

`pdftoppm -jpeg -r 110 <pdf> onizleme` ile birkaç sayfayı görsel kontrol et
(Read ile aç, en az başlık/banner sayfasını ve bir fiyat tablosu sayfasını
gör). Kullanıcıya PDF yolunu ve kısa özet (kaç haber, TÜRİB/TMO satır sayısı,
hangi kaynaklarda sorun oldu, kaç ürün anomali olarak filtrelendi) bildir.

## Tasarım

**Herhangi bir tasarım değişikliği yapmadan/önermeden önce `tasarim.md`
dosyasını oku ve oradaki checklist'i uygula.** Kullanıcı önceki bir
denemenin "hâlâ çok vibecoding" durduğunu söyledi — bu dosya tam olarak
bunu önlemek için yazıldı, atlama.

Güncel tasarım (26-09-2026'da kullanıcı isteğiyle değişti, `html_uret.py`
CSS'inde ve `grafik_uret.py` stilinde gömülü):

- Başlık: "Günlük Özet" (eski "Günlük Gıda & Tarım Bülteni" DEĞİL); ayrıca
  "Sarıaslan Ticaret" yazısı YOK, solda büyük `logo.png` (84px), sağ üstte
  çerçevesiz tarih
- Siyah banner YOK: header ve tablo başlıkları beyaz zemin + koyu yazı,
  ince siyah/buğday (`#c9a339`) çizgilerle ayrılır
- Font: **Times New Roman, tüm yazılar 12 pt** (gövde, tablo, kart, grafik,
  açıklama, kaynakça); yalnızca başlık hiyerarşisi büyük (sayfa başlığı 22,
  bölüm 18, alt bölüm 14 pt). Oswald/Verdana artık kullanılmıyor
- Üstteki KPI kartlarında ürün adı tam görünür (kesilmez, satır kayar),
  kaynak kodu okunur adla yazılır (TURIB_NORMAL_SEANS → TÜRİB)
- Keskin köşe, gölge yok, ince (1px) çizgiler
- Fiyat değişim renkleri renk-körü dostu Okabe-Ito: artış mavi `#0072B2`,
  düşüş turuncu (grafikte taralı); kırmızı/yeşil KULLANMA. Grafikler
  scientific-visualization skill'i ilkeleriyle (`grafik_uret.py`)

## Bilinen kısıtlar / denenip vazgeçilenler

- **Bulut otomasyonu (RemoteTrigger/routine) denendi, çalışmadı**: bulut
  sandbox'ının dış ağ erişimi (Dünya Gazetesi, Reddit, Browser Use, FBN)
  proxy'de 403 ile engelleniyor, sadece GitHub'a erişebiliyor; ayrıca GitHub
  push (yazma) izni de ayrıca verilmesi gerekiyor. Bu yüzden bülten artık
  yerel makinede (bu proje) ve interaktif bir Claude oturumunda üretiliyor.
- **Ham Anthropic API ile otomatik paragraf yazımı denendi, kredi olmadığı
  için vazgeçildi** — kullanıcı bunun yerine Claude Chat/Code'un (bu skill
  üzerinden) doğrudan yazmasını istedi. `paragraf_yaz.py` ve
  `gunluk_bulten_olustur.py` dosyaları API-key'li otomasyon denemesinden
  kalma, kullanma — bu SKILL.md'deki akışı (adım 1-4) izle.
- **python-docx ile üretilen ilk tasarım kullanıcı tarafından reddedildi**
  ("çok çok kötü") — artık HTML+Playwright kullanılıyor, `docx_uret.py` eski,
  kullanma.
