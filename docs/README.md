# NewsChecker Documentation

Welcome to the NewsChecker documentation! This directory contains comprehensive guides and documentation for the NewsChecker AI-powered news verification system.

## 📚 Documentation Index

### Getting Started
- [Installation Guide](installation.md) - How to install and set up NewsChecker
- [Quick Start](quickstart.md) - Get up and running in minutes
- [Configuration](configuration.md) - Complete configuration reference

### User Guides
- [Using the Telegram Bot](telegram-bot.md) - How to use the Telegram interface
- [Web Interface Guide](web-interface.md) - Using the web dashboard
- [API Reference](api-reference.md) - REST API documentation

### Developer Documentation
- [Project Architecture](architecture.md) - System design and components
- [Development Setup](development.md) - Setting up development environment
- [Contributing Guidelines](contributing.md) - How to contribute to the project
- [Testing Guide](testing.md) - Running and writing tests

### Deployment & Operations
- [Docker Deployment](docker-deployment.md) - Containerized deployment
- [Production Setup](production.md) - Production deployment guide
- [Monitoring & Logging](monitoring.md) - System monitoring and logging
- [Troubleshooting](troubleshooting.md) - Common issues and solutions

### Technical References
- [Project Analysis](project_analysis.md) - Detailed project analysis and improvements
- [Security Guidelines](security.md) - Security best practices
- [Performance Tuning](performance.md) - Optimization guidelines
- [Database Schema](database.md) - Database structure and operations

### Features Documentation
- [Credibility Analysis](credibility-analysis.md) - How the AI analysis works
- [Source Verification](source-verification.md) - Source checking mechanisms
- [Rate Limiting](rate-limiting.md) - Rate limiting system
- [Caching System](caching.md) - Caching mechanisms and strategies

## 🏗️ Project Structure

The NewsChecker project follows a modern Python package structure:

```
NewsChecker/
├── src/
│   └── newschecker/              # Main package
│       ├── __init__.py
│       ├── main.py               # Entry point
│       ├── bot/                  # Telegram bot components
│       ├── core/                 # Core business logic
│       ├── utils/                # Utility modules
│       ├── config/               # Configuration management
│       ├── web/                  # Web interface
│       └── admin/                # Administrative functions
├── tests/                        # Test suite
├── docs/                         # Documentation
├── templates/                    # HTML templates
├── scripts/                      # Utility scripts
├── docker-compose.yml            # Docker orchestration
├── Dockerfile                    # Container definition
├── setup.py                      # Package configuration
├── requirements.txt              # Dependencies
├── Makefile                      # Development commands
└── README.md                     # Main project readme
```

## 🚀 Quick Links

- **Installation**: `make setup` or see [Installation Guide](installation.md)
- **Run Bot**: `make run-bot` or `python -m src.newschecker.main bot`
- **Run Web**: `make run-web` or `python -m src.newschecker.main web`
- **Run Tests**: `make test` or `python -m pytest`
- **Docker**: `make docker-run` or `docker-compose up`

## 🤝 Getting Help

- **Issues**: Report bugs and feature requests on GitHub Issues
- **Discussions**: Join project discussions on GitHub Discussions
- **Email**: Contact the team at info@newschecker.az
- **Documentation**: Browse this docs directory for detailed guides

## 📈 Project Status

NewsChecker is actively developed and maintained. Key features:

- ✅ **Production Ready**: Fully functional Telegram bot and web interface
- ✅ **AI-Powered**: Advanced credibility analysis using Google Gemini
- ✅ **Multi-Modal**: Supports text, URL, and image analysis
- ✅ **Secure**: Comprehensive security validation and rate limiting
- ✅ **Scalable**: Docker deployment with monitoring capabilities
- ✅ **Well-Tested**: Comprehensive test suite with good coverage

## 🔄 Recent Updates

- **v1.0.0**: Complete project restructure with clean architecture
- Enhanced security and rate limiting systems
- Comprehensive monitoring and logging
- Production-ready Docker deployment
- Full test coverage and documentation

---

For the most up-to-date information, please refer to the individual documentation files in this directory. 