from pathlib import Path
from typing import Optional, List, Dict
import json5
from qwen_agent.llm.schema import ContentItem

from .web_tools import WebAgent, get_agent, close_agent
from qwen_agent.tools.base import BaseTool, register_tool

from logging import getLogger

logger = getLogger(__name__)


def init_session(
        headless: bool = False,
        url: str = "https://market.yandex.ru/",
        slow_mo_ms: int = 100,
        viewport: Optional[tuple[int, int]] = None,
        user_agent: Optional[str] = None,
        screenshot_path: Path = Path("web-tools/screenshots"),
        browser_type="chromium"
) -> WebAgent:
    agent = get_agent(
        headless=headless, url=url, slow_mo_ms=slow_mo_ms, viewport=viewport, user_agent=user_agent,
        screenshot_path=screenshot_path
    )

    return agent


def close_session() -> None:
    close_agent()


RESULT_STORE: Dict[int, dict] = {}


@register_tool("set_price_filter")
class SetPriceFilterTool(BaseTool):
    description = (
        "Устанавливает фильтр цены по минимальному и максимальному значению "
        "на странице маркетплейса и возвращает скриншот после применения фильтра."
    )
    parameters = [
        {
            "name": "min_price",
            "type": "integer",
            "required": False,
            "description": "Минимальная цена (рубли). Можно опустить, если нет ограничения снизу.",
        },
        {
            "name": "max_price",
            "type": "integer",
            "required": False,
            "description": "Максимальная цена (рубли). Можно опустить, если нет ограничения сверху.",
        },
    ]

    def call(self, params: str, **kwargs) -> List[ContentItem]:
        args = json5.loads(params) if params else {}
        min_price = args.get("min_price")
        max_price = args.get("max_price")

        agent = get_agent()
        path = agent.set_price_filter(min_price=min_price, max_price=max_price)
        return [ContentItem(image=str(path))]

@register_tool("save_candidate")
class SaveCandidateTool(BaseTool):
    description = (
        "Save the currently opened product page as a candidate under a given index. "
        "This tool performs an UPSERT for that index: if a candidate with this index already exists, "
        "it will be overwritten.\n"
        "For each candidate, the tool stores:\n"
        "- product_name: product title used to locate the image on the page,\n"
        "- url: current product page URL (taken automatically),\n"
        "- image_url: URL of the product image (if found),\n"
        "- description: JSON string with detailed product attributes.\n"
        "\n"
        "The 'description' STRING *MUST* be a valid JSON object with the following fields:\n"
        "- price: number (final price in RUB),\n"
        "- rating: number from 0 to 5,\n"
        "- ammountOfReviews: integer, number of reviews,\n"
        "- size: string with the selected size (or \"\" if not applicable),\n"
        "- countOfProduct: integer, how many items (usually 1),\n"
        "- reason: short text explaining why this product fits the user.\n"
        "You MAY add extra fields, but the keys above are REQUIRED and must use these exact names.\n"
        "Always send valid JSON here, never free-form text."
    )

    parameters = [
        {
            "name": "index",
            "type": "integer",
            "required": True,
            "description": (
                "Position of the product in the candidate list (1, 2, 3, ...). "
                "Reuse the same index to REPLACE an existing product."
            )
        },
        {
            "name": "description",
            "type": "string",
            "required": True,
            "description": (
                "JSON string with a structured description of the product. "
                "It MUST include: price, rating, ammountOfReviews, size, countOfProduct, reason. "
                "Example: "
                "{\"price\": 2499.0, \"rating\": 4.7, \"ammountOfReviews\": 123, "
                "\"size\": \"M\", \"countOfProduct\": 1, "
                "\"reason\": \"Лёгкие шорты до колена, подходят для прогулок летом\"}."
            ),
        },
        {
            "name": "product_name",
            "type": "string",
            "required": True,
            "description": (
                "Visible product name on the page (the bold text near the image). "
                "Used to find the correct product image URL."
            ),
        }
    ]

    def call(self, params: str, **kwargs) -> List[ContentItem]:
        args = json5.loads(params) if params else {}
        index = int(args.get("index", len(RESULT_STORE) + 1))
        raw_description = args.get("description", "").replace("\\", "")
        product_name = args.get("product_name", "").replace("\\", "")

        # 1) Парсим description из строки в объект
        if isinstance(raw_description, str):
            try:
                description_parsed = json5.loads(raw_description)
            except Exception:
                description_parsed = {"raw": raw_description}
        else:
            description_parsed = raw_description

        agent = get_agent()

        # 2) Пытаемся получить image_url, но НЕ падаем, если что-то пошло не так
        image_url = None
        try:
            if product_name:
                image_url = agent.return_image_url(card_name=product_name)
        except Exception as e:
            # тут можешь залогировать, если хочешь
            logger.warning("return_image_url failed for %r: %s", product_name, e)
            image_url = None

        url = agent.get_current_url()

        RESULT_STORE[index] = {
            "product_name": product_name,
            "url": url,
            "image_url": image_url,
            "description": description_parsed,
        }

        return [ContentItem(text=f"Saved candidate #{index}: {product_name} - {url}")]



