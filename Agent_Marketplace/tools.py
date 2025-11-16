import os
import re
import webbrowser
from PIL import Image
from Agent_Marketplace.utils import smart_resize, encode_image, draw_point

def click(
        screenshot_path,
        user_query,
        client_openai,
        model_id,
        output_image_path="screenshot_annotated2.png",
        min_pixels=3136,
        max_pixels=12845056,

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
    annotated.save(output_image_path, quality=95)

    print(f"\nAnnotated image saved to: {os.path.abspath(output_image_path)}")

    if os.path.exists(output_image_path):
        webbrowser.open(f"file://{os.path.abspath(output_image_path)}")

    return output_text, output_image_path


# функция извлекает ссылку фото карточки по названию товара
def click_card_and_return_image_url_if_match(page, product_title):
    """
    Находит изображение на текущей странице по тексту в alt и возвращает его URL.
    """
    js_code = f"""
    () => {{
        // Ищем изображение, в alt которого есть указанный текст
        const img = Array.from(document.querySelectorAll('img[alt*="{product_title}"]'))[0];
        return img.src;     
    }}
    """
    img_url = page.evaluate(js_code)
    return img_url

def describe_product_from_image(
        screenshot_path,
        user_query,
        client_openai,
        model_id,
        output_image_path="screenshot_annotated2.png",
        min_pixels=3136,
        max_pixels=12845056,
):
    """Возвращает текстовое описание товара с изображения (без координат)"""

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

    if not base64_image:
        raise ValueError("Failed to encode image")

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

    # Возвращаем только текст — без координат и рисования точек
    return output_text, output_image_path