"""
Textbook Knowledge Agent — owns the full textbook knowledge lifecycle.

Two distinct layers:

  1. ``TextbookKnowledgeAgent`` (plain Python class, no LLM)
     ─ Section-aware chunking with chapter/section metadata.
     ─ Indexing chunks into ChromaDB via VectorStoreService.
     ─ Per-query targeted retrieval used internally and by the ADK tool below.

  2. ``textbook_knowledge_adk_agent`` (Google ADK LlmAgent)
     ─ Wraps the retrieval capability as a first-class ADK agent.
     ─ Exposes ``retrieve_textbook_context`` as a FunctionTool so the model
       can decide *what* to query and *how many* results to request.
     ─ Can be embedded in other ADK agents as an AgentTool, allowing
       EvaluationAgent / StudyPlanAgent to call it as a sub-agent.
"""
import re
from dataclasses import dataclass, field

from google.adk.agents import LlmAgent

from app.services.vector_store import vector_store

_MODEL = "gemini-2.5-flash-lite-preview-06-17"


# ─────────────────────────────────────────────────────────────────────────────
# Data classes shared with other agents
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# Core indexing / retrieval class (no LLM, pure RAG)
# ─────────────────────────────────────────────────────────────────────────────

class TextbookKnowledgeAgent:
    """
    Owns the full textbook knowledge lifecycle: section-aware indexing and
    per-question targeted retrieval.

    This class is intentionally LLM-free — it is a deterministic RAG pipeline.
    The ADK agent layer (``textbook_knowledge_adk_agent``) wraps its retrieval
    method as a FunctionTool so a language model can call it on demand.
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
        gets its own targeted textbook context.
        """
        return [self.retrieve(q, collection_name, n_results) for q in questions]

    # ------------------------------------------------------------------
    # Section parsing
    # ------------------------------------------------------------------

    def _parse_sections(self, text: str) -> list[_TextSection]:
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
        if re.match(r'^\d+(?:\.\d+)*\.?\s+\S', line):
            return True
        if re.match(r'^(?:chapter|unit|section|part)\s+\w', line, re.IGNORECASE):
            return True
        if line.isupper() and 4 <= len(line) <= 80:
            return True
        return False

    def _is_chapter_heading(self, line: str) -> bool:
        lower = line.lower()
        return (
            lower.startswith(("chapter", "unit", "part"))
            or re.match(r'^\d+\.\s+\S', line) is not None
        )


# Module-level singleton used by the upload route and orchestrator.
textbook_knowledge_agent = TextbookKnowledgeAgent()


# ─────────────────────────────────────────────────────────────────────────────
# ADK FunctionTool: bridges the RAG class into the agent framework
# ─────────────────────────────────────────────────────────────────────────────

def retrieve_textbook_context(query: str, collection_name: str, n_results: int = 3) -> str:
    """
    Retrieve relevant textbook passages for an academic query.

    Search the indexed textbook collection and return the most relevant
    passages with their chapter and section metadata. Use this whenever
    you need factual grounding from the course textbook.

    Args:
        query:           The academic question or topic to look up.
        collection_name: The ChromaDB collection ID for the textbook
                         (format: ``textbook_<uuid>``).
        n_results:       Number of passages to retrieve (default 3, max 5).

    Returns:
        Formatted string with chapter/section headers and passage text,
        or a message indicating no relevant material was found.
    """
    n_results = min(max(1, n_results), 5)
    result = textbook_knowledge_agent.retrieve(query, collection_name, n_results)
    return result.formatted_context()


# ─────────────────────────────────────────────────────────────────────────────
# ADK LlmAgent: the textbook knowledge agent as a first-class AI agent
# ─────────────────────────────────────────────────────────────────────────────

textbook_knowledge_adk_agent = LlmAgent(
    name="textbook_knowledge_agent",
    model=_MODEL,
    description=(
        "Retrieves relevant passages from an indexed course textbook. "
        "Given an academic question and a textbook collection name, returns "
        "the most relevant chapter excerpts with section metadata."
    ),
    instruction="""You are a textbook knowledge retrieval specialist.

Your sole job is to find and return the most relevant textbook passages
for the query you receive.

Instructions:
1. Parse the incoming request to identify the academic question/topic
   and the textbook collection_name.
2. Call retrieve_textbook_context with the query and collection_name.
3. Return the retrieved passages verbatim — do NOT summarise, paraphrase,
   or add commentary. The caller needs the raw textbook text for grounding.
4. If no relevant material is found, say so clearly.

You MUST call the retrieve_textbook_context tool. Do not answer from
your own knowledge — always use the tool.""",
    tools=[retrieve_textbook_context],
)
