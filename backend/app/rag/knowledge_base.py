from __future__ import annotations

import re
import uuid
import os
from pathlib import Path
from typing import Any

import chromadb

from backend.app.core.config import BASE_DIR, CHROMA_DB_DIR


class KnowledgeBase:
    """Local RAG layer for support policies and FAQs."""

    def __init__(self, persist_directory: str | None = None, *, enable_embeddings: bool | None = None) -> None:
        self.persist_directory = persist_directory or CHROMA_DB_DIR
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        self.collection = self.client.get_or_create_collection(name="support_knowledge")
        self.enable_embeddings = enable_embeddings if enable_embeddings is not None else (
            os.getenv("RAG_EMBEDDINGS_ENABLED", "true").casefold() == "true"
        )
        self._documents: list[str] = []
        self._metadatas: list[dict[str, str]] = []
        self._embedder: Any = None
        self._index_ready = False
        self._embedding_unavailable = False

    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 80) -> list[str]:
        words = text.split()
        chunks: list[str] = []
        for index in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[index:index + chunk_size])
            if chunk:
                chunks.append(chunk)
        return chunks or [text]

    def ingest_files(self, file_paths: list[str | Path], source_name: str | None = None) -> None:
        documents: list[str] = []
        metadatas: list[dict[str, str]] = []
        for raw_path in file_paths:
            path = Path(raw_path)
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            source = source_name or path.name
            for chunk in self._chunk_text(text):
                documents.append(chunk)
                metadatas.append({"source": source})
        if not documents:
            return
        self._documents.extend(documents)
        self._metadatas.extend(metadatas)
        self._index_ready = False

    def _vector_search(self, query: str, k: int) -> list[dict[str, str]] | None:
        if not self.enable_embeddings or self._embedding_unavailable:
            return None
        try:
            if self._embedder is None:
                from sentence_transformers import SentenceTransformer

                self._embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
            if not self._index_ready and self._documents:
                embeddings = self._embedder.encode(self._documents, convert_to_numpy=True).tolist()
                self.collection.add(
                    documents=self._documents,
                    metadatas=self._metadatas,
                    embeddings=embeddings,
                    ids=[f"doc-{uuid.uuid4().hex}" for _ in self._documents],
                )
                self._index_ready = True
            query_embedding = self._embedder.encode([query], convert_to_numpy=True).tolist()[0]
            result = self.collection.query(query_embeddings=[query_embedding], n_results=k)
            return [
                {
                    "source": metadata.get("source", "unknown"),
                    "text": text,
                }
                for idx, text in enumerate(result.get("documents", [[]])[0])
                for metadata in [result.get("metadatas", [[]])[0][idx] or {}]
            ]
        except Exception:
            self._embedding_unavailable = True
            return None

    def _lexical_search(self, query: str, k: int) -> list[dict[str, str]]:
        query_terms = set(re.findall(r"[a-z0-9]+", query.casefold()))
        ranked = []
        for document, metadata in zip(self._documents, self._metadatas):
            document_terms = set(re.findall(r"[a-z0-9]+", document.casefold()))
            overlap = len(query_terms & document_terms)
            if overlap:
                ranked.append((overlap, metadata.get("source", "unknown"), document))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [{"source": source, "text": text} for _, source, text in ranked[:k]]

    def search(self, query: str, k: int = 3) -> dict[str, Any]:
        if not query.strip():
            return {"ok": False, "error": {"code": "invalid_query", "message": "A search query is required."}}
        items = self._vector_search(query, k) or self._lexical_search(query, k)
        return {"ok": True, "results": items}


def ingest_default_knowledge(knowledge_base: KnowledgeBase) -> None:
    knowledge_dir = BASE_DIR / "data" / "knowledge"
    files = list(knowledge_dir.glob("*.md")) if knowledge_dir.exists() else []
    if not files:
        policy_path = BASE_DIR / "data" / "policies.txt"
        if policy_path.exists():
            files = [policy_path]
    if not files:
        return
    knowledge_base.ingest_files(files)
