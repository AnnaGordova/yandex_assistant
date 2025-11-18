from Agent_Marketplace.agent import Agent_marketplace
import json
import os
if __name__ == '__main__':

    agent_browser = Agent_marketplace()


    # Загружаем JSON-файл
    with open("eval/generated_queries.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    # Берём список запросов
    queries = data["queries"]

    # Пробегаемся по каждому элементу
    for item in queries:
        product_id = item["product_id"]
        d = {
            "explicit_exact" : item["explicit_exact"],
            "paraphrase" : item["paraphrase"],
            "visual" : item["visual"],
            "ambiguous" :  item["ambiguous"],
            "misspelling" : item["misspelling"]
        }
        for k in d:
            if os.path.exists(f'eval/baseline_{product_id}_{k}_cards.json'):
                print(f'eval/baseline_{product_id}_{k}_cards.json существует')
                continue
            page = agent_browser.start_browsing(product_id=product_id, qeury_type=k, query_to_type=d[k])
    #page = agent_browser.start_browsing(query_to_type='Юбка женская')

    #products = agent_browser.run_shopping_agent(user_request= 'Штаны спортивные розовые женские размер 44', client_openai=agent_browser.client, model_id=agent_browser.model)
    #print(products)