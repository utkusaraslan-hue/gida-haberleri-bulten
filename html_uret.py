"""Sarıaslan Ticaret web sitesinin tasarım dilini (paper/ink/wheat/moss/rust,
Oswald başlık + Verdana gövde, keskin köşe, gölgesiz ince çizgiler) kullanan
PDF günlük bülten üretici. Playwright ile HTML -> PDF render edilir.

İçerik akışı editoryal: her kategori (Global Hububat, Global Meyve/Sebze,
Türkiye Hububat, Türkiye Meyve/Sebze) 2 paragraf düz yazı olarak sunulur —
başlık listesi değil. Bu paragraflar dışarıdan (bulten_verisi.paragraflar)
verilir; üretimi script değil, o günkü ajan/oturum yazar."""
import html
from pathlib import Path

from playwright.sync_api import sync_playwright

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Oswald:wght@500;700&display=swap');

:root {
  --ink: #1a1512;
  --paper: #f6f5f1;
  --paper-2: #ffffff;
  --silo: #171410;
  --silo-2: #23201a;
  --wheat: #c9a339;
  --wheat-light: #e4c869;
  --moss: #33654a;
  --moss-pill: #e4efe7;
  --rust: #9b3a2c;
  --rust-pill: #f6e3df;
  --line: rgba(26,21,18,0.16);
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font-family: Verdana, Geneva, sans-serif;
  font-size: 10.5pt;
  line-height: 1.55;
}
.page { padding: 0 0 36px 0; }
h1, h2, h3, .display {
  font-family: 'Oswald', Verdana, sans-serif;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.01em;
  margin: 0;
}
.header {
  background: var(--silo);
  color: var(--paper);
  padding: 28px 40px 24px 40px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 4px solid var(--wheat);
}
.header .brand { display: flex; align-items: center; gap: 14px; }
.header .brand img { height: 46px; width: 46px; object-fit: contain; background: var(--paper); padding: 4px; }
.header .brand .name { font-size: 9pt; letter-spacing: 0.12em; color: var(--wheat-light); font-weight: 700; text-transform: uppercase; }
.header h1 { font-size: 22pt; color: var(--paper); margin-top: 2px; }
.header .date-badge {
  border: 1px solid var(--wheat);
  color: var(--wheat-light);
  font-size: 10pt;
  font-weight: 700;
  padding: 8px 16px;
  letter-spacing: 0.05em;
}
.content { padding: 30px 40px 0 40px; }
.eyebrow {
  font-size: 8.5pt;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--wheat);
  margin: 0 0 4px 0;
}
.section { margin-bottom: 30px; page-break-inside: avoid; }
.section-title {
  font-size: 16pt;
  border-bottom: 2px solid var(--ink);
  padding-bottom: 8px;
  margin-bottom: 14px;
}
.subsection { margin-bottom: 18px; }
.subsection-title {
  font-size: 11.5pt;
  color: var(--ink);
  border-left: 4px solid var(--wheat);
  padding-left: 10px;
  margin-bottom: 8px;
}
.subsection p { margin: 0 0 10px 0; text-align: justify; }
.divider { border: none; border-top: 1px solid var(--line); margin: 24px 0; }

table.pricetable { width: 100%; border-collapse: collapse; margin-bottom: 6px; font-size: 9pt; }
table.pricetable th {
  background: var(--silo);
  color: var(--paper);
  text-align: left;
  font-family: 'Oswald', Verdana, sans-serif;
  font-weight: 500;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  font-size: 8pt;
  padding: 7px 10px;
}
table.pricetable td {
  padding: 6px 10px;
  border-bottom: 1px solid var(--line);
  font-variant-numeric: tabular-nums;
}
table.pricetable tr:nth-child(even) td { background: var(--paper-2); }
.pill { display: inline-block; padding: 1px 8px; font-weight: 700; font-size: 8.5pt; }
.pill.up { background: var(--moss-pill); color: var(--moss); }
.pill.down { background: var(--rust-pill); color: var(--rust); }
.pill.flat { background: var(--paper-2); color: var(--ink); opacity: 0.6; }

