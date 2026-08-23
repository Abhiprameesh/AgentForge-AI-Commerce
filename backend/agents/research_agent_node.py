from agent import llm

from research_agent import (
    retrieve_research_context
)

from agent_memory import (
    store_agent_memory,
    retrieve_agent_memory
)

def research_agent(
    user_input,
    return_chunks=False
):

    # RETRIEVE MEMORY
    memories = retrieve_agent_memory(
        "research",
        user_input
    )

    memory_context = "\n".join(
        memories
    )

    # RETRIEVE RESEARCH CHUNKS
    research_context = ""

    retrieved_chunks = []

    try:

        retrieved_chunks = retrieve_research_context(
            user_input
        )

        research_context = "\n".join(
            retrieved_chunks
        )

    except:

        research_context = ""

    # LLM RESPONSE
    response = llm.invoke(
        f"""
        You are an AI Research Assistant.

        Previous Research Memories:
        {memory_context}

        Research Paper Context:
        {research_context}

        User Request:
        {user_input}

        Responsibilities:
        - summarize research papers
        - explain methodologies
        - explain architectures
        - simplify complex concepts
        - explain findings
        - answer research-related questions
        - help with AI/ML understanding

        Use previous memories if relevant.

        Use the research paper context heavily
        when answering research questions.

        Give detailed research-focused answers.
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
        "research",
        important_memory
    )

    # RETURN FOR OBSERVABILITY
    if return_chunks:

        return (
            response.content,
            retrieved_chunks
        )

    return response.content