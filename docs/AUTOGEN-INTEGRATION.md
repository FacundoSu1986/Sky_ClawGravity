# AutoGen Integration - Sky_Claw

**Date**: 2026-04-03
**Status**: ✅ Implemented

## Overview

This document describes the integration of Microsoft AutoGen into Sky_Claw for multi-agent orchestration. The integration enables conversational interactions between specialized agents using the existing Sky_Claw infrastructure.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MultiAgentOrchestrator                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  GroupChat (AutoGen)                  │   │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐          │   │
│  │  │ Supervisor │ │  Scraper  │ │ Security  │          │   │
│  │  │   Agent    │ │   Agent   │ │   Agent   │          │   │
│  │  └─────┬─────┘ └─────┬─────┘ └─────┬─────┘          │   │
│  └────────┼─────────────┼─────────────┼────────────────┘   │
│           │             │             │                       │
│           v             v             v                       │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              ToolExecutor (Shared)                       ││
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       ││
│  │  │ AsyncTool   │ │  Semantic   │ │   Route     │       ││
│  │  │  Registry   │ │   Router    │ │Classification│       ││
│  │  └─────────────┘ └─────────────┘ └─────────────┘       ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. AutoGenConfig

Configuration class for AutoGen LLM settings.

```python
from sky_claw.agent.autogen_integration import AutoGenConfig

config = AutoGenConfig(
    model="gpt-4",
    api_key="your-api-key",
    temperature=0.7,
    max_tokens=2000
)
```

### 2. SkyClawConversableAgent

Abstract base class for conversational agents.

```python
class SkyClawConversableAgent(ABC):
    async def send_message(self, message: str, recipient: Optional['SkyClawConversableAgent'] = None) -> str
    async def receive_message(self, message: str, sender: 'SkyClawConversableAgent') -> str
    def get_history(self) -> List[Dict[str, Any]]
```

### 3. AutoGenWrapper

Wrapper for AutoGen agents that integrates with Sky_Claw infrastructure.

```python
from sky_claw.agent.autogen_integration import AutoGenWrapper, AutoGenConfig

# Create an assistant agent
agent = AutoGenWrapper(
    name="MyAgent",
    system_message="You are a helpful assistant.",
    agent_type="assistant",  # or "user_proxy"
    tool_executor=my_tool_executor,
    config=AutoGenConfig()
)

# Send a message
response = await agent.send_message("Hello!", recipient=other_agent)
```

### 4. MultiAgentOrchestrator

Orchestrates conversations between multiple agents.

```python
from sky_claw.agent.autogen_integration import (
    MultiAgentOrchestrator, AutoGenWrapper, AutoGenConfig
)

# Create agents
agents = [
    AutoGenWrapper(name="Agent1", system_message="...", agent_type="assistant"),
    AutoGenWrapper(name="Agent2", system_message="...", agent_type="assistant")
]

# Create orchestrator
orchestrator = MultiAgentOrchestrator(
    agents=agents,
    max_round=10
)

# Run conversation
results = await orchestrator.run_conversation(
    initial_message="Let's discuss the mod installation.",
    starter_agent=agents[0]
)
```

### 5. Factory Function

Pre-configured Sky_Claw agents factory.

```python
from sky_claw.agent.autogen_integration import create_sky_claw_agents, AutoGenConfig
from sky_claw.agent.lcel_chains import ToolExecutor

executor = ToolExecutor(tool_name="default", tool_description="Default executor")
agents = create_sky_claw_agents(
    tool_executor=executor,
    config=AutoGenConfig()
)

# agents["supervisor"] - SupervisorAgent
# agents["scraper"] - ScraperAgent
# agents["security"] - SecurityAgent
# agents["database"] - DatabaseAgent
```

### 6. Singleton Orchestrator

Global orchestrator instance with lazy initialization.

```python
from sky_claw.agent.autogen_integration import get_orchestrator

orchestrator = get_orchestrator(
    tool_executor=my_executor,
    config=AutoGenConfig()
)
```

## Graceful Degradation

When AutoGen is not installed, the module operates in **stub mode**:

- All classes function with reduced capabilities
- Conversations are simulated locally
- No external LLM calls are made
- Useful for testing and development without dependencies

```python
from sky_claw.agent.autogen_integration import AUTOGEN_AVAILABLE

if AUTOGEN_AVAILABLE:
    print("Full AutoGen capabilities available")
else:
    print("Running in stub mode - install pyautogen for full functionality")
```

## Installation

To enable full AutoGen functionality:

```bash
pip install pyautogen
```

## Usage Examples