.kaynakca { font-size: 8pt; color: rgba(26,21,18,0.7); }
.kaynakca .k-item { margin-bottom: 3px; }
.kaynakca a { color: var(--ink); text-decoration: none; }
.footer {
  margin-top: 30px;
  border-top: 1px solid var(--line);
  padding: 14px 40px;
  font-size: 8pt;
  color: rgba(26,21,18,0.65);
  display: flex;
  justify-content: space-between;
}
.uyari { font-size: 8.5pt; color: var(--rust); font-style: italic; margin-top: 10px; }
"""


def _pill(deg):
    if deg is None:
        return '<span class="pill flat">-</span>'
    yon = "up" if deg > 0 else ("down" if deg < 0 else "flat")
    isaret = "+" if deg > 0 else ""
    return f'<span class="pill {yon}">{isaret}{deg:.2f}%</span>'


def _fiyat_tablosu_html(satirlar):
    if not satirlar:
        return "<p>Veri alınamadı.</p>"
    satir_html = []
    for r in satirlar:
        onceki = r["ort_fiyat_onceki"] if r["ort_fiyat_onceki"] is not None else "-"
        satir_html.append(
            f"<tr><td>{html.escape(r['kaynak'])}</td><td>{html.escape(r['urun'])}</td>"
            f"<td>{onceki}</td><td>{r['ort_fiyat_son']} {html.escape(r['birim'] or '')}</td>"
            f"<td>{_pill(r['degisim_yuzde'])}</td></tr>"
        )
    return (
        '<table class="pricetable"><thead><tr>'
        "<th>Kaynak</th><th>Ürün</th><th>Önceki</th><th>Bugün</th><th>Değişim</th>"
        "</tr></thead><tbody>" + "".join(satir_html) + "</tbody></table>"
    )


def _paragraflar_html(paragraflar):
    return "".join(f"<p>{html.escape(p)}</p>" for p in paragraflar)


def bulten_html_olustur(tarih_str, logo_yolu, paragraflar, turib_ozet, tmo_ozet, haberler):
    """paragraflar: {
        'global_hububat': [p1, p2], 'global_meyve_sebze': [p1, p2],
        'turkiye_hububat': [p1, p2], 'turkiye_meyve_sebze': [p1, p2],
    }"""
    anomaliler = [r for r in (turib_ozet + tmo_ozet) if r.get("anomali")]
    uyari_html = ""
    if anomaliler:
        uyari_html = f'<div class="uyari">[Not] {len(anomaliler)} üründe veri anomalisi tespit edildi, tablolara dahil edilmedi.</div>'

    kaynakca_items = "".join(
        f'<div class="k-item">[{html.escape(h["kaynak"])}] {html.escape(h["baslik"])}'
        + (f' — <a href="{html.escape(h["link"])}">{html.escape(h["link"])}</a>' if h.get("link") else "")
        + "</div>"
        for h in haberler
    )

    logo_src = Path(logo_yolu).resolve().as_uri() if logo_yolu and Path(logo_yolu).exists() else ""

    return f"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<style>{CSS}</style></head><body>
<div class="page">
  <div class="header">
    <div class="brand">
      {f'<img src="{logo_src}">' if logo_src else ''}
      <div><div class="name">Sarıaslan Ticaret</div><h1>Günlük Gıda &amp; Tarım Bülteni</h1></div>
    </div>
    <div class="date-badge">{html.escape(tarih_str)}</div>
  </div>

  <div class="content">
    <div class="section">
      <div class="eyebrow">Bölüm 1</div>
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

    <div class="section">
      <div class="eyebrow">Bölüm 2</div>
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

    <hr class="divider">

    <div class="section">
      <div class="eyebrow">Bölüm 3</div>
      <div class="section-title">TÜRİB Fiyatları</div>
      {_fiyat_tablosu_html([r for r in turib_ozet if not r.get('anomali')])}
    </div>

    <div class="section">
      <div class="eyebrow">Bölüm 4</div>
      <div class="section-title">TMO Fiyatları</div>
      {_fiyat_tablosu_html([r for r in tmo_ozet if not r.get('anomali')])}
      {uyari_html}
    </div>

    <hr class="divider">

    <div class="section">
      <div class="eyebrow">Bölüm 5</div>
      <div class="section-title">Kaynakça</div>
      <div class="kaynakca">{kaynakca_items}</div>
    </div>
  </div>

  <div class="footer">
    <span>Fiyat verisi: github.com/utkusaraslan-hue/generalgrainrepo</span>
    <span>Hazırlayan: Utku Sarıaslan — Sarıaslan Ticaret</span>
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
