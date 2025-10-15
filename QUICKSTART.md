# Pidgeon Protocol - Quick Start Guide

Get started with the Pidgeon Protocol in 5 minutes!

## Prerequisites

- Python 3.11+
- API key for OpenAI or Anthropic (for LLM features)

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/pidgeon-protocol.git
cd pidgeon-protocol

# Install dependencies
pip install -e .

# Copy and configure environment
cp .env.example .env
```

Edit `.env` and add your API key:
```
OPENAI_API_KEY=your_key_here
```

## Run Your First Workflow

### Option 1: In-Memory Mode (No Redis Required)

The default configuration uses in-memory queues - perfect for getting started!

**Terminal 1 - Start Planner:**
```bash
python -m pidgeon.planner
```

**Terminal 2 - Start Interpreter:**
```bash
python -m pidgeon.interpreter
```

**Terminal 3 - Start Extraction Agent:**
```bash
python -m pidgeon.agents --type extraction
```

**Terminal 4 - Start Summarization Agent:**
```bash
python -m pidgeon.agents --type summarization
```

**Terminal 5 - Submit a Request:**
```bash
python examples/document_pipeline/run_demo.py
```

You should see messages flowing through the system in each terminal!

## What Just Happened?

1. **Demo script** submitted a document analysis request to the Input Queue
2. **Planner** decomposed it into EXTRACTION → SUMMARIZATION tasks
3. **Interpreter** validated and routed each task to the appropriate queue
4. **Extraction Agent** processed the extraction task
5. **Summarization Agent** processed the summarization task using an LLM
6. **Results** flowed back to the Planner for synthesis

## Next Steps

### Try Redis Backend

1. **Install and start Redis:**
```bash
# macOS
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# Windows
# Download from https://redis.io/download
```

2. **Update config/settings.yaml:**
```yaml
queue:
  backend: redis  # Change from memory to redis
```

3. **Restart all components** - they'll now use Redis Streams!

### Create Your Own Agent

```python
# my_custom_agent.py
from pidgeon.agents.base_agent import BaseAgent
from pidgeon.core.models import TaskType

class MyCustomAgent(BaseAgent):
    def __init__(self, agent_id, config, queue_factory):
        super().__init__(agent_id, TaskType.CUSTOM, config, queue_factory)
    
    async def process_task(self, task_payload):
        # Your custom logic here
        input_data = task_payload.get('input_data', {})
        
        # Process the data
        result = f"Processed: {input_data}"
        
        return {
            'output': result,
            'status': 'success'
        }
```

Run it:
```bash
python my_custom_agent.py
```

### Add a New Task Type

1. **Update `pidgeon/core/models.py`:**
```python
class TaskType(str, Enum):
    EXTRACTION = "EXTRACTION"
    SUMMARIZATION = "SUMMARIZATION"
    ANALYSIS = "ANALYSIS"
    CUSTOM = "CUSTOM"
    MY_NEW_TYPE = "MY_NEW_TYPE"  # Add this
```

2. **Update `config/agent_routing.yaml`:**
```yaml
task_types:
  MY_NEW_TYPE:
    queue: structured_task.my_new_type
    timeout_ms: 30000
    max_retries: 3
    priority: 5
```

3. **Create your agent** using the new task type!

## Common Commands

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=pidgeon

# Format code
black pidgeon/

# Type checking
mypy pidgeon/

# Run a specific agent type
python -m pidgeon.agents --type extraction --id my-agent-001

# Monitor with Supervisor
python -m pidgeon.supervisor
```

## Troubleshooting

### "No module named 'pidgeon'"

Make sure you installed in editable mode:
```bash
pip install -e .
```

### "Connection refused" (Redis)

If using Redis backend, ensure Redis is running:
```bash
redis-cli ping  # Should return PONG
```

Or switch back to in-memory mode in `config/settings.yaml`.

### "API key not configured"

Set your API key in `.env`:
```bash
OPENAI_API_KEY=your_key_here
```

## Architecture Overview

```
User Request
     ↓
Input Queue → Planner → Task Queue → Interpreter → Structured Task Queues
                ↑                                            ↓
                |                                         Agents
                |                                            ↓
                └─────────────── Result Queue ←──────────────┘
```

## Learn More

- **Full Documentation**: [README.md](README.md)
- **Architecture Details**: [design.md](design.md)
- **Contributing**: [CONTRIBUTING.md](CONTRIBUTING.md)
- **Examples**: [examples/](examples/)

## Get Help

- GitHub Issues: Report bugs or request features
- Discussions: Ask questions and share ideas
- Email: support@pidgeonprotocol.org

---

Happy building with Pidgeon Protocol! 🕊️


