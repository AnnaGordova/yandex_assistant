from pathlib import Path
from typing import Optional, List
import json5
from qwen_agent.llm.schema import ContentItem

from .web_tools import WebAgent, get_agent, close_agent
from qwen_agent.tools.base import BaseTool, register_tool

def init_session(
        headless: bool = False,
        url: str = "https://market.yandex.ru/",
        slow_mo_ms: int = 1000,
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

RESULT_STORE: list[dict] = []

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
        "Сохраняет текущую карточку товара как кандидата: "
        "URL + краткое текстовое описание, почему она подходит."
    )
    parameters = [
        {
            "name": "description",
            "type": "string",
            "required": True,
            "description": "Короткое описание/пояснение, зачем этот товар выбран.",
        },
    ]

    def call(self, params: str, **kwargs) -> List[ContentItem]:
        args = json5.loads(params) if params else {}
        description = args.get("description", "")

        agent = get_agent()
        url = agent.get_current_url()

        RESULT_STORE.append(
            {
                "url": url,
                "description": description,
            }
        )

        # Можно ещё сделать скрин результата:
        # screenshot_path = agent.screenshot(prefix="result")
        # и тоже сохранить в RESULT_STORE при желании.

        idx = len(RESULT_STORE)
        return [ContentItem(text=f"Saved candidate #{idx}: {url}")]
@register_tool("click")
class ClickTool(BaseTool):
    description = (
        "Clicks at given X,Y coordinates with left/right/middle button and optional double click. "
        "Returns a screenshot after the action."
        "FORMAT: {'x': int, 'y': int}"
    )
    parameters = [
        {
            'name': 'x',
            'type': 'integer',
            'description': 'X coordinate in CSS pixels from 0 to 1000.',
            'required': True
        },
        {
            'name': 'y',
            'type': 'integer',
            'description': 'Y coordinate in CSS pixels from 0 to 1000.',
            'required': True
        },
        {
            'name': 'button',
            'type': 'string',
            'description': "Mouse button to click: 'left', 'right', or 'middle'.",
            'required': False
        },
        {
            'name': 'click_count',
            'type': 'integer',
            'description': 'Number of clicks: 1 for single click, 2 for double click.',
            'required': False
        },
    ]

    def call(self, params: str, **kwargs) -> List[ContentItem]:
        args = json5.loads(params)
        if isinstance(args['x'], list):
            x, y = args['x']
        else:
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
    description = "Waits for a specified number of milliseconds, then returns a screenshot."
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
        ms = args.get('ms', 1000)
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


@register_tool ("return_image_url")
class ReturnImageUrl(BaseTool):
    description = "Returns the url of the product card image by its name."

    parameters =[
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
        return [ContentItem(text=agent.return_image_url(name = args.name))]


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

def get_saved_candidates(clear: bool = True) -> list[dict]:
    global RESULT_STORE
    out = list(RESULT_STORE)
    if clear:
        RESULT_STORE = []
    return out