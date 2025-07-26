# Development Setup Guide

This guide will help you set up a development environment for NewsChecker.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.8+** - [Download Python](https://www.python.org/downloads/)
- **Git** - [Download Git](https://git-scm.com/downloads)
- **Docker & Docker Compose** (optional) - [Download Docker](https://www.docker.com/get-started)

## Quick Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/newschecker/newschecker.git
   cd newschecker
   ```

2. **Run the setup command**:
   ```bash
   make setup
   ```

3. **Configure environment variables**:
   ```bash
   # Edit .env file with your API keys
   cp .env.template .env
   # Add your actual API keys to .env
   ```

4. **Run the application**:
   ```bash
   # Run Telegram bot
   make run-bot
   
   # Or run web interface
   make run-web
   
   # Or run both
   make run-both
   ```

## Detailed Setup

### 1. Environment Setup

Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

Install dependencies:
```bash
# Production dependencies
make install

# Development dependencies
make install-dev
```

### 2. Configuration

Copy the environment template:
```bash
cp .env.template .env
```

Edit `.env` file with your API keys:
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
GEMINI_API_KEY=your_gemini_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_CSE_ID=your_custom_search_engine_id_here
```

### 3. API Keys Setup

#### Telegram Bot Token
1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Create a new bot with `/newbot`
3. Copy the provided token to your `.env` file

#### Google Gemini API Key
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Add to your `.env` file

#### Google Custom Search API
1. Visit [Google Cloud Console](https://console.cloud.google.com/)
2. Enable Custom Search API
3. Create credentials (API key)
4. Set up a Custom Search Engine at [CSE Control Panel](https://cse.google.com/)

### 4. Database Setup

The application uses SQLite by default. The database will be created automatically:
```bash
# Run database migration
make db-migrate
```

### 5. Testing

Run the test suite:
```bash
# Run all tests
make test

# Run tests with coverage
make test

# Run fast tests (exit on first failure)
make test-fast
```

### 6. Code Quality

Format and lint your code:
```bash
# Format code
make format

# Run linting
make lint

# Run all checks
make check
```

## Development Workflow

### 1. Project Structure

The project follows a clean architecture pattern:

```
src/newschecker/
├── __init__.py              # Package initialization
├── main.py                  # Application entry point
├── bot/                     # Telegram bot components
│   ├── __init__.py
│   ├── handlers.py          # Message and command handlers
│   └── commands.py          # Bot command implementations
├── core/                    # Core business logic
│   ├── __init__.py
│   ├── analyzer.py          # Credibility analysis engine
│   ├── database.py          # Database operations
│   ├── cache.py             # Caching system
│   └── search.py            # Search functionality
├── utils/                   # Utility modules
│   ├── __init__.py
│   ├── security.py          # Security validation
│   ├── logging.py           # Enhanced logging
│   ├── rate_limiting.py     # Rate limiting system
│   └── text_processing.py   # Text processing utilities
├── config/                  # Configuration management
│   ├── __init__.py
│   └── settings.py          # Configuration settings
├── web/                     # Web interface
│   ├── __init__.py
│   ├── app.py               # Flask application
│   └── routes.py            # Web routes
└── admin/                   # Administrative functions
    ├── __init__.py
    └── commands.py          # Admin commands
```

### 2. Adding New Features

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Write tests first** (TDD approach):
   ```bash
   # Add tests in tests/ directory
   python -m pytest tests/test_your_feature.py -v
   ```

3. **Implement the feature**:
   - Add your code in the appropriate module
   - Follow the existing code style and patterns
   - Add proper logging and error handling

4. **Test your changes**:
   ```bash
   make test
   make lint
   ```

5. **Submit a pull request**:
   - Ensure all tests pass
   - Add proper documentation
   - Follow the PR template

### 3. Debugging

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
make run-bot
```

Use the development server with auto-reload:
```bash
make dev-bot  # For bot with auto-reload
make dev-web  # For web interface with debug mode
```

### 4. Database Development

View database stats:
```bash
make stats
```

Clean up old data:
```bash
make db-cleanup
```

## Docker Development

### Build and run with Docker:
```bash
# Build the image
make docker-build

# Run with Docker Compose
make docker-run

# View logs
make docker-logs

# Stop containers
make docker-stop
```

### Development with Docker:
```bash
# Get a shell in the container
make docker-shell

# Edit code locally, it will be reflected in the container
# due to volume mounting in docker-compose.yml
```

## Advanced Development

### Performance Profiling

Monitor application performance:
```bash
# Enable performance monitoring
export ENABLE_PERFORMANCE_MONITORING=true

# View performance metrics
python -c "
from src.newschecker.utils.logging import enhanced_logger
print(enhanced_logger.get_performance_metrics())
"
```

### Security Testing

Run security checks:
```bash
make security-check
```

### Dependency Management

Update dependencies:
```bash
make update-deps
```

## Environment Variables

### Required Variables
- `TELEGRAM_BOT_TOKEN` - Telegram bot token
- `GEMINI_API_KEY` - Google Gemini API key
- `GOOGLE_API_KEY` - Google Search API key
- `GOOGLE_CSE_ID` - Google Custom Search Engine ID

### Optional Variables
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `WEB_PORT` - Web interface port (default: 5000)
- `DATABASE_PATH` - Database file path
- `ENABLE_CACHING` - Enable/disable caching
- `ENABLE_RATE_LIMITING` - Enable/disable rate limiting

## Troubleshooting

### Common Issues

1. **Import errors**:
   ```bash
   # Ensure you're in the project directory
   # and have activated the virtual environment
   export PYTHONPATH=.
   ```

2. **API key errors**:
   ```bash
   # Verify your .env file has the correct keys
   make config-check
   ```

3. **Database issues**:
   ```bash
   # Reset database
   rm news_checker.db
   make db-migrate
   ```

### Getting Help

- Check the [troubleshooting guide](troubleshooting.md)
- Review the logs in `logs/` directory
- Join project discussions on GitHub
- Contact the development team

## Code Style Guidelines

- **Python**: Follow PEP 8, use Black for formatting
- **Imports**: Use isort for import organization
- **Type Hints**: Use type hints for better code clarity
- **Documentation**: Add docstrings for all public functions
- **Testing**: Write tests for new features and bug fixes
- **Logging**: Use structured logging with appropriate levels

## Contributing

See [Contributing Guidelines](contributing.md) for detailed information about:
- Code review process
- Commit message conventions
- Pull request guidelines
- Community guidelines 