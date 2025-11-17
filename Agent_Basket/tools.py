import os
import re
import webbrowser
from PIL import Image
from Agent_Marketplace.utils import smart_resize, encode_image, draw_point
import time

import os
from pathlib import Path

def open_browser(p):
    # Папка для сохранения профиля браузера (будет использоваться между запусками)
    user_data_dir = Path("Agent_Basket/browser_profile").resolve()
    user_data_dir.mkdir(parents=True, exist_ok=True)

    print(f"Используется профиль браузера: {user_data_dir}")

    # Запускаем Chromium с постоянным профилем
    context = p.chromium.launch_persistent_context(
        user_data_dir=str(user_data_dir),
        headless=False,
    )

    # Берём первую вкладку или создаём новую
    if context.pages:
        page = context.pages[0]
    else:
        page = context.new_page()

    # Переход на Яндекс.Маркет (для инициализации домена)
    page.goto('https://market.yandex.ru/', wait_until="load")
    return context, page  # ⚠️ Возвращаем context, а не browser!

def surf_to_page(page, url):
    page.goto(url)
    return page

def make_screenshot(page, output_image_path):
    time.sleep(3)
    page.screenshot(path=output_image_path)
    return page

def click(
        page,
        screenshot_path,
        user_query,
        client_openai,
        model_id,
        output_image_path,
        min_pixels=3136,
        max_pixels=12845056,
        pretty_click = False

):
    """Tool клика по изображению: возвращает список координат [x, y]"""

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

    base64_image = encode_image(screenshot_path)

    # Сообщения для модели
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

    # Запрос к модели
    completion = client_openai.chat.completions.create(
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

    # Bounding-box
    bbox = re.search(r'\[([0-9]+),\s*([0-9]+),\s*([0-9]+),\s*([0-9]+)\]', output_text)
    if bbox:
        x1, y1, x2, y2 = map(int, bbox.groups())
        rel_x = (x1 + x2) // 2
        rel_y = (y1 + y2) // 2
        print(f"Extracted bbox → center = ({rel_x}, {rel_y})")

    # Только точка
    else:
        pt = re.search(r'\[([0-9]+),\s*([0-9]+)\]', output_text)
        if pt:
            rel_x, rel_y = map(int, pt.groups())
            print(f"Extracted point = ({rel_x}, {rel_y})")
        else:
            print(" Could not parse point or bbox from model output")
            return output_text, None

    # --- Перевод относительных координат (0–1000) → пиксели resized изображения ---
    abs_x = rel_x / 1000 * resized_w
    abs_y = rel_y / 1000 * resized_h
    coordinate_absolute = [abs_x, abs_y]

    # =================================================================
    #       РИСУЕМ ТОЧКУ НА RESIZED ИЗОБРАЖЕНИИ
    # =================================================================

    annotated = draw_point(resized_image, coordinate_absolute, color="green")
    if pretty_click:
        annotated.save(output_image_path, quality=95)

        print(f"\nAnnotated image saved to: {os.path.abspath(output_image_path)}")

    if os.path.exists(output_image_path):
        webbrowser.open(f"file://{os.path.abspath(output_image_path)}")

    # --- Перевод относительных координат (0–1000) → пиксели ОРИГИНАЛЬНОГО viewport'а ---
    x_on_page = rel_x / 1000 * input_image.width
    y_on_page = rel_y / 1000 * input_image.height

    print(f"Clicking at ({x_on_page:.1f}, {y_on_page:.1f}) on page (viewport px)")

    page.mouse.click(x_on_page, y_on_page)
    return page