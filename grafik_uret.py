"""Fiyat bölümleri için yayın kalitesinde grafikler (scientific-visualization
skill'i ilkeleri): Okabe-Ito renk-körü dostu palet (artış mavi #0072B2,
düşüş turuncu #D55E00 + gri tonlamada okunsun diye tarama deseni), sıfır
referans çizgisi, üst/sağ çerçeve yok, birimli eksen etiketi, sans-serif
Times New Roman 12 pt yazı (bültenin gövde metniyle aynı). Çıktı vektörel SVG metnidir; HTML'e doğrudan gömülür."""
import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ARTIS = "#0072B2"
DUSUS = "#D55E00"
INK = "#1a1512"

STIL = {
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
    "font.size": 12,
    "axes.labelsize": 12,
    "xtick.labelsize": 12,
    "ytick.labelsize": 12,
    "axes.linewidth": 0.5,
    "axes.edgecolor": INK,
    "axes.labelcolor": INK,
    "xtick.color": INK,
    "ytick.color": INK,
    "xtick.major.width": 0.5,
    "ytick.major.width": 0,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "svg.fonttype": "none",  # yazılar metin olarak kalsın, tarayıcı fontuyla çizilsin
    "hatch.linewidth": 0.6,
}


def _kisa_ad(urun):
    ad = urun.replace("TÜRİB ", "").replace(" Endeksi", "")
    return ad.replace("BUĞDAY EKMEKLİK ", "EKMEKLİK ").replace("BUĞDAY MAKARNALIK ", "MAKARNALIK ")


def _panel(ax, satirlar, harf=None, baslik=None, sinir=None):
    satirlar = sorted(satirlar, key=lambda r: r["degisim_yuzde"])
    adlar = [_kisa_ad(r["urun"]) for r in satirlar]
    degerler = [r["degisim_yuzde"] for r in satirlar]
    renkler = [ARTIS if v > 0 else (DUSUS if v < 0 else "#999999") for v in degerler]
    taramalar = ["////" if v < 0 else "" for v in degerler]

    cubuklar = ax.barh(range(len(degerler)), degerler, color=renkler, height=0.62,
                       edgecolor="white", linewidth=0.4)
    for c, t in zip(cubuklar, taramalar):
        c.set_hatch(t)

    ax.axvline(0, color=INK, linewidth=0.8)
    ax.set_yticks(range(len(adlar)))
    ax.set_yticklabels(adlar)
    ax.tick_params(axis="y", length=0, pad=4)
    ax.set_xlabel("Günlük değişim (%)")

    sinir = sinir or _sinir(degerler)
    ax.set_xlim(-sinir, sinir)
    for i, v in enumerate(degerler):
        isaret = "+" if v > 0 else ""
        ax.text(v + (sinir * 0.02 if v >= 0 else -sinir * 0.02), i, f"{isaret}{v:.2f}",
                va="center", ha="left" if v >= 0 else "right", fontsize=12, color=INK)

    if baslik:
        ax.set_title(baslik, fontsize=12, loc="left", color=INK, pad=6)
    if harf:
        ax.text(-0.02, 1.02, harf, transform=ax.transAxes, fontsize=13,
                fontweight="bold", va="bottom", ha="right", color=INK)


def _sinir(degerler):
    # Değer etiketleri çubuk ucuna sığsın diye eksen en büyük değerin 1,6 katı
    return max(1.0, max(abs(v) for v in degerler)) * 1.6


def _svg(fig):
    tampon = io.StringIO()
    fig.savefig(tampon, format="svg", bbox_inches="tight", pad_inches=0.04, transparent=True)
    plt.close(fig)
    svg = tampon.getvalue()
    return svg[svg.index("<svg"):]


def _gecerli(satirlar):
    return [r for r in satirlar if not r.get("anomali") and r.get("degisim_yuzde") is not None]


def turib_grafigi_svg(turib_ozet):
    """A: normal seans ürünleri, B: TÜRİB endeksleri. Veri yoksa None."""
    urunler = _gecerli([r for r in turib_ozet if r["kaynak"] != "TURIB_ENDEKS"])
    endeksler = _gecerli([r for r in turib_ozet if r["kaynak"] == "TURIB_ENDEKS"])
    paneller = [(p, h, b) for p, h, b in (
        (urunler, "A", f"Normal seans, ürün bazında ({len(urunler)} ürün)"),
        (endeksler, "B", f"TÜRİB endeksleri ({len(endeksler)} endeks)"),
    ) if p]
    if not paneller:
        return None
    with plt.rc_context(STIL):
        # 12 pt etiketler yan yana sığmadığı için paneller alt alta dizilir
        oranlar = [len(p) for p, _, _ in paneller]
        fig, eksenler = plt.subplots(
            len(paneller), 1, figsize=(7.2, 0.3 * sum(oranlar) + 0.9 * len(paneller)),
            gridspec_kw={"height_ratios": oranlar, "hspace": 0.35}, squeeze=False)
        # Paneller aynı x ölçeğini paylaşır ki değişimler doğrudan karşılaştırılabilsin
        ortak = _sinir([r["degisim_yuzde"] for p, _, _ in paneller for r in p])
        for ax, (p, h, b) in zip(eksenler[:, 0], paneller):
            _panel(ax, p, harf=h if len(paneller) > 1 else None, baslik=b, sinir=ortak)
        return _svg(fig)


def tmo_grafigi_svg(tmo_ozet):
    satirlar = _gecerli(tmo_ozet)
    if not satirlar:
        return None
    with plt.rc_context(STIL):
        fig, ax = plt.subplots(figsize=(5.4, 0.3 * len(satirlar) + 1.1))
        _panel(ax, satirlar, baslik=f"TMO satış fiyatları ({len(satirlar)} ürün)")
        return _svg(fig)
