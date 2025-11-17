# web_agent/web_tools/web_tools.py
from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime

from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError, Locator

from web_agent.web_tools.utils import _draw_click_marker, get_screen_size

_WEB_AGENT_SINGLETON: Optional["WebAgent"] = None



class WebAgent:
    """
    Обёртка над Playwright для управления браузером + набор действий,
    которые используют tools из web_tools/__init__.py
    """

    def __init__(
        self,
        headless: bool = False,
        url: str = "https://market.yandex.ru/",
        slow_mo_ms: int = 1000,
        viewport: Tuple[int, int] = None,
        user_agent: Optional[str] = None,
        screenshot_path: Path = Path("web_agent/screenshots"),
        browser_type: str = "chromium",
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
        context_kwargs = {
            "viewport": {"width": w, "height": h},
        }
        if self.user_agent:
            context_kwargs["user_agent"] = self.user_agent

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
    ) -> Path:
        """
        x, y – координаты в диапазоне [0, 1000] относительно ТЕКУЩЕГО viewport’а.
        Если сайт открыл карточку в новой вкладке, мы берём её URL,
        закрываем новую вкладку и переходим на этот URL в текущей.
        """
        # Нормализуем вход
        x = max(0, min(1000, int(x)))
        y = max(0, min(1000, int(y)))

        # Берём реальный размер viewport’а
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
            # Пытаемся поймать popup (новую вкладку)
            with self._context.expect_page(timeout=2000) as new_page_info:
                self.page.mouse.click(px, py, button=button, click_count=click_count)
            new_page = new_page_info.value
        except PlaywrightTimeoutError:
            # Никакой новой вкладки не появилось — обычный клик
            self.page.mouse.click(px, py, button=button, click_count=click_count)

        if new_page is not None:
            # Карточка открылась в новой вкладке: забираем URL и закрываем её
            try:
                new_page.wait_for_load_state("domcontentloaded", timeout=15000)
            except PlaywrightTimeoutError:
                pass

            target_url = new_page.url
            try:
                new_page.close()
            except Exception:
                pass

            # Переходим на этот же URL в текущей вкладке
            if target_url:
                try:
                    self.page.goto(target_url, wait_until="domcontentloaded", timeout=15000)
                except PlaywrightTimeoutError:
                    pass
        else:
            # Навигация в той же вкладке (или просто клик без навигации)
            try:
                self.page.wait_for_load_state("domcontentloaded", timeout=5000)
            except PlaywrightTimeoutError:
                pass

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

    def set_price_filter(self, min_price: int | None, max_price: int | None) -> Path:
        """
        Устанавливает фильтр цены на Яндекс.Маркете.
        Ориентируется на инпуты вида
        input#range-filter-field-glprice_*_min и *_max.
        """
        def _fill(locator: Locator, value: int):
            locator.click()
            locator.fill(str(value))     # fill сам очистит поле
            self.page.wait_for_timeout(200)
            locator.press("Enter")

        try:
            # Сначала работаем в блоке фильтра цены, если он есть
            price_scope = self.page.locator('[data-zone-name="price"]')
            if price_scope.count() == 0:
                price_scope = self.page

            if min_price is not None:
                min_input = price_scope.locator(
                    'input[id^="range-filter-field-glprice_"][id$="_min"]'
                ).first
                if min_input.count() == 0:
                    # fallback: placeholder "от"
                    min_input = price_scope.locator("input[placeholder*='от']").first
                if min_input.count() > 0:
                    _fill(min_input, min_price)

            if max_price is not None:
                max_input = price_scope.locator(
                    'input[id^="range-filter-field-glprice_"][id$="_max"]'
                ).first
                if max_input.count() == 0:
                    # fallback: placeholder "до"
                    max_input = price_scope.locator("input[placeholder*='до']").first
                if max_input.count() > 0:
                    _fill(max_input, max_price)

            # ждём, пока выдача перерисуется
            try:
                self.page.wait_for_load_state("domcontentloaded", timeout=10000)
            except PlaywrightTimeoutError:
                pass
            self.page.wait_for_timeout(800)

        except PlaywrightTimeoutError:
            pass

        return self.screenshot(prefix="price")


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
        )
    return _WEB_AGENT_SINGLETON


def close_agent() -> None:
    global _WEB_AGENT_SINGLETON
    if _WEB_AGENT_SINGLETON is not None:
        _WEB_AGENT_SINGLETON.close()
        _WEB_AGENT_SINGLETON = None
