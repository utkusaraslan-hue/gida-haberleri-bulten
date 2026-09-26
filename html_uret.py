"""Sarıaslan Ticaret günlük özet PDF üretici: beyaz zemin, Times New Roman 12 pt,
buğday rengi vurgu, keskin köşe, gölgesiz ince çizgiler.
Playwright ile HTML -> PDF render edilir.

İçerik akışı editoryal: her kategori (Global Hububat, Global Meyve/Sebze,
Türkiye Hububat, Türkiye Meyve/Sebze) 2 paragraf düz yazı olarak sunulur —
başlık listesi değil. Bu paragraflar dışarıdan (bulten_verisi.paragraflar)
verilir; üretimi script değil, o günkü ajan/oturum yazar."""
import html
from pathlib import Path

from playwright.sync_api import sync_playwright

from grafik_uret import tmo_grafigi_svg, turib_grafigi_svg

CSS = """
:root {
  --ink: #1a1512;
  --paper: #ffffff;
  --paper-2: #faf9f6;
  --wheat: #c9a339;
  --rust: #9b3a2c;
  /* Fiyat değişimi: renk-körü dostu Okabe-Ito (artış mavi, düşüş turuncu) */
  --up: #0072B2;
  --up-pill: #e0edf6;
  --down: #b34d00;
  --down-pill: #fbe7da;
  --line: rgba(26,21,18,0.18);
}
* { box-sizing: border-box; }
/* Tüm metin Times New Roman 12 pt; yalnızca başlık hiyerarşisi büyük */
body {
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font-family: 'Times New Roman', Times, serif;
  font-size: 12pt;
  line-height: 1.45;
}
.page { padding: 0 0 36px 0; }
h1 { font-family: inherit; font-weight: 700; margin: 0; }
.header {
  background: var(--paper);
  color: var(--ink);
  padding: 28px 40px 18px 40px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 2px solid var(--wheat);
}
.header .brand { display: flex; align-items: center; gap: 14px; }
.header .brand img { height: 52px; width: 52px; object-fit: contain; }
.header .brand .name { font-size: 12pt; letter-spacing: 0.06em; color: var(--wheat); font-weight: 700; text-transform: uppercase; }
.header h1 { font-size: 22pt; margin-top: 2px; }
.header .date-badge { font-size: 12pt; font-weight: 700; }
.content { padding: 26px 40px 0 40px; }

.stat-row {
  display: flex;
  gap: 1px;
  background: var(--line);
  border: 1px solid var(--line);
  margin-bottom: 28px;
}
.stat-card { flex: 1; min-width: 0; background: var(--paper); padding: 12px 14px; }
.stat-card .stat-label { font-size: 12pt; font-weight: 700; margin-bottom: 6px; line-height: 1.25; }
.stat-card .stat-kaynak { font-size: 12pt; color: rgba(26,21,18,0.6); margin-bottom: 6px; }
.eyebrow {
  font-size: 12pt;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--wheat);
  margin: 0 0 2px 0;
}
.section { margin-bottom: 28px; }
.eyebrow, .section-title, .subsection-title { break-after: avoid; page-break-after: avoid; }
.section-title {
  font-size: 18pt;
  font-weight: 700;
  border-bottom: 1.5px solid var(--ink);
  padding-bottom: 6px;
  margin-bottom: 14px;
}
.subsection { margin-bottom: 16px; }
.subsection-title {
  font-size: 14pt;
  font-weight: 700;
  border-left: 4px solid var(--wheat);
  padding-left: 10px;
  margin-bottom: 8px;
}
.subsection .paragraflar { column-count: 2; column-gap: 28px; column-rule: 1px solid var(--line); }
.subsection p { margin: 0 0 10px 0; text-align: justify; break-inside: avoid; }
.divider { border: none; border-top: 1px solid var(--line); margin: 22px 0; }

table.pricetable { width: 100%; border-collapse: collapse; margin-bottom: 6px; font-size: 12pt; }
table.pricetable th {
  background: var(--paper);
  color: var(--ink);
  text-align: left;
  font-weight: 700;
  padding: 6px 8px;
  border-top: 1.5px solid var(--ink);
  border-bottom: 1.5px solid var(--ink);
}
table.pricetable td { padding: 5px 8px; border-bottom: 1px solid var(--line); font-variant-numeric: tabular-nums; }
table.pricetable tr:nth-child(even) td { background: var(--paper-2); }
table.pricetable thead { display: table-header-group; }
table.pricetable tr { break-inside: avoid; }
/* Kaynak ve sayı sütunları satır kaymasın; sadece ürün adı sarılabilir */
table.pricetable td:not(:nth-child(2)), table.pricetable th { white-space: nowrap; }
.pill { display: inline-block; padding: 1px 8px; font-weight: 700; font-size: 12pt; }
.pill.up { background: var(--up-pill); color: var(--up); }
.pill.down { background: var(--down-pill); color: var(--down); }
.pill.flat { color: var(--ink); opacity: 0.6; }

.kaynakca { font-size: 12pt; }
.kaynakca ul { margin: 0; padding-left: 18px; }
/* Grafik kart içine konmaz (tasarim.md: kart sadece KPI için); ince çizgiyle ayrılır */
.figure { margin: 4px 0 18px 0; padding: 10px 0 10px 0; border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); break-inside: avoid; }
.figure svg { width: 100%; height: auto; display: block; }
.figure.dar svg { width: 72%; }
.figcaption { font-size: 12pt; margin-top: 8px; line-height: 1.4; }
.uyari { font-size: 12pt; color: var(--rust); font-style: italic; margin-top: 10px; }
"""


