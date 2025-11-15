from openai import OpenAI
from Agent_Marketplace.system_prompt import SYSTEM_PROMPT
from Agent_Marketplace.tools import click, open_browser, make_screenshot, click_and_type, scroll
from playwright.sync_api import sync_playwright

class Agent_marketplace:
    def __init__(self):
        """Конструктор класса агента, уточняющего запросы пользователя"""
        self.client = None
        self.model = None
        self.system_prompt = SYSTEM_PROMPT 

        def connect_vllm_api():
            """ Подключение к модели через yandex cloud (сделать как дадут доступ)"""
            self.model = "QuantTrio/Qwen3-VL-30B-A3B-Instruct-AWQ"
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
            page = scroll(page, direction="down", amount=1500)#amount - количество пикселей прокрутки
            page = make_screenshot(page, output_image_path="Agent_Marketplace/artifacts/screen3.png")


