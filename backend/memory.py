from langchain_core.messages import SystemMessage

chat_history = [
    SystemMessage(
        content="""
        You are a helpful AI Career and Research Assistant.

        You remember previous conversations and help users
        with AI/ML learning, resumes, research, and interviews.
        """
    )
]