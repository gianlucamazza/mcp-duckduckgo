"""
MCP prompt definitions for the DuckDuckGo search plugin.
"""

from __future__ import annotations

from pydantic import Field

from .server import mcp


@mcp.prompt()  # pragma: no cover
def search_assistant(
    topic: str = Field(..., description="The topic to search for"),
) -> str:  # vulture: ignore
    """
    Creates a prompt to help formulate an effective search query for the given topic.
    """
    return f"""
    I need to search for information about {topic}.

    Please help me formulate an effective search query that will:
    1. Be specific and focused
    2. Use relevant keywords
    3. Avoid unnecessary words
    4. Be under 400 characters

    Then, use the duckduckgo_web_search tool with this query to find the most relevant information.
    """


@mcp.prompt()  # pragma: no cover
def fact_check_assistant(
    statement: str = Field(..., description="The statement to fact check"),
) -> str:  # vulture: ignore
    """
    Creates a prompt to help verify the accuracy of a statement.
    """
    return f"""
    I need to verify if the following statement is accurate:

    "{statement}"

    Please help me:
    1. Use the fact_check tool to check this statement across multiple sources
    2. Analyze the results to determine if the statement is likely true or false
    3. Explain the consensus view and any notable disagreements
    4. Consider the reliability of the different sources

    If necessary, use the duckduckgo_web_search tool to find additional information
    and the duckduckgo_get_details tool to extract more context from key sources.
    """


@mcp.prompt()  # pragma: no cover
def technical_search_assistant(
    query: str = Field(..., description="The technical query or problem"),
    language: str | None = Field(
        None, description="Programming language (e.g. Python, JavaScript)"
    ),
) -> str:  # vulture: ignore
    """
    Creates a prompt to help with technical documentation searches.
    """
    language_text = f" in {language}" if language else ""

    return f"""
    I need to find technical information about: "{query}"{language_text}.

    Please help me:
    1. Formulate an effective technical search query
    2. Use the dev_search tool to find relevant documentation, code examples, and resources
    3. Focus on high-quality sources like official documentation, reputable tutorials, and Stack Overflow
    4. Provide code examples and explanations that address my specific needs

    For the most useful sources, use duckduckgo_get_details to extract more detailed information.
    """


@mcp.prompt()  # pragma: no cover
def location_search_assistant(
    query: str = Field(..., description="What you're looking for"),
    location: str = Field(..., description="The geographic location"),
) -> str:  # vulture: ignore
    """
    Creates a prompt to help with location-based searches.
    """
    return f"""
    I need to find information about {query} in {location}.

    Please help me:
    1. Use the location_search tool to find relevant local information
    2. Focus on details specific to this location
    3. Provide practical information such as addresses, opening hours, or other relevant details
    4. Suggest related searches that might be helpful for this location

    For particularly interesting results, use duckduckgo_get_details to extract more comprehensive information.
    """


@mcp.prompt()  # pragma: no cover
def summary_assistant(
    url: str = Field(..., description="URL of the webpage to summarize"),
) -> str:  # vulture: ignore
    """
    Creates a prompt to help summarize content from a webpage.
    """
    return f"""
    I need to understand the key information from this webpage: {url}

    Please help me:
    1. Use the summarize_webpage tool to generate a concise summary
    2. Highlight the most important points and main ideas
    3. Organize the information in a clear, readable format
    4. Provide context about the source and its credibility

    If necessary, use the duckduckgo_get_details tool to gather additional information about the source.
    """
