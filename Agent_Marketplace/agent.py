from openai import OpenAI
from Agent_Marketplace.system_prompt import SYSTEM_PROMPT
from Agent_Marketplace.tools import click
from Agent_Marketplace.tools import click_card_and_return_image_url_if_match
from playwright.sync_api import sync_playwright
from Agent_Marketplace.tools import describe_product_from_image

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
        screenshot_path = "Agent_Marketplace/main_screen.png"
        user_query = "Найди координаты чекбокса 48 размера и верни их  в формате [x, y]. "  

        output_text, saved_path = click(
            screenshot_path, user_query, self.client, self.model, output_image_path="Agent_Marketplace/artifacts/main_screen2.png"
        )


        return output_text, saved_path
    

    def start_browsing_test(self):
        screenshot_path = "yandex_assistant/Agent_Marketplace/artifacts/Card_screen1.png"
        user_query = "Определи название товара на изображении и верни его"

        # Запускаем браузер
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            page.goto("https://market.yandex.ru/card/platye-zhenskoye-a-a-awesome-apparel-by-ksenia-avakyan/4308768525?do-waremd5=b_0cdcInuGLDAGP3pWnsfg&cpc=XWA8vD33CFJx-Qu3o5MD0RVfIsqkOdQqKNeLV22ejQu4MbkTI-xBtemA1412Ez1jgS44fhNpEFRASXDicSS5jAvR9NglHdN21I8yIX_S5GCNXw4NG1yzRCR3LmB3UpFXGhV18LZYip-cYibIsRFhUu3paclrz_LIY9DI0nXMnm9cY1fmNBdNVz-Ta1ALbMK_nZahQyyivW4_R-Ohyr9WnVnsOQN4ur3mQajumDWGpiwucOfIXG4nxnDMH7XAkI8D2Pc1WNGCDhGN2RLmUYc_MYj7tH4pZhiGWCfATLHIh7AP1te3KuB4G4DxjjqskD7kSJnRHIa-cIlqHNqYA-Wajzi592YmSAY5LUoQ61HEj9biTn5kLdvnYjt6BbqSgcBNJvh5fsTPD5UuV0VMnL9N0DwovpbhBmzXJgIQLjR4MkDev4cYG3VTKAEbI5vKclvSmHV_OIUsR__Br4hjjMDUQBfDD9EkUDRkEsBJkDho7lcFJzPlQ27qKXGkyA9FUBKkx-suv21aluZQ8PMVoggrdzFFwsuMHkMc5WgwSeVjCbfc7E-m-381fCO_ZUw3-JL_krn3G112J3n945eEdKFIaEBmwKND2vvtSp6X8-SIwcZKq3GYQA06d9d13mEEt95kLvwnyA7DWQk5lbIluXphV1kdk8ug7UgymZVBLdeHnNyVR_BoNk1_Z_y-YcIFcbjP0Dx_6TJOM2c%2C&nid=66071566&ogV=-6")

            # Делаем скриншот
            page.screenshot(path=screenshot_path)

            # Отправляем скриншот в модель, чтобы получить название товара
            output_text, _ = describe_product_from_image(
                screenshot_path,
                user_query,
                self.client,
                self.model,
                output_image_path="Agent_Marketplace/artifacts/product_title.png"
            )

            # Извлекаем название товара из ответа модели
            product_title = output_text.strip()

            # Получаем URL изображения по alt (названию товара)
            img_url = click_card_and_return_image_url_if_match(page, product_title)

            browser.close()

            if img_url:
                return "URL картинки товара:", img_url
            else:
                return "Не удалось получить URL изображения", None