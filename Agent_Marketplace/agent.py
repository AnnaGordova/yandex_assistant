import time

from openai import OpenAI
from Agent_Marketplace.system_prompt import SYSTEM_PROMPT
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

