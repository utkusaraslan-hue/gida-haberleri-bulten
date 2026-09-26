# Tasarım Kuralları — "Vibecoding" Görünümünden Kaçınma

Bu dosya, günlük bülten PDF'ini (ve bu projedeki her görsel çıktıyı) üretirken
uyulması gereken tasarım disiplinini tanımlar. Amaç: raporun "bir AI bunu
checklist'ten üretti" hissi vermemesi, gerçek bir editörün/tasarımcının
elinden çıkmış gibi durması.

Kaynak: "AI slop" / "vibe-coded UI" üzerine yapılan araştırma (MindStudio,
Venngage, The Fountain Institute, 925 Studios, Braingrid, aimadethis.substack —
bkz. altta linkler) + klasik print/editoryal tasarım prensipleri (grid,
hizalama, boşluk hiyerarşisi).

## 1. "Vibecoding" nedir, neden oluyor

AI tasarım araçları (ve LLM'ler) eğitim verisinde en sık tekrar eden
kalıpları üretir — bu kalıplar tek başına zararsız ama üst üste binince
("10 default bir araya gelince") anında "AI yaptı" hissi veriyor. Kimse tek
bir rastgele karar yüzünden "vibecoded" demiyor; sorun HER kararın en kolay/en
sık seçilen default'a düşmesi.

## 2. En sık görülen "slop" belirtileri (checklist — HER birini kontrol et)

**Renk:**
- [ ] Mor→mavi/indigo gradyan var mı? (AI'ın "Times New Roman"ı — asla kullanma)
- [ ] Fonksiyonu olmayan dekoratif renk/glow/parlama var mı?
- [ ] Her blok farklı bir vurgu rengi mi alıyor, yoksa TEK bir vurgu rengi mi
      tutarlı kullanılıyor?
- [ ] Renk gerçekten bir anlam mı taşıyor (artış/düşüş, durum), yoksa süs mü?

**Tipografi:**
- [ ] Inter/Roboto/Open Sans/sistem sans-serif mi kullanılıyor? (jenerik —
      kaçın; markaya özgü, seçilmiş bir font kullan)
- [ ] Tek bir font her yerde mi (başlık/gövde ayrımı yok mu)?
- [ ] Başlıklar "Build the future" tarzı boş/genel mi, yoksa gerçek bilgi mi
      taşıyor?

**Layout / kartlar:**
- [ ] Her şey bir "card" içinde mi? Kart içinde kart var mı (2-3 seviye
      nesting)? — kartı SADECE gerçekten grupla-nması gereken, etkileşimli
      veya vurgulanması gereken içerik için kullan; grid/beyaz alan ile
      ayırmak genelde yeterli.
- [ ] Tüm bileşenlerde AYNI köşe yuvarlaklığı (ör. her yerde 16px radius)
      körü körüne mi uygulanmış?
- [ ] Padding/spacing her yerde birebir aynı mı (düşünülmemiş, kopyala-
      yapıştır hissi)?

**Görsel malzeme:**
- [ ] Stok fotoğraf / AI illüstrasyon (aşırı pürüzsüz, simetrik, "plastik"
      görünümlü) kullanılıyor mu? — gerçek veri/gerçek haber görseli kullan.
- [ ] Emoji, ikon yerine kullanılmış mı? — emoji bir arayüz kararı DEĞİLDİR,
      "gerçek bir karar vermekten kaçınma" belirtisidir.
- [ ] Anlamsız durum noktaları/rozetleri var mı (ne temsil ettiği
      tanımlanmamış renkli daireler)?

**Genel:**
- [ ] Bu tasarımı biri "ChatGPT/Claude'a 'profesyonel görünsün' dedim, bu
      çıktı" diye tahmin eder mi? Öyleyse geri dön.

## 3. Print/PDF'e özgü ek kurallar (websiteden farklı olarak)

Bizim çıktımız bir web arayüzü değil, basılabilir/PDF bir rapor — bu yüzden
web-slop kontrol listesinin ÜSTÜNE şunlar da geçerli:

- **Grid disiplini**: Görünmez de olsa bir sütun sistemi (bizde: tek sütun
  başlıklar, 2 sütunlu gövde metni) TUTARLI uygulanmalı — sayfa sayfa farklı
  hizalama mantığı kullanma.
- **Hizalama**: Her eleman (başlık, tablo, kart) aynı sol/sağ marjine
  hizalanmalı. Hizasız/kayık elemanlar amatör hissi verir — en büyük
  "özensiz" sinyali.
- **Boşluk hiyerarşisi**: Bölümler arası boşluk > alt-bölümler arası boşluk >
  paragraflar arası boşluk. Üç seviye açıkça ayırt edilebilmeli, hepsi aynı
  boşlukla ayrılmamalı.
- **Marj**: Sayfa kenar boşlukları sabit ve kasıtlı olmalı (biz 40px content
  padding kullanıyoruz) — tarayıcı/renderer default'una bırakma.
- **Sayfa kırılması**: Bir başlık sayfa sonunda yalnız kalıp içeriği bir
  sonraki sayfaya düşürmemeli (`break-after: avoid` başlıklarda zorunlu);
  tablo/paragraf ortadan bölünüyorsa kontrollü olmalı, rastgele olmamalı.

## 4. Bizim kilitli tasarım sistemimiz (bu projede DEĞİŞTİRİLMEDEN kullanılacak)

26-09-2026'da kullanıcı isteğiyle güncellendi (eski koyu "silo" header +
Oswald/Verdana sistemi bırakıldı). Güncel sistem `html_uret.py` ve
`grafik_uret.py` içinde:

- **Renkler**: ink `#1a1512` metin, beyaz zemin; wheat `#c9a339` TEK vurgu
  rengi (üst başlık çizgisi, "Bölüm" etiketleri, alt başlık çubuğu). Koyu/siyah
  banner YOK — header ve tablo başlıkları beyaz zemin + ince siyah çizgi.
  Fiyat artış/düşüş için renk-körü dostu mavi/turuncu (Okabe-Ito) — yeşil/
  kırmızı DEĞİL.
- **Tipografi**: Times New Roman, tüm yazılar 12 pt (gövde, tablo, kart,
  grafik, açıklama, kaynakça). Başlık/gövde ayrımı font değişimiyle değil,
  boyut ve kalınlıkla yapılır: sayfa başlığı 22, bölüm 18, alt bölüm 14 pt,
  hepsi kalın.
- **Köşe/gölge**: köşe yuvarlaklığı YOK, gölge YOK — 1px ince çizgiler.
  Rounded-corner/shadow ekleme, bu tam olarak slop'a geri dönüş olur.
- **Kart kullanımı**: SADECE en büyük fiyat değişimlerini gösteren üstteki
  KPI kartları. Haber metni, paragraf ve grafikler kart İÇİNE KONMAZ;
  grafikler üst/alt ince çizgiyle ayrılır.
- **İçerik dili**: Başlık "Günlük Özet". Reddit adı ve gazeteci isimleri
  metinde geçmez; kaynakça sadece site adları (link yok); alt bilgi yok.

## 5. Her yeni tasarım denemesinden önce/sonra yapılacak

1. Bölüm 2'deki checklist'i tek tek işaretle.
2. Bölüm 4'teki kilitli sistemden SAPMA olup olmadığını kontrol et (yeni bir
   renk, yeni bir font, rounded corner, gölge eklenmiş mi?).
