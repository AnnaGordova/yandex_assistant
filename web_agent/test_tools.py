# test_price_filter.py
import json5

from web_agent.web_tools import init_session, SaveCandidateTool
from web_agent.web_tools.web_tools import WebAgent  # только ради type hints, можно не импортить

def main():
    agent: WebAgent = init_session(
        headless=False,
        url="https://market.yandex.ru/card/televizor-tcl-32-s4k-qled-hd-hdr-google-tv-smart-tv-32-dyuyma/4718313216?do-waremd5=i4yTzeK_XkG77Nb_gViXyg&cpc=57PtH06gizwPEVHmOOcM1emr0maYEVnrjGhixg7epNgLTUfSCiDeIUhs6D05RdbI0_136ef-HxkZZReGMDwEUK2SMPYHyZz66nbU6lCFh7Nilxo_c7GrGoi-GSkd9cgPLxU5R_mU8KkInNp4fL3GgudS9Hl4pkjMic5Qi_6hmpV9pC2lNPXzmHBMjd7B4JoPkJjywckUGimg93WIj7yny6nLl2jHSYjG9iFo13VBsDtDvO70B1eDUvturOnkWBCm2sql0YSk8qpCNkettUBua7JOsTtI1MSXcm8PgUQfFvMXbw4k7QxiucP6WMgmJrw6TP--VPBdkIJS61AzNIK1B-qFNRR2gECJ9TO9NrlXux3tcVoPZGLGnJH-x_JxpNzehGbINYR4-dbnNVRx5Ssarvn_-ZluN6ci26Mg-NZV4SMjNNET7dhefk8F-AfEaNUhzvGMRNWkGi-GHW93OABITg%2C%2C&ogV=-6",
        slow_mo_ms=300,
    )

    print("Браузер открыт. Сейчас попробуем выставить цену 1500–7000 руб.")
    args = '{"description": "{\"model\": \"TCL 32\" S4K QLED HDR SMART TV\", \"brand\": \"TCL\", \"price\": 15839, \"size\": \"32\", \"smart_tv\": true, \"features\": [\"QLED\", \"HDR\", \"Google TV\"], \"rating\": 4.8, \"reviews\": 182, \"reason\": \"Подходит по диагонали (32\"), является Smart TV с поддержкой Google TV, имеет современные технологии QLED и HDR, цена в рамках бюджета.\"}","index": 2,  "product_name": "Телевизор TCL 32\" S4K QLED HDR SMART TV"}'.replace('\\', '')
    print(dict(json5.loads(args)))
    screenshot_path = SaveCandidateTool(**args)
    print("Скрин после применения фильтра:", screenshot_path)

    input("Посмотри в окно. Нажми Enter, чтобы закрыть.")
    agent.close()

if __name__ == "__main__":
    main()
