from Agent_Marketplace.agent import Agent_marketplace

if __name__ == '__main__':
    '''
    agent_researcher = Agent_marketplace()
    result_x_y, path = agent_researcher.start_browsing()
    print(result_x_y)
    print(path)'''
    agent_browser = Agent_marketplace()
    page = agent_browser.start_browsing()
    print(page)