from web_agent.agent import init_agent, run_agent

if __name__ == '__main__':
    agent = init_agent()
    run_agent(query="{'query': 'мужские плавки L', 'filters': {'sex': 'male', 'size': 'L', 'min_price': None, 'max_price': None}, 'extra': 'предназначены для поездки на море, нужна удобная и быстросохнущая ткань'}")