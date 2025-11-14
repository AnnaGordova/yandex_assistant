# marketplace_agent.py
import json
import os
import time
from typing import Dict, List, Any
from Agent_Marketplace.playwright_worker import YandexMarketScraper

class MarketplaceAgent:

    def __init__(self, visual_agent, scraper: YandexMarketScraper):
        self.visual_agent = visual_agent
        self.scraper = scraper
        self.viewport_width = 1280
        self.viewport_height = 900
        self.max_pages = 3
        self.collected_items = []

    def _analyze_cards_on_page(self, page_num: int, max_items_needed: int) -> List[Dict]:
        """Анализирует карточки на текущей странице и возвращает подходящие"""
        instruction = (
            f"Страница {page_num}. Проанализируй ВСЕ карточки товаров. "
            "Для КАЖДОЙ карточки верни:\n"
            "- x_ratio/y_ratio центра карточки\n"
            "- название товара\n"
            "- цену как число\n"
            "- рейтинг (звезды)\n"
            "- количество отзывов\n"
            "- размер (если указан в описании)\n\n"
            "Формат (ТОЛЬКО JSON):\n"
            "{\n"
            "  \"cards\": [\n"
            "    {\n"
            "      \"x_ratio\": 0.x,\n"
            "      \"y_ratio\": 0.y,\n"
            "      \"title\": \"Название\",\n"
            "      \"price\": 123,\n"
            "      \"rating\": 4.5,\n"
            "      \"reviews_count\": 24,\n"
            "      \"size\": \"52 (RU)\"\n"
            "    }\n"
            "  ]\n"
            "}"
        )
        
        resp = self.scraper.ask_model_for_coords(
            self.visual_agent,
            instruction
        )
        
        # Сохранение артефакта
        os.makedirs("artifacts", exist_ok=True)
        fname = os.path.join(
            "artifacts",
            f"{int(time.time())}_page_{page_num}_analysis.json"
        )
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(resp, f, indent=2, ensure_ascii=False)
        
        cards = resp.get("parsed", {}).get("cards", [])
        return cards[:max_items_needed]  # Берем только нужное количество

    def _extract_product_details(self) -> Dict[str, Any]:
        """Извлекает детали товара со страницы карточки"""
        # Получение URL и скриншота страницы
        current_url = self.scraper._page.url
        screenshot_path = self.scraper.screenshot_save("product_page")
        
        # Инструкция для визуальной модели
        instruction = (
            "Это страница товара на Яндекс.Маркете. Верни ТОЛЬКО JSON со следующими данными:\n"
            "- 'description': полное описание товара (1-2 предложения)\n"
            "- 'image_url': прямая ссылка на основное изображение товара (атрибут src главного изображения)\n\n"
            "Формат:\n"
            "{\n"
            "  \"description\": \"Описание...\",\n"
            "  \"image_url\": \"https://...\"\n"
            "}"
        )
        
        # Анализ страницы товара
        resp = self.scraper.ask_model_for_coords(
            self.visual_agent,
            instruction
        )
        
        product_data = resp.get("parsed", {})
        return {
            "description": product_data.get("description", "Описание отсутствует"),
            "image_url": product_data.get("image_url", "")
        }

    def _process_single_product(self, card: Dict, item_id: int) -> Dict[str, Any]:
        """Обрабатывает одну карточку товара: кликает, собирает данные, возвращается"""
        try:
            # Конвертация координат
            abs_x = int(card["x_ratio"] * self.viewport_width)
            abs_y = int(card["y_ratio"] * self.viewport_height)
            
            # Клик по карточке
            self.scraper.click_at_abs(abs_x, abs_y)
            time.sleep(1.5)
            
            # Извлечение данных со страницы товара
            product_details = self._extract_product_details()
            
            # Возврат на страницу результатов
            self.scraper._page.go_back()
            time.sleep(1.0)
            
            # Формирование полных данных товара
            return {
                "Id": item_id,
                "Name": card.get("title", "Без названия"),
                "Link": self.scraper._page.url,  # URL после возврата
                "Description": product_details["description"],
                "Price": card.get("price", 0),
                "Picture": product_details["image_url"],
                "Rating": int(card.get("rating", 0) * 10),  # 4.5 -> 45
                "AmmountOfReviews": card.get("reviews_count", 0),
                "size": card.get("size", ""),
                "CountOfProduct": 1
            }
        except Exception as e:
            print(f"Ошибка обработки товара: {str(e)}")
            try:
                self.scraper._page.go_back()
                time.sleep(0.5)
            except:
                pass
            return None

    def _search_and_collect_items(self, query: str, max_items: int = 3) -> List[Dict]:
        """Основной цикл поиска для одного запроса"""
        self.collected_items = []
        current_page = 1
        
        # 1. Выполнение поиска
        self.scraper.find_search_input_and_focus()
        self.scraper.input_search_and_wait(query)
        
        # 2. Анализ страниц до получения нужного количества товаров
        while current_page <= self.max_pages and len(self.collected_items) < max_items:
            print(f"Анализ страницы {current_page} для запроса: {query}")
            items_needed = max_items - len(self.collected_items)
            
            # Анализ карточек на странице
            cards = self._analyze_cards_on_page(current_page, items_needed)
            
            # Сбор деталей для каждой карточки
            for card in cards:
                if len(self.collected_items) >= max_items:
                    break
                
                item_id = len(self.collected_items) + 1
                product_data = self._process_single_product(card, item_id)
                
                if product_data:
                    self.collected_items.append(product_data)
                    print(f"Добавлен товар: {product_data['Name']}")
            
            # Переход на следующую страницу если нужно
            if len(self.collected_items) < max_items and current_page < self.max_pages:
                print(f"Переход на страницу {current_page + 1}")
                self.scraper.next_page()
                time.sleep(1.5)
            
            current_page += 1
        
        return self.collected_items[:max_items]

    def process_request(self, request: Dict[str, Any]) -> str:
        """
        Основной метод обработки запроса
        request: {
            'status': 'ok', 
            'queries': ['женская пляжная футболка синяя размер М', 'женские пляжные шорты зеленые размер L']
        }
        """
        try:
            # Проверка формата запроса
            if "queries" not in request or not isinstance(request["queries"], list):
                return json.dumps({
                    "error": "Некорректный формат запроса. Ожидается объект с полем 'queries' (список строк)",
                    "items": []
                }, ensure_ascii=False)
            
            all_items = []
            total_collected = 0
            
            # Обработка каждого запроса
            for idx, query in enumerate(request["queries"]):
                print(f"Обработка запроса {idx+1}/{len(request['queries'])}: {query}")
                
                # Поиск и сбор товаров для текущего запроса (максимум 1 товар на запрос)
                items = self._search_and_collect_items(query, max_items=1)
                
                # Добавляем товары в общий результат
                if items:
                    all_items.append({
                        "query": query,
                        "items": items[:1]  # Берем не более 1 товара на запрос
                    })
                    total_collected += len(items)
                
                # Ограничение на общее количество товаров (максимум 3)
                if total_collected >= 3:
                    break
            
            # Формирование результата
            result = {"items": []}
            item_counter = 1
            
            for query_group in all_items:
                for item in query_group["items"]:
                    result["items"].append({
                        "Id": item_counter,
                        "Name": item["Name"],
                        "Link": item["Link"],
                        "Description": item["Description"],
                        "Price": item["Price"],
                        "Picture": item["Picture"],
                        "Rating": item["Rating"],
                        "AmmountOfReviews": item["AmmountOfReviews"],
                        "size": item["size"],
                        "CountOfProduct": item["CountOfProduct"]
                    })
                    item_counter += 1
            
            # Ограничение на 3 товара
            result["items"] = result["items"][:3]
            
            # Добавляем информацию об исходных запросах для отладки
            result["original_queries"] = request["queries"]
            
            return json.dumps(result, ensure_ascii=False, indent=2)
        
        except Exception as e:
            error_msg = f"Критическая ошибка: {str(e)}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            return json.dumps({
                "error": error_msg,
                "items": [],
                "original_queries": request.get("queries", [])
            }, ensure_ascii=False)