# agent.py

from typing import Optional, List, Tuple
from pathlib import Path

from .web_tools import WebAgent
from .web_tools import make_web_tools, init_session, close_session
from .system_prompt_web import SYSTEM_PROMPT

from qwen_agent.utils.output_beautify import multimodal_typewriter_print
from qwen_agent.agents import Assistant

# Конфиг работы LLM/VLM модели агента
llm_cfg = {
    'model_type': "qwenvl_oai",
    'model': "QuantTrio/Qwen3-VL-32B-Instruct-AWQ",
    'model_server': "http://195.209.210.28:8000/v1",
    'api_key': None,
    'generate_cfg': {
        "temperature": 0.1,
        "top_p": 1.0,
        "repetition_penalty": 1.1,
        # "max_new_tokens": 1024,
    }
}

_agent_singleton: Optional[Assistant] = None
_web_agent_singleton: Optional[WebAgent] = None

DEFAULT_SLOW_MO_MS = 50


def init_agent(show_browser: bool = False) -> Tuple[Assistant, WebAgent]:
    """
    Инициализация агентов.
    """
    web_agent = init_session(
        screenshot_path=Path("web_agent/screenshots"),
        headless=not show_browser,
        slow_mo_ms=DEFAULT_SLOW_MO_MS,
    )
    print("web agent initialized")
    web_tools = make_web_tools()
    print("tools initialized")

    agent = Assistant(
        llm=llm_cfg,
        function_list=web_tools,
        system_message=SYSTEM_PROMPT,
    )
    print("Assistant initialized")
    return agent, web_agent


def get_agents(show_browser: bool = False) -> Tuple[Assistant, WebAgent]:
    """
    Возвращает созданный или существующий экземпляр Assistant и WebAgent.
    """
    global _agent_singleton, _web_agent_singleton

    if _agent_singleton is None or _web_agent_singleton is None:
        _agent_singleton, _web_agent_singleton = init_agent(show_browser=show_browser)

    return _agent_singleton, _web_agent_singleton


def run_agent(user_query: str, history_text: str | None = None) -> str:
    agent, web_agent = get_agents(show_browser=True)

    # Компактный контекст + новый запрос
    if history_text:
        full_text = (
            "Краткая история диалога (что уже делали и какие товары смотрели):\n"
            f"{history_text}\n\n"
            "Новое сообщение пользователя:\n"
            f"{user_query}\n"
        )
    else:
        full_text = user_query

    start_screen = web_agent.screenshot()
    messages = [{
        "role": "user",
        "content": [
            {"image": str(start_screen)},
            {"text": full_text},
        ],
    }]

    response_plain_text = ""
    for ret_messages in agent.run(messages):
        response_plain_text = multimodal_typewriter_print(
            ret_messages,
            response_plain_text,
        )

    return response_plain_text
