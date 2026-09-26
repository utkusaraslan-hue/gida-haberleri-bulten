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
- Food Business News RSS feed'leri (Genel, Tahıl, Tedarik Zinciri, Meyve/Sebze)
- Reddit (r/FoodNews, r/agriculture, r/farming) — sıkı rate-limit var, istekler
  arasında bilinçli bekleme var, bazen 429 ile bir/iki kaynak atlanabilir, sorun değil
- Browser Use Cloud API ile LinkedIn/Bloomberg HT'den iki gazetecinin son
  paylaşımları: **İrfan Donat** ve **Ali Ekber Yıldırım** (dikkat: "Elif Ekber
  Yıldırım" YANLIŞ isim, kullanıcı bunu düzeltti — doğrusu Ali Ekber Yıldırım)

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

Reddit + Browser Use nedeniyle toplam birkaç dakika sürebilir, sabırlı ol —
uzun sürüyor diye kesme, `run_in_background` ile çalıştırıp bekleyebilirsin.

### 2. Paragrafları SEN yaz (editoryal — bu asıl senin işin)

`veri.json`'daki `haberler`'i oku, 4 kategori için **TAM OLARAK 2'şer
paragraf** akıcı Türkçe düz yazı yaz. Bu bir haber bülteni editörlüğü —
başlıkları madde madde sıralama, gerçek bağlam kurarak sentezle.

Kategoriler (kaynak ülkesi × ürün tipi, 2 boyutlu ayrım):
- `global_hububat`: Global kaynaklı (FBN, Reddit) hububat/tahıl/genel gıda
- `global_meyve_sebze`: Global kaynaklı meyve-sebze
- `turkiye_hububat`: Türkiye kaynaklı (Dünya Gazetesi, İrfan Donat/Ali Ekber
  Yıldırım) hububat/tahıl/genel tarım-gıda
- `turkiye_meyve_sebze`: Türkiye kaynaklı meyve-sebze

Kurallar:
- Sadece `veri.json`'daki gerçek haberlerden bilgi kullan, rakam/olay uydurma.
- İngilizce haberleri (FBN, Reddit) Türkçeye çevirip sentezle, kaynağı belirt.
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
from html_uret import bulten_html_olustur, pdf_uret

d = json.load(open("ham-veri/<tarih-klasoru>/veri.json"))
turib_ozet = [r for r in d["fiyat"] if r["kaynak"].startswith("TURIB")]
tmo_ozet = [r for r in d["fiyat"] if r["kaynak"] == "TMO"]

paragraflar = { ... }  # adım 2

html_metni = bulten_html_olustur(d["tarih"], "logo.png", paragraflar, turib_ozet, tmo_ozet, d["haberler"])
# Nihai bülten ham-veri/'nin DIŞINDA, kendi tarihli klasöründe tutulur
cikti_klasoru = Path(d["tarih"])
cikti_klasoru.mkdir(exist_ok=True)
pdf_yolu = cikti_klasoru / f"gunluk_gida_ozet_{d['tarih']}.pdf"
pdf_uret(html_metni, pdf_yolu, cikti_klasoru)
print("PDF:", pdf_yolu)
```

`html_uret.py` playwright kullanıyor — chromium kurulu olmalı (gerekirse
`playwright install chromium`). Bülten sırası: 1) Türkiye (Hububat/Genel +
Meyve-Sebze alt bölümleri), 2) Global Piyasa (aynı alt bölümler), 3) TÜRİB
Fiyatları (tablo), 4) TMO Fiyatları (tablo), 5) Kaynakça + credit.

### 4. Doğrula ve raporla

`pdftoppm -jpeg -r 110 <pdf> onizleme` ile birkaç sayfayı görsel kontrol et
(Read ile aç, en az başlık/banner sayfasını ve bir fiyat tablosu sayfasını
gör). Kullanıcıya PDF yolunu ve kısa özet (kaç haber, TÜRİB/TMO satır sayısı,
hangi kaynaklarda sorun oldu, kaç ürün anomali olarak filtrelendi) bildir.

## Tasarım (zorunlu — değiştirilmeden kalmalı)

**Herhangi bir tasarım değişikliği yapmadan/önermeden önce `tasarim.md`
dosyasını oku ve oradaki checklist'i uygula.** Kullanıcı önceki bir
denemenin "hâlâ çok vibecoding" durduğunu söyledi — bu dosya tam olarak
bunu önlemek için yazıldı, atlama.

Tasarım, Sarıaslan Ticaret web sitesinden (`yine-bi-agent/website/web/src/app/globals.css`)
birebir alındı; kullanıcı ilk docx tasarımını ("çok kötü, profesyonel değil")
reddedip bunu istedi. Token'lar zaten `html_uret.py`'nin CSS'ine gömülü:

- Renkler: ink `#1a1512`, paper `#f6f5f1`, silo (koyu header) `#171410`,
  wheat (altın vurgu) `#c9a339`/`#e4c869`, moss (yeşil/artış) `#33654a`,
  rust (kırmızı/düşüş) `#9b3a2c`
- Font: başlıklar Oswald (büyük harf, kalın), gövde Verdana — **Times New
  Roman DEĞİL**, o eski docx sürümünde kalan bir tercihti, artık geçerli değil
- Keskin köşe, gölge yok, ince (1px) çizgiler — Tailwind'in `border-line`
  hairline stiline uygun
- Logo: `logo.png` (Sarıaslan Ticaret arması), header'ın sol üstünde
- Fiyat değişim renkleri renk-körü dostu turuncu/mavi (Okabe-Ito paleti,
  `#D55E00`/`#0072B2`) — HTML'de pill/badge olarak moss/rust kullanılıyor,
  eğer ek bir grafik eklenirse (matplotlib) kırmızı/yeşil DEĞİL bu paleti kullan

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
