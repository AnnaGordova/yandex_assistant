"""
Web Agent — единый экземпляр Playwright-агента для работы с веб-страницами

Возможности:
- Открывает браузер и один раз загружает https://www.wildberries.ru/
- Гарантирует «стабильное» состояние страницы (ждёт не только load, но и затухание динамических изменений DOM)
- Делает скриншот текущего состояния страницы
- Клик по координатам (x, y)
- Ввод текста по координатам (x, y): сначала клик по (x, y), затем набор текста
- Скроллит страницу
- Ожидает указанное число миллисекунд
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional, Literal

from playwright.sync_api import Playwright, sync_playwright, Browser, BrowserContext, Page, \
    TimeoutError as PWTimeoutError, ViewportSize

class WebAgent:
    """Агент, создающий браузер с указанной страницей.

    Параметры конструктора:
      - headless: запускать ли браузер без UI (по умолчанию False — видимый браузер)
      - url: ссылка на веб-страницу
      - slow_mo_ms: замедление операций (мс) для наглядности
      - viewport: кортеж (width, height) или None для системного размера окна
      - screenshot_path: путь для сохранения скриншотов
    """

    def __init__(
        self,
        headless: bool = True,
        url: str = "https://market.yandex.ru/",
        slow_mo_ms: int = 1000,
        viewport: Optional[tuple[int, int]] = (1366, 900),
        user_agent: Optional[str] = None,
        screenshot_path: Path = Path("screenshots"),
    ) -> None:
        self._playwright_cm = sync_playwright()
        self._pw: Playwright = self._playwright_cm.__enter__()
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self.url = url
        self.screenshot_path = screenshot_path

        self._browser = self._pw.chromium.launch(
            headless=headless,
            slow_mo=slow_mo_ms or 0,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-extensions",
                "--no-default-browser-check",
                "--disable-notifications",
            ],
        )

        context_args = dict(
            locale="ru-RU",
            timezone_id="Europe/Moscow",
            ignore_https_errors=True,
        )
        if viewport:
            context_args["viewport"] = ViewportSize(width=viewport[0], height=viewport[1])

        if user_agent:
            context_args["user_agent"] = user_agent

        self._context = self._browser.new_context(**context_args)
        self._page = self._context.new_page()

        self._page.goto(self.url, wait_until="domcontentloaded")
        self.wait_until_stable(max_wait_ms=1000)

    # --------------------------- Публичные операции ---------------------------
    @property
    def page(self) -> Page:
        assert self._page is not None, "Страница ещё не инициализирована или агент закрыт"
        return self._page

    def wait_until_stable(self, max_wait_ms: int = 500, dom_quiet_ms: int = 500) -> None:
        """Ждёт «стабилизацию» страницы — не только load, но и паузу DOM-мутаций.

        Алгоритм:
          1) domcontentloaded
          2) load
          3) networkidle (best-effort)
          4) тишина DOM (мутаций нет подряд dom_quiet_ms)
        """
        p = self.page
        deadline = time.time() + max_wait_ms / 1000

        def _remaining() -> int:
            return max(0, int((deadline - time.time()) * 1000))

        try:
            p.wait_for_load_state("domcontentloaded", timeout=_remaining())
        except PWTimeoutError:
            pass
        try:
            p.wait_for_load_state("load", timeout=_remaining())
        except PWTimeoutError:
            pass
        # networkidle может не наступить из-за веб-сокетов; делаем best-effort
        try:
            p.wait_for_load_state("networkidle", timeout=min(1000, _remaining()))
        except PWTimeoutError:
            pass
        # Тишина DOM (MutationObserver):
        self._wait_for_dom_quiet(quiet_ms=dom_quiet_ms, timeout_ms=_remaining())

    def screenshot(self, screenshot_path: Optional[str | os.PathLike] = None, full_page: bool = False) -> Path:
        """Сохраняет скриншот страницы и возвращает путь к файлу."""
        p = self.page
        out_path = self._ensure_path(screenshot_path)
        self.wait_until_stable()
        p.screenshot(path=str(out_path), full_page=full_page, type="png")
        return out_path

    def click_and_screenshot(
        self,
        x: int,
        y: int,
        screenshot_path: Optional[str | os.PathLike] = None,
        button: Literal["left", "right", "middle"] = "left",
        click_count: int = 1,
        full_page: bool = False,
    ) -> Path:
        """Кликает мышью по координатам (x, y) в области страницы и делает скриншот.

        - Координаты указываются относительно видимой области страницы (viewport).
        - button: 'left' | 'right' | 'middle'
        - click_count: количество кликов (1 — обычный клик, 2 — даблклик)
        """
        p = self.page
        # Клик по координатам
        p.mouse.click(x, y, button=button, click_count=click_count)
        # Навигация/динамика после клика
        self.wait_until_stable()
        return self.screenshot(screenshot_path, full_page=full_page)

    def fill_and_screenshot(
        self,
        text: str,
        x: int = None,
        y: int = None,
        screenshot_path: Optional[str | os.PathLike] = None,
        press_enter: bool = False,
        typing_delay_ms: int = 10,
        clear_before: bool = True,
        full_page: bool = False,
    ) -> Path:
        """Кликает по координатам (x, y) для фокуса, вводит текст с клавиатуры и делает скриншот.

        - Координаты указываются относительно viewport.
        - clear_before: Ctrl+A + Delete перед вводом
        - press_enter: нажать Enter после ввода (например, для поиска)
        - typing_delay_ms: задержка между символами (мс) при наборе
        """
        p = self.page
        # Валидация координат относительно viewport (если он задан)
        if x is not None and y is not None:
            try:
                vs = p.viewport_size
                if vs is not None:
                    vw, vh = vs.get("width", 0), vs.get("height", 0)
                    if x < 0 or y < 0 or x >= vw or y >= vh:
                        raise ValueError(f"Coordinates out of viewport: ({x},{y}) not in [0..{vw - 1}]x[0..{vh - 1}]")
            except Exception:
                # Не прерываем — Playwright сам сообщит об ошибке, если координаты некорректны
                pass

            # 1) Клик по координатам, чтобы сфокусировать поле
            p.mouse.click(x, y)
            p.wait_for_timeout(300)

        # 2) Опциональная очистка: Ctrl+A + Delete
        if clear_before:
            try:
                p.keyboard.press("Control+A")
                p.keyboard.press("Delete")
            except Exception:
                pass

        # 3) Ввод текста
        if text:
            p.keyboard.type(text, delay=max(0, typing_delay_ms))

        # 4) Опционально нажать Enter
        if press_enter:
            p.keyboard.press("Enter")

        # 5) Подождать стабилизацию и сделать скриншот
        self.wait_until_stable()
        return self.screenshot(screenshot_path, full_page=full_page)

    def scroll_and_screenshot(
        self,
        delta_x: int = 0,
        delta_y: int = 800,
        screenshot_path: Optional[str | os.PathLike] = None,
        full_page: bool = False,
    ) -> Path:
        """Скроллит страницу и делает скриншот.

        - delta_x: Скролл по X
        - delta_y: Скролл по Y
        """
        p = self.page
        p.mouse.wheel(delta_x, delta_y)
        self.wait_until_stable()
        return self.screenshot(screenshot_path, full_page=full_page)

    def wait(
        self,
        ms: int = 1000,
        screenshot_path: Optional[str | os.PathLike] = None,
        full_page: bool = False,
    ) -> Path:
        """Ожидание и скриншот.

        - ms: Время в миллисекундах для ожидания
        """
        p = self.page
        p.wait_for_timeout(ms)
        return self.screenshot(screenshot_path, full_page=full_page)

    def go_back_and_screenshot(
            self,
            screenshot_path: Optional[str | os.PathLike] = None,
            full_page: bool = False,
    ) -> Path:
        """Возвращается на предыдущую страницу браузера и делает скриншот.

        - wait_until: событие загрузки страницы перед скрином.
        """
        p = self.page
        p.go_back()

        if self.url not in p.url:
            p.goto(self.url)

        self.wait_until_stable()
        return self.screenshot(screenshot_path, full_page=full_page)

    def get_current_url(self) -> str:
        """Возвращает текущий URL страницы."""
        return self.page.url

    def zoom_bbox_and_screenshot(
            self,
            x: int,
            y: int,
            width: int,
            height: int,
            screenshot_path: Optional[str | os.PathLike] = None,
    ) -> Path:
        """
        Приближает область (bbox) так, чтобы она заполняла весь viewport, и делает скриншот.

        Координаты bbox — в рамках текущего viewport.
        """
        p = self.page

        # Получаем текущее окно
        viewport = p.viewport_size
        if viewport is None:
            vpw = p.evaluate("() => window.innerWidth")
            vph = p.evaluate("() => window.innerHeight")
        else:
            vpw = viewport["width"]
            vph = viewport["height"]

        # Вычисляем масштаб
        scale = min(vpw / width, vph / height)

        # Координаты bbox -> сдвигаем страницу так, чтобы bbox оказался в (0, 0) перед масштабированием
        # То есть мы смещаем body, чтобы левая верхняя точка bbox была в углу экрана.
        translate_x = -x
        translate_y = -y

        # Устанавливаем масштаб и сдвиг
        p.evaluate(
            """({scale, tx, ty}) => {
                const body = document.body;
                body.style.transformOrigin = '0 0';
                body.style.transform = `translate(${tx}px, ${ty}px) scale(${scale})`;
            }""",
            {"scale": scale, "tx": translate_x, "ty": translate_y},
        )

        self.wait_until_stable()
        path = self.screenshot(screenshot_path, full_page=False)

        # Восстанавливаем нормальный масштаб
        p.evaluate("""() => { document.body.style.transform = 'none'; }""")
        return path

    def close(self) -> None:
        """Закрыть страницу/контекст/браузер и Playwright."""
        try:
            if self._page:
                self._page.close()
        except Exception:
            pass
        try:
            if self._context:
                self._context.close()
        except Exception:
            pass
        try:
            if self._browser:
                self._browser.close()
        except Exception:
            pass
        try:
            if self._playwright_cm:
                self._playwright_cm.__exit__(None, None, None)
        except Exception:
            pass
        finally:
            self._page = None
            self._context = None
            self._browser = None

    def _wait_for_dom_quiet(self, quiet_ms: int = 800, timeout_ms: int = 10000) -> None:
        """Ожидание «тишины» DOM — отсутствия мутаций в течение quiet_ms подряд.

        Реализовано через MutationObserver внутри страницы.
        """
        if timeout_ms <= 0:
            return
        try:
            self.page.evaluate(
                """
                (quietMs, timeoutMs) => {
                  return new Promise((resolve) => {
                    let done = false;
                    const cleanup = () => { if (!done) { done = true; observer.disconnect(); clearTimeout(timeout); resolve(true); } };
                    const observer = new MutationObserver(() => {
                      clearTimeout(quietTimer);
                      quietTimer = setTimeout(cleanup, quietMs);
                    });
                    observer.observe(document, { subtree: true, childList: true, attributes: true, characterData: true });
                    // Если мутаций нет — всё равно сработает через quietMs
                    let quietTimer = setTimeout(cleanup, quietMs);
                    const timeout = setTimeout(cleanup, timeoutMs);
                  });
                }
                """,
                quiet_ms,
            )
        except Exception:
            pass

    def _ensure_path(self, screenshot_path: Optional[str | os.PathLike]) -> Path:
        if screenshot_path:
            p = Path(screenshot_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            if p.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
                p = p.with_suffix(".png")
            return p
        else:
            self.screenshot_path.mkdir(parents=True, exist_ok=True)
            ts = time.strftime("%Y%m%d-%H%M%S")
            return self.screenshot_path / f"ym-{ts}.png"


# --------------------------- Модульный синглтон ---------------------------
_agent_singleton: Optional[WebAgent] = None


def get_agent(
    headless: bool = False,
    url: str = "https://market.yandex.ru/",
    slow_mo_ms: int = 1000,
    viewport: Optional[tuple[int, int]] = (1000, 1000),
    user_agent: Optional[str] = None,
    screenshot_path: Path = Path("web-tools/screenshots"),
) -> WebAgent:
    """Возвращает единый экземпляр агента (создаётся при первом вызове).

    Повторные вызовы возвращают уже созданный экземпляр, тем самым браузер/страница
    используются повторно в рамках процесса Python.
    """
    global _agent_singleton
    if _agent_singleton is None:
        _agent_singleton = WebAgent(
            headless=headless,
            url=url,
            slow_mo_ms=slow_mo_ms,
            viewport=viewport,
            user_agent=user_agent,
            screenshot_path=screenshot_path,
        )
    return _agent_singleton


def close_agent() -> None:
    """Явно закрыть singleton-агента и освободить ресурсы."""
    global _agent_singleton
    if _agent_singleton is not None:
        try:
            _agent_singleton.close()
        finally:
            _agent_singleton = None