def _pill(deg):
    if deg is None:
        return '<span class="pill flat">-</span>'
    yon = "up" if deg > 0 else ("down" if deg < 0 else "flat")
    isaret = "+" if deg > 0 else ""
    return f'<span class="pill {yon}">{isaret}{deg:.2f}%</span>'


KAYNAK_ADLARI = {"TURIB_NORMAL_SEANS": "TÜRİB", "TURIB_ENDEKS": "TÜRİB Endeks", "TMO": "TMO"}


def _kaynak_adi(kod):
    return KAYNAK_ADLARI.get(kod, kod)


def _fiyat_tablosu_html(satirlar):
    if not satirlar:
        return "<p>Veri alınamadı.</p>"
    satir_html = []
    for r in satirlar:
        onceki = r["ort_fiyat_onceki"] if r["ort_fiyat_onceki"] is not None else "-"
        satir_html.append(
            f"<tr><td>{html.escape(_kaynak_adi(r['kaynak']))}</td><td>{html.escape(r['urun'])}</td>"
            f"<td>{onceki}</td><td>{r['ort_fiyat_son']} {html.escape(r['birim'] or '')}</td>"
            f"<td>{_pill(r['degisim_yuzde'])}</td></tr>"
        )
    return (
        '<table class="pricetable"><thead><tr>'
        "<th>Kaynak</th><th>Ürün</th><th>Önceki</th><th>Bugün</th><th>Değişim</th>"
        "</tr></thead><tbody>" + "".join(satir_html) + "</tbody></table>"
    )


def _paragraflar_html(paragraflar):
    if not paragraflar:
        return ""
    return '<div class="paragraflar">' + "".join(f"<p>{html.escape(p)}</p>" for p in paragraflar) + "</div>"


def _stat_kartlari_html(turib_ozet, tmo_ozet, adet=4):
    tumu = [r for r in (turib_ozet + tmo_ozet) if not r.get("anomali") and r.get("degisim_yuzde") is not None]
    tumu.sort(key=lambda r: abs(r["degisim_yuzde"]), reverse=True)
    secilenler = tumu[:adet]
    if not secilenler:
        return ""
    kartlar = []
    for r in secilenler:
        kartlar.append(
            '<div class="stat-card">'
            f'<div class="stat-label">{html.escape(r["urun"])}</div>'
            f'<div class="stat-kaynak">{html.escape(_kaynak_adi(r["kaynak"]))}</div>'
            f'<div class="stat-value">{_pill(r["degisim_yuzde"])}</div>'
            "</div>"
        )
    return '<div class="stat-row">' + "".join(kartlar) + "</div>"


def _sekil_html(svg, no, aciklama, dar=False):
    if not svg:
        return ""
    return (f'<div class="figure{' dar' if dar else ''}">{svg}'
            f'<div class="figcaption"><b>Şekil {no}.</b> {aciklama}</div></div>')


def _kaynak_siteleri(haberler):
    """Kaynakçada link/başlık yok, sadece site adları. Reddit adı geçmez,
    gazeteciler isimle anılmaz (kullanıcı tercihi)."""
    siteler = []
    for h in haberler:
        k = h["kaynak"]
        if k.startswith("Dünya Gazetesi"):
            ad = "Dünya Gazetesi"
        elif k.startswith("Food Business News"):
            ad = "Food Business News"
        elif k.startswith("Reddit"):
            ad = "Yurt dışı sosyal medya ve sektör forumları"
        elif k.startswith("LinkedIn/Bloomberg"):
            ad = "Bloomberg HT ve tarım gazetecilerinin paylaşımları"
        else:
            ad = k
        if ad not in siteler:
            siteler.append(ad)
    return siteler + ["TÜRİB ve TMO (fiyat verileri)"]


