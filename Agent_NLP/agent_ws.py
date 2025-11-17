from openai import OpenAI
from Agent_NLP.system_prompt import TEXT_SYSTEM_PROMPT
from Agent_NLP.utils import parse_agent_response


class Agent_nlp:
    def __init__(self):
        """Агент, который по истории диалога либо задаёт один вопрос,
        либо возвращает финальный JSON для поиска товаров.
        """
        self.client = None
        self.model = None
        self.system_prompt = TEXT_SYSTEM_PROMPT

        def connect_vllm_api():
            self.model = "QuantTrio/Qwen3-VL-32B-Instruct-AWQ"
            self.client = OpenAI(
                base_url="http://195.209.210.28:8000/v1",
                api_key="sk-no-key-required",
            )

        connect_vllm_api()
        print("Agent_NLP connected")

    def _raw_call(self, messages):
        """Вызов модели + парсинг ответа в dict."""
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.2,
            max_tokens=800,
        )
        assistant_text = resp.choices[0].message.content
        if not isinstance(assistant_text, str):
            assistant_text = str(assistant_text)

        parsed = parse_agent_response(assistant_text)
        if not isinstance(parsed, dict):
            parsed = {"raw": assistant_text}
        return parsed

    def generate(self, user_message, dialog_history=None):
        """Если где-то используется напрямую."""
        messages = [{"role": "system", "content": self.system_prompt}]
        if dialog_history:
            messages.extend(dialog_history)
        messages.append({"role": "user", "content": user_message})
        return self._raw_call(messages)

    def process_dialog(self, dialog):
        """
        ВХОД:
          dialog: список сообщений истории:
          [
            {"role": "assistant", "content": "..."},
            {"role": "user", "content": "..."},
            ...
          ]

        ВЫХОД (нормализованный для WebSocket-сервера):
          1) Вопрос:
             {"status": "questions", "questions": "один следующий вопрос"}

          2) Финал:
             {"status": "ok", "items": [ {...}, ... ]}
        """
        if not dialog:
            return {
                "status": "questions",
                "questions": "Что вы хотите купить? Опишите товар."
            }

        # находим последнего user-а
        last_user_idx = None
        for i in range(len(dialog) - 1, -1, -1):
            if dialog[i].get("role") == "user":
                last_user_idx = i
                break

        if last_user_idx is None:
            return {
                "status": "questions",
                "questions": "Сначала расскажите, что вы хотите купить на маркетплейсе."
            }

        last_user_msg = dialog[last_user_idx].get("content", "")
        dialog_history = dialog[:last_user_idx]

        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(dialog_history)
        messages.append({"role": "user", "content": last_user_msg})

        parsed = self._raw_call(messages)

        if parsed.get("status") == "ok":
            return parsed

        q_value = parsed.get("questions") or parsed.get("question")

        # если это список – берём первый
        if isinstance(q_value, list):
            q_value = q_value[0] if q_value else None

        # если там что-то странное — делаем дефолт
        if not isinstance(q_value, str) or not q_value.strip():
            q_value = "Уточните, пожалуйста, что именно вы хотите купить."

        return {
            "status": "questions",
            "questions": q_value,
        }