3. PDF'i `pdftoppm` ile render edip GÖRSEL olarak incele — CSS'in "doğru"
   göründüğünü varsayma, gerçekten bak.
4. Kendine sor: "Bu sayfayı Sarıaslan Ticaret'in gerçek bir tasarımcısı mı
   yaptı, yoksa bir AI mı 'profesyonel bülten' diye tahmin etti?"

## Kaynaklar

- [How to Avoid AI Slop When Using Claude Design](https://www.mindstudio.ai/blog/claude-design-avoid-ai-slop-design-system)
- [What Is AI Slop in Design? How to Fix It — Venngage](https://venngage.com/blog/ai-slop-in-design/)
- [7 Signs a UI Has Been Vibe Coded — The Fountain Institute](https://www.thefountaininstitute.com/blog/signs-vibe-coded-ui)
- [AI Slop Web Design: Complete Guide — 925 Studios](https://www.925studios.co/blog/ai-slop-web-design-guide)
- [Why All Vibe-Coded Designs Look the Same — aimadethis.substack](https://aimadethis.substack.com/p/why-all-vibecoded-designs-look-the)
- [Design Systems for AI Coding — Braingrid](https://www.braingrid.ai/blog/design-system-optimized-for-ai-coding)
- [Graphic Design Fundamentals: Alignment and Grid Systems — Noun Project](https://blog.thenounproject.com/graphic-design-fundamentals-alignment-and-grid-systems/)
