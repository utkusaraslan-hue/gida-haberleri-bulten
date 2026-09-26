"""Bültenin banner görseli ve fiyat grafiklerini üretir (matplotlib + PIL)."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFilter

RENK_KOYU = (15, 32, 64)      # lacivert - koyu
RENK_ORTA = (30, 74, 130)     # kurumsal mavi
RENK_ACIK = (120, 165, 210)   # açık mavi


def banner_uret(cikti_yolu, genislik=1600, yukseklik=280):
    """Başak/toprak tonlarında yatay degrade banner üretir."""
    img = Image.new("RGB", (genislik, yukseklik), RENK_ORTA)
    draw = ImageDraw.Draw(img)
    for x in range(genislik):
        oran = x / genislik
        r = int(RENK_KOYU[0] + (RENK_ACIK[0] - RENK_KOYU[0]) * oran)
        g = int(RENK_KOYU[1] + (RENK_ACIK[1] - RENK_KOYU[1]) * oran)
        b = int(RENK_KOYU[2] + (RENK_ACIK[2] - RENK_KOYU[2]) * oran)
        draw.line([(x, 0), (x, yukseklik)], fill=(r, g, b))
    # hafif doku için bulanık şeritler
    img = img.filter(ImageFilter.GaussianBlur(0.5))
    img.save(cikti_yolu)
    return cikti_yolu


def fiyat_hareketi_grafigi(cikti_yolu, tmo_ozet, adet=8):
    """En çok hareket eden ürünler için yatay bar grafiği."""
    veri = [r for r in tmo_ozet if not r["anomali"] and r["degisim_yuzde"] is not None]
    veri.sort(key=lambda r: abs(r["degisim_yuzde"]), reverse=True)
    veri = veri[:adet][::-1]
    if not veri:
        return None

    etiketler = [f"{r['urun'][:28]} ({r['kaynak']})" for r in veri]
    degerler = [r["degisim_yuzde"] for r in veri]
    renkler = ["#b23b3b" if d < 0 else "#3d7a3d" for d in degerler]

    fig, ax = plt.subplots(figsize=(7.5, 3.8), dpi=150)
    ax.barh(etiketler, degerler, color=renkler)
    ax.axvline(0, color="#444", linewidth=0.8)
    ax.set_xlabel("Önceki güne göre değişim (%)")
    ax.set_title("En Çok Hareket Eden Ürünler", fontsize=11, fontweight="bold", color=f"#{RENK_KOYU[0]:02x}{RENK_KOYU[1]:02x}{RENK_KOYU[2]:02x}")
    ax.tick_params(axis="y", labelsize=8)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    fig.savefig(cikti_yolu)
    plt.close(fig)
    return cikti_yolu


def kaynak_dagilim_grafigi(cikti_yolu, haberler):
    """Kaynak başına toplanan haber sayısını gösteren pasta grafiği."""
    if not haberler:
        return None
    sayimlar = {}
    for h in haberler:
        sayimlar[h["kaynak"]] = sayimlar.get(h["kaynak"], 0) + 1

    fig, ax = plt.subplots(figsize=(5.5, 4), dpi=150)
    renkler = plt.cm.YlOrBr([0.3 + 0.5 * i / max(len(sayimlar) - 1, 1) for i in range(len(sayimlar))])
    ax.pie(
        sayimlar.values(), labels=sayimlar.keys(), autopct="%1.0f%%",
        colors=renkler, textprops={"fontsize": 7},
    )
    ax.set_title("Kaynak Dağılımı", fontsize=11, fontweight="bold")
    fig.tight_layout()
    fig.savefig(cikti_yolu)
    plt.close(fig)
    return cikti_yolu


if __name__ == "__main__":
    out = Path(__file__).parent / "_test_banner.png"
    banner_uret(out)
    print("banner:", out)
