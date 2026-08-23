from agent import llm

def router_agent(user_input):

    response = llm.invoke(
        f"""
        You are an AI Router Agent.

        Decide which specialized agent
        should handle the user request.

        Available Agents:
        - resume
        - research
        - career
        - interview

        Return ONLY ONE WORD.

        User Request:
        {user_input}
        """
    )

    return response.content.strip().lower()