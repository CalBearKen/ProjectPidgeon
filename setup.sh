#!/bin/bash
# Pidgeon Protocol Setup Script

echo "=========================================="
echo "Pidgeon Protocol Setup"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.11"

if [[ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]]; then
    echo "❌ Error: Python 3.11+ required. Found: $python_version"
    exit 1
fi
echo "✅ Python version OK: $python_version"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
if [ -d "venv" ]; then
    echo "Virtual environment already exists, skipping..."
else
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✅ Virtual environment activated"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install -e . > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed"
else
    echo "❌ Error installing dependencies"
    exit 1
fi
echo ""

# Install dev dependencies
read -p "Install development dependencies? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    pip install -e ".[dev]" > /dev/null 2>&1
    echo "✅ Development dependencies installed"
fi
echo ""

# Setup environment file
echo "Setting up environment..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✅ Created .env file from template"
    echo "⚠️  Please edit .env and add your API keys"
else
    echo ".env file already exists, skipping..."
fi
echo ""

# Check Redis (optional)
echo "Checking Redis availability..."
if command -v redis-cli &> /dev/null; then
    if redis-cli ping > /dev/null 2>&1; then
        echo "✅ Redis is installed and running"
        echo "   You can use 'redis' backend in config/settings.yaml"
    else
        echo "⚠️  Redis is installed but not running"
        echo "   Start with: brew services start redis (macOS)"
        echo "   Or: sudo systemctl start redis (Linux)"
    fi
else
    echo "ℹ️  Redis not found - using in-memory queues (default)"
    echo "   Install Redis for production deployments:"
    echo "   - macOS: brew install redis"
    echo "   - Ubuntu: sudo apt-get install redis-server"
fi
echo ""

# Run tests
read -p "Run tests to verify installation? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Running tests..."
    pytest tests/unit/ -v
    if [ $? -eq 0 ]; then
        echo "✅ All tests passed"
    else
        echo "⚠️  Some tests failed"
    fi
fi
echo ""

echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env and add your API keys"
echo "2. Review config/settings.yaml"
echo "3. Run the demo: python examples/document_pipeline/run_demo.py"
echo "4. Read QUICKSTART.md for detailed instructions"
echo ""
echo "To activate the virtual environment in future:"
echo "  source venv/bin/activate"
echo ""
echo "Happy building! 🕊️"


