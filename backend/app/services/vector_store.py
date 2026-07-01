import uuid
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.core.config import settings


class VectorStoreService:
    """ChromaDB-backed vector store for textbook RAG retrieval."""

    _client: chromadb.ClientAPI | None = None

    def _get_client(self) -> chromadb.ClientAPI:
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=settings.CHROMA_PERSIST_DIR,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        return self._client

    def get_or_create_collection(self, collection_name: str) -> chromadb.Collection:
        client = self._get_client()
        return client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def index_textbook(self, textbook_id: str, text: str) -> str:
        """Chunk text and add to ChromaDB. Returns collection name."""
        collection_name = f"textbook_{textbook_id}"
        collection = self.get_or_create_collection(collection_name)

        chunks = self._chunk_text(text, chunk_size=800, overlap=100)
        if not chunks:
            return collection_name

        ids = [str(uuid.uuid4()) for _ in chunks]
        metadatas = [{"textbook_id": textbook_id, "chunk_index": i} for i in range(len(chunks))]

        collection.add(documents=chunks, ids=ids, metadatas=metadatas)
        return collection_name

    def query_textbook(self, collection_name: str, query: str, n_results: int = 5) -> list[str]:
        """Retrieve relevant chunks from a textbook collection."""
        try:
            collection = self.get_or_create_collection(collection_name)
            results = collection.query(
                query_texts=[query],
                n_results=min(n_results, collection.count()),
            )
            return results["documents"][0] if results["documents"] else []
        except Exception:
            return []

    def index_with_metadata(
        self,
        collection_name: str,
        chunks: list[str],
        metadatas: list[dict],
    ) -> None:
        """Add pre-chunked documents with custom metadata to a named collection."""
        collection = self.get_or_create_collection(collection_name)
        ids = [str(uuid.uuid4()) for _ in chunks]
        collection.add(documents=chunks, ids=ids, metadatas=metadatas)

    def query_with_metadata(
        self,
        collection_name: str,
        query: str,
        n_results: int = 3,
    ) -> list[dict]:
        """Query and return documents together with their stored metadata."""
        try:
            collection = self.get_or_create_collection(collection_name)
            count = collection.count()
            if count == 0:
                return []
            results = collection.query(
                query_texts=[query],
                n_results=min(n_results, count),
            )
            documents = results["documents"][0] if results["documents"] else []
            metadatas_list = results["metadatas"][0] if results["metadatas"] else []
            return [
                {"document": doc, "metadata": meta}
                for doc, meta in zip(documents, metadatas_list)
            ]
        except Exception:
            return []

    def _chunk_text(self, text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
        words = text.split()
        chunks: list[str] = []
        start = 0
        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunks.append(" ".join(words[start:end]))
            start += chunk_size - overlap
        return chunks


vector_store = VectorStoreService()
