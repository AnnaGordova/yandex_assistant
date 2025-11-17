from web_agent.agent import init_agent, run_agent
from web_agent.web_tools import get_saved_candidates, close_session

if __name__ == '__main__':
    # agent = init_agent()
    text, dialog_ctx = run_agent(query="{'query': 'мужская кожаная куртка в строгом стиле', 'filters': {'sex': 'male', 'size': '48-52', 'min_price': None, 'max_price': 10000}, 'extra': 'кожаная куртка в строгом стиле, черного цвета, на молнии без капюшона, мужская, размер 48-52, бюджет до 10000 рублей'}")
    feedback = input("U: ")
    while feedback != "break":
        text, dialog_ctx= run_agent(query=(
        "Вот фидбек от пользователя по уже подобранным товарам: "
        f"{feedback}\n"
        "Замени ТОЛКО товар, который попросил пользователь. остальные не трогай"),
        messages=dialog_ctx
        )
        feedback = input("U: ")

    print(get_saved_candidates())
    close_session()