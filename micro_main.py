from Agent_Marketplace.agent import Agent_marketplace

if __name__ == '__main__':
    agent_researcher = Agent_marketplace()
    result_x_y, path = agent_researcher.start_browsing()
    print(result_x_y)
    print(path)