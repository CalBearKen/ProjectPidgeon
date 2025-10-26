
**Queue-centric, event-driven communication framework for multi-agent AI systems.**

The Pidgeon Protocol replaces brittle, synchronous agent-to-agent calls with asynchronous message queues, enabling fault isolation, independent scaling, and comprehensive observability for AI agent coordination.

###THIS FRAMEWORK HAS NOT BEEN PRODUCTION TESTED, FOR TESTING AND DEVELOPMENT ONLY

## Overview

The Pidgeon Protocol implements a message-queue-based coordination layer that allows AI agents across vendors, models, and frameworks to cooperate seamlessly, securely, and at scale. By decoupling intelligence from infrastructure, it establishes the foundation for an open coordination layer.

- **Design Documents**: [design.md](design.md), [PidgeonProtocol.md](PidgeonProtocol.md)
- **Academic Paper**: [queue_paper.md](queue_paper.md)
- **Requirements**: [requirements.md](requirements.md)

### Key Features

- **Asynchronous Message Passing** - Eliminates synchronous dependencies between agents
- **Fault Isolation** - Component failures don't cascade through the system
- **Independent Scaling** - Each component scales based on workload demand
- **Comprehensive Observability** - End-to-end tracing with correlation IDs
- **Protocol Agnostic** - Supports MCP, A2A, and ACP protocols
- **Queue Backend Flexibility** - In-memory for dev, Redis/Kafka for production

## Architecture

### Components

```
┌─────────────┐         ┌────────────┐         ┌──────────────┐
│   Input     │────────▶│  Planner   │────────▶│  Task Queue  │
│   Queue     │         │  (LLM)     │         └──────────────┘
└─────────────┘         └────────────┘                │
                              ▲                       ▼
                              │              ┌────────────────┐
                              │              │  Interpreter   │
                              │              └────────────────┘
                              │                       │
                        ┌─────────────┐              ▼
                        │   Result    │     ┌─────────────────┐
                        │   Queue     │◀────│ Structured Task │
                        └─────────────┘     │     Queues      │
                              ▲             └─────────────────┘
                              │                      │
                              │                      ▼
                              │             ┌─────────────────┐
                              │             │  Agent Pool     │
                              │             │  - Extraction   │
                              └─────────────│  - Summarization│
                                            │  - Analysis     │
                                            └─────────────────┘
                                                     
                        ┌─────────────────────────────────────┐
                        │          Supervisor                 │
                        │  (monitors all queues & agents)     │
                        └─────────────────────────────────────┘
                                  │           │
                          ┌───────┴───────┐   │
                          ▼               ▼   ▼
                   ┌──────────────┐  ┌─────────────┐
                   │ Dead Letter  │  │  Control    │
                   │    Queue     │  │   Queue     │
                   └──────────────┘  └─────────────┘
```

### Core Components

1. **LLM Planner** - Decomposes user requests into executable tasks, adapts plans based on results
2. **Interpreter** - Validates messages, enriches with routing metadata, transforms protocols
3. **Supervisor** - Monitors queues, enforces retry policies, detects anomalies
4. **Specialized Agents** - Stateless workers that process domain-specific tasks

### Queue Types

- **Input Queue** - User requests and external events
- **Task Queue** - High-level tasks from Planner
- **Structured Task Queue** - Validated, executable tasks for agents
- **Result Queue** - Agent outputs
- **Dead Letter Queue** - Failed messages for triage

## Installation

### Prerequisites

- Python 3.11 or higher
- Redis (optional, for production deployments)

### Install from Source

```bash
git clone https://github.com/CalBearKen/pidgeon-protocol.git
cd pidgeon-protocol
pip install -e .
```

### Install with Development Dependencies

```bash
pip install -e ".[dev]"
```

## Quick Start

### 🐳 Recommended: Docker (Easiest!)

**3 steps to get everything running:**

```bash
# 1. Create environment file
cp env.template .env
# Edit .env and add your OPENAI_API_KEY

# 2. Start everything with one command!
docker-compose up -d

# 3. Submit a test request
docker-compose exec planner python examples/document_pipeline/run_demo.py

# View logs
docker-compose logs -f

# Stop when done
docker-compose down
```

**Windows PowerShell:**
```powershell
# Even easier - automated script!
.\docker-start.ps1
```

See [DOCKER_GUIDE.md](DOCKER_GUIDE.md) for details.

---

### 🐍 Alternative: Local Python Installation

### 1. Configure Environment

Create a `.env` file:

```bash
cp env.template .env
# Edit .env and add your API keys
```

### 2. Configure Queue Backend

For development, use in-memory queues (default):

```yaml
# config/settings.yaml
queue:
  backend: memory
```

For production, use Redis:

```yaml
# config/settings.yaml
queue:
  backend: redis
  redis:
    host: localhost
    port: 6379
```

### 3. Run the Demo

#### Option A: Run All Components (Unix/Linux/Mac)

```bash
chmod +x examples/document_pipeline/run_all.sh
./examples/document_pipeline/run_all.sh
```

#### Option B: Run Components Individually

Terminal 1 - Planner:
```bash
python -m pidgeon.planner
```

Terminal 2 - Interpreter:
```bash
python -m pidgeon.interpreter
```

Terminal 3 - Extraction Agent:
```bash
python -m pidgeon.agents --type extraction
```

Terminal 4 - Summarization Agent:
```bash
python -m pidgeon.agents --type summarization
```

