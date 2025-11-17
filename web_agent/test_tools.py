# test_price_filter.py
from web_agent.web_tools import init_session
from web_agent.web_tools.web_tools import WebAgent  # только ради type hints, можно не импортить

def main():
    # откроем поиск по какому-нибудь запросу
    agent: WebAgent = init_session(
        headless=False,
        url="https://market.yandex.ru/card/zarina-kurtka-muzhskaya-tsvet-temno-korichnevyy-razmer-m-zr2504042204-27/103760691099?do-waremd5=6fHRwCk6vSgpA2zdpJehLg&cpc=myQee6t3RMNv3dKVf5iicFdr46E4FnR0v_gDh_QPY3DNkxE6KY0BetM-3CBemESi1mmAGTJDuot-vw3eX-S56FgLHv-vAyy_Ka1nX01mXcaGMJ0A3QgIytXPvCUFz1pYZOQ41P0BUhFNKZKwD0DbsxtOnTOv_-bhmrAsR7dq7pgJcR4-sXZ2OvT6gpO410eeAyq3FQEPBspzPVL8uZO38y-QIoIdWxG4YWN0kvHHOUNjWo4QtZ3Z_dw-Sv_iXkt6lgtUsn_yFDlFAStrklwTlTaBoo3fWGdhYWUEz_YoDctFwSkQ2-YcgIUJsX9tTIGlWnHMEtFgfYpS-W491UZqRJ9gEUADtJITSo9gVO7X7I00E1dbnPzeB0F47MNazDShKj4iT_dqLcbKVRgMnAivRum0iKh4n06bXiHQx6PChalJJ26-3z1-AIxfFOLFL6frIldzVTUkjZ_Wj4pRjg3P-nX3-9ql7W8vKjeJeLQODcPKGpjSJu0mjIeZ9abYXbUa-cRSibeicNn4zJbd3Ta7CMtYP398Ipf4YZyjgAVTljhEKsx0vG-bqCwhzlOPeDR6azNqceeZzKykfUAVWrbkAuNbuIx7aasuoAx_BwuDIqeeRZg-wyA2Q1pmoKEmUNHGvWQw88NvS1bwu5rUuFrQZahQXiUxHbIhu_I324Od6Oi9nVpOLuivNv4xl1XqO3ny4I6q7Nd5TQIobTQTTc7LXg%2C%2C&nid=68619233&ogV=-6",
        slow_mo_ms=300,
    )

    print("Браузер открыт. Сейчас попробуем выставить цену 1500–7000 руб.")
    screenshot_path = agent.return_image_url(card_name="Куртка Zarina Man")
    print("Скрин после применения фильтра:", screenshot_path)

    input("Посмотри в окно. Нажми Enter, чтобы закрыть.")
    agent.close()

if __name__ == "__main__":
    main()