@register_tool("click")
class ClickTool(BaseTool):
    description = (
        "Click on a specific point on the page using viewport coordinates."
        "- pass 'x' and 'y' explicitly in the JSON object."
        "- The JSON MUST be valid, for example: "
        "{'x': 130, 'y': 819, 'button': 'left', 'click_count': 1}."
        "- Use this tool only when you see on the screenshot where you want to click."
        "The tool returns a screenshot after performing the click."
    )
    parameters = [
        {
            'name': 'x',
            'type': 'integer',
            'description': (
                "X coordinate of the click position in viewport coordinates (0–1000). "
                "0 is the left edge, 1000 is the right edge."
            ),
            'required': True
        },
        {
            'name': 'y',
            'type': 'integer',
            'description': (
                "Y coordinate of the click position in viewport coordinates (0–1000). "
                "0 is the top edge, 1000 is the bottom edge."
            ),
            'required': True
        },
        {
            'name': 'button',
            'type': 'string',
            'description': (
                "Mouse button to use for the click. "
                "Allowed values: 'left' (default), 'right', 'middle'."
            ),
            'required': False
        },
        {
            'name': 'click_count',
            'type': 'integer',
            'description': (
                "Number of times to click at the given position: "
                "1 for a single click (default), 2 for a double click."
            ),
            'required': False
        },
    ]

    def call(self, params: str, **kwargs) -> List[ContentItem]:
        args = json5.loads(params)
        x, y = int(args['x']), int(args['y'])
        button = args.get('button', 'left')
        click_count = args.get('click_count', 1)

        agent = get_agent()
        path = agent.click_and_screenshot(
            x=x,
            y=y,
            button=button,
            click_count=click_count,
        )
        return [ContentItem(image=str(path))]


@register_tool("type_text")
class TypeTextTool(BaseTool):
    description = "BEFORE USING THIS TOOL YOU NEED TO CLICK THE FIELD. Tool to input text into current field. Optionally clears the input and presses Enter, then returns a screenshot. You can use that to fill search field for example."

    parameters = [
        {
            'name': 'text',
            'type': 'string',
            'description': 'Text to type into the focused field.',
            'required': True
        },
        {
            'name': 'press_enter',
            'type': 'boolean',
            'description': 'Press Enter after typing.',
            'required': False
        },
        {
            'name': 'clear_before',
            'type': 'boolean',
            'description': 'Clears input field before typing.',
            'required': False
        },
    ]

    def call(self, params: str, **kwargs) -> List[ContentItem]:
        args = json5.loads(params)
        text = args['text']
        press_enter = args.get('press_enter', True)
        clear_before = args.get('clear_before', True)

        agent = get_agent()
        path = agent.fill_and_screenshot(
            text=text,
            press_enter=press_enter,
            clear_before=clear_before,
        )
        return [ContentItem(image=str(path))]


