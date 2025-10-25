# Contributing to Pidgeon Protocol

Thank you for your interest in contributing to the Pidgeon Protocol! This document provides guidelines and instructions for contributing.

## Code of Conduct

We are committed to providing a welcoming and inclusive environment. Please be respectful and constructive in all interactions.

## Getting Started

### Development Setup

1. **Fork and clone the repository**

```bash
git clone https://github.com/CalBearKen/pidgeon-protocol.git
cd pidgeon-protocol
```

2. **Create a virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install development dependencies**

```bash
pip install -e ".[dev]"
```

4. **Set up pre-commit hooks**

```bash
# Install pre-commit if not already installed
pip install pre-commit
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=pidgeon --cov-report=html

# Run specific test file
pytest tests/unit/test_models.py

# Run specific test
pytest tests/unit/test_models.py::TestMessageEnvelope::test_create_envelope
```

### Code Quality

We use several tools to maintain code quality:

```bash
# Format code
black pidgeon/ tests/

# Lint code
ruff check pidgeon/ tests/

# Type checking
mypy pidgeon/
```

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/yourusername/pidgeon-protocol/issues)
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python version, etc.)
   - Code samples or error messages

### Suggesting Features

1. Check [Discussions](https://github.com/yourusername/pidgeon-protocol/discussions) for existing proposals
2. Create a new discussion with:
   - Use case and motivation
   - Proposed solution
   - Alternatives considered
   - Impact on existing functionality

### Pull Requests

1. **Create a branch**

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

2. **Make your changes**

   - Write clear, documented code
   - Follow existing code style
   - Add tests for new functionality
   - Update documentation as needed

3. **Commit your changes**

```bash
git add .
git commit -m "feat: add new queue backend for Kafka"
```

Use conventional commits:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Test additions or changes
- `refactor:` - Code refactoring
- `perf:` - Performance improvements
- `chore:` - Build process or auxiliary tool changes

4. **Push and create PR**

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub with:
- Clear description of changes
- Link to related issues
- Screenshots/examples if applicable
- Test results

## Development Guidelines

### Code Style

- Follow PEP 8 with 100 character line length
- Use type hints for all function signatures
- Write docstrings for all public APIs
- Keep functions focused and small

### Testing

- Write unit tests for all new functionality
- Maintain or improve code coverage
- Use descriptive test names
- Test both success and error cases

### Documentation

- Update README.md for user-facing changes
- Update docstrings for code changes
- Add examples for new features
- Update configuration documentation

### Architecture

- Maintain separation of concerns
- Keep components loosely coupled
- Use dependency injection
- Follow the queue abstraction pattern

## Project Structure

```
pidgeon/
├── core/              # Core interfaces and models
├── implementations/   # Queue backend implementations
├── planner/          # LLM Planner component
├── interpreter/      # Message validation component
├── supervisor/       # Monitoring component
├── agents/           # Agent framework
└── gateway/          # LLM Gateway
```

## Specific Contribution Areas

### Adding a New Queue Backend

1. Implement `QueueInterface` in `pidgeon/implementations/`
2. Add configuration in `config/settings.yaml`
3. Update `QueueFactory` to support new backend
4. Add integration tests
5. Update documentation

### Adding a New Agent Type

1. Extend `BaseAgent` in `pidgeon/agents/`
2. Implement `process_task` method
3. Add task type to `TaskType` enum
4. Update routing configuration
5. Add tests and examples

### Adding a New LLM Provider

1. Add provider methods to `LLMGateway`
2. Update configuration schema
3. Add tests with mocked responses
4. Update documentation

## Review Process

1. **Automated checks** run on all PRs:
   - Tests must pass
   - Code coverage must not decrease
   - Linting must pass

2. **Code review** by maintainers:
   - Design and architecture
   - Code quality and style
   - Test coverage
   - Documentation

3. **Approval and merge**:
   - At least one maintainer approval required
   - All checks must pass
   - Branch must be up to date with main

## Questions?

- Reach out to https://www.linkedin.com/in/ken-li-cal/

## License

By contributing, you agree that your contributions will be licensed under the Apache 2.0 License.

---

**Thank you for contributing to Pidgeon Protocol!**

