import asyncio
import logging
import os
from typing import Optional, Union

import chainlit as cl
from jinja2 import Template
from outline_client import outline
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SimpleError(BaseModel):
    message: str


class DocumentInfo(BaseModel):
    id: str
    url: str
    title: str


class CollectionDocuments(BaseModel):
    documents: list[DocumentInfo]

    def to_markdown(self):
        return Template("""
        {% for doc in collection.documents %}
        - [{{ doc.title }}]({{ outline_base_url }}{{ doc.url }})

        {% endfor %}
        """).render(collection=self, outline_base_url=os.environ["OUTLINE_BASE_URL"])


class Document(DocumentInfo):
    text: str = Field(description="The content of document in markdown format")
    createdAt: str
    updatedAt: Union[None | str] = Field(default=None)
    publishedAt: Union[None | str] = Field(default=None)
    archivedAt: Union[None | str] = Field(default=None)

    def to_markdown(self):
        return Template("""
        {{ doc.id }} - [{{ doc.title }}]({{ outline_base_url }}{{ doc.url }})

        {{ doc.text }}
        """).render(doc=self, outline_base_url=os.environ["OUTLINE_BASE_URL"])


class SearchResult(BaseModel):
    document_id: str
    document_url: str
    document_title: str
    related_text_part: str = Field(description="The part of the document that is related to the search query")

    def to_markdown(self):
        return Template("""
        [{{ doc.document_title }}]({{ outline_base_url }}{{ doc.document_url }})

        {{ doc.related_text_part }}
        """).render(doc=self, outline_base_url=os.environ["OUTLINE_BASE_URL"])


@cl.step(name="Document Loader", type="tool")
async def get_doc_by_url(doc_url: str) -> Union[Document, SimpleError]:
    """
    Fetch a document by its URL.

    Args:
        doc_url (str): The URL of the document to fetch. It can be full URL like 'https://docs.divar.dev/doc/data-assistant-accepted-1403-12-26-6RwQmlbrCu' or the path like '/doc/data-assistant-accepted-1403-12-26-6RwQmlbrCu'.

    Returns:
        OutlineDocument: The fetched document as an Document object.

    Raises:
        Exception: If there is an error fetching the document.
    """
    cl.context.current_step.input = doc_url
    result = await _get_doc(url=doc_url)
    if isinstance(result, SimpleError):
        return result
    else:
        cl.context.current_step.output = result.to_markdown()
        return result


@cl.step(name="Document Search", type="tool")
async def search_docs(keywords: list[str]) -> dict[str, Union[list[SearchResult], SimpleError]]:
    """
    Search in documents with keywords. For each keyword at most 5 documents are returned.

    Args:
        keywords (list[str]): Up to 10 keywords that are either exact terms, synonyms, or paraphrased forms of the original question. These keywords should be provided in both Persian and English to maximize the chances of finding relevant documents.

    Returns:
        dict[str, list[SearchResult]]: A dictionary where each key is a keyword from the input list, and the value is a list of SearchResult objects.
    """
    try:
        unique_keywords = set(keywords)

        async def search_for_keyword(keyword):
            step = f"### Searching for keyword: {keyword}\n\n"
            try:
                response = await outline.search_docs(keyword, offset=0, limit=5)
                result = []
                for search_result in response.get("data", []):
                    sr = SearchResult(
                        document_id=search_result["document"]["id"],
                        document_url=search_result["document"]["url"],
                        document_title=search_result["document"]["title"],
                        related_text_part=search_result["context"],
                    )
                    step += f"#### Found {sr.document_id}\n{sr.to_markdown()}\n\n"
                    result.append(sr)
                return keyword, result, step
            except Exception as e:
                error_message = f"Error searching keyword '{keyword}': {e}"
                logger.exception(error_message)
                return keyword, SimpleError(message=error_message), error_message

        results = await asyncio.gather(*(search_for_keyword(kw) for kw in unique_keywords))

        mapping = {}
        step_output = ""
        for keyword, result, step_output_part in results:
            step_output += step_output_part
            mapping[keyword] = result

        cl.context.current_step.output = step_output
        return mapping
    except Exception:
        logger.exception(f"Error searching documents with keywords '{keywords}'")
        raise


@cl.step(name="Current Page URL Loader", type="tool", show_input=False)
async def get_current_page_url() -> str:
    """
    Fetches the current page URL.

    This function retrieves the URL of the current page or returns an error message.

    Returns:
        str: The current page URL if available, or an error message if not.
    """
    if cl.context.session.client_type == "copilot":
        fn = cl.CopilotFunction(name="page-url", args={})
        return await fn.acall()
    else:
        return "Error: Current page URL is not available in this context."


async def _get_doc(*, doc_id: Optional[str] = None, url: Optional[str] = None):
    try:
        response = await outline.get_doc(doc_id if doc_id else url)
        doc = Document(**response)
        return doc
    except Exception as e:
        message = (
            f"Error fetching document by ID '{doc_id}': {e}"
            if doc_id
            else f"Error fetching document by URL '{url}': {e}"
        )
        logger.exception(message)
        return SimpleError(message=message)