@register_tool("scroll")
class ScrollTool(BaseTool):
    description = "Scrolls the page by deltaX and deltaY and returns a screenshot."
    parameters = [
        {
            'name': 'delta_x',
            'type': 'integer',
            'description': 'Horizontal scroll delta (positive = left, negative = right).',
            'required': False
        },
        {
            'name': 'delta_y',
            'type': 'integer',
            'description': 'Vertical scroll delta (positive = up, negative = down).',
            'required': False
        },
    ]

    def call(self, params: str, **kwargs) -> List[ContentItem]:
        args = json5.loads(params) if params else {}
        delta_x = -args.get('delta_x', 0)
        delta_y = -args.get('delta_y', 1000)

        agent = get_agent()
        path = agent.scroll_and_screenshot(
            delta_x=delta_x,
            delta_y=delta_y,
        )
        return [ContentItem(image=str(path))]


@register_tool("wait")
class WaitTool(BaseTool):
    description = "Waits for a specified number of milliseconds (200-500 ms), then returns a screenshot."
    parameters = [
        {
            'name': 'ms',
            'type': 'integer',
            'description': 'Milliseconds to wait.',
            'required': False
        },
    ]

    def call(self, params: str, **kwargs) -> List[ContentItem]:
        args = json5.loads(params) if params else {}
        ms = args.get('ms', 300)
        agent = get_agent()
        path = agent.wait(ms=ms)
        return [ContentItem(image=str(path))]


@register_tool("go_back")
class GoBackTool(BaseTool):
    description = "Goes back to the previous page in browser history and returns a screenshot."
    parameters = []

    def call(self, params: str, **kwargs) -> List[ContentItem]:
        agent = get_agent()
        path = agent.go_back_and_screenshot()
        return [ContentItem(image=str(path))]


@register_tool("get_current_url")
class GetCurrentURL(BaseTool):
    description = "Returns the current URL of the webpage."
    parameters = []

    def call(self, params: str, **kwargs) -> List[ContentItem]:
        agent = get_agent()
        return [ContentItem(text=agent.get_current_url())]


@register_tool("zoom")
class Zoom(BaseTool):
    description = "Magnifies a region of the page (bbox) so that it fills the entire viewport and returns a screenshot."

    parameters = [
        {
            "name": "x",
            "type": "number",
            "required": True,
            "description": "Left X coordinate of the bbox in viewport coordinates from 0 to 1000."
        },
        {
            "name": "y",
            "type": "number",
            "required": True,
            "description": "Top Y coordinate of the bbox in viewport coordinates from 0 to 1000."
        },
        {
            "name": "width",
            "type": "number",
            "required": True,
            "description": "Width of the bbox."
        },
        {
            "name": "height",
            "type": "number",
            "required": True,
            "description": "Height of the bbox."
        }
    ]

    def call(self, params: str, **kwargs) -> List[ContentItem]:
        args = json5.loads(params) if params else {}
        x = args['x']
        y = args['y']
        width = args['width']
        height = args['height']
        agent = get_agent()
        path = agent.zoom_bbox_and_screenshot(
            x=x,
            y=y,
            width=width,
            height=height
        )
        return [ContentItem(image=str(path))]


@register_tool("return_image_url")
class ReturnImageUrl(BaseTool):
    description = "Returns the url of the product card image by its name."

    parameters = [
        {
            "name": "product_name",
            "type": "string",
            "required": True,
            "description": "product card name. At the left from image, bold text."
        }
    ]

    def call(self, params: str, **kwargs) -> List[ContentItem]:
        args = json5.loads(params) if params else {}
        agent = get_agent()
        return [ContentItem(text=agent.return_image_url(card_name=args['product_name']))]


def make_web_tools(agent: WebAgent | None = None) -> list[BaseTool]:
    """Возвращает список зарегистрированных web-tools.

    Параметр agent сохраняем для обратной совместимости, но не используем,
    так как инструменты работают через singleton get_agent().
    """
    return [
        ClickTool(),
        TypeTextTool(),
        ScrollTool(),
        WaitTool(),
        GoBackTool(),
        GetCurrentURL(),
        Zoom(),
        SaveCandidateTool(),
        SetPriceFilterTool(),
        ReturnImageUrl(),
    ]


def get_saved_candidates(clear: bool = False) -> dict:
    global RESULT_STORE
    out = RESULT_STORE.copy()
    if clear:
        RESULT_STORE = {}
    return out
