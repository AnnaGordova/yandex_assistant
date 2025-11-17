import os
from os.path import exists
from pathlib import Path
from typing import Optional, List

from .web_tools import WebAgent
from .web_tools import make_web_tools, init_session, close_session
# from web_agent.config import settings
from .system_prompt_web import SYSTEM_PROMPT
import time

from qwen_agent.utils.output_beautify import multimodal_typewriter_print
from qwen_agent.agents import Assistant

# Конфиг работы LLM/VLM модели агента
llm_cfg = {
    'model_type': "qwenvl_oai",
    'model': "QuantTrio/Qwen3-VL-30B-A3B-Instruct-AWQ",
    'model_server': "http://195.209.210.28:8000/v1",
    'api_key': None,

    'generate_cfg': {
        "temperature": 0.05,
        "top_p": 1.0,
        "repetition_penalty": 1.1
    }
}

_agent_singleton: Optional[Assistant] = None
_web_agent_singleton: Optional[WebAgent] = None

# минимальный интервал между полными прогонками агента
MIN_INTERVAL_BETWEEN_RUNS = 10.0    # секунд
# задержка между действиями браузера (playwright slow_mo)
DEFAULT_SLOW_MO_MS = 1500          # мс

def init_agent(show_browser: bool = True):
    """
    Инициализация агентов.
    """
    web_agent = init_session(screenshot_path=Path("web_agent/screenshots"), headless=not show_browser, slow_mo_ms=DEFAULT_SLOW_MO_MS)
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

def get_agents(show_browser: bool = True):
    """
    Возвращает созданный или существующий экземпляр Assistant и WebAgent.
    """
    global _agent_singleton, _web_agent_singleton

    if _agent_singleton is None:
        _agent_singleton, _web_agent_singleton = init_agent(show_browser=show_browser)

    return _agent_singleton, _web_agent_singleton

def run_agent(query: str, messages: List = None):
    """
    Запуск агента с заданной историей сообщений и входным запросом.
    """
    agent, web_agent = get_agents(show_browser=True)

    if not messages:
        messages = []

    start_screen = web_agent.screenshot()
    messages += [
        {"role": "user", "content": [
            {"image": str(start_screen)},
            {"text": query}
        ]}
    ]

    # TODO подумать как возвращать ответ и размышления агента
    response_plain_text = ''
    for ret_messages in agent.run(messages):
        response_plain_text = multimodal_typewriter_print(ret_messages, response_plain_text)

    close_session()

    return response_plain_text