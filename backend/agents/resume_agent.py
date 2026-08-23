from agent import llm

from agent_memory import (
    store_agent_memory,
    retrieve_agent_memory
)

def resume_agent(
    user_input,
    resume_text=""
):
    # RETRIEVE MEMORY
    memories = retrieve_agent_memory(
        "resume",
        user_input
    )

    memory_context = "\n".join(
        memories
    )

    # ATS & Profile Context
    resume_context = f"""
    Uploaded Resume Text:
    {resume_text}
    """ if resume_text else "No resume uploaded yet. Ask the user to upload their resume in the sidebar."

    response = llm.invoke(
        f"""
        You are a Premium AI Resume Coach and ATS Expert.

        Resume Context:
        {resume_context}

        Previous Conversation Memories:
        {memory_context}

        User Request:
        {user_input}

        Responsibilities:
        - Analyze the uploaded resume text for ATS keyword alignment, phrasing, and formatting.
        - Give clear, bulleted improvement suggestions with specific, actionable examples.
        - Map their skills to AI/ML job roles and recommend relevant study topics or project enhancements.
        - Answer specific resume questions or critique their profile sections.

        Use previous memories if relevant.
        Give practical, highly personalized career and resume advice.
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
        "resume",
        important_memory
    )

    return response.content