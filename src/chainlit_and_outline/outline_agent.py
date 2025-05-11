import logging

from outline_agent_tools import get_current_page_url, get_doc_by_url, search_docs
from pydantic import BaseModel, Field, ValidationError
from pydantic_ai import Agent, Tool, messages

logger = logging.getLogger(__name__)


class Response(BaseModel):
    message: str = Field(
        description="Response based on context, in markdown format or conversation with user", default=""
    )

    def to_markdown(self) -> str:
        return self.message


SYSTEM_PROMPT = """
You are a helpful assistant for the Outline users at Divar.
Outline is a documentation service that employees at Divar use to create, share, and manage documents.

You have access to the following tools to help you:
    1.	`get_doc_by_url`: Use this to fetch a full document if you have a URL or path.
    2.  `get_current_page_url`: Use this to get the URL of the current page.
    3.	`search_docs`: Use this to search for documents relevant to a question or topic.
"""


class OutlineAgent:
    def __init__(self, use_internet_search: bool = False):
        self.agent = Agent(
            model="gpt-4.1",
            name="Outline Agent",
            output_type=Response,
            tools=[
                Tool(get_doc_by_url, takes_ctx=False),
                Tool(search_docs, takes_ctx=False),
                Tool(get_current_page_url, takes_ctx=False),
            ],
            output_retries=3,
            system_prompt=SYSTEM_PROMPT,
        )

    async def run_stream(self, message: str, message_history: list[messages.ModelMessage]):
        async with self.agent.run_stream(message, message_history=message_history) as result:
            async for message, last in result.stream_structured():
                try:
                    response = await result.validate_structured_output(message, allow_partial=not last)
                    yield response, result.all_messages()
                except ValidationError:
                    logger.warning("Could not parse partial or final result message from LLM")
