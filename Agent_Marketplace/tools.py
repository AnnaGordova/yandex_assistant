import os
import re
import webbrowser
from PIL import Image
from Agent_Marketplace.utils import smart_resize, encode_image, draw_point
import time

def make_screenshot(page, output_image_path):
    time.sleep(2)
    page.screenshot(path=output_image_path)
    return page


def open_browser(p):
    browser = p.chromium.launch(headless=False)
    # инициализация страницы
    page = browser.new_page()
    # переход по url адресу:
    page.goto('https://market.yandex.ru/')
    return browser, page


def click(
        page,
        screenshot_path,
        user_query,
        client_openai,
        model_id,
        output_image_path="screenshot_annotated2.png",
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

def click_and_type(
    page,
    screenshot_path,
    user_query,
    client_openai,
    model_id,
    text_to_type,
    output_image_path="screenshot_annotated_input.png",
    min_pixels=3136,
    max_pixels=12845056,
    pretty_click=False,
    press_enter=True,
):
    """
    Tool: находит элемент по изображению (например, строку поиска), кликает в него и вводит текст.

    Args:
        page: Playwright page object
        screenshot_path: путь к скриншоту для анализа
        user_query: промпт для модели (например, "Найди координаты строки поиска в формате [x, y]")
        client_openai: OpenAI-совместимый клиент
        model_id: ID модели (например, "Qwen/Qwen3-VL-...")
        text_to_type: текст, который нужно ввести после клика
        output_image_path: куда сохранить аннотированный скриншот
        min_pixels / max_pixels: параметры smart_resize (для Qwen-VL)
        pretty_click: рисовать ли точку и открывать изображение
        press_enter: нажимать ли Enter после ввода

    Returns:
        page: обновлённый page object
    """

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
    print("\n=== Model Output (click_and_type) ===")
    print(output_text)

    # =================================================================
    #   ИЗВЛЕЧЕНИЕ КООРДИНАТ (Qwen формат — относительные 0–1000)
    # =================================================================

    rel_x = rel_y = None

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
            print("❌ Could not parse point or bbox from model output")
            return page  # or raise ValueError

    # --- Перевод относительных координат (0–1000) → пиксели viewport'а (оригинала) ---
    x_on_page = rel_x / 1000 * input_image.width
    y_on_page = rel_y / 1000 * input_image.height

    print(f"🖱️  Clicking at ({x_on_page:.1f}, {y_on_page:.1f}) on page (viewport {input_image.width}×{input_image.height})")

    # --- Клик ---
    page.mouse.click(x_on_page, y_on_page)
    time.sleep(0.3)  # дать фокус установиться

    # --- Ввод текста ---
    print(f"⌨️  Typing: '{text_to_type}'")
    page.keyboard.type(text_to_type, delay=50)  # delay имитирует человеческую скорость

    # --- Нажатие Enter (опционально) ---
    if press_enter:
        print("⏎  Pressing Enter")
        page.keyboard.press("Enter")

    # =================================================================
    #       РИСУЕМ ТОЧКУ НА RESIZED ИЗОБРАЖЕНИИ (для отладки)
    # =================================================================

    # Координаты для аннотации — на resized изображении
    abs_x_annot = rel_x / 1000 * resized_w
    abs_y_annot = rel_y / 1000 * resized_h

    annotated = draw_point(resized_image, [abs_x_annot, abs_y_annot], color="blue")
    if pretty_click:
        annotated.save(output_image_path, quality=95)
        print(f"\n🖼️  Annotated image saved to: {os.path.abspath(output_image_path)}")
        webbrowser.open(f"file://{os.path.abspath(output_image_path)}")

    return page
def scroll(
    page,
    direction="down",
    amount=300,
    smooth=True,
    delay_after=0.8
):
    if direction not in ("up", "down"):
        raise ValueError("direction must be 'up' or 'down'")

    scroll_delta = -amount if direction == "up" else amount

    current_scroll_y = page.evaluate("window.scrollY")
    new_scroll_y = max(0, current_scroll_y + scroll_delta)

    print(f"🖱️  Scroll {direction} by {amount}px → from Y={current_scroll_y:.0f} to Y={new_scroll_y:.0f}")

    if smooth:
        # ✅ ПРАВИЛЬНО: передаём функцию + аргумент
        page.evaluate(
            """(y) => {
                window.scrollTo({
                    top: y,
                    behavior: 'smooth'
                });
            }""",
            new_scroll_y
        )
    else:
        # ✅ Также корректно
        page.evaluate("window.scrollTo(0, arguments[0])", new_scroll_y)

    time.sleep(delay_after)
    return page
