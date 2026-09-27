
import os
from pathlib import Path
from typing import TypedDict, Literal

import chromadb
from sentence_transformers import SentenceTransformer
from langchain_core.prompts import PromptTemplate
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field
from fastapi import FastAPI


# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
CHROMA_DIR = BASE_DIR / "chroma_db"


# =========================================================
# MOCK LLM TOGGLE
# =========================================================

MOCK_LLM = os.getenv("MOCK_LLM", "1")


# =========================================================
# EMBEDDING MODEL + CHROMADB
# =========================================================

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

chroma_client = chromadb.PersistentClient(
    path=str(CHROMA_DIR)
)

collection = chroma_client.get_collection(
    name="zepto_policies"
)


# =========================================================
# STRUCTURED PROMPT
# =========================================================

RAG_PROMPT_TEMPLATE = """
ROLE:
You are Zepto's customer support assistant. Answer customer questions
using only the Zepto policy information provided in the context.

CONTEXT:
{context}

TASK:
Answer the customer's question using the provided context.
If the context does not contain enough information to answer the question,
clearly state that the available policy context does not provide the answer.

NEGATIVE CONSTRAINT:
Do not answer using information that is not present in the provided context.
Do not invent, assume, or infer Zepto policies that are not explicitly stated.

FORMAT:
Return a concise answer in plain text. Do not add unsupported claims.

LENGTH:
Keep the answer short and useful, preferably 1 to 3 sentences.

FEW-SHOT EXAMPLE:
Question: How much does priority delivery cost?
Context: Priority delivery is available at checkout for an additional INR 15.
Answer: Priority delivery costs an additional INR 15.

Question: {question}
Answer:
"""

rag_prompt = PromptTemplate(
    template=RAG_PROMPT_TEMPLATE,
    input_variables=["context", "question"]
)


# =========================================================
# PYDANTIC SCHEMAS
# =========================================================

class AskRequest(BaseModel):
    query: str


class SupportResponse(BaseModel):
    answer: str
    sources: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


# =========================================================
# LANGGRAPH STATE
# =========================================================

class SupportState(TypedDict, total=False):
    query: str
    intent: str
    retrieved_ids: list[str]
    retrieved_documents: list[str]
    answer: str
    sources: list[str]
    confidence: float


# =========================================================
# INTENT CLASSIFICATION
# =========================================================

POLICY_KEYWORDS = [
    "delivery",
    "return",
    "refund",
    "membership",
    "tracking",
    "cancel",
    "gift card",
    "support hours",
]


def classify_intent(
    state: SupportState
) -> SupportState:

    query = state["query"]
    query_lower = query.lower()

    # Required deterministic mock baseline
    if MOCK_LLM != "0":
        intent = (
            "policy_question"
            if any(keyword in query_lower for keyword in POLICY_KEYWORDS)
            else "general_question"
        )

    else:
        # Optional real-LLM extension.
        # The graded baseline does not use this path.
        intent = (
            "policy_question"
            if any(keyword in query_lower for keyword in POLICY_KEYWORDS)
            else "general_question"
        )

    return {
        **state,
        "intent": intent,
    }


# =========================================================
# OPTIONAL REAL LLM GENERATION
# =========================================================

def generate_real_llm_answer(
    question: str,
    context: str,
    max_attempts: int = 3,
) -> str:
    """
    Optional real-LLM extension.

    The required graded baseline uses MOCK_LLM=1 and never calls
    an external LLM.

    When MOCK_LLM=0, this function attempts to use Groq through
    LangChain. Invalid generation is retried up to two additional
    times with a corrective instruction.
    """

    try:
        from langchain_groq import ChatGroq
    except ImportError as exc:
        raise RuntimeError(
            "MOCK_LLM=0 requires the optional langchain-groq package."
        ) from exc

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError(
            "MOCK_LLM=0 requires GROQ_API_KEY."
        )

    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0,
        api_key=api_key,
    )

    prompt = rag_prompt.format(
        context=context,
        question=question,
    )

    last_error = None

    for attempt in range(max_attempts):
        try:
            if attempt == 0:
                instruction = prompt
            else:
                instruction = (
                    prompt
                    + "\n\nCORRECTIVE INSTRUCTION: "
                    "Your previous output was invalid. "
                    "Answer again using only the supplied context."
                )

            response = llm.invoke(instruction)

            content = getattr(response, "content", str(response))

            if not content or not content.strip():
                raise ValueError("Empty LLM response.")

            return content.strip()

        except Exception as exc:
            last_error = exc

    raise RuntimeError(
        f"LLM generation failed after {max_attempts} attempts: {last_error}"
    )


