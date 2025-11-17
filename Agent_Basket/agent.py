import time
from openai import OpenAI
from Agent_Basket.tools import click, open_browser, make_screenshot, surf_to_page
from playwright.sync_api import sync_playwright

class Agent_Basket:
    def __init__(self):
        """Конструктор класса агента, добавляющего товары в корзину"""
        self.client = None
        self.model = None

        def connect_vllm_api():
            """ Подключение к модели через yandex cloud (сделать как дадут доступ)"""
            self.model = "QuantTrio/Qwen3-VL-32B-Instruct-AWQ"
            self.client = OpenAI(
                base_url="http://195.209.210.28:8000/v1",
                api_key="sk-no-key-required",  # No API key needed for local vLLM server
            )

        connect_vllm_api()

    def start_basketing(self, clean = True):
        """Здесь принятие на вход списка товаров и добавление их в корзину, пока что список товаров задан статически"""
        with sync_playwright() as p:

            context, page = open_browser(p)  # ← изменилось имя переменной
            urls = [
                'https://market.yandex.ru/card/bryuki-zhenskiye-laina-sportivnyye-shtany/102142147191?do-waremd5=s85sR2dS1r9NncJzcAVwYQ&sponsored=1&cpc=vVGNwwXWAymwynDX6LAiUyOdzTsULnI8TMhI_8aEbLMZrvkc8GeJw47HZKA46JJIesXuuMT0QdcispqzkZrlEQuCk8CpxMWFcZb2vHxIniNrD1CCYsHyoayHSX9VA_WLyypjwNcSvwFM2SGsG7-75dluR3GG5TsgVFPPshpuzXq-fKXAAOCRgVv7O3gGsDjiR1BkNWBHtRCaXGNv7Gypct5DDpR3C9lDN7aqST5I70R3GYRn7dTP3qG02tczAvb8ndh_8-hCbG2np6aF86kKqx_bXJwRhG6otWrPeyi9eytgxgGlrUh8-loItrH-i5KVXc6iwS3qsDh7qk1KCjREEDbmc2prJpY8I7yNOenIbLDhzKQ-ROuwoERsg9WowGFMvJkRSDuqvEKsUxk7JGbNS7TwqG0XvvAiFpOO81NsAJAQ7OBxILKRKF6NoAsDb5lIJQs4Xz9nHA8fJMD9fUKQEo8llF2s2v78chHN_OtSnd4LhXsj1INp7gmiJne0s5YoeKM3xS_g_BiFRj1dD1OJciuiZIQZsFG55J0ouJjfl9KvKGhgTHXcFWnHBxuO7XPsldyHIH0B1MsoN8wbPFK8KLjX6YW-Lzna5ZlTIqy0BZjUh07WEdjajogLZzw-SC3Qh0Zriq9Sdl6m-yUrg3TUwzxMkvuJrrbMzptC87vLS1Pdrsg-4xQejdokIWpzmlmEq_j4_Id-MeC4Z8iLbUviAw%2C%2C&nid=66704452&ogV=-6',
                'https://market.yandex.ru/card/futbolka-zhenskaya-ohana-market-oversayz-razmer-56/103097158195?do-waremd5=XyR_llhMy7te0Zvw7lOJZA&sponsored=1&cpc=62FZE6m8jkEG-bEYfn06NLzO6Kc6Ne25ixmVsweP07x_PLAKf1nPFvbarJcw3vsway72YbGmZVTsr7YuHfIugOkoCDSXMWRKZFNjl8opURmS9N_Thliy33l0K27CqBkIM8NhJ1WIcxDw_zN6qzBXrrv2XML8s2nP0iF3P38liI_lXNwgmVB7kgh_UJw36nC2jRRFFDuCVWePGDe8VZWdX2pFiLF7wy14AI7SdF1AmLp7Eq2PKdfZ7qBsxBdCeYokOK-_a9okh5S6R6Q9x8CTPL2dv2RVh3AydDa0kwwcU-dVk9H2cYcwbSbtCq5WQ5JIoQnj6aseun7jqbtJTh4_oxlPLac0WKWMzR1qYB0nMQz5BH98SFOOAEmaA19L8MuCNbNT01tytJ_1iCtDDn7TF_573CSYbEZkb6G8hADLRvIYweBoEwAVVgqzQ65BGDCZ0AMewCSlcd_MUA23mx7jp19hUKD6FbsE0llPHYCCYjJzQqTvqqxW4RYjCwu6zPmYOMVHS10mPNf7UmCxQyqV7t6y6LHCxh-FoSUJLNlSbA5atpJTfEWL6YGsUFar_nBfxcY6ZE8v5Pa-eFL73Cj_6hUzaOJoLZ_lyLtN6qzBzd1gRlSU_KYfVRo6eKkJlqsR1Rtt255p9pUlcfowWfoS1E0Tg9-kS1pgPLCldpo6Wb_eKWp2BfxaO7PbO74ZJ0UlT1Mg978-o2EPWwjVaNeRLyGuEARoEGY9nYrTdaqY5x5ApTAN2UsE8I2aoxMGdAO5&nid=69732938&ogV=-6',
                'https://market.yandex.ru/card/futbolka-s-printom-palm-tvoye-tsvet-svetlo-goluboy/4468317180?do-waremd5=0V0KnF2VY2dLjs30rLk5PA&sponsored=1&cpc=r0xyHE6qPDLHU1ZwB5orIKU2QTIedUSU8o0qkGrFTnJGz1Nhwt8P-r0omd-RC2I84WfQAcOnPOMA2q6XBIOp4Har9NCFQD4lJS_sE55dTPTU34hz8s_yyRwmrUS37UzbQbjhia62UR3YSY2tBHNN_WXmW2spSe7q6pnTTCdNm4xNdEHj8WuXQNVfqkZ0eYbeZ0PcETVW4gSDmm75EgUq8ySpc7V9OtyMidvQmFf1LWLe26l_ZrtMXez14_Z0K-LS7qI-pq8XIU119IhueiIBR0ILhGxQUanKuJoxJme211YrveN4iUhtjIyQVv-NQOD1e0-3aAGOENaObrab1HfdmE_xHvYg4vWqQwUL4Shh0NHCWWVvc7QrEhkjGx8FKfrL1l5VigL6fhmUd6VH5f7UR-lc9dULN4TLWWk7oEGgsoTkbXYusR6KdAWwjaWs5bXgRA67WI3LL22VkoI9N7tWf0dV0WSgkQj1A5uMVI0kjQjx6Xo3seLyDWJCz9QC9oEDTeiTkwjLFwkghdUAMkYeD7QrUrtqv2SFBgIn8hudCkjymj0bNS1vQlofbzJlFgI6gAmBshzVhpTsoudB_PK9nnA84TtG21qIchgBfZKDt6N4lNyM71ZnqomRJsM59bP8GVwoeXrvZlK94PWKQxaQO6E-m5BciMDRkDEDkBcXUCLcZYZ2IdgWwVsMvrpj9fRJBjykzV6GhvJPk8Kl9A6ie-LlQcy2lbuHXZ2hr9j2Lok%2C&nid=69747144&ogV=-6']

            #time.sleep(60) #для регистрации в первый раз, зарегаться и ждать окончания выполнения программы
            if clean:
                page = make_screenshot(page, output_image_path="Agent_Basket/artifacts/screen0.png")

                page = click(
                    page=page,
                    screenshot_path=f"Agent_Basket/artifacts/screen0.png",
                    user_query="Найди координаты середины иконки 'Корзина' в формате [x, y].",
                    client_openai=self.client,
                    model_id=self.model,
                    output_image_path=f"Agent_Basket/artifacts/click_screen0.png",
                    pretty_click=False
                )

                page = make_screenshot(page, output_image_path="Agent_Basket/artifacts/screen1.png")

                page = click(
                    page=page,
                    screenshot_path=f"Agent_Basket/artifacts/screen1.png",
                    user_query="Найди координаты центра кнопки 'Удалить' в формате [x, y].",
                    client_openai=self.client,
                    model_id=self.model,
                    output_image_path=f"Agent_Basket/artifacts/click_screen1.png",
                    pretty_click=False
                )

                page = make_screenshot(page, output_image_path="Agent_Basket/artifacts/screen2.png")
                page = click(
                    page=page,
                    screenshot_path=f"Agent_Basket/artifacts/screen2.png",
                    user_query="Найди координаты центра кнопки 'Удалить' во всплывающем окне в формате [x, y].",
                    client_openai=self.client,
                    model_id=self.model,
                    output_image_path=f"Agent_Basket/artifacts/click_screen2.png",
                    pretty_click=False
                )

            page = make_screenshot(page, output_image_path="Agent_Basket/artifacts/screen3.png")

            k = 4
            for u in urls:
                page = surf_to_page(page, u)
                page = make_screenshot(page, output_image_path=f"Agent_Basket/artifacts/screen{k}.png")
                page = click(
                    page=page,
                    screenshot_path=f"Agent_Basket/artifacts/screen{k}.png",
                    user_query="Найди координаты центра кнопки 'В корзину' в формате [x, y].",
                    client_openai=self.client,
                    model_id=self.model,
                    output_image_path=f"Agent_Basket/artifacts/click_screen{k}.png",
                    pretty_click=False
                )
                k += 1
                time.sleep(3)
            time.sleep(15)
            # Закрываем контекст (профиль сохранится!)
            context.close()


