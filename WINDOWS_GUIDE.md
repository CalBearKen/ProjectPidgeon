# Running Pidgeon Protocol on Windows

Complete guide for running Pidgeon Protocol on Windows 10/11.

## Prerequisites

### 1. Install Python 3.11+

Download from [python.org](https://www.python.org/downloads/) or use winget:

```powershell
winget install Python.Python.3.11
```

Verify installation:
```powershell
python --version
```

### 2. Optional: Install Redis (for production mode)

**Option A: Using WSL2 (Recommended)**
```powershell
# Install WSL2 if not already installed
wsl --install

# In WSL terminal:
sudo apt-get update
sudo apt-get install redis-server
sudo service redis-server start
```

**Option B: Windows Native (Memurai)**
Download from [memurai.com](https://www.memurai.com/) - Redis-compatible for Windows

**Option C: Docker Desktop**
```powershell
docker run -d -p 6379:6379 redis:latest
```

**For Development**: Skip Redis and use in-memory queues (default)!

## Installation

### 1. Open PowerShell as Administrator (optional, for system-wide install)

Or just use regular PowerShell for user install.

### 2. Navigate to Project Directory

```powershell
cd C:\Projects\Pidgeon
```

### 3. Create Virtual Environment

```powershell
python -m venv venv
```

### 4. Activate Virtual Environment

```powershell
.\venv\Scripts\Activate.ps1
```

**If you get an execution policy error:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\venv\Scripts\Activate.ps1
```

You should see `(venv)` in your prompt.

### 5. Install Dependencies

```powershell
pip install -e .
```

### 6. Create Environment File

```powershell
Copy-Item env.template .env
notepad .env
```

Add your API key:
```
OPENAI_API_KEY=sk-your-actual-key-here
```

Save and close.

## Running the System

### Option 1: Quick Test with In-Memory Queues (Recommended for First Run)

Open **5 separate PowerShell windows**, activate venv in each, then run:

**Terminal 1 - Planner:**
```powershell
cd C:\Projects\Pidgeon
.\venv\Scripts\Activate.ps1
python -m pidgeon.planner
```

**Terminal 2 - Interpreter:**
```powershell
cd C:\Projects\Pidgeon
.\venv\Scripts\Activate.ps1
python -m pidgeon.interpreter
```

**Terminal 3 - Extraction Agent:**
```powershell
cd C:\Projects\Pidgeon
.\venv\Scripts\Activate.ps1
python -m pidgeon.agents --type extraction
```

**Terminal 4 - Summarization Agent:**
```powershell
cd C:\Projects\Pidgeon
.\venv\Scripts\Activate.ps1
python -m pidgeon.agents --type summarization
```

**Terminal 5 - Submit Request:**
```powershell
cd C:\Projects\Pidgeon
.\venv\Scripts\Activate.ps1
python examples\document_pipeline\run_demo.py
```

You should see messages flowing through each component!

### Option 2: Using Windows Terminal (Easier!)

If you have [Windows Terminal](https://aka.ms/terminal):

1. Open Windows Terminal
2. Split into 5 panes (Alt+Shift+Plus or Alt+Shift+Minus)
3. Run each command in a different pane

### Option 3: PowerShell Script (All in Background)

Create `run_all.ps1`:

```powershell
# Save this as run_all.ps1
Write-Host "Starting Pidgeon Protocol Components..." -ForegroundColor Green

$jobs = @()

# Start each component as background job
$jobs += Start-Job -ScriptBlock {
    Set-Location C:\Projects\Pidgeon
    .\venv\Scripts\Activate.ps1
    python -m pidgeon.planner
}
Write-Host "Started Planner" -ForegroundColor Cyan

$jobs += Start-Job -ScriptBlock {
    Set-Location C:\Projects\Pidgeon
    .\venv\Scripts\Activate.ps1
    python -m pidgeon.interpreter
}
Write-Host "Started Interpreter" -ForegroundColor Cyan

$jobs += Start-Job -ScriptBlock {
    Set-Location C:\Projects\Pidgeon
    .\venv\Scripts\Activate.ps1
    python -m pidgeon.agents --type extraction
}
Write-Host "Started Extraction Agent" -ForegroundColor Cyan

$jobs += Start-Job -ScriptBlock {
    Set-Location C:\Projects\Pidgeon
    .\venv\Scripts\Activate.ps1
    python -m pidgeon.agents --type summarization
}
Write-Host "Started Summarization Agent" -ForegroundColor Cyan

Start-Sleep -Seconds 3
Write-Host "`nAll components started. Submitting demo request..." -ForegroundColor Green

# Run demo
.\venv\Scripts\Activate.ps1
python examples\document_pipeline\run_demo.py

Write-Host "`nPress Enter to view component outputs..." -ForegroundColor Yellow
Read-Host

# Show job outputs
foreach ($job in $jobs) {
    Write-Host "`n========== Job $($job.Id) Output ==========" -ForegroundColor Magenta
    Receive-Job -Job $job
}

Write-Host "`nPress Enter to stop all components..." -ForegroundColor Yellow
Read-Host

# Stop all jobs
$jobs | Stop-Job
$jobs | Remove-Job

Write-Host "All components stopped." -ForegroundColor Green
```

Run it:
```powershell
.\run_all.ps1
```

## Configuration for Windows

### In-Memory Mode (Default - No Redis Required)

The default `config\settings.yaml` is already set for in-memory:

```yaml
queue:
  backend: memory
```

This is perfect for development and testing!

### Redis Mode (Optional)

If you installed Redis, edit `config\settings.yaml`:

```yaml
queue:
  backend: redis
  redis:
    host: localhost  # or 127.0.0.1
    port: 6379
    db: 0
```

**For WSL2 Redis**, you might need:
```yaml
    host: localhost  # WSL2 automatically forwards
```

## Testing

```powershell
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with verbose output
pytest -v

# Run specific test
pytest tests\unit\test_models.py
```

## Troubleshooting

### Issue: "python: command not found"

Try `py` instead:
```powershell
py -m venv venv
py -m pip install -e .
```

### Issue: "Cannot load module ... is not digitally signed"

Run this in PowerShell as Administrator:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope LocalMachine
```

Or just for current user:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Issue: "No module named 'pidgeon'"

Make sure you:
1. Activated the virtual environment (`.\venv\Scripts\Activate.ps1`)
2. Installed in editable mode (`pip install -e .`)

### Issue: "Connection refused" (Redis)

If using Redis mode but Redis isn't running:
1. Start Redis (see installation section)
2. Or switch back to memory mode in `config\settings.yaml`

### Issue: "API key not configured"

1. Make sure `.env` file exists
2. Check it has `OPENAI_API_KEY=your-key`
3. No quotes needed around the key
4. Restart components after changing `.env`

### Issue: Path too long errors

Windows has 260 character path limit. If you hit this:
1. Enable long paths: [Microsoft Guide](https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation)
2. Or move project closer to C:\ root

### Issue: Anti-virus blocking Python

Some anti-virus software blocks Python scripts:
1. Add exception for your project folder
2. Add exception for Python installation

## Using Windows Terminal (Recommended)

Windows Terminal makes multi-component testing much easier:

1. Install Windows Terminal from Microsoft Store
2. Open Windows Terminal
3. Create new tab: `Ctrl+Shift+T`
4. Split panes: `Alt+Shift+Plus` (horizontal) or `Alt+Shift+Minus` (vertical)
5. Navigate between panes: `Alt+Arrow Keys`

Layout suggestion:
```
┌──────────┬──────────┐
│ Planner  │Interpret │
├──────────┼──────────┤
│Extraction│  Summary │
├──────────┴──────────┤
│    Demo/Logs       │
└────────────────────┘
```

## Performance Tips

### Use Windows Terminal instead of cmd.exe
- Better performance
- Multiple panes
- Better Unicode support

### Close unused applications
- LLM operations are memory-intensive
- Close browser tabs, etc.

### Use SSD for virtual environment
- Much faster package installs
- Better Python performance

## Next Steps

1. ✅ **Verify it works**: Run the demo and see components communicate
2. 📚 **Learn the architecture**: Read `README.md` and `design.md`
3. 🔧 **Create custom agent**: Follow `QUICKSTART.md` guide
4. 🚀 **Deploy with Redis**: Switch backend when ready

## Quick Command Reference

```powershell
# Activate venv
.\venv\Scripts\Activate.ps1

# Deactivate venv
deactivate

# Run component
python -m pidgeon.planner
python -m pidgeon.interpreter
python -m pidgeon.supervisor
python -m pidgeon.agents --type extraction

# Run tests
pytest

# Format code
black pidgeon\

# Check types
mypy pidgeon\
```

## Getting Help

- Check `README.md` for general documentation
- Check `QUICKSTART.md` for quick start guide
- Open issue on GitHub
- Check logs in component output

---

**You're all set! Happy building on Windows! 🪟🕊️**

