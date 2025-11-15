import os
import re
import base64
import webbrowser
from openai import OpenAI
from PIL import Image, ImageDraw, ImageColor
from transformers.models.qwen2_vl.image_processing_qwen2_vl_fast import smart_resize


# =======================
#     ВСПОМОГАТЕЛЬНЫЕS
# =======================

def encode_image(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def draw_point(image: Image.Image, point: list, color=None):
    if isinstance(color, str):
        try:
            color = ImageColor.getrgb(color)
            color = color + (128,)
        except ValueError:
            color = (255, 0, 0, 128)
    else:
        color = (255, 0, 0, 128)

    overlay = Image.new('RGBA', image.size, (255, 255, 255, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    radius = min(image.size) * 0.05
    x, y = point

    overlay_draw.ellipse(
        [(x - radius, y - radius), (x + radius, y + radius)],
        fill=color
    )

    center_radius = radius * 0.1
    overlay_draw.ellipse(
        [(x - center_radius, y - center_radius),
         (x + center_radius, y + center_radius)],
        fill=(0, 255, 0, 255)
    )

    image = image.convert('RGBA')
    combined = Image.alpha_composite(image, overlay)
    return combined.convert('RGB')


# =======================
#   ОСНОВНОЙ PIPELINE
# =======================

# параметры, совместимые с Qwen2-VL
min_pixels = 3136
max_pixels = 12845056


def perform_gui_grounding_with_api(
        screenshot_path,
        user_query,
        model_id,
        base_url,
        api_key,
        output_image_path="screenshot_annotated2.png"
):
    # --- Загружаем оригинал ---
    input_image = Image.open(screenshot_path)

    # --- Smart resize: обязательно для Qwen3-VL ---
    resized_h, resized_w = smart_resize(
        input_image.height,
        input_image.width,
        factor=32,
        min_pixels=min_pixels,
        max_pixels=max_pixels,
    )
    resized_image = input_image.resize((resized_w, resized_h))

    # --- Кодируем изображение (оригинал или resized — не важно, для модели размер читается внутри) ---
    base64_image = encode_image(screenshot_path)

    # --- Инициализация клиента ---
    client = OpenAI(base_url=base_url, api_key=api_key)

    # --- Сообщения для модели ---
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{base64_image}"},
                },
                {"type": "text", "text": user_query},
            ],
        }
    ]

    # --- Запрос к модели ---
    completion = client.chat.completions.create(
        model=model_id,
        messages=messages,
        max_tokens=500,
    )

    output_text = completion.choices[0].message.content
    print("\n=== Model Output ===")
    print(output_text)

    # =================================================================
    #   ИЗВЛЕЧЕНИЕ КООРДИНАТ (Qwen формат — относительные 0–1000)
    # =================================================================

    coordinate_absolute = None

    # 1️⃣ Bounding-box
    bbox = re.search(r'\[([0-9]+),\s*([0-9]+),\s*([0-9]+),\s*([0-9]+)\]', output_text)
    if bbox:
        x1, y1, x2, y2 = map(int, bbox.groups())
        rel_x = (x1 + x2) // 2
        rel_y = (y1 + y2) // 2
        print(f"Extracted bbox → center = ({rel_x}, {rel_y})")

    # 2️⃣ Только точка
    else:
        pt = re.search(r'\[([0-9]+),\s*([0-9]+)\]', output_text)
        if pt:
            rel_x, rel_y = map(int, pt.groups())
            print(f"Extracted point = ({rel_x}, {rel_y})")
        else:
            print("❌ Could not parse point or bbox from model output")
            return output_text, None

    # --- Перевод относительных координат (0–1000) → пиксели resized изображения ---
    abs_x = rel_x / 1000 * resized_w
    abs_y = rel_y / 1000 * resized_h
    coordinate_absolute = [abs_x, abs_y]

    # =================================================================
    #       РИСУЕМ ТОЧКУ НА RESIZED ИЗОБРАЖЕНИИ
    # =================================================================

    annotated = draw_point(resized_image, coordinate_absolute, color="green")
    annotated.save(output_image_path, quality=95)

    print(f"\nAnnotated image saved to: {os.path.abspath(output_image_path)}")

    if os.path.exists(output_image_path):
        webbrowser.open(f"file://{os.path.abspath(output_image_path)}")

    return output_text, output_image_path


# --- Пример использования ---
if __name__ == "__main__":
    screenshot_path = "main_screen.png"          
    user_query = "Найди координаты середины поискового запроса 'Найти товары'  в формате [x, y]. "  # КРИТИЧНО: строгий формат!
    model_id = "QuantTrio/Qwen3-VL-30B-A3B-Instruct-AWQ"
    base_url = "http://195.209.210.28:8000/v1"        # Замените на ваш URL
    api_key = "sk-no-key-required"               # Замените, если требуется

    output_text, saved_path = perform_gui_grounding_with_api(
        screenshot_path, user_query, model_id, base_url, api_key
    )