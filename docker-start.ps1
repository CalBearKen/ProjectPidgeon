# Quick start script for Pidgeon Protocol with Docker

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Pidgeon Protocol - Docker Quick Start" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
try {
    docker info | Out-Null
    Write-Host "✓ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker is not running" -ForegroundColor Red
    Write-Host "  Please start Docker Desktop and try again" -ForegroundColor Yellow
    exit 1
}

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "✗ .env file not found" -ForegroundColor Red
    Write-Host "  Creating .env from template..." -ForegroundColor Yellow
    
    if (Test-Path "env.template") {
        Copy-Item "env.template" ".env"
        Write-Host "  Created .env file" -ForegroundColor Green
        Write-Host ""
        Write-Host "  ⚠ IMPORTANT: Edit .env and add your API keys!" -ForegroundColor Yellow
        Write-Host "  Then run this script again." -ForegroundColor Yellow
        Write-Host ""
        notepad .env
        exit 0
    } else {
        Write-Host "  env.template not found!" -ForegroundColor Red
        exit 1
    }
}

# Check if API key is set
$envContent = Get-Content ".env" -Raw
if ($envContent -match "your_openai_api_key_here" -or $envContent -match "your_anthropic_api_key_here") {
    Write-Host "⚠ Warning: API keys look like placeholders" -ForegroundColor Yellow
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne "y") {
        notepad .env
        exit 0
    }
}

Write-Host ""
Write-Host "Starting Pidgeon Protocol services..." -ForegroundColor Cyan
Write-Host ""

# Start services
docker-compose up -d --build

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "================================================" -ForegroundColor Green
    Write-Host "  ✓ All services started successfully!" -ForegroundColor Green
    Write-Host "================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Services running:" -ForegroundColor Cyan
    docker-compose ps
    Write-Host ""
    Write-Host "View logs:" -ForegroundColor Yellow
    Write-Host "  docker-compose logs -f" -ForegroundColor White
    Write-Host ""
    Write-Host "Submit a test request:" -ForegroundColor Yellow
    Write-Host "  docker-compose exec planner python examples/document_pipeline/run_demo.py" -ForegroundColor White
    Write-Host ""
    Write-Host "Stop all services:" -ForegroundColor Yellow
    Write-Host "  docker-compose down" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "✗ Failed to start services" -ForegroundColor Red
    Write-Host "Check logs: docker-compose logs" -ForegroundColor Yellow
    Write-Host ""
}

