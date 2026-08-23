from langchain_core.tools import tool
import datetime
from tavily import TavilyClient
from dotenv import load_dotenv
import os
from pypdf import PdfReader

load_dotenv()

tavily = TavilyClient(
    api_key=os.getenv("TAVILY_API_KEY")
)


@tool
def analyze_resume(file_path: str) -> str:
    """
    Analyze a resume PDF and provide improvement suggestions.
    """

    try:

        reader = PdfReader(file_path)

        resume_text = ""

        for page in reader.pages:
            resume_text += page.extract_text()

        return resume_text

    except Exception as e:
        return f"Resume analysis error: {str(e)}"

@tool
def web_search(query: str) -> str:
    """Search the web for latest information."""

    response = tavily.search(
        query=query,
        search_depth="basic",
        max_results=3
    )

    results = []

    for result in response["results"]:
        results.append(
            f"Title: {result['title']}\n"
            f"Content: {result['content']}\n"
        )

    return "\n".join(results)

@tool
def get_current_time() -> str:
    """Returns current date and time."""
    return str(datetime.datetime.now())

@tool
def motivational_quote() -> str:
    """Returns motivational quote."""
    return "Success comes from consistency and discipline."

@tool
def resume_tip() -> str:
    """Returns a resume improvement tip."""
    return "Use action verbs and measurable achievements."

@tool
def generate_ml_interview_question() -> str:
    """Returns an ML interview question."""
    return "Explain bias vs variance in machine learning."