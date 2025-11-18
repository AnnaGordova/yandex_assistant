from openai import OpenAI
from eval.system_prompt import TEXT_SYSTEM_PROMPT
import json

class Agent_eval:
    def __init__(self):
        """Конструктор класса агента, уточняющего запросы пользователя"""
        self.client = None
        self.model = None
        self.system_prompt = TEXT_SYSTEM_PROMPT

        self.connect_vllm_api()

    def connect_vllm_api(self):
        """Подключение к локальному серверу vLLM с моделью Qwen"""
        self.model = "QuantTrio/Qwen3-VL-32B-Instruct-AWQ"
        self.client = OpenAI(
            base_url="http://195.209.210.28:8000/v1",
            api_key="sk-no-key-required",  # no key for local vLLM
        )

    def generate_queries(self, products_json: dict):
        """
        Отправляет входной JSON с товарами в модель и возвращает результат.

        :param products_json: dict — JSON с карточками товаров
        :return: dict — JSON с 5 запросами для каждого товара
        """

        # Превращаем словарь в строку перед отправкой
        user_payload = json.dumps(products_json, ensure_ascii=False)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {
                    "role": "user",
                    "content": f"Вот входные данные: {user_payload}"
                }
            ],
            temperature=0.7,
            max_tokens=1500
        )

        raw_text = response.choices[0].message.content

        # Попытка преобразовать ответ в JSON
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            # Если модель вернула лишний текст — пытаемся извлечь JSON
            try:
                start = raw_text.index("{")
                end = raw_text.rindex("}") + 1
                return json.loads(raw_text[start:end])
            except Exception:
                raise ValueError(f"Ошибка парсинга JSON: \n{raw_text}")
