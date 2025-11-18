# auth_bootstrap.py
from pathlib import Path
from playwright.sync_api import sync_playwright

AUTH_STATE_PATH = Path("auth/yandex_state.json")


def main():
    AUTH_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        page.goto("https://market.yandex.ru/", wait_until="domcontentloaded")
        print("Открылся Яндекс.Маркет. Залогинься, как обычно.")
        input("Когда закончишь авторизацию (увидишь, что ты залогинен), нажми Enter...")

        context.storage_state(path=str(AUTH_STATE_PATH))
        print(f"Состояние сессии сохранено в {AUTH_STATE_PATH}")

        browser.close()


def check():
    print("AUTH_STATE_PATH:", AUTH_STATE_PATH, "exists:", AUTH_STATE_PATH.exists())

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)

        # ВАЖНО: storage_state передаётся сюда
        context = browser.new_context(storage_state=str(AUTH_STATE_PATH))

        page = context.new_page()
        page.goto("https://market.yandex.ru/", wait_until="domcontentloaded")

        input("Проверь, что ты залогинен. Нажми Enter для выхода...")

        browser.close()


# if __name__ == "__main__":
#     main()

if __name__ == "__main__":
    check()
