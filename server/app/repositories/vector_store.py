"""ChromaDB vector store integration for deduplication workflows."""
from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Iterable, List, Sequence

import chromadb
from chromadb.api.client import ClientAPI
from chromadb.api.models.Collection import Collection

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class ChromaVectorStore:
    """Manage ChromaDB client lifecycle and operations."""

    def __init__(self) -> None:
        self._client: ClientAPI | None = None
        self._collection: Collection | None = None
        self._lock = asyncio.Lock()

    async def ainit(self) -> None:
        """Initialise the ChromaDB client and target collection."""
        async with self._lock:
            if self._client is not None:
                return

            settings = get_settings()
            logger.info(
                "Connecting to ChromaDB at %s:%s", settings.chroma_host, settings.chroma_port
            )
            self._client = await asyncio.to_thread(
                chromadb.HttpClient,
                host=settings.chroma_host,
                port=settings.chroma_port,
            )
            self._collection = await asyncio.to_thread(
                self._client.get_or_create_collection,
                name=settings.chroma_collection,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("ChromaDB collection ready: %s", settings.chroma_collection)

    async def aclose(self) -> None:
        """Close the ChromaDB client if initialised."""
        async with self._lock:
            if self._client is None:
                return
            await asyncio.to_thread(self._client.reset)
            self._client = None
            self._collection = None

    async def upsert_rows(self, rows: Sequence[str]) -> None:
        """Insert hashes of dataset rows for deduplication tracking."""
        if not rows:
            return
        collection = await self._get_collection()
        ids = [self._hash_row(row) for row in rows]
        await asyncio.to_thread(collection.upsert, ids=ids, documents=list(rows))

    async def find_duplicates(self, rows: Iterable[str]) -> List[str]:
        """Return the subset of rows already present in ChromaDB."""
        collection = await self._get_collection()
        serialized = list(rows)
        if not serialized:
            return []
        ids = [self._hash_row(row) for row in serialized]
        result = await asyncio.to_thread(
            collection.get,
            ids=ids,
        )
        found_ids = set(result.get("ids", []))
        return [row for row, row_id in zip(serialized, ids) if row_id in found_ids]

    async def _get_collection(self) -> Collection:
        if self._collection is None:
            raise RuntimeError("Chroma collection not initialised")
        return self._collection

    @staticmethod
    def _hash_row(row: str) -> str:
        return hashlib.sha256(row.encode("utf-8")).hexdigest()


_store = ChromaVectorStore()


def get_vector_store() -> ChromaVectorStore:
    """Return singleton vector store reference."""
    return _store
