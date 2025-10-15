# Docker Guide for Pidgeon Protocol

Run the entire Pidgeon Protocol system with a single command using Docker!

## Prerequisites

- Docker Desktop for Windows: [Download here](https://www.docker.com/products/docker-desktop/)
- Your OpenAI or Anthropic API key

## Quick Start (3 Steps!)

### 1. Create Environment File

```powershell
Copy-Item env.template .env
notepad .env
```

Add your API key:
```
OPENAI_API_KEY=sk-your-actual-key-here
```

### 2. Update Configuration for Redis

Edit `config\settings.yaml` and change the queue backend:

```yaml
queue:
  backend: redis  # Change from 'memory' to 'redis'
  redis:
    host: redis   # Use Docker service name
    port: 6379
    db: 0

state:
  backend: redis
  redis:
    host: redis   # Use Docker service name
    port: 6379
    db: 1
```

### 3. Start Everything!

```powershell
# Build and start all services
docker-compose up --build
```

That's it! All components are now running:
- ✅ Redis (message broker)
- ✅ LLM Planner
- ✅ Interpreter
- ✅ Supervisor
- ✅ 2x Extraction Agents
- ✅ 2x Summarization Agents
- ✅ 1x Analysis Agent

## Usage

### View Logs

**All components:**
```powershell
docker-compose logs -f
```

**Specific component:**
```powershell
docker-compose logs -f planner
docker-compose logs -f extraction-agent
docker-compose logs -f summarization-agent
```

### Submit a Request

**Option 1: Run demo script in container**
```powershell
docker-compose exec planner python examples/document_pipeline/run_demo.py
```

**Option 2: Run demo locally (if you have Python)**
```powershell
.\venv\Scripts\Activate.ps1
python examples\document_pipeline\run_demo.py
```

### Monitor Redis

```powershell
# Connect to Redis CLI
docker-compose exec redis redis-cli

# Inside Redis CLI:
KEYS pidgeon:*          # See all Pidgeon queues
XLEN pidgeon:stream:input    # Check input queue depth
XLEN pidgeon:stream:task     # Check task queue depth
MONITOR                      # Watch all Redis commands in real-time
```

### Scale Agents

Need more processing power? Scale up agents:

```powershell
# Scale extraction agents to 5 instances
docker-compose up -d --scale extraction-agent=5

# Scale summarization agents to 3 instances
docker-compose up -d --scale summarization-agent=3
```

### Stop Everything

```powershell
# Stop all services
docker-compose down

# Stop and remove volumes (clears Redis data)
docker-compose down -v
```

## Commands Reference

```powershell
# Start in background
docker-compose up -d

# Rebuild after code changes
docker-compose up --build

# Stop services
docker-compose stop

# Start stopped services
docker-compose start

# Restart a specific service
docker-compose restart planner

# View running services
docker-compose ps

# Remove everything
docker-compose down -v
```

## Development Workflow

### Code Changes

The containers mount your local code as volumes, so changes take effect immediately:

1. Edit code in `pidgeon/`
2. Restart the service: `docker-compose restart planner`
3. Changes are live!

### Configuration Changes

1. Edit `config/settings.yaml` or `config/agent_routing.yaml`
2. Restart affected services: `docker-compose restart planner interpreter`

### Add New Agent Type

1. Create new agent in `pidgeon/agents/my_new_agent.py`
2. Add service to `docker-compose.yml`:

```yaml
  my-new-agent:
    build: .
    command: python -m pidgeon.agents --type my_new_type
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./config:/app/config:ro
      - ./pidgeon:/app/pidgeon
    depends_on:
      redis:
        condition: service_healthy
```

3. Restart: `docker-compose up -d`

## Architecture Overview

```
┌─────────────────────────────────────┐
│         Docker Compose              │
│                                     │
│  ┌──────────┐  ┌──────────┐       │
│  │ Planner  │  │Interpret │       │
│  └────┬─────┘  └────┬─────┘       │
│       │             │              │
│       └──────┬──────┘              │
│              │                     │
│         ┌────▼────┐                │
│         │  Redis  │                │
│         └────┬────┘                │
│              │                     │
│     ┌────────┴────────┐            │
│     │                 │            │
│  ┌──▼───┐  ┌────▼────┐  ┌────▼──┐ │
│  │Agent │  │ Agent   │  │Agent  │ │
│  │ x2   │  │  x2     │  │  x1   │ │
│  └──────┘  └─────────┘  └───────┘ │
│                                     │
└─────────────────────────────────────┘
```

## Troubleshooting

### Docker not found

Install Docker Desktop: https://www.docker.com/products/docker-desktop/

### Port 6379 already in use

Another Redis instance is running:
```powershell
# Stop other Redis
docker ps  # Find Redis containers
docker stop <container_id>
```

Or change port in `docker-compose.yml`:
```yaml
redis:
  ports:
    - "6380:6379"  # Use 6380 instead
```

### Services won't start

Check logs:
```powershell
docker-compose logs
```

Common issues:
- Missing API key in `.env`
- Config file syntax errors
- Docker out of memory (increase in Docker Desktop settings)

### "Cannot connect to Redis"

Make sure Redis is healthy:
```powershell
docker-compose ps
# redis should show "healthy" status

# Check Redis logs
docker-compose logs redis
```

### Code changes not taking effect

Rebuild the images:
```powershell
docker-compose up --build
```

### High CPU/Memory usage

LLM operations are resource-intensive. Adjust Docker Desktop resources:
1. Docker Desktop → Settings → Resources
2. Increase CPU and Memory limits
3. Restart Docker Desktop

## Production Considerations

For production deployment:

1. **Use .env file properly**: Never commit `.env` to Git
2. **Resource limits**: Add to docker-compose.yml:
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '0.5'
         memory: 512M
   ```
3. **Health checks**: Already configured for Redis
4. **Logging**: Configure log aggregation (ELK stack, etc.)
5. **Secrets management**: Use Docker secrets or external secret managers
6. **Monitoring**: Add Prometheus + Grafana (see future enhancements)

## Kubernetes (Coming Soon)

For production-scale deployments, Kubernetes manifests are planned:

```bash
kubectl apply -f k8s/
```

This will include:
- Deployments for each component
- Services for networking
- ConfigMaps for configuration
- Secrets for API keys
- Horizontal Pod Autoscalers
- Ingress for external access

## Benefits of Docker Approach

✅ **One command to start everything**
✅ **Consistent environment** (no Python version issues)
✅ **Easy scaling** (add more agent instances)
✅ **Isolated** (doesn't affect your system)
✅ **Production-ready** (same containers dev to prod)
✅ **Easy cleanup** (one command to remove everything)

---

**You're now running Pidgeon Protocol like a pro! 🐳🕊️**