### Example 1: Simple Two-Agent Conversation

```python
import asyncio
from sky_claw.agent.autogen_integration import (
    AutoGenWrapper, AutoGenConfig
)

async def main():
    config = AutoGenConfig(model="gpt-4")
    
    alice = AutoGenWrapper(
        name="Alice",
        system_message="You are Alice, a helpful assistant.",
        agent_type="assistant",
        config=config
    )
    
    bob = AutoGenWrapper(
        name="Bob",
        system_message="You are Bob, a technical expert.",
        agent_type="assistant",
        config=config
    )
    
    response = await alice.send_message(
        "Hi Bob, can you help me with mod installation?",
        recipient=bob
    )
    print(f"Bob's response: {response}")

asyncio.run(main())
```

### Example 2: Multi-Agent Task Orchestration

```python
import asyncio
from sky_claw.agent.autogen_integration import (
    create_sky_claw_agents, MultiAgentOrchestrator, AutoGenConfig
)
from sky_claw.agent.lcel_chains import ToolExecutor

async def main():
    executor = ToolExecutor(tool_name="sky_claw", tool_description="Sky_Claw tools")
    config = AutoGenConfig(model="gpt-4")
    
    # Create pre-configured agents
    agents = create_sky_claw_agents(executor, config)
    
    # Create orchestrator
    orchestrator = MultiAgentOrchestrator(
        agents=list(agents.values()),
        max_round=5
    )
    
    # Run multi-agent conversation
    results = await orchestrator.run_conversation(
        initial_message="Analyze the security of mod ID 12345",
        starter_agent=agents["supervisor"]
    )
    
    print(f"Conversation completed in {results['rounds']} rounds")
    for msg in results["messages"]:
        print(f"{msg.get('agent', 'unknown')}: {msg.get('content', '')[:100]}...")

asyncio.run(main())
```

### Example 3: Integration with LLMRouter

```python
from sky_claw.agent.router import LLMRouter
from sky_claw.agent.autogen_integration import get_orchestrator, AutoGenConfig
from sky_claw.core.schemas import RouteClassification

# Initialize router with AutoGen orchestrator
router = LLMRouter(
    provider=my_provider,
    tool_registry=my_registry
)

# Get orchestrator
orchestrator = get_orchestrator(
    tool_executor=router._lcel_tool_executor,
    config=AutoGenConfig()
)

# Route to appropriate agent based on classification
async def route_to_agent(message: str, classification: RouteClassification):
    if classification.target_agent:
        agent = orchestrator.get_agent(classification.target_agent)
        if agent:
            return await agent.send_message(message)
    return await orchestrator.run_conversation(message)
```

## Testing

Run the integration tests:

```bash
cd "Claude antigravity/Sky_Claw-main"
python tests/test_autogen_integration.py
```

## API Reference

### AutoGenConfig

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| model | str | "gpt-4" | LLM model identifier |
| api_key | Optional[str] | None | API key for LLM |
| base_url | Optional[str] | None | Base URL for LLM API |
| temperature | float | 0.7 | Sampling temperature |
| max_tokens | int | 2000 | Maximum tokens per response |
| timeout | int | 60 | Request timeout in seconds |

### AutoGenWrapper

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| name | str | required | Agent name |
| system_message | str | required | System prompt |
| agent_type | str | "assistant" | Agent type ("assistant" or "user_proxy") |
| tool_executor | Optional[Any] | None | ToolExecutor instance |
| config | Optional[AutoGenConfig] | None | LLM configuration |
| human_input_mode | str | "NEVER" | Human input mode |
| max_consecutive_auto_reply | int | 10 | Max auto replies |

### MultiAgentOrchestrator

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| agents | List[AutoGenWrapper] | required | List of agents |
| max_round | int | 10 | Maximum conversation rounds |
| route_classification_callback | Optional[Callable] | None | Callback for routing |

## Troubleshooting

### Import Error: No module named 'autogen'

Install AutoGen:
```bash
pip install pyautogen
```

### Stub Mode Issues

If running in stub mode unexpectedly:
1. Verify AutoGen installation: `pip show pyautogen`
2. Check import: `python -c "import autogen; print(autogen.__version__)"`
3. Restart Python environment

### Agent Communication Failures

1. Ensure all agents have valid configurations
2. Check that `tool_executor` is properly initialized
3. Verify network connectivity for LLM API calls

## Next Steps

- [ ] Implement Tree-of-Thought (Tarea 2.3)
- [ ] Implement LangGraph StateGraph (Tarea 3.1)
- [ ] Add streaming support for agent responses
- [ ] Implement agent memory persistence
