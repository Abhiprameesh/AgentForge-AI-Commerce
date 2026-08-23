from agent import llm

from agent_memory import (
    store_agent_memory,
    retrieve_agent_memory
)

def interview_agent(user_input):

    # RETRIEVE MEMORY
    memories = retrieve_agent_memory(
        "interview",
        user_input
    )

    memory_context = "\n".join(
        memories
    )

    response = llm.invoke(
        f"""
        You are an Expert Technical Interviewer.

        Previous Interview Memories:
        {memory_context}

        User Request / Answer:
        {user_input}

        Responsibilities:
        - Conduct a mock interview based on the user's resume and career interests.
        - Ask one question at a time.
        - Evaluate the user's answer constructively and give brief feedback before asking the next question.
        - Be professional but encouraging.
        - Keep your responses concise since they will be spoken out loud via text-to-speech.

        Respond directly to the user as if you are speaking to them in an interview.
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
        "interview",
        important_memory
    )

    return response.content