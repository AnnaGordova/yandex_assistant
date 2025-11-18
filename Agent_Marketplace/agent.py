import re
import time
from openai import OpenAI
from Agent_Marketplace.system_prompt2 import SYSTEM_PROMPT
from Agent_Marketplace.tools import click, open_browser, make_screenshot, click_and_type, scroll, describe_product_from_image, return_product_page_url, return_image_url
from playwright.sync_api import sync_playwright
import os
import json

class Agent_marketplace:
    def __init__(self):
        """Конструктор класса агента, взаимодействующего с интерфейсом"""
        self.client = None
        self.model = None
        self.system_prompt = SYSTEM_PROMPT 

        def connect_vllm_api():
            """ Подключение к модели через yandex cloud (сделать как дадут доступ)"""
            self.model = "QuantTrio/Qwen3-VL-32B-Instruct-AWQ"
            self.client = OpenAI(
                base_url="http://195.209.210.28:8000/v1",
                api_key="sk-no-key-required",  # No API key needed for local vLLM server
            )

        connect_vllm_api()

    def start_browsing(self, query_to_type="мужская рубашка в гавайском стиле", product_id = 0, qeury_type = 'notstated'):
        """Здесь будет логика хождения агента по браузеру, пока что тут просто один клик"""
        '''
        screenshot_path = "Agent_Marketplace/main_screen.png"
        user_query = "Найди координаты середины поискового запроса 'Найти товары'  в формате [x, y]. "  # КРИТИЧНО: строгий формат!

        output_text= click(
            screenshot_path, user_query, self.client, self.model, output_image_path="Agent_Marketplace/artifacts/main_screen2.png"
        )'''

        with sync_playwright() as p:
            browser, page = open_browser(p)
            page = make_screenshot(page, output_image_path="Agent_Marketplace/artifacts/screen1.png")
            page = click_and_type(
                page=page,
                screenshot_path="Agent_Marketplace/artifacts/screen1.png",
                user_query="Найди координаты середины строки поиска в формате [x, y].",
                client_openai=self.client,
                model_id=self.model,
                text_to_type=query_to_type,
                press_enter=True,
            )
            page = make_screenshot(page, output_image_path="Agent_Marketplace/artifacts/screen2.png")
            title_list, url_list, url_photo_list = [], [], []
            for i in range(1, 4):
                with page.context.expect_page() as new_page_info:
                    page = click(
                        page=page,
                        screenshot_path="Agent_Marketplace/artifacts/screen2.png",
                        user_query=f"Найди координаты центра {i}-ой карточки товара в формате [x, y].",
                        client_openai=self.client,
                        model_id=self.model,
                    )
                    new_page = new_page_info.value
                    time.sleep(5)

                # Теперь делайте скриншот НОВОЙ страницы:
                new_page.screenshot(path=f"Agent_Marketplace/artifacts/card_screen{i}.png")

                # Отправляем скриншот в модель, чтобы получить название товара
                output_text, _ = describe_product_from_image(
                    screenshot_path=f'Agent_Marketplace/artifacts/card_screen{i}.png',
                    user_query="Определи название товара на изображении и верни его",
                    client_openai=self.client,
                    model_id=self.model,
                    output_image_path=f"Agent_Marketplace/artifacts/product_card{i}.png"
                )


                # Получаем URL страницы товара
                product_url = return_product_page_url(new_page, output_text.strip())
                title_list.append(output_text.strip())
                if product_url:
                    print("URL карточки товара:", product_url)
                    url_list.append(product_url)
                else:
                    print("Не удалось получить URL карточки", None)
                    url_list.append('error')

                photo_url = return_image_url(new_page, output_text.strip())

                if photo_url:
                    print("URL фото товара:", photo_url)
                    url_photo_list.append(photo_url)
                else:
                    print("Не удалось получить URL фото", None)
                    url_photo_list.append('error')

            products = []
            for i in range(3):

                d = {
                    'title': title_list[i],
                    'url': url_list[i],
                    'photo_url': url_photo_list[i]
                }
                products.append(d)

                data = {"products": products}

            with open(f"eval/baseline_{product_id}_{qeury_type}_cards.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"JSON создан: baseline_{product_id}_{qeury_type}_cards.json")

    def sanitize_folder_name(name: str) -> str:
        """Очищает строку, чтобы можно было использовать как имя папки."""
        return re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name).strip()[:100]

    def run_shopping_agent(self, user_request: str, client_openai, model_id: str):
        # Создаём папку для скриншотов
        folder_name = f"Agent_Marketplace/screenshots_{user_request}"
        os.makedirs(folder_name, exist_ok=True)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Пользователь: {user_request}"}
        ]

        browser = None
        page = None
        found_products = []
        max_steps = 15
        step = 0

        with sync_playwright() as p:
            while step < max_steps:
                step += 1

                # --- Запрос к модели ---
                completion = client_openai.chat.completions.create(
                    model=self.model,
                    messages=messages,
                )
                response = completion.choices[0].message.content
                print(f"\n[Step {step}] Model response:\n{response}")
                messages.append({"role": "assistant", "content": response})

                # --- Парсим ACTION ---
                action_match = re.search(r"ACTION:\s*(\w+)\((.*)\)", response)
                if not action_match:
                    print("⚠️ Не удалось распознать действие. Прерываем.")
                    break

                action_name = action_match.group(1)
                action_args = action_match.group(2)

                # --- Вспомогательная функция для формирования пути ---
                def sp(filename: str) -> str:
                    return os.path.join(folder_name, filename)

                # --- Выполнение действия ---
                if action_name == "OPEN_BROWSER":
                    browser, page = open_browser(p)
                    screenshot_path = sp("screenshot_start.png")
                    page = make_screenshot(page, screenshot_path)
                    obs = f"Открыт Яндекс.Маркет. Сделан скриншот: {screenshot_path}"
                    messages.append({"role": "user", "content": obs})

                elif action_name == "TYPE_SEARCH_QUERY":
                    query = action_args.strip('"')
                    screenshot_path = sp("before_search.png")
                    page = make_screenshot(page, screenshot_path)
                    page = click_and_type(
                        page=page,
                        screenshot_path=screenshot_path,
                        user_query="Найди координаты середины поискового запроса 'Найти товары' в формате [x, y].",
                        client_openai=client_openai,
                        model_id=model_id,
                        text_to_type=query,
                        press_enter=True
                    )
                    time.sleep(2)
                    page = make_screenshot(page, sp("after_search.png"))
                    messages.append({"role": "user", "content": f"Запрос '{query}' введён. Сделан скриншот."})

                elif action_name == "SCROLL":
                    direction = "down"
                    page = scroll(page, direction=direction, amount=500)
                    page = make_screenshot(page, sp(f"scroll_{step}.png"))
                    messages.append({"role": "user", "content": f"Прокрутка вниз. Сделан скриншот."})

                elif action_name == "CLICK_ON_PRODUCT":
                    screenshot_path = sp(f"click_ready_{step}.png")
                    page = make_screenshot(page, screenshot_path)
                    click_prompt = f"Пользователь ищет: {user_request}. Найди на изображении один подходящий товар и верни его координаты в формате [x, y] (0–1000)."
                    page = click(
                        page=page,
                        screenshot_path=screenshot_path,
                        user_query=click_prompt,
                        client_openai=client_openai,
                        model_id=model_id,
                        pretty_click=True
                    )
                    time.sleep(2)
                    card_screenshot = sp(f"product_card_{len(found_products) + 1}.png")
                    page = make_screenshot(page, card_screenshot)
                    messages.append(
                        {"role": "user", "content": f"Открыта карточка товара. Сделан скриншот: {card_screenshot}"})

                elif action_name == "SCREENSHOT_AND_DESCRIBE":
                    screenshot_path = sp(f"desc_{step}.png")
                    page = make_screenshot(page, screenshot_path)
                    desc_prompt = "Опиши этот товар: название, ключевые характеристики, цену. Не возвращай координаты."
                    description, _ = describe_product_from_image(
                        screenshot_path=screenshot_path,
                        user_query=desc_prompt,
                        client_openai=client_openai,
                        model_id=model_id
                    )
                    found_products.append({"description": description, "screenshot": screenshot_path})
                    messages.append({"role": "user", "content": f"Описание товара получено: {description}"})

                    if len(found_products) >= 3:
                        pass  # можно добавить логику завершения

                elif action_name == "EXTRACT_IMAGE_URL":
                    try:
                        title = re.search(r"Название:\s*(.*)", found_products[-1]["description"]).group(1)
                    except:
                        title = "неизвестный товар"
                    img_url = return_image_url(page, title)
                    if img_url:
                        found_products[-1]["image_url"] = img_url
                    messages.append({"role": "user", "content": f"URL изображения: {img_url}"})

                elif action_name == "FINAL_ANSWER":
                    print("✅ Финальный ответ от модели:")
                    print(response)
                    break

                else:
                    print(f"Неизвестное действие: {action_name}")
                    break

                time.sleep(1)

            if browser:
                browser.close()

            return found_products