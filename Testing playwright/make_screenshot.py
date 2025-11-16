from playwright.sync_api import sync_playwright


def sync_work():
    # открыть соединение
    with sync_playwright() as p:
        # инициализация браузера (без видимого открытия браузера)
        # browser = p.chromium.launch()

        # инициализация браузера (с явным открытием браузера)
        browser = p.chromium.launch(headless=False)
        # инициализация страницы
        page = browser.new_page()
        # переход по url адресу:
        page.goto('https://market.yandex.ru/search?text=рубашка%20гавайская%20мужская&hid=53546043&hid=53546173&rs=eJwzusGoNImRy-Biw8XmCxsvbLjYcWHXhQ0KFzZf2HBhExDvvNgIErjYr3BhD1DFNhhX4Pn1dnYlFg4hAUkgySDAACE1GLJINqqKw9DEwsDU0tKogXF9-xHJLkYmDoYqVo7dM45IbmBkeMHI-ImRj4NBgkEBJKKwd-YRyb-MLRf47JuYuDhAzhB4ASR6mSYctLOfytTEbW6_ggmkEgBko2d-&rt=11&glfilter=14805991%3A14805992')
        # сделать скриншот
        page.screenshot(path='second.png')
        browser.close()

        
sync_work()

