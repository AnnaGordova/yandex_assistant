from openai import OpenAI
from Agent_NLP.system_prompt import TEXT_SYSTEM_PROMPT
from Agent_NLP.utils import parse_agent_response
class Agent_nlp:
    def __init__(self):
        """Конструктор класса агента, уточняющего запросы пользователя"""
        self.client = None
        self.model = None
        self.system_prompt = TEXT_SYSTEM_PROMPT

        def connect_vllm_api():
            """ Подключение к модели через yandex cloud (сделать как дадут доступ)"""
            self.model = "QuantTrio/Qwen3-VL-32B-Instruct-AWQ"
            self.client = OpenAI(
                base_url="http://195.209.210.28:8000/v1",
                api_key="sk-no-key-required",  # No API key needed for local vLLM server
            )


        def connect_openrouter_api():
            OPENROUTER_API_KEY ="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"
            OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
            MODEL_TEXT = "qwen/qwen2.5-vl-32b-instruct:free"
            self.client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=OPENROUTER_API_KEY)
            self.model = MODEL_TEXT

        #connect_openrouter_api()
        connect_vllm_api()

    def generate(self, user_message, dialog_history=None):
        """
        user_message: строка (например: "хочу купить гавайскую рубашку")
        dialog_history: список словарей [{'role':'user'/'assistant','content':...}, ...]
        Возвращает распарсенный объект (см. utils.parse_agent_response).
        """
        messages = [{"role": "system", "content": TEXT_SYSTEM_PROMPT}]
        if dialog_history:
            # dialog_history ожидается в виде [{'role':...,'content':...}, ...]
            messages.extend(dialog_history)
        messages.append({"role": "user", "content": user_message})
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.2,
            max_tokens=800
        )
        assistant_text = resp.choices[0].message.content
        parsed = parse_agent_response(assistant_text if isinstance(assistant_text, str) else str(assistant_text))
        return parsed

    def start_dialog(self):
        dialog = []
        parsed = self.generate("Поздоровайся с пользователем и спроси, как ты можешь ему помочь", dialog_history=dialog)
        print(parsed['questions'][0])
        dialog.append({"role": "assistant", "content": parsed['questions'][0]})

        user_query = input("\nQ: ")
        parsed = self.generate(user_query, dialog_history=dialog)
        dialog.append({"role": "user", "content": user_query})

        while parsed['status'] == 'questions':
            questions = parsed.get("questions", [])
            for q in questions:
                print("\nQ:", q)
                a = input("A: ").strip()
                dialog.append({"role": "assistant", "content": q})
                dialog.append({"role": "user", "content": a})

            parsed = self.generate("На основе диалога сформируй поисковую фразу, содержащую все параметры от пользователя (JSON {'status':'ok','query':['Например брюки синие 48 размера мужские']}).",
                dialog_history=dialog)
        return parsed

