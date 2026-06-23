"""cut_shiba_bg.py – Tách nền (kem/tan) khỏi ảnh Shiba 3D bằng flood-fill từ 4 góc,
tạo PNG nền trong suốt để hòa vào mọi nền card. Giữ nguyên file gốc.

Chạy: python tools/cut_shiba_bg.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ASSETS = Path(__file__).resolve().parents[1] / "src" / "frontend" / "assets"
SEED = (255, 0, 255)  # màu sentinel không trùng ảnh


def cut(name: str, thresh: int = 60, feather: float = 1.4) -> None:
    src = ASSETS / f"{name}.png"
    dst = ASSETS / f"{name}_cut.png"
    im = Image.open(src).convert("RGB")
    w, h = im.size

    work = im.copy()
    for corner in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1),
                   (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)]:
        ImageDraw.floodfill(work, corner, SEED, thresh=thresh)

    rgba = im.convert("RGBA")
    wpx = work.load()
    rpx = rgba.load()
    cleared = 0
    for y in range(h):
        for x in range(w):
            if wpx[x, y] == SEED:
                r, g, b, _ = rpx[x, y]
                rpx[x, y] = (r, g, b, 0)
                cleared += 1

    # feather mép alpha cho mịn
    alpha = rgba.getchannel("A").filter(ImageFilter.GaussianBlur(feather))
    rgba.putalpha(alpha)

    cx, cy = w // 2, int(h * 0.55)
    center_alpha = rgba.getpixel((cx, cy))[3]
    rgba.save(dst)
    pct = 100 * cleared / (w * h)
    print(f"{name}: cleared {pct:.1f}% nền, alpha tâm shiba={center_alpha} -> {dst.name}")


if __name__ == "__main__":
    # desk nền đồng đều -> thresh thấp đủ; ai/win nền gradient -> thresh cao hơn
    cut("shiba_desk", thresh=42)
    cut("shiba_ai", thresh=72)
    cut("shiba_win", thresh=66)
