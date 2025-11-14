from openai import OpenAI
#from Agent_NLP.system_prompt import TEXT_SYSTEM_PROMPT Поменять на свой систем промпт
class Agent_nlp:
    def __init__(self):
        """Конструктор класса агента, уточняющего запросы пользователя"""
        self.client = None
        self.model = None
        #self.system_prompt = TEXT_SYSTEM_PROMPT поменять на свой систем промпт

        def connect_vllm_api():
            """ Подключение к модели через yandex cloud (сделать как дадут доступ)"""
            self.model = "QuantTrio/Qwen3-VL-30B-A3B-Instruct-AWQ"
            self.client = OpenAI(
                base_url="http://195.209.210.28:8000/v1",
                api_key="sk-no-key-required",  # No API key needed for local vLLM server
            )

        connect_vllm_api()