from pathlib import Path

from PIL import Image, ImageColor, ImageDraw


def get_screen_size() -> tuple[int, int]:
    """Возвращает размер экрана. Если не получилось — 1920x1080."""
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        w = root.winfo_screenwidth()
        h = root.winfo_screenheight()
        root.destroy()
        print(f"Screen size founded: {w}x{h}")
        return w, h
    except Exception:
        return 1920, 1080

def _draw_click_marker(path: Path, x_px: int, y_px: int, color: str = "red") -> None:
    """
    Рисует красивую «мишень» в точке клика на скриншоте по координатам в пикселях.
    Скриншот перезаписывается по тому же path.
    """
    image = Image.open(path).convert("RGBA")

    # цвет как в твоей функции
    if isinstance(color, str):
        try:
            rgb = ImageColor.getrgb(color)
            color_rgba = rgb + (128,)
        except ValueError:
            color_rgba = (255, 0, 0, 128)
    else:
        color_rgba = (255, 0, 0, 128)

    overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    w, h = image.size
    radius = min(w, h) * 0.05  # внешний круг
    cx, cy = x_px, y_px

    # внешний полупрозрачный круг
    draw.ellipse(
        [(cx - radius, cy - radius), (cx + radius, cy + radius)],
        fill=color_rgba,
    )

    # небольшой яркий центр
    center_radius = radius * 0.12
    draw.ellipse(
        [
            (cx - center_radius, cy - center_radius),
            (cx + center_radius, cy + center_radius),
        ],
        fill=(0, 255, 0, 255),
    )

    combined = Image.alpha_composite(image, overlay).convert("RGB")
    combined.save(path)

