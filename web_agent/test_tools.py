# test_price_filter.py
from web_agent.web_tools import init_session
from web_agent.web_tools.web_tools import WebAgent  # только ради type hints, можно не импортить

def main():
    # откроем поиск по какому-нибудь запросу
    agent: WebAgent = init_session(
        headless=False,
        url="https://market.yandex.ru/search?text=кроссовки",
        slow_mo_ms=300,
    )

    print("Браузер открыт. Сейчас попробуем выставить цену 1500–7000 руб.")
    screenshot_path = agent.set_price_filter(min_price=1500, max_price=7000)
    print("Скрин после применения фильтра:", screenshot_path)

    input("Посмотри в окне, как отработал фильтр. Нажми Enter, чтобы закрыть.")
    agent.close()

if __name__ == "__main__":
    main()
