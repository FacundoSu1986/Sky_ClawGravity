# LangChain/LangGraph Implementation Playbook

This playbook provides concrete, production-grade examples and verification steps for building sophisticated AI agent systems following the patterns defined in `SKILL.md`.

## Core Implementation Examples

### 1. Robust Late-Stage State Graph
This pattern implements a non-linear workflow with state-based routing and persistent checkpointers.

```python
import operator
from typing import Annotated, Sequence, TypedDict, Union, Literal
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

# Define persistent state
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    intermediate_steps: Annotated[list, operator.add]
    error_count: int

# Initialize LLM with Claude Sonnet 4.5
model = ChatAnthropic(model="claude-3-7-sonnet-20250219", temperature=0)

async def call_model(state: AgentState):
    response = await model.ainvoke(state["messages"])
    return {"messages": [response]}

# Build the Graph
workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_edge(START, "agent")
workflow.add_edge("agent", END)

# Compile with checkpointer for persistence
checkpointer = MemorySaver()
app = workflow.compile(checkpointer=checkpointer)
```

### 2. High-Performance RAG with Voyage AI
Official recommendation for Claude: Use Voyage AI embeddings for superior semantic resonance.

```python
from langchain_voyageai import VoyageAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CohereRerank

# Initialize Embeddings
embeddings = VoyageAIEmbeddings(model="voyage-3-large")

# Setup Hybrid Search (Example using Pinecone)
vectorstore = PineconeVectorStore(index_name="my-index", embedding=embeddings)

# Implement Reranking for Precision
compressor = CohereRerank(model="rerank-english-v3.0")
compression_retriever = ContextualCompressionRetriever(
    base_compressor=compressor, 
    base_retriever=vectorstore.as_retriever(search_kwargs={"k": 10})
)
```

### 3. Async-First Tool Integration
Standardized tool pattern with robust error handling and structured output.

```python
from langchain_core.tools import tool
from pydantic import BaseModel, Field

class SearchInput(BaseModel):
    query: str = Field(description="Search query to perform")

@tool("web_search", args_schema=SearchInput)
async def web_search(query: str):
    """Perform a web search for real-time information."""
    try:
        # Implementation of external tool call
        result = await my_search_api.search(query)
        return result
    except Exception as e:
        return f"Tool Error: {str(e)} - Please fallback to direct reasoning."
```

## Production Checklist & Verification

### ✅ Phase 1: Foundation
- [ ] **Model Selection**: Ensure `Claude-3.7-Sonnet` or `Claude-3-5-Sonnet` is used.
- [ ] **Infrastructure**: Environment variables loaded (`ANTHROPIC_API_KEY`, `VOYAGE_API_KEY`).
- [ ] **Observability**: Set `LANGSMITH_TRACING=true` and `LANGSMITH_API_KEY`.

### ✅ Phase 2: Implementation
- [ ] **Async Patterns**: Verify `ainvoke`, `astream`, and `aprocess` are used throughout.
- [ ] **Error Handling**: Every tool call wrapped in try/except.
- [ ] **Cost Efficiency**: Token limits set on memory buffers.

### ✅ Phase 3: Validation
- [ ] **Evaluation**: Run LangSmith evaluation suite using `qa` or `cot_qa` evaluators.
- [ ] **Streaming**: Test Server-Sent Events (SSE) for real-time UI updates.

## Troubleshooting Common Issues

| Issue | Potential Cause | Recommended Fix |
| :--- | :--- | :--- |
| **Max Token Limits** | Too many history messages | Use `ConversationTokenBufferMemory` |
| **Hallucination** | Low temperature or poor context | Implement Reranking and RAG Fusion |
| **Slow Latency** | Sequential blocking calls | Switch to `asyncio.gather` for independent nodes |
| **Checkpointer Issues** | Serialization error | Ensure all state objects are JSON-serializable |

---
*Follow these patterns to ensure scalability, observability, and premium performance.*