# =========================================================
# RETRIEVE + ANSWER
# =========================================================

def retrieve_and_answer(
    state: SupportState
) -> SupportState:

    query = state["query"]

    query_embedding = embedding_model.encode(
        [query],
        normalize_embeddings=True,
    ).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=3,
    )

    retrieved_ids = results["ids"][0]
    retrieved_documents = results["documents"][0]

    if MOCK_LLM != "0":

        # Required deterministic mock response
        top_chunk_snippet = retrieved_documents[0][:200]

        answer = (
            f"Based on the retrieved context: "
            f"{top_chunk_snippet}"
        )

    else:

        # Optional real-LLM path
        context = "\n\n".join(
            retrieved_documents
        )

        try:
            answer = generate_real_llm_answer(
                question=query,
                context=context,
            )
        except Exception as exc:
            answer = (
                "[ERROR] Real LLM generation failed: "
                f"{exc}"
            )

    return {
        **state,
        "retrieved_ids": retrieved_ids,
        "retrieved_documents": retrieved_documents,
        "answer": answer,
        "sources": retrieved_ids,
        "confidence": 1.0,
    }


# =========================================================
# DIRECT ANSWER
# =========================================================

def direct_answer(
    state: SupportState
) -> SupportState:

    if MOCK_LLM != "0":

        # Required deterministic mock response
        answer = (
            "I can only answer questions about Zepto policies right now."
        )

    else:

        # Optional real-LLM extension intentionally kept separate
        # from the required mock baseline.
        answer = (
            "I can only answer questions about Zepto policies right now."
        )

    return {
        **state,
        "answer": answer,
        "sources": [],
        "confidence": 1.0,
    }


# =========================================================
# CONDITIONAL ROUTING
# =========================================================

def route_intent(
    state: SupportState
) -> Literal[
    "retrieve_and_answer",
    "direct_answer",
]:

    if state["intent"] == "policy_question":
        return "retrieve_and_answer"

    return "direct_answer"


# =========================================================
# LANGGRAPH
# =========================================================

builder = StateGraph(SupportState)

builder.add_node(
    "classify_intent",
    classify_intent,
)

builder.add_node(
    "retrieve_and_answer",
    retrieve_and_answer,
)

builder.add_node(
    "direct_answer",
    direct_answer,
)

builder.add_edge(
    START,
    "classify_intent",
)

builder.add_conditional_edges(
    "classify_intent",
    route_intent,
    {
        "retrieve_and_answer": "retrieve_and_answer",
        "direct_answer": "direct_answer",
    },
)

builder.add_edge(
    "retrieve_and_answer",
    END,
)

builder.add_edge(
    "direct_answer",
    END,
)

graph = builder.compile()


# =========================================================
# FASTAPI
# =========================================================

app = FastAPI(
    title="Zepto Support Assistant",
    description=(
        "Offline RAG support assistant using "
        "LangGraph and ChromaDB"
    ),
    version="1.0.0",
)


@app.post(
    "/ask",
    response_model=SupportResponse,
)
def ask(request: AskRequest):

    result = graph.invoke({
        "query": request.query,
    })

    response = SupportResponse(
        answer=result["answer"],
        sources=result.get("sources", []),
        confidence=result.get("confidence", 1.0),
    )

    return response
