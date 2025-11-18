from eval.agent import Agent_eval
import json

if __name__ == '__main__':
    agent_researcher = Agent_eval()

    # Загружаем product_cards.json
    with open("eval/product_cards.json", "r", encoding="utf-8") as f:
        products = json.load(f)

    # Генерируем запросы
    output = agent_researcher.generate_queries(products)

    # Сохраняем результат
    with open("eval/generated_queries.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("Генерация завершена. Файл saved to generated_queries.json")
