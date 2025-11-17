import re
import time
from openai import OpenAI
from Agent_Marketplace.system_prompt2 import SYSTEM_PROMPT
from Agent_Marketplace.tools import click, open_browser, make_screenshot, click_and_type, scroll, describe_product_from_image, click_card_and_return_image_url_if_match
from playwright.sync_api import sync_playwright

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

    def start_browsing(self):
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
                text_to_type="Желтая гавайская рубашка",
                press_enter=True,
            )
            page = make_screenshot(page, output_image_path="Agent_Marketplace/artifacts/screen2.png")
            page = scroll(page, direction="down", amount=400)#amount - количество пикселей прокрутки
            page = make_screenshot(page, output_image_path="Agent_Marketplace/artifacts/screen3.png")

            with page.context.expect_page() as new_page_info:
                page = click(
                    page=page,
                    screenshot_path="Agent_Marketplace/artifacts/screen3.png",
                    user_query="Найди координаты произвольной карточки товара в формате [x, y].",
                    client_openai=self.client,
                    model_id=self.model
                )
                new_page = new_page_info.value
                time.sleep(3)

            # Теперь делайте скриншот НОВОЙ страницы:
            new_page.screenshot(path="Agent_Marketplace/artifacts/screen4.png")

            # Отправляем скриншот в модель, чтобы получить название товара
            output_text, _ = describe_product_from_image(
                screenshot_path='Agent_Marketplace/artifacts/screen4.png',
                user_query="Определи название товара на изображении и верни его",
                client_openai=self.client,
                model_id=self.model,
                output_image_path="Agent_Marketplace/artifacts/product_card.png"
            )

            print(output_text.strip())
            # Получаем URL изображения по alt (названию товара)
            img_url = click_card_and_return_image_url_if_match(new_page, output_text.strip())


            if img_url:
                return "URL картинки товара:", img_url
            else:
                return "Не удалось получить URL изображения", None

            time.sleep(5)



    def run_shopping_agent(self, user_request, client_openai, model_id: str):
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

                # --- Выполнение действия ---
                if action_name == "OPEN_BROWSER":
                    browser, page = open_browser(p)
                    screenshot_path = "screenshot_start.png"
                    page = make_screenshot(page, screenshot_path)
                    obs = f"Открыт Яндекс.Маркет. Сделан скриншот: {screenshot_path}"
                    messages.append({"role": "user", "content": obs})

                elif action_name == "TYPE_SEARCH_QUERY":
                    query = action_args.strip('"')
                    screenshot_path = "before_search.png"
                    page = make_screenshot(page, screenshot_path)
                    page = click_and_type(
                        page=page,
                        screenshot_path=screenshot_path,
                        user_query="Найди координаты середины поискового запроса 'Найти товары'  в формате [x, y].",
                        client_openai=client_openai,
                        model_id=model_id,
                        text_to_type=query,
                        press_enter=True
                    )
                    time.sleep(2)
                    page = make_screenshot(page, "after_search.png")
                    messages.append({"role": "user", "content": f"Запрос '{query}' введён. Сделан скриншот."})

                elif action_name == "SCROLL":
                    direction = "down"
                    page = scroll(page, direction=direction, amount=500)
                    page = make_screenshot(page, f"scroll_{step}.png")
                    messages.append({"role": "user", "content": f"Прокрутка вниз. Сделан скриншот."})

                elif action_name == "CLICK_ON_PRODUCT":
                    # Например: CLICK_ON_PRODUCT("товар 1")
                    screenshot_path = f"click_ready_{step}.png"
                    page = make_screenshot(page, screenshot_path)
                    # Попросим модель указать координаты нужного товара
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
                    # Сделаем скриншот карточки
                    card_screenshot = f"product_card_{len(found_products) + 1}.png"
                    page = make_screenshot(page, card_screenshot)
                    messages.append(
                        {"role": "user", "content": f"Открыта карточка товара. Сделан скриншот: {card_screenshot}"})

                elif action_name == "SCREENSHOT_AND_DESCRIBE":
                    screenshot_path = f"desc_{step}.png"
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
                        # Попробуем извлечь названия для получения URL изображений
                        pass

                elif action_name == "EXTRACT_IMAGE_URL":
                    # Допустим, аргумент — название из описания
                    # Это можно улучшить: парсить название из found_products[-1]["description"]
                    try:
                        title = re.search(r"Название:\s*(.*)", found_products[-1]["description"]).group(1)
                    except:
                        title = "неизвестный товар"
                    img_url = click_card_and_return_image_url_if_match(page, title)
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

            # --- Закрытие браузера ---
            if browser:
                browser.close()

            # --- Возврат результатов ---
            return found_products