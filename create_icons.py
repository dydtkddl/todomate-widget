"""
create_icons.py
SVG 도형을 Pillow로 직접 그려서 icon.png / icon.ico 생성
"""

from PIL import Image, ImageDraw
import math


def draw_clover(size=512, color=(26, 26, 26)):
    """네잎클로버 로고를 그린다."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    center = size / 2
    offset = size * 0.211     # 중심에서 각 원 중심까지 거리 (108/512)
    radius = size * 0.250     # 각 원의 반지름 (128/512)

    # 상, 하, 좌, 우 원 중심 좌표
    positions = [
        (center, center - offset),  # 상
        (center, center + offset),  # 하
        (center - offset, center),  # 좌
        (center + offset, center),  # 우
    ]

    for cx, cy in positions:
        x0 = cx - radius
        y0 = cy - radius
        x1 = cx + radius
        y1 = cy + radius
        draw.ellipse([x0, y0, x1, y1], fill=color)

    return img


def main():
    # 512x512 원본
    img_512 = draw_clover(512, color=(26, 26, 26))

    # icon.png (64x64, pystray용)
    img_64 = img_512.resize((64, 64), Image.LANCZOS)
    img_64.save("icon.png", "PNG")
    print("[OK] icon.png (64x64)")

    # icon.ico (멀티사이즈, exe/바로가기용)
    ico_images = []
    for s in [16, 32, 48, 64, 128, 256]:
        ico_images.append(img_512.resize((s, s), Image.LANCZOS))

    ico_images[0].save(
        "icon.ico",
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
        append_images=ico_images[1:],
    )
    print("[OK] icon.ico (16/32/48/64/128/256)")

    # 고해상도 PNG (인스톨러 배너 등에 활용)
    img_256 = img_512.resize((256, 256), Image.LANCZOS)
    img_256.save("icon_256.png", "PNG")
    print("[OK] icon_256.png (256x256)")


if __name__ == "__main__":
    main()
