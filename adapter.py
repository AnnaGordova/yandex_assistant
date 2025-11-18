# adapter.py
from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional

from Agent_NLP.agent_ws import Agent_nlp
from web_agent.agent import get_agents, run_agent

Phase = Literal["nlp", "web"]

@dataclass
class AdapterSession:
    token: str
    phase: Phase = "nlp"
    # история диалога в формате, который понимает NLP-агент
    nlp_dialog: List[dict] = field(default_factory=list)
    # компактная история текста для web-агента
    web_history_text: str = ""
    # последний ответ NLP-агента (чтобы понимать, когда переключаться)
    last_nlp_result: Optional[dict] = None
    # можно хранить ещё что-то: собранные параметры, кандидатов и т.п.
    params: dict = field(default_factory=dict)



class Adapter:
    def __init__(self):
        self.sessions: Dict[str, AdapterSession] = {}
        self.nlp_agent = Agent_nlp()
        # web_assistant сейчас нужен только внутри run_agent,
        # но инициализация через get_agents прогреет браузер.
        self.web_assistant, self.web_agent = get_agents(show_browser=True)

    def get_session(self, token: str) -> AdapterSession:
        if token not in self.sessions:
            self.sessions[token] = AdapterSession(token=token)
        return self.sessions[token]

    def process_message_request(self, req: dict) -> dict:
        token = req.get("token") or req.get("Token")
        session = self.get_session(token)

        # обновляем параметры из формы
        session.params.update({
            "address": req.get("params", {}).get("address"),
            "budget": req.get("params", {}).get("budget"),
            "wishes": req.get("params", {}).get("wishes"),
            "email": req.get("email"),
        })

        chat_history = req.get("chatHistory") or []
        message_text = req.get("message") or ""

        # спец. обработка кнопок (см. ниже)
        control_resp = self._handle_control_actions(session, message_text)
        if control_resp is not None:
            return control_resp

        if session.phase == "nlp":
            return self._process_with_nlp(session, chat_history, message_text)
        else:
            return self._process_with_web(session, chat_history, message_text)

    def _process_with_nlp(self, session: AdapterSession,
                          chat_history: list[dict],
                          message_text: str) -> dict:
        dialog = build_nlp_dialog_from_history(chat_history)

        # последний пользовательский месседж тоже уже есть в history,
        # но если хочешь – можно явно прокинуть message_text как "последний вопрос"
        result = self.nlp_agent.process_dialog(dialog)
        session.last_nlp_result = result
        session.nlp_dialog = dialog

        # Пример: считаем, что status == "questions" => продолжаем спрашивать
        status = result.get("status", "questions")

        # если агент уже собрал поисковую фразу/структуру — переключаемся на web
        if status in ("ok", "search"):
            session.phase = "web"

        # ответ фронту
        return {
            "agent": "nlp",
            "phase": session.phase,
            "status": status,
            "message": result.get("questions") or result.get("answer") or "",
            # сюда можно добавить, например, собранный JSON-запрос
            "payload": result,
        }

    def _process_with_web(self, session: AdapterSession,
                          chat_history: list[dict],
                          message_text: str) -> dict:
        history_text = build_web_history_text(chat_history)
        session.web_history_text = history_text

        # Дополнительно можешь обогатить message_text параметрами:
        full_user_message = (
            f"{message_text}\n\n"
            f"Параметры пользователя:\n"
            f"- Бюджет: {session.params.get('budget')}\n"
            f"- Адрес/регион: {session.params.get('address')}\n"
            f"- Пожелания: {session.params.get('wishes')}\n"
        )

        web_text = run_agent(user_query=full_user_message, history_text=history_text)

        # Если хочешь — можешь после run_agent вытащить кандидатов
        # из web_agent.web_tools.get_saved_candidates()

        return {
            "agent": "web",
            "phase": "web",
            "status": "results",
            "message": web_text,
            # "candidates": candidates,
            # "shareUrl": share_url,
        }

def build_nlp_dialog_from_history(chat_history: list[dict]) -> list[dict]:
    dialog = []
    for msg in chat_history:
        role = "user" if msg.get("isUser") else "assistant"
        dialog.append({
            "role": role,
            "content": msg.get("text", "")
        })
    return dialog

def build_web_history_text(chat_history: list[dict]) -> str:
    lines = []
    for msg in chat_history[-10:]:  # ограничим, чтобы не раздувать
        prefix = "Пользователь:" if msg.get("isUser") else "Ассистент:"
        lines.append(f"{prefix} {msg.get('text', '')}")
    return "\n".join(lines)

