# shopper/playwright_worker.py
import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from urllib.parse import quote_plus
from Agent_Marketplace.config import ARTIFACTS_DIR
from PIL import Image, ImageDraw
from io import BytesIO

Path(ARTIFACTS_DIR).mkdir(parents=True, exist_ok=True)

def draw_point_on_image_bytes(img_bytes, point, out_path, color=(255, 0, 0, 128)):
    """
    Нарисовать полупрозрачную метку на картинке и сохранить.
    point: (x, y) — абсолютные пиксели относительно изображения.
    img_bytes: bytes
    """
    im = Image.open(BytesIO(img_bytes)).convert("RGBA")
    overlay = Image.new("RGBA", im.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    w, h = im.size

    radius = max(8, int(min(w, h) * 0.05))
    x, y = point
    left_up = (x - radius, y - radius)
    right_down = (x + radius, y + radius)
    draw.ellipse([left_up, right_down], fill=color)

    cr = max(3, int(radius * 0.12))
    draw.ellipse([(x - cr, y - cr), (x + cr, y + cr)], fill=(0, 255, 0, 255))

    combined = Image.alpha_composite(im, overlay)
    combined.convert("RGB").save(out_path)
    return out_path

class YandexMarketScraper:
    def __init__(self, headless=False, viewport={"width": 1280, "height": 900}):
        self._play = sync_playwright().start()
        self._browser = self._play.chromium.launch(headless=headless)
        self._context = self._browser.new_context(viewport=viewport)
        self._page = self._context.new_page()
        self.counter = 0
        self.viewport_width = viewport["width"]
        self.viewport_height = viewport["height"]

    def close(self):
        try:
            self._page.close()
            self._context.close()
            self._browser.close()
            self._play.stop()
        except Exception:
            pass

    def _next_name(self):
        self.counter += 1
        return f"{int(time.time())}_{self.counter}"

    def screenshot_bytes(self):
        """Возвращает байты скриншота всей страницы"""
        return self._page.screenshot(full_page=True)

    def screenshot_save(self, prefix):
        """Сохраняет скриншот и возвращает путь к файлу"""
        fname = os.path.join(ARTIFACTS_DIR, f"{self._next_name()}_{prefix}.png")
        self._page.screenshot(path=fname, full_page=True)
        print(f"[screenshot] saved: {fname}")
        return fname

    def save_html(self, prefix):
        """Сохраняет HTML страницы и возвращает путь к файлу"""
        fname = os.path.join(ARTIFACTS_DIR, f"{self._next_name()}_{prefix}.html")
        try:
            html = self._page.content()
            with open(fname, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"[html] saved: {fname}")
            return fname
        except Exception as e:
            print("Failed to save HTML:", e)
            return None

    def open_home(self):
        """Открывает главную страницу Яндекс.Маркета"""
        self._page.goto("https://market.yandex.ru/", timeout=20000)
        time.sleep(1.0)
        return self.screenshot_save("home")

    def find_search_input_and_focus(self):
        """
        Находит поле поиска и фокусируется на нем.
        Возвращает True если успешно, False в противном случае.
        """
        # DOM-based надежные селекторы для поля поиска
        selectors = [
            "input[data-auto='search-input']",
            "input#header-search",
            "input[name='text']",
            "input[placeholder*='Найти']"
        ]
        
        for sel in selectors:
            try:
                el = self._page.query_selector(sel)
                if el and el.is_visible():
                    # Прокручиваем к элементу если нужно
                    el.scroll_into_view_if_needed()
                    # Фокусируемся на элементе
                    el.focus()
                    time.sleep(0.3)
                    return True
            except Exception as e:
                continue
        
        # Fallback: клик в область поиска
        try:
            self._page.mouse.click(600, 80)
            time.sleep(0.5)
            return True
        except Exception as e:
            print("Fallback click failed:", e)
            return False

    def input_search_and_wait(self, query):
        """
        Вводит поисковый запрос и ждет загрузки результатов.
        Предполагает, что поле поиска уже сфокусировано.
        """
        try:
            # Очищаем поле поиска
            self._page.keyboard.press("Control+a")
            self._page.keyboard.press("Delete")
            time.sleep(0.3)
            
            # Вводим запрос
            self._page.keyboard.type(query, delay=50)
            time.sleep(0.5)
            self._page.keyboard.press("Enter")
            
            # Ждем загрузки результатов
            try:
                self._page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                time.sleep(2.0)
                
            return self.screenshot_save("after_search")
        except Exception as e:
            print("Search input failed:", e)
            # Fallback: переход по URL
            try:
                search_url = f"https://market.yandex.ru/search?text={quote_plus(query)}"
                self._page.goto(search_url, timeout=15000)
                try:
                    self._page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    time.sleep(2.0)
                return self.screenshot_save("after_search_fallback")
            except Exception as e2:
                print("Fallback search failed:", e2)
                return None

    def next_page(self):
        """
        Переходит на следующую страницу результатов поиска.
        Возвращает путь к скриншоту или None при ошибке.
        """
        try:
            # Пытаемся найти кнопку "Следующая страница"
            next_button_selectors = [
                "a[data-autotest-id='pagination-next']", 
                "a[data-auto='pagination-next']",
                "button:has-text('Следующая')",
                "button:has-text('Вперед')"
            ]
            
            for selector in next_button_selectors:
                button = self._page.query_selector(selector)
                if button and button.is_visible() and not button.is_disabled():
                    button.click()
                    time.sleep(1.5)
                    return self.screenshot_save("next_page")
            
            # Fallback: ищем через визуальный анализ
            print("Не найдена кнопка следующей страницы через DOM, пробуем визуальный анализ")
            return self.screenshot_save("no_next_page")
            
        except Exception as e:
            print("Ошибка при переходе на следующую страницу:", e)
            return self.screenshot_save("next_page_error")

    def ask_model_for_coords(self, visual_agent, instruction):
        """
        Делает скриншот и запрашивает координаты у визуальной модели.
        instruction: инструкция для модели на русском языке
        Возвращает ответ модели в формате: 
        {
            "_raw": "сырой ответ модели",
            "parsed": { распарсенный JSON или None }
        }
        """
        try:
            # Делаем скриншот
            img_bytes = self.screenshot_bytes()
            
            # Получаем ответ от модели
            response = visual_agent.ask(img_bytes, instruction, image_format="png")
            
            # Пытаемся распарсить JSON из ответа
            if "_raw" in response and "parsed" not in response:
                raw_text = response["_raw"]
                parsed = None
                
                # Ищем JSON в ответе
                import json
                import re
                
                # Ищем первый JSON-объект в тексте
                json_match = re.search(r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})', raw_text)
                if json_match:
                    try:
                        parsed = json.loads(json_match.group(1))
                    except json.JSONDecodeError:
                        pass
                
                response["parsed"] = parsed
            
            return response
            
        except Exception as e:
            print("Ошибка при запросе к визуальной модели:", e)
            return {
                "_raw": str(e),
                "parsed": None,
                "error": True
            }

    def click_at_abs(self, abs_x, abs_y):
        """
        Кликает по абсолютным координатам на странице.
        abs_x, abs_y: абсолютные координаты в пикселях относительно всей страницы
        """
        try:
            # Получаем текущую прокрутку
            scroll = self._page.evaluate("() => ({scrollX: window.scrollX, scrollY: window.scrollY})")
            scroll_x = scroll.get("scrollX", 0)
            scroll_y = scroll.get("scrollY", 0)
            
            # Вычисляем координаты относительно viewport
            vx = abs_x - scroll_x
            vy = abs_y - scroll_y
            
            # Прокручиваем так, чтобы точка была в центре viewport
            self._page.evaluate("""
                (x, y) => {
                    window.scrollTo({
                        top: y - window.innerHeight/2,
                        left: x - window.innerWidth/2
                    });
                }
            """, abs_x, abs_y)
            time.sleep(0.3)
            
            # Пересчитываем viewport координаты после прокрутки
            scroll = self._page.evaluate("() => ({scrollX: window.scrollX, scrollY: window.scrollY})")
            vx = abs_x - scroll.get("scrollX", 0)
            vy = abs_y - scroll.get("scrollY", 0)
            
            # Двигаем мышь и кликаем
            self._page.mouse.move(vx, vy)
            time.sleep(0.1)
            self._page.mouse.click(vx, vy)
            time.sleep(0.8)
            
            # Сохраняем аннотированный скриншот
            post_bytes = self.screenshot_bytes()
            annotated_path = os.path.join(
                ARTIFACTS_DIR, 
                f"{self._next_name()}_click_at_{abs_x}_{abs_y}.png"
            )
            draw_point_on_image_bytes(post_bytes, (abs_x, abs_y), annotated_path)
            
            return annotated_path
            
        except Exception as e:
            print(f"Ошибка при клике по координатам ({abs_x}, {abs_y}):", e)
            return None

    def zoom_to_element(self, x_ratio, y_ratio):
        """
        Приближает область вокруг элемента для более точного взаимодействия.
        x_ratio, y_ratio: относительные координаты (0.0-1.0) центра элемента
        """
        try:
            # Получаем размеры страницы
            page_width = self._page.evaluate("document.documentElement.scrollWidth")
            page_height = self._page.evaluate("document.documentElement.scrollHeight")
            
            # Конвертируем в абсолютные координаты
            abs_x = int(x_ratio * page_width)
            abs_y = int(y_ratio * page_height)
            
            # Прокручиваем к элементу
            self._page.evaluate("""
                (x, y) => {
                    window.scrollTo({
                        top: y - window.innerHeight/2,
                        left: x - window.innerWidth/2
                    });
                }
            """, abs_x, abs_y)
            time.sleep(0.5)
            
            # Сохраняем скриншот для отладки
            return self.screenshot_save(f"zoom_to_{x_ratio:.2f}_{y_ratio:.2f}")
            
        except Exception as e:
            print(f"Ошибка при приближении к элементу ({x_ratio}, {y_ratio}):", e)
            return None

    def click_cards_from_model(self, visual_agent, instruction_for_cards, max_cards=3):
        """
        Запрашивает у модели координаты карточек и кликает по ним.
        instruction_for_cards: инструкция для модели на русском
        max_cards: максимальное количество карточек для клика
        
        Возвращает результаты в формате:
        {
            "results": [
                {
                    "clicked_index": 1,
                    "abs": [abs_x, abs_y],
                    "annotated": "путь/к/аннотированному_скриншоту.png",
                    "url": "URL страницы товара после клика"
                },
                ...
            ],
            "raw": "сырой ответ модели",
            "parsed": "распарсенный ответ модели"
        }
        """
        try:
            # Получаем координаты карточек от модели
            resp = self.ask_model_for_coords(visual_agent, instruction_for_cards)
            parsed = resp.get("parsed") or {}
            raw = resp.get("_raw")
            
            # Извлекаем карточки из ответа
            cards = []
            if isinstance(parsed, dict):
                cards = parsed.get("cards") or parsed.get("coordinates") or parsed.get("coords") or []
            elif isinstance(parsed, list):
                cards = parsed
            
            if not cards:
                return {
                    "error": "no_cards_found",
                    "raw": raw,
                    "parsed": parsed
                }
            
            # Получаем размеры изображения для конвертации координат
            img_bytes = self.screenshot_bytes()
            im = Image.open(BytesIO(img_bytes))
            img_w, img_h = im.size
            
            results = []
            
            # Кликаем по каждой карточке
            for i, card in enumerate(cards[:max_cards]):
                # Извлекаем координаты
                x_ratio = y_ratio = None
                
                if isinstance(card, dict):
                    # Поддержка разных форматов координат
                    for key in ["x_ratio", "x", "x_rel"]:
                        if key in card and 0.0 <= card[key] <= 1.0:
                            x_ratio = card[key]
                            break
                    for key in ["y_ratio", "y", "y_rel"]:
                        if key in card and 0.0 <= card[key] <= 1.0:
                            y_ratio = card[key]
                            break
                elif isinstance(card, (list, tuple)) and len(card) >= 2:
                    x_ratio, y_ratio = card[0], card[1]
                
                if x_ratio is None or y_ratio is None:
                    continue
                
                # Конвертируем в абсолютные пиксели
                abs_x = int(round(x_ratio * img_w))
                abs_y = int(round(y_ratio * img_h))
                
                # Кликаем по карточке
                annotated = self.click_at_abs(abs_x, abs_y)
                
                # Ждем загрузки страницы товара
                time.sleep(1.5)
                
                # Сохраняем URL страницы товара
                try:
                    product_url = self._page.url
                except Exception:
                    product_url = None
                
                # Возвращаемся на страницу результатов
                try:
                    self._page.go_back()
                    time.sleep(1.0)
                except Exception:
                    pass
                
                # Добавляем результат
                results.append({
                    "clicked_index": i + 1,
                    "abs": [abs_x, abs_y],
                    "annotated": annotated,
                    "url": product_url
                })
            
            return {
                "raw": raw,
                "parsed": parsed,
                "results": results
            }
            
        except Exception as e:
            print("Ошибка при клике по карточкам:", e)
            import traceback
            traceback.print_exc()
            return {
                "error": str(e),
                "results": []
            }