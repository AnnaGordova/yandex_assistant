# test_price_filter.py
import json5

from Agents.web_agent.agent import get_agents
from Agents.web_agent.web_tools import init_session, SaveCandidateTool
from Agents.web_agent.web_tools.web_tools import WebAgent  # только ради type hints, можно не импортить

def test_save_cand():
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

def test_cart():
    agent, web_agent = get_agents(show_browser=True)

    urls = [
        r"https://market.yandex.ru/card/podushka-podstavka-dlya-nog-podporka-chernaya-dlya-doma-i-raboty-valik-podstavka-dlya-pedikyura-opora-dlya-nog/101461812885?do-waremd5=Zrg5knPE3l1tzgqALLeO_A&cpc=n4H8H-GUPNCdCC0TgU1Zzt0vGMu7phY9_55EGyIrBGcPerGZLWw-GinWSv8KXrgC79lcw3kNLrD13kByNNGoZZOvoipKa3hBaKszS04sKWPeWiiAQuZzXUvhZ3SZ-y7BKyZl7hrxWs_pjGwHVEsGoDAZUlBGTd9QHxWyWuvrzAzau-5u9Tx9p2m0zwKDSHHe-MX4DtUbApVMbblG4v0GF16Ej78e4lI0JLRFm64g2e96mKHaPQR0I31FRdPzWjRWhpcZxlJ6nhuqC3tb90Qw4vu9zULdVLIO2Pi-hjuHj1an4xnI6htg0fD1dTCSYa4UCXd3wELIpgc0-mwQi2DaIpVHL0hVQjCYALf4eLOYZJuq3NcFJNH4l1YFc8ZkgrA5RNzaEuf8qsUHMhp47xtdg-4_c__4iKwJTmXn0jymhqtrpGr4zVUzS3zeuUA1hDi13B70Z_IrenOY1BtI6oTdZpAJ0AfyJwPS1Kz914PBW1NQesBFdDcfUtkNNI933-629dj2qonvPLTEk8pLFzqq2Ys0BUd6Ed1PzLbZEIiV0NzRZXw38dFP29beIh2lIWMtxRWUVCwwxZq5vI3YBgv0Q0II2Go-g8Nj22EZiHph7CiPzqUQOuZOZmlmpOtMBlNb11OOnixXzYEseHb_SeVZ3iOermWd-2D8HDsWXYArxub5vDWbboOy2HSd-uwW40D-&ogV=-6",
        r"https://market.yandex.ru/card/massazhnaya-podstavka-dlya-nog-pod-stol-dlya-detey-i-vzroslykh-seryy/4495690141?do-waremd5=AXX87ZAvwSSFQ-dX5RPLwQ&sponsored=1&cpc=kwo_DbrWjC6T3LdpyW2WoW6cdhOMmzNW73h7D5fg1SjAixX_W-woHYDczrfsrf7EzGzdgDQRIl8XzyuoZXMwSepYo5QkhWofzH18U6EVuS9pBJQZueqf_fbX_Bqu-9oP3Z7gis4keKCy7P_JsaumMrKPlKv30LFla4Rg-tZVhxZ6j6iwTaN9OAt7BLb_S9BZpzMYvD4zDEeWlHN6uLeIrzTAQoCbi_JRzpZtn9MX1KLIrRal9GLyUVs4RdoIGvhwxmR2EcmsbiltMEebmmB4xLcgLY7wfciHnZr6PO1eDpTh2fQqCpLnB2AJxrU8i7fTHTYnitJf6SICbOXVEs8sG5GuSCBRu7mvVCpwR9X17eaMgP5suFpsANvdtSvi5w8YIwylBlgPVdRec05qIKp_fOSa4MvpHySdwSVwYvsoNfXMKQ1aiOa2IhP7CrtC6W1KaBsLVhaaf2nHbnKkg-hw8_7bA63qcQ9-eBw6fuQ6tUaFcWRisVt2QBFlXknag4zq1DcnnA5V6qmv060lFPlkgw%2C%2C&ogV=-6",
    ]

    share_url = web_agent.add_products_to_cart_and_get_share_link(urls, clear_before=True)
    print("Ссылка на корзину:", share_url)
if __name__ == "__main__":
    test_cart()