Terminal 5 - Analysis Agent:
```bash
python -m pidgeon.agents --type analysis
```

Terminal 6 - Supervisor (optional):
```bash
python -m pidgeon.supervisor
```

Terminal 7 - Submit Demo Request:
```bash
python examples/document_pipeline/run_demo.py
```

## Configuration

### Queue Backend Options

**In-Memory (Development)**
```yaml
queue:
  backend: memory
  memory:
    max_size: 10000
```

**Redis (Production)**
```yaml
queue:
  backend: redis
  redis:
    host: localhost
    port: 6379
    db: 0
    stream_prefix: pidgeon
    max_connections: 10
```

**Kafka (Enterprise - Coming Soon)**
```yaml
queue:
  backend: kafka
  kafka:
    brokers: ["localhost:9092"]
    topic_prefix: pidgeon
```

### Agent Routing

Configure task types and routing in `config/agent_routing.yaml`:

```yaml
task_types:
  EXTRACTION:
    queue: structured_task.extraction
    timeout_ms: 30000
    max_retries: 3
    priority: 5
```

### LLM Providers

Configure LLM providers in `config/settings.yaml`:

```yaml
llm:
  default_provider: openai
  providers:
    openai:
      api_key: ${OPENAI_API_KEY}
      model: gpt-4
    anthropic:
      api_key: ${ANTHROPIC_API_KEY}
      model: claude-3-sonnet
```

## Development

### Running Tests

```bash
pytest tests/
```

### Running Tests with Coverage

```bash
pytest --cov=pidgeon tests/
```

### Code Formatting

```bash
black pidgeon/ tests/
```

### Type Checking

```bash
mypy pidgeon/
```

## Architecture Details

### Message Format

All messages follow the Pidgeon Protocol envelope format:

```python
{
  "header": {
    "message_id": "uuid",
    "correlation_id": "uuid",
    "context_id": "urn:mcp:session-id",  # Optional MCP context
    "actor_role": "planner|interpreter|agent|supervisor",
    "task_type": "EXTRACTION|SUMMARIZATION|ANALYSIS",
    "priority": 5,                        # 1-10, higher is more urgent
    "ttl_ms": 30000,                      # Time to live
    "schema_version": "v1.0",
    "enqueue_ts": "2024-01-01T00:00:00Z",
    "retry_count": 0,
    "max_retries": 3
  },
  "payload": {
    "task_id": "uuid",
    "input_data": {},
    "output_data": {},
    "metadata": {}
  }
}
```

### Workflow Example

1. **User submits request**: "Analyze Q4 sales report"
2. **Planner decomposes** into tasks:
   - EXTRACTION: Extract data from report
   - SUMMARIZATION: Summarize key findings
   - ANALYSIS: Analyze trends
3. **Interpreter validates** each task and routes to appropriate queues
4. **Agents process** tasks concurrently:
   - Extraction Agent extracts data
   - Summarization Agent summarizes with LLM
   - Analysis Agent generates insights
5. **Results flow back** to Planner via Result Queue
6. **Planner synthesizes** final comprehensive response

### Error Handling

- **Transient Errors**: Automatic retry with exponential backoff
- **Permanent Errors**: Moved to Dead Letter Queue for manual triage
- **Circuit Breakers**: Supervisor pauses failing agents automatically
- **TTL Enforcement**: Expired messages moved to DLQ

### Observability

- **Correlation IDs**: Track requests end-to-end
- **Timestamps**: Enqueue and processing times logged
- **Queue Metrics**: Depth, throughput, latency monitored
- **Agent Stats**: Success rate, processing times tracked

## Protocol Extensibility

The Pidgeon Protocol supports multiple agent communication protocols:

- **MCP (Model Context Protocol)**: Context preservation across retries
- **A2A (Agent-to-Agent)**: Capability discovery and negotiation
- **ACP (Agent Communication Protocol)**: Streaming and multimodal content

## Production Deployment

### Docker Compose (Coming Soon)

```bash
docker-compose up -d
```

### Kubernetes (Coming Soon)

```bash
kubectl apply -f k8s/
```

### Scaling Patterns

1. **Horizontal Agent Scaling**: Add more agent instances for high load
2. **Queue Partitioning**: Distribute load across partitions
3. **Regional Distribution**: Deploy across regions for low latency

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[MIT License](LICENSE)

## Citation

If you use Pidgeon Protocol in your research, please cite:

```bibtex
@article{li2024pidgeon,
  title={A Queue-Based Redesign for Scalable, Resilient AI Coordination},
  author={Li, Jiarui},
  journal={arXiv preprint},
  year={2024}
}
```

## Roadmap

- [x] Core queue abstraction (Memory, Redis)
- [x] Planner, Interpreter, Supervisor components
- [x] Base agent framework with sample agents
- [x] Document analysis demo workflow
- [ ] Comprehensive test suite
- [ ] Kafka backend implementation
- [ ] Docker/Kubernetes deployment configs
- [ ] Web UI for monitoring and DLQ triage
- [ ] Formal protocol specification
- [ ] Multi-language SDKs (Go, TypeScript, Java)
- [ ] Enterprise features (encryption, federation)

## Links



## Support

- **Issues**: [GitHub Issues](https://github.com/CalBearKen/pidgeon-protocol/issues)
- **Discussions**: [GitHub Discussions](https://github.com/CalBearKen/pidgeon-protocol/discussions)
---

**I solumnly swear that I am up to no good.**




