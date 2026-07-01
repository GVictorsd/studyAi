"""
Textbook Knowledge Agent — dedicated agent for textbook indexing and retrieval.

Responsible for:
  - Section-aware chunking with chapter/section metadata
  - Indexing chunks into ChromaDB via VectorStoreService
  - Per-question targeted retrieval (not whole-exam retrieval)
"""
import re
from dataclasses import dataclass, field

from app.services.vector_store import vector_store


@dataclass
class KnowledgeChunk:
    content: str
    chapter: str
    section: str
    chunk_index: int


@dataclass
class KnowledgeResult:
    query: str
    chunks: list[KnowledgeChunk] = field(default_factory=list)

    def formatted_context(self) -> str:
        if not self.chunks:
            return "No relevant textbook material found."
        parts = []
        for chunk in self.chunks:
            if chunk.chapter or chunk.section:
                header = f"[{chunk.chapter} \u203a {chunk.section}]"
                parts.append(f"{header}\n{chunk.content}")
            else:
                parts.append(chunk.content)
        return "\n\n---\n\n".join(parts)


@dataclass
class _TextSection:
    chapter: str
    section: str
    content: str


class TextbookKnowledgeAgent:
    """
    Dedicated agent that owns the full textbook knowledge lifecycle:
    section-aware indexing and per-question targeted retrieval.

    Unlike embedding RAG inside EvaluationAgent, this agent:
    - Stores chapter/section metadata alongside each chunk
    - Queries once per question (not once per whole exam)
    - Can be reused by any agent that needs textbook grounding
    """

    CHUNK_SIZE = 600
    CHUNK_OVERLAP = 80

    def index(self, textbook_id: str, text: str) -> str:
        """
        Parse textbook into sections, chunk each section with metadata,
        and store in ChromaDB. Returns the collection name.
        """
        collection_name = f"textbook_{textbook_id}"
        sections = self._parse_sections(text)

        all_chunks: list[str] = []
        all_metadatas: list[dict] = []

        for section in sections:
            words = section.content.split()
            start = 0
            while start < len(words):
                end = min(start + self.CHUNK_SIZE, len(words))
                all_chunks.append(" ".join(words[start:end]))
                all_metadatas.append({
                    "textbook_id": textbook_id,
                    "chapter": section.chapter,
                    "section": section.section,
                })
                start += self.CHUNK_SIZE - self.CHUNK_OVERLAP

        if all_chunks:
            vector_store.index_with_metadata(collection_name, all_chunks, all_metadatas)

        return collection_name

    def retrieve(
        self,
        query: str,
        collection_name: str,
        n_results: int = 3,
    ) -> KnowledgeResult:
        """Retrieve the most relevant chunks for a single query string."""
        raw = vector_store.query_with_metadata(collection_name, query, n_results)
        chunks = [
            KnowledgeChunk(
                content=item["document"],
                chapter=item["metadata"].get("chapter", ""),
                section=item["metadata"].get("section", ""),
                chunk_index=i,
            )
            for i, item in enumerate(raw)
        ]
        return KnowledgeResult(query=query, chunks=chunks)

    def retrieve_for_questions(
        self,
        questions: list[str],
        collection_name: str,
        n_results: int = 3,
    ) -> list[KnowledgeResult]:
        """
        Issue a separate retrieval query per question so each question
        gets its own targeted textbook context instead of one averaged
        result for the whole exam.
        """
        return [self.retrieve(q, collection_name, n_results) for q in questions]

    # ------------------------------------------------------------------
    # Section parsing
    # ------------------------------------------------------------------

    def _parse_sections(self, text: str) -> list[_TextSection]:
        """
        Detect chapter/section headings and split text accordingly.
        Falls back to treating the entire text as one section when no
        headings are detected (e.g. plain-text dumps without structure).
        """
        lines = text.split("\n")
        sections: list[_TextSection] = []
        current_chapter = "Introduction"
        current_section = "General"
        buffer: list[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            if self._is_heading(stripped):
                if buffer:
                    sections.append(_TextSection(
                        chapter=current_chapter,
                        section=current_section,
                        content=" ".join(buffer),
                    ))
                    buffer = []

                if self._is_chapter_heading(stripped):
                    current_chapter = stripped
                    current_section = stripped
                else:
                    current_section = stripped
            else:
                buffer.append(stripped)

        if buffer:
            sections.append(_TextSection(
                chapter=current_chapter,
                section=current_section,
                content=" ".join(buffer),
            ))

        if not sections:
            return [_TextSection(
                chapter="Textbook",
                section="Full Content",
                content=text,
            )]

        return sections

    def _is_heading(self, line: str) -> bool:
        if len(line) > 120:
            return False
        # Numbered: "1.", "1.2", "1.2.3" followed by text
        if re.match(r'^\d+(?:\.\d+)*\.?\s+\S', line):
            return True
        # Keyword-prefixed: "Chapter 3 ...", "Section 2 ...", "Unit 4 ..."
        if re.match(r'^(?:chapter|unit|section|part)\s+\w', line, re.IGNORECASE):
            return True
        # ALL-CAPS short line (common heading style in scanned PDFs)
        if line.isupper() and 4 <= len(line) <= 80:
            return True
        return False

    def _is_chapter_heading(self, line: str) -> bool:
        lower = line.lower()
        return (
            lower.startswith(("chapter", "unit", "part"))
            or re.match(r'^\d+\.\s+\S', line) is not None
        )


textbook_knowledge_agent = TextbookKnowledgeAgent()
