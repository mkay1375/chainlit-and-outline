import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class OutlineClient:
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = base_url or os.environ.get("OUTLINE_BASE_URL")
        self.api_token = api_key or os.environ.get("OUTLINE_API_KEY")

        if not self.base_url:
            raise ValueError(
                "Outline base URL is required. Set OUTLINE_BASE_URL environment variable or pass it directly."
            )
        if not self.api_token:
            raise ValueError(
                "Outline API token is required. Set OUTLINE_API_KEY environment variable or pass it directly."
            )

        self.base_url = self.base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _make_request(
        self, endpoint: str, method: str = "GET", params: Optional[dict] = None, data: Optional[dict] = None
    ) -> dict:
        url = f"{self.base_url}/api/{endpoint.lstrip('/')}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method=method, url=url, headers=self.headers, params=params, json=data, timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.warning(f"HTTP status error calling Outline API: {e}")
                raise
            except httpx.RequestError as e:
                logger.warning(f"Request error calling Outline API: {e}")
                raise

    async def get_doc(self, id_or_url: str) -> dict:
        doc_id = id_or_url.strip("/").split("/")[-1]
        result = await self._make_request("documents.info", method="POST", data={"id": doc_id})
        return result.get("data")

    async def search_docs(
        self,
        query: str,
        *,
        offset: int = 0,
        limit: int = 20,
        collection_id: Optional[str] = None,
        document_id: Optional[str] = None,
    ) -> dict:
        params = {"query": query, "offset": offset, "limit": limit, "statusFilter": ["published"]}
        if collection_id:
            params["collectionId"] = collection_id
        if document_id:
            params["documentId"] = document_id
        return await self._make_request("documents.search", method="POST", data=params)


outline = OutlineClient()