def bulten_html_olustur(tarih_str, logo_yolu, paragraflar, turib_ozet, tmo_ozet, haberler):
    """paragraflar: {
        'global_hububat': [p1, p2], 'global_meyve_sebze': [p1, p2],
        'turkiye_hububat': [p1, p2], 'turkiye_meyve_sebze': [p1, p2],
    }"""
    anomaliler = [r for r in (turib_ozet + tmo_ozet) if r.get("anomali")]
    uyari_html = ""
    if anomaliler:
        uyari_html = f'<div class="uyari">[Not] {len(anomaliler)} üründe veri anomalisi tespit edildi, tablolara dahil edilmedi.</div>'

    kaynakca_items = "".join(f"<li>{html.escape(k)}</li>" for k in _kaynak_siteleri(haberler))

    logo_src = Path(logo_yolu).resolve().as_uri() if logo_yolu and Path(logo_yolu).exists() else ""

    return f"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<style>{CSS}</style></head><body>
<div class="page">
  <div class="header">
    <div class="brand">
      {f'<img src="{logo_src}">' if logo_src else ''}
      <div><div class="name">Sarıaslan Ticaret</div><h1>Günlük Özet</h1></div>
    </div>
    <div class="date-badge">{html.escape(tarih_str)}</div>
  </div>

  <div class="content">
    {_stat_kartlari_html(turib_ozet, tmo_ozet)}

    <div class="section">
      <div class="eyebrow">Bölüm 1</div>
      <div class="section-title">Türkiye</div>
      <div class="subsection">
        <div class="subsection-title">Hububat / Genel Tarım-Gıda</div>
        {_paragraflar_html(paragraflar.get('turkiye_hububat', []))}
      </div>
      <div class="subsection">
        <div class="subsection-title">Meyve / Sebze</div>
        {_paragraflar_html(paragraflar.get('turkiye_meyve_sebze', []))}
      </div>
    </div>

    <div class="section">
      <div class="eyebrow">Bölüm 2</div>
      <div class="section-title">Global Piyasa</div>
      <div class="subsection">
        <div class="subsection-title">Hububat / Genel Tarım-Gıda</div>
        {_paragraflar_html(paragraflar.get('global_hububat', []))}
      </div>
      <div class="subsection">
        <div class="subsection-title">Meyve / Sebze</div>
        {_paragraflar_html(paragraflar.get('global_meyve_sebze', []))}
      </div>
    </div>

    <hr class="divider">

    <div class="section">
      <div class="eyebrow">Bölüm 3</div>
      <div class="section-title">TÜRİB Fiyatları</div>
      {_sekil_html(turib_grafigi_svg(turib_ozet), 1, "Her ürün/endeks için kendi son iki işlem gününe göre ortalama fiyattaki yüzde değişim. Mavi düz çubuk artışı, turuncu taralı çubuk düşüşü gösterir. Tek gözlem karşılaştırması olduğundan hata çubuğu yoktur; değişimi hesaplanamayan ve anomali işaretli satırlar dışarıda bırakılmıştır.")}
      {_fiyat_tablosu_html([r for r in turib_ozet if not r.get('anomali')])}
    </div>

    <div class="section">
      <div class="eyebrow">Bölüm 4</div>
      <div class="section-title">TMO Fiyatları</div>
      {_sekil_html(tmo_grafigi_svg(tmo_ozet), 2, "TMO satış fiyatlarında (TL/ton) son iki yayın günü arasındaki yüzde değişim. Renk ve desen kodlaması Şekil 1 ile aynıdır; fiyatı 0 gelen ve anomali işaretli ürünler dahil edilmemiştir.", dar=True)}
      {_fiyat_tablosu_html([r for r in tmo_ozet if not r.get('anomali')])}
      {uyari_html}
    </div>

    <hr class="divider">

    <div class="section">
      <div class="eyebrow">Bölüm 5</div>
      <div class="section-title">Kaynakça</div>
      <div class="kaynakca"><ul>{kaynakca_items}</ul></div>
    </div>
  </div>

</div>
</body></html>"""


def pdf_uret(html_metni, cikti_pdf_yolu, calisma_klasoru):
    html_yolu = Path(calisma_klasoru) / "_bulten_gecici.html"
    html_yolu.write_text(html_metni, encoding="utf-8")
    with sync_playwright() as p:
        tarayici = p.chromium.launch()
        sayfa = tarayici.new_page()
        sayfa.goto(html_yolu.resolve().as_uri())
        sayfa.wait_for_timeout(400)
        sayfa.pdf(
            path=str(cikti_pdf_yolu),
            format="A4",
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
            print_background=True,
        )
        tarayici.close()
    html_yolu.unlink(missing_ok=True)
    return cikti_pdf_yolu
