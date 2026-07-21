"""
Knowledge Base with RAG (Retrieval-Augmented Generation)

Uses ChromaDB for vector storage and semantic search.
Provides document ingestion, embedding, and retrieval.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class Document:
    """A document in the knowledge base."""

    id: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None


@dataclass
class SearchResult:
    """A search result from the knowledge base."""

    document: Document
    score: float
    snippet: str = ""


class KnowledgeBase:
    """
    RAG-powered knowledge base using ChromaDB.

    Features:
    - Document ingestion (text, markdown, URLs)
    - Chunking with overlap for long documents
    - Semantic search via embeddings
    - Metadata filtering
    - Collection management
    """

    def __init__(
        self,
        chroma_host: str = "localhost",
        chroma_port: int = 8000,
        collection_name: str = "superagent_knowledge",
        embedding_model: str = "openai/text-embedding-3-small",
    ):
        self.chroma_host = chroma_host
        self.chroma_port = chroma_port
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self._client = None
        self._collection = None

    async def initialize(self) -> None:
        """Connect to ChromaDB and get/create collection."""
        import chromadb

        self._client = chromadb.HttpClient(
            host=self.chroma_host,
            port=self.chroma_port,
        )

        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        count = self._collection.count()
        logger.info(
            "knowledge_base_initialized",
            collection=self.collection_name,
            documents=count,
        )

    def _chunk_text(
        self,
        text: str,
        chunk_size: int = 1000,
        overlap: int = 200,
    ) -> list[str]:
        """Split text into overlapping chunks."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]

            # Try to break at sentence boundary
            if end < len(text):
                last_period = chunk.rfind(".")
                last_newline = chunk.rfind("\n")
                break_at = max(last_period, last_newline)
                if break_at > chunk_size * 0.5:
                    chunk = chunk[: break_at + 1]
                    end = start + break_at + 1

            chunks.append(chunk.strip())
            start = end - overlap

        return [c for c in chunks if c]

    def _make_id(self, content: str, source: str = "") -> str:
        """Generate a deterministic ID for a document chunk."""
        return hashlib.sha256(f"{source}:{content}".encode()).hexdigest()[:16]

    async def ingest_text(
        self,
        text: str,
        source: str = "manual",
        metadata: dict[str, Any] | None = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> int:
        """
        Ingest text into the knowledge base.

        Returns the number of chunks created.
        """
        if not self._collection:
            await self.initialize()

        chunks = self._chunk_text(text, chunk_size, chunk_overlap)
        if not chunks:
            return 0

        ids = []
        documents = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            doc_id = self._make_id(chunk, source)
            ids.append(f"{doc_id}_{i}")
            documents.append(chunk)
            metadatas.append({
                "source": source,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "ingested_at": time.time(),
                **(metadata or {}),
            })

        self._collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

        logger.info(
            "text_ingested",
            source=source,
            chunks=len(chunks),
            total_docs=self._collection.count(),
        )
        return len(chunks)

    async def ingest_file(
        self,
        file_path: str,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Ingest a file into the knowledge base."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        text = path.read_text(encoding="utf-8")
        file_metadata = {
            "filename": path.name,
            "file_path": str(path),
            "file_type": path.suffix,
            **(metadata or {}),
        }

        return await self.ingest_text(
            text,
            source=str(path),
            metadata=file_metadata,
        )

    async def search(
        self,
        query: str,
        n_results: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """
        Semantic search over the knowledge base.

        Args:
            query: Search query
            n_results: Number of results to return
            where: Metadata filter (ChromaDB where clause)

        Returns:
            List of SearchResult with document and relevance score
        """
        if not self._collection:
            await self.initialize()

        kwargs: dict[str, Any] = {
            "query_texts": [query],
            "n_results": n_results,
        }
        if where:
            kwargs["where"] = where

        results = self._collection.query(**kwargs)

        search_results = []
        if results and results["documents"]:
            for i, doc_text in enumerate(results["documents"][0]):
                doc = Document(
                    id=results["ids"][0][i] if results["ids"] else "",
                    content=doc_text,
                    metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                )
                # ChromaDB returns distances; convert to similarity score
                distance = results["distances"][0][i] if results["distances"] else 0
                score = 1.0 - distance  # cosine distance to similarity

                search_results.append(SearchResult(
                    document=doc,
                    score=score,
                    snippet=doc_text[:200],
                ))

        return search_results

    async def get_context(
        self,
        query: str,
        max_tokens: int = 3000,
        n_results: int = 5,
    ) -> str:
        """
        Get relevant context for RAG.

        Returns formatted text suitable for injection into LLM prompts.
        """
        results = await self.search(query, n_results=n_results)

        if not results:
            return ""

        context_parts = []
        total_chars = 0
        max_chars = max_tokens * 4  # rough token-to-char ratio

        for result in results:
            snippet = result.document.content
            if total_chars + len(snippet) > max_chars:
                break
            source = result.document.metadata.get("source", "unknown")
            context_parts.append(f"[Source: {source} | Relevance: {result.score:.2f}]\n{snippet}")
            total_chars += len(snippet)

        return "\n\n---\n\n".join(context_parts)

    async def delete_by_source(self, source: str) -> int:
        """Delete all documents from a specific source."""
        if not self._collection:
            await self.initialize()

        results = self._collection.get(where={"source": source})
        if results and results["ids"]:
            self._collection.delete(ids=results["ids"])
            count = len(results["ids"])
            logger.info("documents_deleted", source=source, count=count)
            return count
        return 0

    async def get_stats(self) -> dict[str, Any]:
        """Get knowledge base statistics."""
        if not self._collection:
            await self.initialize()

        count = self._collection.count()

        # Get unique sources
        all_docs = self._collection.get(include=["metadatas"])
        sources = set()
        if all_docs and all_docs["metadatas"]:
            for meta in all_docs["metadatas"]:
                if "source" in meta:
                    sources.add(meta["source"])

        return {
            "total_documents": count,
            "unique_sources": len(sources),
            "sources": list(sources),
            "collection": self.collection_name,
        }
