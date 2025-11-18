from Agent_Marketplace.agent import Agent_marketplace

if __name__ == '__main__':
    '''
    agent_researcher = Agent_marketplace()
    result_x_y, path = agent_researcher.start_browsing()
    print(result_x_y)
    print(path)'''
    agent_browser = Agent_marketplace()
    page = agent_browser.start_browsing(query_to_type='Стринги женские')
    #products = agent_browser.run_shopping_agent(user_request= 'Штаны спортивные розовые женские размер 44', client_openai=agent_browser.client, model_id=agent_browser.model)
    #print(products)