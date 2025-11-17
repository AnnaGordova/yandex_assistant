from web_agent.agent import init_agent, run_agent
from web_agent.web_tools import get_saved_candidates

if __name__ == '__main__':
    # agent = init_agent()
    run_agent(query="{'query': 'мужская кожаная куртка в строгом стиле', 'filters': {'sex': 'male', 'size': '48-52', 'min_price': None, 'max_price': 10000}, 'extra': 'кожаная куртка в строгом стиле, черного цвета, на молнии без капюшона, мужская, размер 48-52, бюджет до 10000 рублей'}")
    print(get_saved_candidates())