# web_agent/web_tools/web_tools.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Tuple, Sequence
from datetime import datetime

from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError, Locator

from web_agent.web_tools.utils import _draw_click_marker, get_screen_size

_WEB_AGENT_SINGLETON: Optional["WebAgent"] = None
AUTH_STATE_PATH =  Path(__file__).parents[1]/Path("auth/yandex_state.json")



class WebAgent:
    """
    Обёртка над Playwright для управления браузером + набор действий,
    которые используют tools из web_tools/__init__.py
    """

    def __init__(
        self,
        headless: bool = False,
        url: str = "https://market.yandex.ru/",
        slow_mo_ms: int = 0,
        viewport: Tuple[int, int] = None,
        user_agent: Optional[str] = None,
        screenshot_path: Path = Path("web_agent/screenshots"),
        browser_type: str = "chromium",
        storage_state_path: Optional[Path] = None,
    ):
        self.headless = headless
        self.start_url = url
        self.slow_mo_ms = slow_mo_ms
        self.viewport = viewport
        self.user_agent = user_agent
        self.screenshot_path = Path(screenshot_path)
        self.screenshot_path.mkdir(parents=True, exist_ok=True)

        # --- стартуем Playwright и выбираем движок ---
        self._playwright = sync_playwright().start()

        bt = browser_type.lower()
        browser_factory = {
            "chromium": self._playwright.chromium,
            "chrome": self._playwright.chromium,
            "edge": self._playwright.chromium,
            "firefox": self._playwright.firefox,
            "webkit": self._playwright.webkit,
        }.get(bt, self._playwright.chromium)

        launch_kwargs = {
            "headless": self.headless,
            "slow_mo": self.slow_mo_ms,
        }

        self._browser = browser_factory.launch(**launch_kwargs)
        print("browser launched")
        if self.viewport is None:
            self.viewport = get_screen_size()
        w, h = self.viewport
        print(f"viewport size: {w}x{h}")
        print(f"set slowmo: {slow_mo_ms} ms")
        context_kwargs = {
            "viewport": {"width": w, "height": h},
        }
        if self.user_agent:
            context_kwargs["user_agent"] = self.user_agent

        print(storage_state_path)
        if storage_state_path is not None and storage_state_path:
            context_kwargs["storage_state"] = storage_state_path
        print(context_kwargs)
        self._context = self._browser.new_context(**context_kwargs)
        self.page: Page = self._context.new_page()

        # НЕ ждём networkidle, иначе Яндекс может вечно грузиться
        self.page.goto(self.start_url, wait_until="domcontentloaded", timeout=15000)
        print("start page opened:", self.start_url)

    # ---------- служебное ----------

    def _make_screenshot_path(self, prefix: str = "ym") -> Path:
        ts = datetime.now().strftime("%Y%m%d-%H_%M_%S")
        filename = f"ym-{ts}-{prefix}.png"
        return self.screenshot_path / filename

    def screenshot(self, prefix: str = "ym") -> Path:
        path = self._make_screenshot_path(prefix)
        self.page.screenshot(path=str(path), full_page=False)
        return path

    def close(self):
        try:
            self._context.close()
        except Exception:
            pass
        try:
            self._browser.close()
        except Exception:
            pass
        try:
            self._playwright.stop()
        except Exception:
            pass

    # ---------- действия, которые вызывают tools ----------

    def click_and_screenshot(
            self,
            x: int,
            y: int,
            button: str = "left",
            click_count: int = 1,
            wait_after_ms: int = 400,
    ) -> Path:
        """
        x, y – координаты в диапазоне [0, 1000] относительно текущего viewport’а.
        Если сайт открыл карточку в новой вкладке, мы берём её URL,
        закрываем новую вкладку и переходим на этот URL в текущей.
        После клика ждём немного и делаем скриншот.
        """

        # Нормализуем вход
        x = max(0, min(1000, int(x)))
        y = max(0, min(1000, int(y)))

        vp = self.page.viewport_size
        if vp is None:
            vp = {
                "width": self.page.evaluate("() => window.innerWidth"),
                "height": self.page.evaluate("() => window.innerHeight"),
            }
        vw, vh = vp["width"], vp["height"]

        px = int(vw * x / 1000)
        py = int(vh * y / 1000)

        new_page = None
        try:
            with self._context.expect_page(timeout=2000) as new_page_info:
                self.page.mouse.click(px, py, button=button, click_count=click_count)
            new_page = new_page_info.value
        except PlaywrightTimeoutError:
            new_page = None

        if new_page is not None:
            try:
                new_page.wait_for_load_state("domcontentloaded", timeout=15000)
            except PlaywrightTimeoutError:
                pass

            target_url = new_page.url
            try:
                new_page.close()
            except Exception:
                pass
            if target_url:
                try:
                    self.page.goto(target_url, wait_until="domcontentloaded", timeout=15000)
                    try:
                        self.page.wait_for_load_state("networkidle", timeout=5000)
                    except PlaywrightTimeoutError:
                        pass
                except PlaywrightTimeoutError:
                    pass
        else:
            # Навигация в той же вкладке или просто клик по фильтру
            try:
                # если клик действительно триггерит загрузку, поймаем её
                self.page.wait_for_load_state("domcontentloaded", timeout=3000)
            except PlaywrightTimeoutError:
                pass

        # Даем верстке и фильтрам «устаканиться»
        self.page.wait_for_timeout(wait_after_ms)

        path = self.screenshot(prefix="click")
        _draw_click_marker(path, px, py)
        return path

    def fill_and_screenshot(
        self,
        text: str,
        press_enter: bool = True,
        clear_before: bool = True,
    ) -> Path:
        """
        Печатает текст в текущий сфокусированный инпут.
        Перед этим (опционально) очищает его.
        """
        if clear_before:
            # Ctrl+A, Delete
            self.page.keyboard.press("Control+A")
            self.page.keyboard.press("Delete")

        self.page.keyboard.type(text)

        if press_enter:
            self.page.keyboard.press("Enter")

        return self.screenshot(prefix="type")

    def scroll_and_screenshot(
        self,
        delta_x: int = 0,
        delta_y: int = 1000,
    ) -> Path:
        """
        Скроллит страницу и делает скриншот.
        delta_y > 0 – вниз, <0 – вверх (аналог wheel).
        """
        self.page.evaluate(
            "(args) => { window.scrollBy(args.dx, args.dy); }",
            {"dx": int(delta_x), "dy": int(delta_y)},
        )
        return self.screenshot(prefix="scroll")

    def wait(self, ms: int = 1000) -> Path:
        self.page.wait_for_timeout(ms)
        return self.screenshot(prefix="wait")

    def go_back_and_screenshot(self) -> Path:
        try:
            self.page.go_back(wait_until="domcontentloaded", timeout=15000)
        except Exception:
            # если назад нельзя – просто остаёмся
            pass
        return self.screenshot(prefix="back")

    def get_current_url(self) -> str:
        return self.page.url

    def zoom_bbox_and_screenshot(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> Path:
        """
        "Зум" области: вырезаем прямоугольник и возвращаем скрин только этой области.
        Все координаты в [0, 1000] относительно viewport.
        """
        vw, vh = self.viewport
        px = vw * x / 1000.0
        py = vh * y / 1000.0
        pw = vw * width / 1000.0
        ph = vh * height / 1000.0

        path = self._make_screenshot_path(prefix="zoom")
        self.page.screenshot(
            path=str(path),
            clip={"x": px, "y": py, "width": pw, "height": ph},
        )
        return path

    def return_image_url(self, card_name: str) -> str | None:
        """
        Находит URL изображения карточки по названию товара.

        Логика:
        - нормализуем название и alt: нижний регистр, ё -> е, убираем все кроме латиницы/кириллицы и цифр;
        - ищем <img> с alt, у которого нормализованный alt начинается
          с нормализованного card_name;
        - возвращаем src первого подходящего изображения или None.
        """

        safe_name = json.dumps(card_name)  # экранируем строку для JS

        js_code = f"""
           () => {{
               const original = {safe_name};

               function normalize(str) {{
                   return (str || '')
                       .toLowerCase()
                       .replace(/ё/g, 'е')
                       // оставляем латиницу, кириллицу и цифры, остальное выбрасываем
                       .replace(/[^a-z0-9а-я]+/g, '');
               }}

               const target = normalize(original);
               if (!target) return null;

               const imgs = Array.from(document.querySelectorAll('img[alt][src]'));
               let best = null;

               for (const img of imgs) {{
                   const alt = img.getAttribute('alt') || '';
                   const altNorm = normalize(alt);
                   if (!altNorm) continue;

                   // проверяем, что НОРМАЛИЗОВАННЫЙ alt начинается
                   // с НОРМАЛИЗОВАННОГО имени товара
                   if (altNorm.slice(0, target.length) === target) {{
                       best = img;
                       break;
                   }}
               }}

               return best ? best.src : null;
           }}
           """

        return self.page.evaluate(js_code)

    def set_price_filter(self, min_price: int | None, max_price: int | None) -> Path:
        """
        Устанавливает фильтр цены на Яндекс.Маркете.
        Ориентируется на инпуты вида
        input#range-filter-field-glprice_*_min и *_max.
        """

        def _fill(locator: Locator, value: int):
            self.page.wait_for_load_state("domcontentloaded", timeout=8000)
            locator.click()
            # на всякий случай подчистим поле
            locator.press("Control+A")
            locator.press("Delete")
            locator.fill(str(value))
            self.page.wait_for_timeout(400)
            locator.press("Enter")

        try:
            # --- MIN ---
            if min_price is not None:
                min_input = self.page.locator(
                    'input[id^="range-filter-field-glprice_"][id$="_min"]:visible'
                ).first
                if min_input.count() == 0:
                    # запасной вариант – placeholder "от"
                    min_input = self.page.locator(
                        'input[placeholder*="от"]'
                    ).first

                if min_input.count() > 0:
                    _fill(min_input, min_price)
                else:
                    print("set_price_filter: min input not found")

            # --- MAX ---
            if max_price is not None:
                max_input = self.page.locator(
                    'input[id^="range-filter-field-glprice_"][id$="_max"]:visible'
                ).first
                if max_input.count() == 0:
                    # запасной вариант – placeholder "до"
                    max_input = self.page.locator(
                        'input[placeholder*="до"]'
                    ).first

                if max_input.count() > 0:
                    _fill(max_input, max_price)
                else:
                    print("set_price_filter: max input not found")

            try:
                self.page.wait_for_load_state("domcontentloaded", timeout=10000)
            except PlaywrightTimeoutError:
                pass
            self.page.wait_for_timeout(800)

        except PlaywrightTimeoutError:
            pass

        return self.screenshot(prefix="price")

    def open_cart(self) -> None:
        """Открыть страницу корзины Маркета."""
        self.page.goto("https://market.yandex.ru/my/cart", wait_until="domcontentloaded", timeout=5000)
        self.page.wait_for_timeout(1000)

    def clear_cart(self, wait_ms: int = 500) -> None:
        """
        Очищает корзину: кликает по кнопкам удаления товаров.
        Использует data-auto="remove-button", как в твоём HTML.
        """
        self.open_cart()

        while True:
            remove_buttons = self.page.locator('[data-auto="remove-button"][role="button"]')
            count = remove_buttons.count()
            if count == 0:
                break

            # Удаляем по одному
            remove_buttons.first.click()
            self.page.wait_for_timeout(wait_ms)

    def add_products_to_cart_and_get_share_link(
        self,
        product_urls: Sequence[str],
        clear_before: bool = True,
        wait_after_click_ms: int = 1500,
    ) -> str:
        """
        1) При необходимости очищает корзину.
        2) Добавляет товары по списку URL карточек.
        3) Возвращает URL из кнопки 'Поделиться' в корзине.
        """

        if clear_before:
            self.clear_cart()

        for url in product_urls:
            print(f"[add_to_cart] Открываю {url}")
            self.page.goto(url, wait_until="domcontentloaded")
            self.page.wait_for_timeout(800)

            # Кнопка 'В корзину'
            add_btn = self.page.locator('button[data-auto="cartButton"]')
            if add_btn.count() == 0:
                # fallback: вдруг вёрстку поменяют, оставим чуть более общий селектор
                add_btn = self.page.locator('[data-auto="cartButton"]')

            if add_btn.count() == 0:
                raise RuntimeError(f"Не нашёл кнопку 'В корзину' для {url}")

            add_btn.first.click()
            print(f"[add_to_cart] Товар с {url} добавлен в корзину")

            self.page.wait_for_timeout(wait_after_click_ms)

        # 3. Открыть корзину и нажать 'Поделиться'
        self.open_cart()
        self.page.wait_for_timeout(3000)
        share_btn = self.page.get_by_text("Поделиться", exact=True)
        if share_btn.count() == 0:
            share_btn = self.page.locator('span:has-text("Поделиться")')

        if share_btn.count() == 0:
            raise RuntimeError("Не нашёл кнопку 'Поделиться' в корзине")

        share_btn.first.click()

        self._context.grant_permissions(
            ["clipboard-read", "clipboard-write"],
            origin="https://market.yandex.ru",
        )

        share_btn.first.click()
        self.page.wait_for_timeout(500)

        # прочитать ссылку из буфера
        share_url = self.page.evaluate("navigator.clipboard.readText()")
        print(f"[add_to_cart] Ссылка для 'Поделиться': {share_url}")
        return share_url

# ---------- singleton-хелперы, которые дергает __init__.py ----------

def get_agent(
    headless: bool = False,
    url: str = "https://market.yandex.ru/",
    slow_mo_ms: int = 0,
    viewport: Optional[Tuple[int, int]] = None,
    user_agent: Optional[str] = None,
    screenshot_path: Path = Path("web_agent/screenshots"),
    browser_type: str = "chromium",
) -> WebAgent:
    global _WEB_AGENT_SINGLETON

    if viewport is None:
        # если вдруг не передали – на всякий случай зададим дефолт
        viewport = (1920, 1080)

    if _WEB_AGENT_SINGLETON is None:
        _WEB_AGENT_SINGLETON = WebAgent(
            headless=headless,
            url=url,
            slow_mo_ms=slow_mo_ms,
            viewport=viewport,
            user_agent=user_agent,
            screenshot_path=screenshot_path,
            browser_type=browser_type,
            storage_state_path=AUTH_STATE_PATH,
        )
    return _WEB_AGENT_SINGLETON


def close_agent() -> None:
    global _WEB_AGENT_SINGLETON
    if _WEB_AGENT_SINGLETON is not None:
        _WEB_AGENT_SINGLETON.close()
        _WEB_AGENT_SINGLETON = None
