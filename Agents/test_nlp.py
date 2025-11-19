from Agents.nlp_agent.agent import Agent_nlp

if __name__ == '__main__':
    agent_researcher = Agent_nlp()
    search_list = agent_researcher.start_dialog()
    print(search_list)