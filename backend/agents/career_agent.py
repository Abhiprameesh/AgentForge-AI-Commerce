from agent import llm

from agent_memory import (
    store_agent_memory,
    retrieve_agent_memory
)

def career_agent(user_input):

    # RETRIEVE MEMORY
    memories = retrieve_agent_memory(
        "career",
        user_input
    )

    memory_context = "\n".join(
        memories
    )

    response = llm.invoke(
        f"""
        You are an AI Career Mentor.

        Previous Career Memories:
        {memory_context}

        User Request:
        {user_input}

        Responsibilities:
        - AI/ML career guidance
        - internship advice
        - roadmap creation
        - learning strategies
        - project guidance

        Use previous memories if relevant.

        Give practical personalized advice.
        """
    )

    # STORE MEMORY
    important_memory = f"""
    User:
    {user_input}

    AI:
    {response.content}
    """

    store_agent_memory(
        "career",
        important_memory
    )

    return response.content